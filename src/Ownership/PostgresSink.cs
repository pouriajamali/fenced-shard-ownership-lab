using System.Data;
using System.Text.Json;
using Npgsql;

namespace Ownership;

public sealed class PostgresSink
{
    private readonly NpgsqlDataSource source;
    private readonly ICommitObserver observer;
    private readonly string runId;
    public PostgresSink(NpgsqlDataSource source, string runId, ICommitObserver? observer = null)
    {
        this.source = source; this.runId = Contract.Identity(runId); this.observer = observer ?? new NoCommitObserver();
    }

    public static NpgsqlDataSource OpenLocal(string connectionString)
    {
        var options = new NpgsqlConnectionStringBuilder(connectionString);
        if (options.Host != "127.0.0.1" || options.Port < 1024 || options.Database != "ownership_lab" || options.Username != "ownership_lab")
            throw new ContractException("DEDICATED_LOOPBACK_DATABASE_REQUIRED");
        options.Timeout = 3; options.CommandTimeout = 5; options.MaxPoolSize = 4;
        options.Pooling = true; options.IncludeErrorDetail = false;
        return NpgsqlDataSource.Create(options.ConnectionString);
    }

    public async Task InitializeFreshAsync(CancellationToken token)
    {
        await using var connection = await source.OpenConnectionAsync(token);
        await using var transaction = await connection.BeginTransactionAsync(token);
        await using var create = new NpgsqlCommand("""
            CREATE SCHEMA ownership_lab_v1;
            CREATE TABLE ownership_lab_v1.state (
              shard text PRIMARY KEY CHECK (shard='synthetic-shard'), run_id text NOT NULL,
              cluster_id text NOT NULL, fence bigint NOT NULL CHECK(fence>0), owner text NOT NULL,
              total bigint NOT NULL CHECK(total>=0));
            CREATE TABLE ownership_lab_v1.effects (
              shard text NOT NULL REFERENCES ownership_lab_v1.state(shard), operation_id text NOT NULL,
              request_hash text NOT NULL, receipt text NOT NULL, delta bigint NOT NULL CHECK(delta>0),
              PRIMARY KEY(shard,operation_id));
            """, connection, transaction);
        await create.ExecuteNonQueryAsync(token);
        await transaction.CommitAsync(token);
    }

    public async Task<SinkReply> ActivateAsync(Acquisition acquisition, CancellationToken token)
    {
        acquisition.Validate();
        try
        {
            await using var connection = await source.OpenConnectionAsync(token);
            await using var transaction = await connection.BeginTransactionAsync(IsolationLevel.ReadCommitted, token);
            await using (var insert = new NpgsqlCommand("""
                INSERT INTO ownership_lab_v1.state(shard,run_id,cluster_id,fence,owner,total)
                VALUES($1,$2,$3,$4,$5,0) ON CONFLICT(shard) DO NOTHING
                """, connection, transaction))
            {
                Add(insert, Contract.Shard, runId, acquisition.ClusterId, acquisition.Fence, acquisition.Owner);
                await insert.ExecuteNonQueryAsync(token);
            }
            var state = await LockedStateAsync(connection, transaction, token);
            if (state.RunId != runId || state.ClusterId != acquisition.ClusterId) return new("LINEAGE_MISMATCH");
            if (acquisition.Fence < state.Fence || (acquisition.Fence == state.Fence && acquisition.Owner != state.Owner)) return new("STALE_FENCE");
            await using var update = new NpgsqlCommand("UPDATE ownership_lab_v1.state SET fence=$1,owner=$2 WHERE shard=$3", connection, transaction);
            Add(update, acquisition.Fence, acquisition.Owner, Contract.Shard);
            await update.ExecuteNonQueryAsync(token);
            await observer.ObserveAsync("activation", CommitStage.BeforeCommit, token);
            await transaction.CommitAsync(token);
            await observer.ObserveAsync("activation", CommitStage.AfterCommit, token);
            return new("ACTIVATED");
        }
        catch (Exception error) when (error is NpgsqlException or OperationCanceledException or TimeoutException or IOException)
        { return new("UNKNOWN"); }
    }

    public async Task<SinkReply> ApplyAsync(Acquisition acquisition, BusinessOperation operation, CancellationToken token)
    {
        acquisition.Validate(); var hash = operation.Digest();
        try
        {
            await using var connection = await source.OpenConnectionAsync(token);
            await using var transaction = await connection.BeginTransactionAsync(IsolationLevel.ReadCommitted, token);
            await observer.ObserveAsync("effect", CommitStage.BeforeLock, token);
            var state = await LockedStateAsync(connection, transaction, token);
            if (state.RunId != runId || state.ClusterId != acquisition.ClusterId) return new("LINEAGE_MISMATCH");
            if (state.Fence != acquisition.Fence || state.Owner != acquisition.Owner) return new("STALE_FENCE");
            await using (var lookup = new NpgsqlCommand("SELECT request_hash,receipt FROM ownership_lab_v1.effects WHERE shard=$1 AND operation_id=$2", connection, transaction))
            {
                Add(lookup, Contract.Shard, operation.Id);
                await using var reader = await lookup.ExecuteReaderAsync(token);
                if (await reader.ReadAsync(token))
                    return reader.GetString(0) == hash ? new("REPLAYED", JsonSerializer.Deserialize<EffectReceipt>(reader.GetString(1), Contract.Json)) : new("IDENTITY_CONFLICT");
            }
            var total = Contract.AddTotal(state.Total, operation.Delta);
            if (total is null) return new("OVERFLOW_REJECTED");
            var receipt = new EffectReceipt(operation.Id, operation.Delta, total.Value, acquisition.Fence);
            await using var effect = new NpgsqlCommand("INSERT INTO ownership_lab_v1.effects(shard,operation_id,request_hash,receipt,delta) VALUES($1,$2,$3,$4,$5)", connection, transaction);
            Add(effect, Contract.Shard, operation.Id, hash, JsonSerializer.Serialize(receipt, Contract.Json), operation.Delta);
            await effect.ExecuteNonQueryAsync(token);
            await using var update = new NpgsqlCommand("UPDATE ownership_lab_v1.state SET total=$1 WHERE shard=$2", connection, transaction);
            Add(update, receipt.TotalAfter, Contract.Shard);
            await update.ExecuteNonQueryAsync(token);
            await observer.ObserveAsync("effect", CommitStage.BeforeCommit, token);
            await transaction.CommitAsync(token);
            await observer.ObserveAsync("effect", CommitStage.AfterCommit, token);
            return new("APPLIED", receipt);
        }
        catch (Exception error) when (error is NpgsqlException or OperationCanceledException or TimeoutException or IOException)
        { return new("UNKNOWN"); }
    }

    public async Task<EffectReceipt?> LookupAsync(BusinessOperation operation, CancellationToken token)
    {
        var hash = operation.Digest();
        await using var connection = await source.OpenConnectionAsync(token);
        await using var command = new NpgsqlCommand("""
            SELECT e.request_hash,e.receipt FROM ownership_lab_v1.effects e
            JOIN ownership_lab_v1.state s USING(shard) WHERE s.run_id=$1 AND e.shard=$2 AND e.operation_id=$3
            """, connection);
        Add(command, runId, Contract.Shard, operation.Id);
        await using var reader = await command.ExecuteReaderAsync(token);
        if (!await reader.ReadAsync(token)) return null;
        if (reader.GetString(0) != hash) throw new ContractException("IDENTITY_CONFLICT");
        return JsonSerializer.Deserialize<EffectReceipt>(reader.GetString(1), Contract.Json);
    }

    public async Task<SinkSnapshot?> SnapshotAsync(CancellationToken token)
    {
        await using var connection = await source.OpenConnectionAsync(token);
        await using var command = new NpgsqlCommand("""
            SELECT s.run_id,s.cluster_id,s.fence,s.owner,s.total,
              (SELECT count(*) FROM ownership_lab_v1.effects e WHERE e.shard=s.shard)
            FROM ownership_lab_v1.state s WHERE s.shard=$1
            """, connection);
        Add(command, Contract.Shard);
        await using var reader = await command.ExecuteReaderAsync(token);
        return await reader.ReadAsync(token) ? new(reader.GetString(0), reader.GetString(1), reader.GetInt64(2), reader.GetString(3), reader.GetInt64(4), reader.GetInt64(5)) : null;
    }

    private static async Task<SinkSnapshot> LockedStateAsync(NpgsqlConnection connection, NpgsqlTransaction transaction, CancellationToken token)
    {
        await using var command = new NpgsqlCommand("SELECT run_id,cluster_id,fence,owner,total FROM ownership_lab_v1.state WHERE shard=$1 FOR UPDATE", connection, transaction);
        Add(command, Contract.Shard);
        await using var reader = await command.ExecuteReaderAsync(token);
        if (!await reader.ReadAsync(token)) throw new ContractException("SINK_NOT_ACTIVATED");
        return new(reader.GetString(0), reader.GetString(1), reader.GetInt64(2), reader.GetString(3), reader.GetInt64(4), 0);
    }
    private static void Add(NpgsqlCommand command, params object[] values)
    {
        foreach (var value in values) command.Parameters.AddWithValue(value);
    }
}
