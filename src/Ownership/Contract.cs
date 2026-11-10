using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Ownership;
public sealed class ContractException(string code) : Exception(code)
{
    public string Code { get; } = code;
}

public static class Contract
{
    public const string Shard = "synthetic-shard";
    public const long MaximumDelta = 1_000_000;
    public const int MaximumFrameBytes = 32_768;
    public static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
    {
        NumberHandling = JsonNumberHandling.WriteAsString | JsonNumberHandling.AllowReadingFromString
    };
    public static string Identity(string value)
    {
        if (value.Length is < 1 or > 64 || value.Any(c => !char.IsAsciiLetterOrDigit(c) && c is not '-' and not '_' and not '.'))
            throw new ContractException("INVALID_IDENTITY");
        return value;
    }

    public static string Cluster(string value)
    {
        if (!ulong.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out var parsed) || parsed == 0 || parsed.ToString(CultureInfo.InvariantCulture) != value)
            throw new ContractException("INVALID_CLUSTER_LINEAGE");
        return value;
    }

    public static Uri Loopback(Uri endpoint)
    {
        if (!endpoint.OriginalString.StartsWith("http://127.0.0.1:", StringComparison.Ordinal) || endpoint.Scheme != "http" || endpoint.Host != "127.0.0.1" || endpoint.Port < 1024 || endpoint.UserInfo.Length != 0 || endpoint.AbsolutePath != "/" || endpoint.Query.Length != 0 || endpoint.Fragment.Length != 0)
            throw new ContractException("LITERAL_LOOPBACK_ENDPOINT_REQUIRED");
        return endpoint;
    }

    public static long PositiveIntegerString(JsonElement parent, string name)
    {
        if (parent.ValueKind != JsonValueKind.Object || !parent.TryGetProperty(name, out var field) || field.ValueKind != JsonValueKind.String || !long.TryParse(field.GetString(), NumberStyles.None, CultureInfo.InvariantCulture, out var value) || value <= 0 || value.ToString(CultureInfo.InvariantCulture) != field.GetString())
            throw new ContractException("INVALID_INT64_" + name.ToUpperInvariant());
        return value;
    }

    public static JsonElement Object(JsonElement parent, string name)
    {
        if (parent.ValueKind != JsonValueKind.Object || !parent.TryGetProperty(name, out var value) || value.ValueKind != JsonValueKind.Object)
            throw new ContractException("INVALID_OBJECT_" + name.ToUpperInvariant());
        return value;
    }

    public static string String(JsonElement parent, string name)
    {
        if (parent.ValueKind != JsonValueKind.Object || !parent.TryGetProperty(name, out var value) || value.ValueKind != JsonValueKind.String)
            throw new ContractException("INVALID_STRING_" + name.ToUpperInvariant());
        return value.GetString()!;
    }

    public static long? AddTotal(long current, long delta)
    {
        if (current < 0 || delta is < 1 or > MaximumDelta)
            throw new ContractException("INVALID_TOTAL_DOMAIN");
        return current > long.MaxValue - delta ? null : checked(current + delta);
    }
}

public sealed record Acquisition(string Owner, string ClusterId, long Fence, long LeaseId, long Ttl)
{
    public Acquisition Validate()
    {
        Contract.Identity(Owner);
        Contract.Cluster(ClusterId);
        if (Fence <= 0 || LeaseId <= 0 || Ttl is < 1 or > 60)
            throw new ContractException("INVALID_ACQUISITION");
        return this;
    }
}

public sealed record BusinessOperation(string Id, long Delta)
{
    public string Digest()
    {
        Contract.Identity(Id);
        if (Delta is < 1 or > Contract.MaximumDelta)
            throw new ContractException("DELTA_OUT_OF_RANGE");
        return Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes("effect-v1\n" + Contract.Shard + "\n" + Id + "\n" + Delta.ToString(CultureInfo.InvariantCulture) + "\n")));
    }
}

public sealed record EffectReceipt(string OperationId, long Delta, long TotalAfter, long OriginalFence);
public sealed record SinkReply(string Status, EffectReceipt? Receipt = null);
public sealed record SinkSnapshot(string RunId, string ClusterId, long Fence, string Owner, long Total, long Operations);
public enum CommitStage
{
    BeforeLock,
    BeforeCommit,
    AfterCommit
}

public interface ICommitObserver
{
    ValueTask ObserveAsync(string operation, CommitStage stage, CancellationToken cancellationToken);
}

public sealed class NoCommitObserver : ICommitObserver
{
    public ValueTask ObserveAsync(string operation, CommitStage stage, CancellationToken cancellationToken) => ValueTask.CompletedTask;
}
