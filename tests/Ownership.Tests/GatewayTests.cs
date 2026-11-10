using System.Net;
using System.Text;
using System.Text.Json;
using Ownership;
using Xunit;

namespace Ownership.Tests;
public sealed class GatewayTests
{
    private static readonly Uri Local = new("http://127.0.0.1:23791/");
    private static string Header(string revision = "9007199254740993") => "\"header\":{\"cluster_id\":\"18446744073709551615\",\"revision\":\"" + revision + "\"}";
    private static string Grant => "{" + Header() + ",\"ID\":\"9007199254740995\",\"TTL\":\"5\"}";
    private static string Acquired => "{" + Header() + ",\"succeeded\":true}";

    private static string Range(string owner = "worker-a", string revision = "9007199254740993", string lease = "9007199254740995") => "{" + Header() + ",\"kvs\":[{\"key\":\"" + Convert.ToBase64String(Encoding.UTF8.GetBytes("/ownership-lab/v1/" + Contract.Shard)) + "\",\"value\":\"" + Convert.ToBase64String(Encoding.UTF8.GetBytes(owner)) + "\",\"lease\":\"" + lease + "\",\"create_revision\":\"" + revision + "\"}]}";
    [Fact]
    public async Task AcquiresExactBeyondDoublePrecisionFromActualOwnedKey()
    {
        using var handler = new ScriptedHandler(Grant, Acquired, Range());
        using var client = new HttpClient(handler);
        var acquisition = await new EtcdGateway(client, Local).AcquireAsync("worker-a", 5, TestContext.Current.CancellationToken);
        Assert.NotNull(acquisition);
        Assert.Equal(9007199254740993L, acquisition.Fence);
        Assert.Equal(9007199254740995L, acquisition.LeaseId);
        Assert.Equal("18446744073709551615", acquisition.ClusterId);
        using var request = JsonDocument.Parse(handler.Bodies[1]);
        Assert.Equal("VERSION", request.RootElement.GetProperty("compare")[0].GetProperty("target").GetString());
        Assert.Equal("0", request.RootElement.GetProperty("compare")[0].GetProperty("version").GetString());
    }

    [Theory]
    [InlineData("other-owner", "9007199254740993", "9007199254740995")]
    [InlineData("worker-a", "9007199254740994", "9007199254740995")]
    [InlineData("worker-a", "9007199254740993", "9007199254740996")]
    public async Task DoesNotActivateUnconfirmedOwnership(string owner, string revision, string lease)
    {
        using var handler = new ScriptedHandler(Grant, Acquired, Range(owner, revision, lease));
        using var client = new HttpClient(handler);
        await Assert.ThrowsAsync<ContractException>(() => new EtcdGateway(client, Local).AcquireAsync("worker-a", 5, TestContext.Current.CancellationToken));
    }

    [Fact]
    public async Task DeniedCompareDoesNotReadOrActivateAnotherOwner()
    {
        using var handler = new ScriptedHandler(Grant, "{" + Header() + ",\"succeeded\":false}");
        using var client = new HttpClient(handler);
        Assert.Null(await new EtcdGateway(client, Local).AcquireAsync("worker-a", 5, TestContext.Current.CancellationToken));
        Assert.Equal(2, handler.Bodies.Count);
    }

    [Theory]
    [InlineData("0")]
    [InlineData("-1")]
    [InlineData("01")]
    [InlineData("9223372036854775808")]
    [InlineData("1.0")]
    [InlineData("1e3")]
    [InlineData(" 1")]
    [InlineData("+1")]
    public async Task LeaseIntegerStringMustBeCanonicalPositiveInt64(string id)
    {
        using var handler = new ScriptedHandler("{" + Header() + ",\"ID\":\"" + id + "\",\"TTL\":\"5\"}");
        using var client = new HttpClient(handler);
        await Assert.ThrowsAsync<ContractException>(() => new EtcdGateway(client, Local).AcquireAsync("worker-a", 5, TestContext.Current.CancellationToken));
    }

    [Fact]
    public async Task NumericJsonDoesNotReplaceExactIntegerStringContract()
    {
        using var handler = new ScriptedHandler("{" + Header() + ",\"ID\":9007199254740995,\"TTL\":\"5\"}");
        using var client = new HttpClient(handler);
        await Assert.ThrowsAsync<ContractException>(() => new EtcdGateway(client, Local).AcquireAsync("worker-a", 5, TestContext.Current.CancellationToken));
    }

    [Theory]
    [InlineData("{\"result\":{\"ID\":\"9007199254740995\",\"TTL\":\"5\"}}\n")]
    [InlineData("{\"result\":{\"header\":{\"cluster_id\":\"18446744073709551615\"},\"ID\":\"9007199254740995\",\"TTL\":\"0\"}}\n")]
    [InlineData("{\"result\":{\"header\":{\"cluster_id\":\"18446744073709551615\"},\"ID\":\"9007199254740995\",\"TTL\":\"5\"}}")]
    [InlineData("{\"error\":\"expired\"}\n")]
    [InlineData("{\"result\":\n")]
    public async Task Http200WithoutCompleteMatchingPositiveRenewalIsNotSuccess(string frame)
    {
        using var handler = new ScriptedHandler(frame);
        using var client = new HttpClient(handler);
        var gateway = new EtcdGateway(client, Local);
        var error = await Record.ExceptionAsync(() => gateway.RenewAsync(new("worker-a", "18446744073709551615", 7, 9007199254740995, 5), TestContext.Current.CancellationToken));
        Assert.True(error is ContractException or JsonException);
    }

    [Fact]
    public async Task RenewalWithOtherLeaseOrClusterIsNotConfirmed()
    {
        foreach (var(cluster, lease)in new[]
        {
            ("42", "9007199254740995"),
            ("18446744073709551615", "2")
        }

        )
        {
            using var handler = new ScriptedHandler("{\"result\":{\"header\":{\"cluster_id\":\"" + cluster + "\"},\"ID\":\"" + lease + "\",\"TTL\":\"5\"}}\n");
            using var client = new HttpClient(handler);
            Assert.False(await new EtcdGateway(client, Local).RenewAsync(new("worker-a", "18446744073709551615", 7, 9007199254740995, 5), TestContext.Current.CancellationToken));
        }
    }

    [Fact]
    public async Task CompleteRenewalKeepsExactLeaseIdentity()
    {
        using var handler = new ScriptedHandler("{\"result\":{\"header\":{\"cluster_id\":\"18446744073709551615\"},\"ID\":\"9007199254740995\",\"TTL\":\"5\"}}\n");
        using var client = new HttpClient(handler);
        Assert.True(await new EtcdGateway(client, Local).RenewAsync(new("worker-a", "18446744073709551615", 7, 9007199254740995, 5), TestContext.Current.CancellationToken));
    }

    [Fact]
    public async Task AmbiguousDuplicateLeaseFieldIsRejected()
    {
        using var handler = new ScriptedHandler("{" + Header() + ",\"ID\":\"1\",\"ID\":\"2\",\"TTL\":\"5\"}");
        using var client = new HttpClient(handler);
        var error = await Assert.ThrowsAsync<ContractException>(() => new EtcdGateway(client, Local).AcquireAsync("worker-a", 5, TestContext.Current.CancellationToken));
        Assert.Equal("DUPLICATE_JSON_PROPERTY", error.Code);
    }

    [Fact]
    public async Task OversizedFrameFailsBeforeParsing()
    {
        using var handler = new ScriptedHandler(new string (' ', Contract.MaximumFrameBytes + 1));
        using var client = new HttpClient(handler);
        var error = await Assert.ThrowsAsync<ContractException>(() => new EtcdGateway(client, Local).AcquireAsync("worker-a", 5, TestContext.Current.CancellationToken));
        Assert.Equal("GATEWAY_FRAME_TOO_LARGE", error.Code);
    }

    private sealed class ScriptedHandler(params string[] frames) : HttpMessageHandler
    {
        public List<string> Bodies { get; } = [];

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            Bodies.Add(await request.Content!.ReadAsStringAsync(cancellationToken));
            return new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(frames[Bodies.Count - 1], Encoding.UTF8, "application/json")
            };
        }
    }
}
