using Ownership;
using Xunit;

namespace Ownership.Tests;

public sealed class ContractTests
{
    [Fact]
    public void CumulativeBoundaryMatchesIndependentUnboundedIntegerArithmetic()
    {
        var random = new Random(20261109);
        foreach (var initial in new[] { 0L, 1L, long.MaxValue - 1, long.MaxValue - 1_000_000, long.MaxValue })
            for (var i = 0; i < 100; i++)
            {
                var delta = random.Next(1, 1_000_001);
                var reference = new System.Numerics.BigInteger(initial) + delta;
                var actual = Contract.AddTotal(initial, delta);
                if (reference > long.MaxValue) Assert.Null(actual);
                else Assert.Equal((long)reference, actual);
            }
    }
    [Theory]
    [InlineData("http://example.com:2379/")]
    [InlineData("http://localhost:2379/")]
    [InlineData("http://2130706433:2379/")]
    [InlineData("http://[::1]:2379/")]
    [InlineData("http://127.0.0.1:2379/private")]
    [InlineData("http://127.0.0.1:2379/?redirect=1")]
    [InlineData("http://127.0.0.1:80/")]
    [InlineData("http://user@127.0.0.1:2379/")]
    public void ExternalOrAmbiguousEndpointsAreRejected(string uri) => Assert.Throws<ContractException>(() => Contract.Loopback(new Uri(uri)));

    [Fact]
    public void ForbiddenIdentityCharactersAreRejectedAtEveryPosition()
    {
        foreach (var forbidden in new[] { ' ', '\n', '\r', '\0', '/', '\\', 'é', '\t', ':', '\u202e' })
            for (var position = 0; position < 12; position++)
                Assert.Throws<ContractException>(() => Contract.Identity(new string('a', position) + forbidden + new string('b', 11 - position)));
        Assert.Throws<ContractException>(() => Contract.Identity(""));
        Assert.Throws<ContractException>(() => Contract.Identity(new string('a', 65)));
    }

    [Fact]
    public void BusinessIdentityDoesNotDependOnGeneration()
    {
        var operation = new BusinessOperation("synthetic-001", 27);
        Assert.Equal(operation.Digest(), new BusinessOperation("synthetic-001", 27).Digest());
        Assert.NotEqual(operation.Digest(), new BusinessOperation("synthetic-001", 28).Digest());
        Assert.NotEqual(operation.Digest(), new BusinessOperation("synthetic-002", 27).Digest());
    }

    [Theory]
    [InlineData(-1)]
    [InlineData(0)]
    [InlineData(1000001)]
    [InlineData(long.MaxValue)]
    public void InvalidDeltaCannotReachStorage(long quantity) => Assert.Throws<ContractException>(() => new BusinessOperation("op", quantity).Digest());

    [Theory]
    [InlineData("Host=localhost;Port=25432;Username=ownership_lab;Database=ownership_lab")]
    [InlineData("Host=127.0.0.1;Port=25432;Username=postgres;Database=ownership_lab")]
    [InlineData("Host=127.0.0.1;Port=25432;Username=ownership_lab;Database=customer")]
    public void SinkCannotTargetAnUnrelatedService(string connection) => Assert.Throws<ContractException>(() => PostgresSink.OpenLocal(connection));
}
