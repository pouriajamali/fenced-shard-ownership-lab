using System.Globalization;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

namespace Ownership;
/// <summary>A bounded fixture adapter; workers and local endpoints are trusted, not Byzantine.</summary>
public sealed class EtcdGateway
{
    private readonly HttpClient client;
    private readonly Uri endpoint;
    public EtcdGateway(HttpClient client, Uri endpoint)
    {
        this.client = client;
        this.endpoint = Contract.Loopback(endpoint);
    }

    public async Task<Acquisition?> AcquireAsync(string owner, long ttl, CancellationToken cancellationToken)
    {
        Contract.Identity(owner);
        if (ttl is < 1 or > 60)
            throw new ContractException("TTL_OUT_OF_RANGE");
        var grant = await RequestAsync("v3/lease/grant", new { TTL = Format(ttl) }, cancellationToken);
        var leaseId = Contract.PositiveIntegerString(grant, "ID");
        var acknowledgedTtl = Contract.PositiveIntegerString(grant, "TTL");
        if (acknowledgedTtl > 60)
            throw new ContractException("TTL_OUT_OF_RANGE");
        var cluster = HeaderCluster(grant);
        var key = Bytes("/ownership-lab/v1/" + Contract.Shard);
        var transaction = await RequestAsync("v3/kv/txn", new { compare = new[] { new { key, target = "VERSION", version = "0" } }, success = new[] { new { request_put = new { key, value = Bytes(owner), lease = Format(leaseId) } } }, failure = Array.Empty<object>() }, cancellationToken);
        if (HeaderCluster(transaction) != cluster)
            throw new ContractException("CLUSTER_LINEAGE_CHANGED");
        if (!transaction.TryGetProperty("succeeded", out var succeeded) || succeeded.ValueKind != JsonValueKind.True)
            return null;
        var committedRevision = Contract.PositiveIntegerString(Contract.Object(transaction, "header"), "revision");
        var range = await RequestAsync("v3/kv/range", new { key, serializable = false }, cancellationToken);
        if (HeaderCluster(range) != cluster || !range.TryGetProperty("kvs", out var kvs) || kvs.ValueKind != JsonValueKind.Array || kvs.GetArrayLength() != 1)
            throw new ContractException("ACQUISITION_UNCONFIRMED");
        var ownedKey = kvs[0];
        if (Contract.String(ownedKey, "key") != key || Contract.String(ownedKey, "value") != Bytes(owner) || Contract.PositiveIntegerString(ownedKey, "lease") != leaseId || Contract.PositiveIntegerString(ownedKey, "create_revision") != committedRevision)
            throw new ContractException("ACQUISITION_UNCONFIRMED");
        return new Acquisition(owner, cluster, committedRevision, leaseId, acknowledgedTtl).Validate();
    }

    public async Task<bool> RenewAsync(Acquisition acquisition, CancellationToken cancellationToken)
    {
        acquisition.Validate();
        var frame = await RequestAsync("v3/lease/keepalive", new { ID = Format(acquisition.LeaseId) }, cancellationToken, true);
        var result = Contract.Object(frame, "result");
        return HeaderCluster(result) == acquisition.ClusterId && Contract.PositiveIntegerString(result, "ID") == acquisition.LeaseId && Contract.PositiveIntegerString(result, "TTL")is >= 1 and <= 60;
    }

    public async Task ReleaseAsync(Acquisition acquisition, CancellationToken cancellationToken)
    {
        acquisition.Validate();
        var result = await RequestAsync("v3/lease/revoke", new { ID = Format(acquisition.LeaseId) }, cancellationToken);
        if (HeaderCluster(result) != acquisition.ClusterId)
            throw new ContractException("CLUSTER_LINEAGE_CHANGED");
    }

    private async Task<JsonElement> RequestAsync(string path, object body, CancellationToken cancellationToken, bool frame = false)
    {
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(TimeSpan.FromSeconds(3));
        using var request = new HttpRequestMessage(HttpMethod.Post, new Uri(endpoint, path));
        request.Content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json");
        request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
        using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, deadline.Token);
        if (!response.IsSuccessStatusCode)
            throw new ContractException("COORDINATOR_UNAVAILABLE");
        await using var stream = await response.Content.ReadAsStreamAsync(deadline.Token);
        using var bytes = new MemoryStream();
        var buffer = new byte[1];
        while (await stream.ReadAsync(buffer, deadline.Token) != 0)
        {
            if (bytes.Length >= Contract.MaximumFrameBytes)
                throw new ContractException("GATEWAY_FRAME_TOO_LARGE");
            bytes.WriteByte(buffer[0]);
            if (frame && buffer[0] == (byte)'\n')
                break;
        }

        if (bytes.Length == 0)
            throw new ContractException("GATEWAY_EMPTY_FRAME");
        if (frame && bytes.GetBuffer()[bytes.Length - 1] != (byte)'\n')
            throw new ContractException("GATEWAY_INCOMPLETE_FRAME");
        using var document = JsonDocument.Parse(bytes.ToArray(), new JsonDocumentOptions { MaxDepth = 16 });
        if (document.RootElement.ValueKind != JsonValueKind.Object || document.RootElement.TryGetProperty("error", out _))
            throw new ContractException("GATEWAY_ERROR_FRAME");
        RejectDuplicateProperties(document.RootElement);
        return document.RootElement.Clone();
    }

    private static string HeaderCluster(JsonElement parent)
    {
        return Contract.Cluster(Contract.String(Contract.Object(parent, "header"), "cluster_id"));
    }

    private static void RejectDuplicateProperties(JsonElement value)
    {
        if (value.ValueKind == JsonValueKind.Object)
        {
            HashSet<string> keys = new(StringComparer.Ordinal);
            foreach (var property in value.EnumerateObject())
            {
                if (!keys.Add(property.Name))
                    throw new ContractException("DUPLICATE_JSON_PROPERTY");
                RejectDuplicateProperties(property.Value);
            }
        }
        else if (value.ValueKind == JsonValueKind.Array)
            foreach (var item in value.EnumerateArray())
                RejectDuplicateProperties(item);
    }

    private static string Format(long value) => value.ToString(CultureInfo.InvariantCulture);
    private static string Bytes(string value) => Convert.ToBase64String(Encoding.UTF8.GetBytes(value));
}
