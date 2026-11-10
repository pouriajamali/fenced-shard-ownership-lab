using System.Diagnostics;
using System.Text.Json;
using OpenTelemetry;
using OpenTelemetry.Trace;
using Ownership;

internal static class LabTelemetry
{
    internal static readonly ActivitySource Source = new("OwnershipLab");
    internal static TracerProvider? Create() => Environment.GetEnvironmentVariable("OWNERSHIP_LAB_TELEMETRY") == "1" ? Sdk.CreateTracerProviderBuilder().AddSource("OwnershipLab").SetSampler(new AlwaysOnSampler()).AddProcessor(new SimpleActivityExportProcessor(new RedactedExporter())).Build() : null;
    // Whitelist fields: no SQL, identities, payloads, endpoints or connection strings.
    private sealed class RedactedExporter : BaseExporter<Activity>
    {
        public override ExportResult Export(in Batch<Activity> batch)
        {
            foreach (var activity in batch)
                Console.Error.WriteLine(JsonSerializer.Serialize(new { signal = "trace", operation = activity.OperationName, traceId = activity.TraceId.ToHexString(), status = activity.Status.ToString(), durationTicks = activity.Duration.Ticks }, Contract.Json));
            return ExportResult.Success;
        }
    }
}
