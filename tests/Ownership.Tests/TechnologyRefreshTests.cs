using System.Globalization;
using System.Runtime.InteropServices;
using System.Text.Json;
using Ownership;
using Xunit;

namespace Ownership.Tests;

// Independent literal migration vectors. Written during source preparation;
// no execution or SDK/runtime qualification is implied by their presence.
public sealed class TechnologyRefreshTests
{
    private const string GoldenDigest = "f358bf35c35bdffee1d3963f19a2364f9e38b054b70953e4ae62c0da0a75c1aa";

    [Fact]
    public void ActualTargetAndRuntimeAreNet11()
    {
        Assert.Equal(".NETCoreApp,Version=v11.0", AppContext.TargetFrameworkName);
        Assert.Equal("11.0.0", Environment.Version.ToString());
        Assert.Equal(Architecture.X64, RuntimeInformation.ProcessArchitecture);
    }

    [Fact]
    public void EffectReceiptWireMatchesIndependentStringValuedLiteral()
    {
        var receipt = new EffectReceipt("op_9007", 1, 9_007_199_254_740_993L, 9_007_199_254_740_995L);
        const string expected = "{\"operationId\":\"op_9007\",\"delta\":\"1\",\"totalAfter\":\"9007199254740993\",\"originalFence\":\"9007199254740995\"}";
        Assert.Equal(expected, JsonSerializer.Serialize(receipt, Contract.Json));
        Assert.Equal(receipt, JsonSerializer.Deserialize<EffectReceipt>(expected, Contract.Json));
    }

    [Fact]
    public void LeaseBeyondDoublePrecisionRetainsExactLiteral()
    {
        using var document = JsonDocument.Parse("{\"lease\":\"9007199254740993\"}");
        Assert.Equal(9_007_199_254_740_993L, Contract.PositiveIntegerString(document.RootElement, "lease"));
    }

    [Fact]
    public void CanonicalInt64RejectsIndependentWrongJsonLiterals()
    {
        string[] frames =
        [
            "{\"lease\":9007199254740993}", "{\"lease\":\"01\"}",
            "{\"lease\":\"+1\"}", "{\"lease\":\" 1\"}",
            "{\"lease\":\"0\"}", "{\"lease\":\"1.0\"}",
            "{\"lease\":\"1e0\"}", "{\"lease\":\"9223372036854775808\"}",
            "{\"lease\":null}", "{\"lease\":true}"
        ];
        foreach (var frame in frames)
        {
            using var document = JsonDocument.Parse(frame);
            var error = Assert.Throws<ContractException>(() => Contract.PositiveIntegerString(document.RootElement, "lease"));
            Assert.Equal("INVALID_INT64_LEASE", error.Code);
        }
    }

    [Fact]
    public void ClusterUInt64BoundaryAndRejectionsStayCanonical()
    {
        Assert.Equal("18446744073709551615", Contract.Cluster("18446744073709551615"));
        foreach (var value in new[] { "", "0", "01", "-1", "1.0", " 1", "18446744073709551616" })
        {
            var error = Assert.Throws<ContractException>(() => Contract.Cluster(value));
            Assert.Equal("INVALID_CLUSTER_LINEAGE", error.Code);
        }
    }

    [Fact]
    public void TotalBoundaryMatchesIndependentIntegerLiterals()
    {
        Assert.Equal<long?>(9_223_372_036_854_775_807L, Contract.AddTotal(9_223_372_036_853_775_807L, 1_000_000));
        Assert.Null(Contract.AddTotal(9_223_372_036_853_775_808L, 1_000_000));
        Assert.Null(Contract.AddTotal(9_223_372_036_854_775_807L, 1));
        Assert.Equal("INVALID_TOTAL_DOMAIN", Assert.Throws<ContractException>(() => Contract.AddTotal(-1, 1)).Code);
    }

    [Fact]
    public void BusinessDigestMatchesIndependentUtf8LfGolden()
    {
        Assert.Equal(GoldenDigest, new BusinessOperation("synthetic-001", 27).Digest());
    }

    [Fact]
    public void CultureChangesCannotAlterWireIntegerOrDigestGolden()
    {
        var previousCulture = CultureInfo.CurrentCulture;
        var previousUiCulture = CultureInfo.CurrentUICulture;
        try
        {
            foreach (var name in new[] { "en-US", "fa-IR", "tr-TR" })
            {
                CultureInfo.CurrentCulture = CultureInfo.GetCultureInfo(name);
                CultureInfo.CurrentUICulture = CultureInfo.GetCultureInfo(name);
                Assert.Equal(GoldenDigest, new BusinessOperation("synthetic-001", 27).Digest());
                using var document = JsonDocument.Parse("{\"lease\":\"9223372036854775807\"}");
                Assert.Equal(long.MaxValue, Contract.PositiveIntegerString(document.RootElement, "lease"));
            }
        }
        finally
        {
            CultureInfo.CurrentCulture = previousCulture;
            CultureInfo.CurrentUICulture = previousUiCulture;
        }
    }

    [Fact]
    public void LiteralLoopbackEndpointBoundariesArePreserved()
    {
        Assert.Equal("http://127.0.0.1:2379/", Contract.Loopback(new Uri("http://127.0.0.1:2379/")).AbsoluteUri);
        foreach (var value in new[] { "http://localhost:2379/", "http://127.0.0.1:2379/?x=1", "http://127.0.0.1:2379/#x", "http://127.0.0.1:80/", "http://user@127.0.0.1:2379/" })
        {
            var error = Assert.Throws<ContractException>(() => Contract.Loopback(new Uri(value)));
            Assert.Equal("LITERAL_LOOPBACK_ENDPOINT_REQUIRED", error.Code);
        }
    }
}
