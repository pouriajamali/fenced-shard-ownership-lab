using System.Globalization;
using System.Text.Json;
using Ownership;

return await RunAsync(args);

static async Task<int> RunAsync(string[] args)
{
    if (args.Length == 0 || args[0] == "--help")
    {
        Console.WriteLine("Ownership Lab: acquire ENDPOINT OWNER TTL | renew ENDPOINT OWNER CLUSTER FENCE LEASE TTL | release ENDPOINT OWNER CLUSTER FENCE LEASE TTL | init RUN | activate RUN OWNER CLUSTER FENCE LEASE TTL | apply RUN OWNER CLUSTER FENCE LEASE TTL OPERATION DELTA | lookup RUN OPERATION DELTA | snapshot RUN");
        Console.WriteLine("Synthetic literal-loopback only. Sink uses OWNERSHIP_LAB_DB; effects may be UNKNOWN after disconnect. --help does not connect.");
        return 0;
    }
    using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(15));
    if (args.Length == 1 && args[0] == "--version")
    {
        Emit(new { product = "fenced-shard-ownership-lab", version = System.Reflection.Assembly.GetExecutingAssembly().GetCustomAttributes(typeof(System.Reflection.AssemblyInformationalVersionAttribute), false).Cast<System.Reflection.AssemblyInformationalVersionAttribute>().Single().InformationalVersion });
        return 0;
    }
    try
    {
        object? result;
        var action = args[0];
        using var tracing = LabTelemetry.Create();
        using var activity = LabTelemetry.Source.StartActivity("ownership." + (action is "acquire" or "renew" or "release" or "init" or "activate" or "apply" or "lookup" or "snapshot" ? action : "invalid"));
        if (action == "acquire" && args.Length == 4)
        {
            using var client = Client();
            result = await new EtcdGateway(client, new Uri(args[1])).AcquireAsync(args[2], Number(args[3]), deadline.Token);
            Emit(result ?? new { status = "ACQUISITION_DENIED" }); return result is null ? 3 : 0;
        }
        if (action is "renew" or "release" && args.Length == 7)
        {
            using var client = Client(); var gateway = new EtcdGateway(client, new Uri(args[1]));
            var acquisition = From(args, 2);
            if (action == "renew") result = new { status = await gateway.RenewAsync(acquisition, deadline.Token) ? "RENEWED" : "RENEWAL_UNCONFIRMED" };
            else { await gateway.ReleaseAsync(acquisition, deadline.Token); result = new { status = "RELEASED" }; }
            Emit(result); return 0;
        }
        await using var source = PostgresSink.OpenLocal(Environment.GetEnvironmentVariable("OWNERSHIP_LAB_DB") ?? throw new ContractException("DATABASE_ENV_REQUIRED"));
        var run = args.Length > 1 ? args[1] : throw new ContractException("ARGUMENTS_REQUIRED");
        var sink = new PostgresSink(source, run, new FixtureObserver());
        if (action == "init" && args.Length == 2) { await sink.InitializeFreshAsync(deadline.Token); result = new { status = "INITIALIZED_FRESH" }; }
        else if (action == "activate" && args.Length == 7) result = await sink.ActivateAsync(From(args, 2), deadline.Token);
        else if (action == "apply" && args.Length == 9) result = await sink.ApplyAsync(From(args, 2), new BusinessOperation(args[7], Number(args[8])), deadline.Token);
        else if (action == "lookup" && args.Length == 4) result = await sink.LookupAsync(new BusinessOperation(args[2], Number(args[3])), deadline.Token);
        else if (action == "snapshot" && args.Length == 2) result = await sink.SnapshotAsync(deadline.Token);
        else throw new ContractException("INVALID_ARGUMENTS");
        Emit(result);
        return result is SinkReply reply && reply.Status == "UNKNOWN" ? 4 : 0;
    }
    catch (Exception error) when (error is ContractException or FormatException or OverflowException or JsonException or ArgumentException or HttpRequestException or OperationCanceledException or Npgsql.NpgsqlException or IOException)
    {
        // Never write connection strings, server error text or environment secrets into a public receipt.
        Emit(new { status = "ERROR", code = error is ContractException contract ? contract.Code : error.GetType().Name });
        return 2;
    }
}

static HttpClient Client() => new(new SocketsHttpHandler { AllowAutoRedirect = false, UseProxy = false }) { Timeout = Timeout.InfiniteTimeSpan };
static Acquisition From(string[] args, int start) => new Acquisition(args[start], args[start + 1], Number(args[start + 2]), Number(args[start + 3]), Number(args[start + 4])).Validate();
static long Number(string text) => long.Parse(text, NumberStyles.None, CultureInfo.InvariantCulture);
static void Emit(object? value)
{
    var payload = JsonSerializer.SerializeToElement(value, Contract.Json);
    var status = payload.ValueKind == JsonValueKind.Object && payload.TryGetProperty("status", out var result) ? result.GetString() : null;
    System.Diagnostics.Activity.Current?.SetStatus(status is "UNKNOWN" or "ERROR" ? System.Diagnostics.ActivityStatusCode.Error : System.Diagnostics.ActivityStatusCode.Ok);
    Console.WriteLine(payload.GetRawText());
}

// The pause hook is an explicit owned-child test fixture, never a retry or external process control.
sealed class FixtureObserver : ICommitObserver
{
    public async ValueTask ObserveAsync(string operation, CommitStage stage, CancellationToken cancellationToken)
    {
        var requested = Environment.GetEnvironmentVariable("OWNERSHIP_LAB_PAUSE");
        if (requested != operation + ":" + stage) return;
        var root = Environment.GetEnvironmentVariable("OWNERSHIP_LAB_HOOK_DIR") ?? throw new ContractException("HOOK_DIR_REQUIRED");
        if (!Path.IsPathFullyQualified(root) || !Directory.Exists(root)) throw new ContractException("EXISTING_ABSOLUTE_HOOK_DIR_REQUIRED");
        var ready = Path.Combine(root, "ready");
        await using (var file = new FileStream(ready, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
        { await file.WriteAsync(System.Text.Encoding.UTF8.GetBytes(operation + ":" + stage), cancellationToken); await file.FlushAsync(cancellationToken); }
        while (!File.Exists(Path.Combine(root, "continue"))) await Task.Delay(25, cancellationToken);
    }
}
