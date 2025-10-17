# Tor Exit Node FAQ

## How Tor Exit Nodes Work

### What is a Tor Exit Node?

A **Tor exit node** is the last relay in a Tor circuit before traffic reaches the internet. When you make a request through Tor:

```
Your App → Tor Entry → Tor Middle → Tor Exit → YouTube
```

YouTube sees the **exit node's IP address**, not yours.

### How Many Exit Nodes Exist?

- **~1,200-1,500 active exit nodes** worldwide at any time
- Constantly changing as volunteers add/remove nodes
- Each has different bandwidth and policies
- Some block certain ports or services

### Can You Reuse Exit Nodes?

**YES** - but with limitations:

#### Short-term (Same Session)
- ✅ **You CAN hold a circuit open** for extended periods
- Tor will keep the same circuit (same 3 relays) until:
  - You request a new circuit (`NEWNYM` signal)
  - Circuit expires (~10 minutes by default)
  - Node goes offline

#### Long-term (Across Sessions)
- ❌ **You CANNOT guarantee the same exit** after app restart
- ❌ **You CANNOT "reserve" an exit node** for an hour
- ✅ **You CAN track which exits to avoid** (what our tracker does)

## Our Implementation

### What We Do

1. **Check exit IP** when acquiring a connection
2. **Rotate circuit** if exit IP is:
   - Already in use by another active worker
   - Used within the last hour (tracked in `notes/exit_nodes.json`)
3. **Record usage** with timestamp for cooldown enforcement
4. **Persist across restarts** - the tracker survives app termination

### What We DON'T Do

- ❌ Reserve specific exit nodes in advance
- ❌ Hold circuits open for an hour
- ❌ Control which exit node Tor selects (Tor decides randomly)

### How Circuit Rotation Works

```python
# Worker gets a connection from pool
with pool.acquire(worker_id=1) as fetcher:
    # Pool checks current exit IP
    exit_ip = get_exit_ip()  # e.g., "185.220.101.1"

    # Is this IP in cooldown? (used < 1 hour ago)
    if not tracker.is_available(exit_ip):
        # YES - rotate to get a different exit
        fetcher.rotate_tor_circuit()
        # Tor picks a NEW random exit from ~1,200 available
        exit_ip = get_exit_ip()  # e.g., "109.70.100.6"

    # Record this exit IP with timestamp
    tracker.record_use(exit_ip, worker_id=1)

    # Use this exit for all requests in this session
    fetcher.fetch_transcript(video_id)
```

## Common Scenarios

### Scenario 1: Fresh Start (No History)

```
Worker 1: Gets random exit → 185.220.101.1 ✓
Worker 2: Gets random exit → 109.70.100.6 ✓
Worker 3: Gets random exit → 185.220.101.1 ⚠️  (collision!)
  → Rotates → 199.249.230.77 ✓
```

### Scenario 2: Restarting After 30 Minutes

```
Previous run used:
- 185.220.101.1 (30 min ago)
- 109.70.100.6 (30 min ago)
- 199.249.230.77 (30 min ago)

New run:
Worker 1: Gets 185.220.101.1 ⚠️  (in cooldown, 30m remaining)
  → Rotates → 176.10.99.200 ✓
Worker 2: Gets 109.70.100.6 ⚠️  (in cooldown)
  → Rotates → 185.220.102.19 ✓
```

### Scenario 3: Control Port Unavailable

```
Worker 1: Tries to rotate circuit
  → ConnectionRefusedError
  → Marks control port unavailable
  → Uses whatever exit Tor gives (no rotation)

Worker 2: Sees control port unavailable
  → Skips rotation entirely
  → Faster startup, but may reuse exits
```

## Limitations & Trade-offs

### Why Not Hold Circuits Open for 1 Hour?

**Problem**: Tor circuits are designed to rotate every ~10 minutes for anonymity.

**If we tried**:
- Circuit would expire anyway (~10 min)
- Exit node might go offline
- Wastes resources keeping idle connections
- Doesn't scale (1,200 exits / 3 workers = 400 videos max before exhaustion)

### Why Not Pre-allocate Exit Nodes?

**Problem**: Tor chooses exits randomly based on:
- Bandwidth availability
- Geographic distribution
- Exit policies
- Load balancing

**We can't**:
- Tell Tor "use exit 185.220.101.1"
- Reserve exits for future use
- Guarantee we won't see the same exit twice

**We CAN**:
- Check the exit we got
- Rotate if it's unacceptable
- Track history to avoid recent reuse

## Configuration

### Cooldown Period

```python
pool = TorExitNodePool(
    pool_size=3,
    cooldown_hours=1.0  # Don't reuse exits within 1 hour
)
```

**Trade-offs**:
- **Longer cooldown**: Better rate limit avoidance, but may exhaust exits
- **Shorter cooldown**: More exits available, but higher risk of detection

### Max Rotation Attempts

```python
pool = TorExitNodePool(
    max_rotation_attempts=10  # Try 10 times to get unique exit
)
```

**If all attempts fail**:
- Proceeds with whatever exit it has (may be in cooldown)
- Better than blocking forever
- Logs warning for monitoring

## Monitoring

### Check Pool Stats

```python
stats = pool.get_stats()
print(stats)
```

Output:
```json
{
  "pool_size": 3,
  "in_use": 3,
  "available": 0,
  "active_exit_ips": ["185.220.101.1", "109.70.100.6", "199.249.230.77"],
  "unique_exit_ips": 3,
  "all_unique": true,
  "tracker": {
    "total_tracked": 47,
    "in_cooldown": 12,
    "available": 35,
    "cooldown_hours": 1.0
  }
}
```

### Check Exit Node Log

```bash
cat notes/exit_nodes.json | jq '.'
```

```json
{
  "185.220.101.1": {
    "first_seen": "2025-10-17T14:30:45.123456",
    "last_used": "2025-10-17T15:45:30.789012",
    "use_count": 3,
    "last_worker_id": 2
  }
}
```

### Find IPs in Cooldown

```bash
cat notes/exit_nodes.json | jq 'to_entries |
  map(select((now - (.value.last_used | fromdateiso8601)) < 3600)) |
  from_entries'
```

## Best Practices

### For Production

1. **Use Docker with multiple Tor instances**:
   ```yaml
   tor1: ports: ["9050:9050", "9051:9051"]
   tor2: ports: ["9052:9050", "9053:9051"]
   tor3: ports: ["9054:9050", "9055:9051"]
   ```

2. **Enable control ports** for circuit rotation

3. **Monitor tracker stats** to ensure unique exits

4. **Set appropriate cooldown** (1 hour recommended for YouTube)

### For Development

1. **Single Tor instance** works fine
2. **Control port optional** (rotation helps but isn't critical)
3. **Tracker still tracks** even without rotation

## Troubleshooting

### "Many exit nodes are being reused"

**Causes**:
- Control port unavailable → can't rotate
- Not enough exit nodes available for your pool size
- Cooldown expired (>1 hour since last use)

**Solutions**:
- Enable Tor control port (see `docs/docker.md`)
- Reduce parallel workers
- Increase `max_rotation_attempts`

### "INFO:stem:Error while receiving a control message"

**Cause**: Tor control port not running or not accessible

**Solutions**:
- Start Tor with control port enabled
- Check `tor_control_port` setting
- App will disable rotation and use fixed exits (degraded mode)

### "Could not obtain unique exit IP after 10 attempts"

**Cause**: Pool exhaustion - all available exits already in use or cooldown

**Solutions**:
- Reduce `pool_size` (fewer parallel workers)
- Reduce `cooldown_hours` (allow faster reuse)
- Wait for exits to expire from cooldown

## Summary

**What the tracker does**:
- ✅ Prevents using same exit within 1 hour
- ✅ Works across app restarts
- ✅ Rotates circuits to find unique exits
- ✅ Logs all exit usage with timestamps

**What it doesn't do**:
- ❌ Reserve exits in advance
- ❌ Hold circuits open for hours
- ❌ Control which exit Tor selects
- ❌ Guarantee 100% unique exits (Tor's randomness limits this)

**Result**: Best-effort exit diversity with persistent cooldown tracking
