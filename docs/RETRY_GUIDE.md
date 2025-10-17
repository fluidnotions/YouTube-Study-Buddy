# Retry Failed Jobs Guide

## Overview

The retry system automatically retries failed video processing jobs at regular intervals, solving the common problem of temporary YouTube IP blocks and rate limits causing permanent failures.

## How It Works

### Automatic Classification

When a job fails, it's automatically classified as either:

**Retryable** (temporary failures):
- YouTube IP blocking / rate limits
- Network timeouts
- Connection errors
- Tor circuit failures

**Non-Retryable** (permanent failures):
- No subtitles/transcripts available
- Video is private or deleted
- Invalid video ID
- Members-only content

### Retry Scheduling

- Default retry interval: **15 minutes**
- Jobs are retried indefinitely until success or permanent failure
- Each retry attempt is logged with timestamps
- Retry count is tracked for analysis

## Usage

### Check Status of Failed Jobs

```bash
python retry_failed_jobs.py --status
```

Shows:
- Total failed jobs
- Retryable vs non-retryable breakdown
- Time until next retry for each job
- Retry attempt count

Example output:
```
📊 FAILED JOBS STATUS
============================================================
Total failed:        4
Retryable:           3
Non-retryable:       1
Ready to retry now:  2

🔄 RETRYABLE JOBS (3)
------------------------------------------------------------
  3Mg5pAg5ZLs
    Error: Could not get transcript: Both Tor and yt-dlp failed
    Retries: 1
    Next retry: in 12 minutes
```

### One-Time Retry

Retry all eligible jobs once:

```bash
python retry_failed_jobs.py
```

Use this when:
- You've fixed Tor connection issues
- YouTube blocks have likely expired
- You want manual control over retry timing

### Continuous Monitoring (Recommended)

Run continuously and auto-retry every 15 minutes:

```bash
python retry_failed_jobs.py --watch
```

This mode:
- Runs in background checking for failed jobs
- Automatically retries when interval expires
- Logs all retry attempts
- Press Ctrl+C to stop

### Custom Retry Interval

Change the retry interval (in minutes):

```bash
python retry_failed_jobs.py --watch --interval 30  # 30 minutes
python retry_failed_jobs.py --watch --interval 5   # 5 minutes (aggressive)
```

**Recommended intervals:**
- **15 minutes**: Default, good balance
- **30 minutes**: Conservative, less likely to hit rate limits
- **5-10 minutes**: Aggressive, use when YouTube is not blocking

## Integration with Processing Pipeline

The retry system works with the existing processing log (`notes/processing_log.json`):

1. **Job fails**: Logged with error message
2. **Retry metadata added**: `retry_count`, `next_retry_time`, `is_retryable`
3. **Scheduler checks log**: Finds jobs ready for retry
4. **Job retried**: Full processing pipeline re-run
5. **Result logged**: Success or new retry scheduled

## Viewing Retry Metadata

The processing log includes retry fields for each job:

```json
{
  "video_id": "abc123",
  "error": "Could not get transcript: Both Tor and yt-dlp fallback failed",
  "retry_count": 2,
  "last_retry_time": 1760694607.052,
  "next_retry_time": 1760695507.052,
  "is_retryable": true
}
```

## Best Practices

### For High Success Rate

1. **Run in watch mode**: Set it and forget it
   ```bash
   nohup python retry_failed_jobs.py --watch > retry.log 2>&1 &
   ```

2. **Check status periodically**: Monitor progress
   ```bash
   python retry_failed_jobs.py --status
   ```

3. **Restart Tor occasionally**: Fresh exit nodes help
   ```bash
   sudo systemctl restart tor
   ```

### For Debugging

1. **Check logs**: View retry attempts
   ```bash
   tail -f notes/processing_log.json
   ```

2. **Manual retry test**: Test single job
   ```bash
   python retry_failed_jobs.py  # One-time retry
   ```

## Troubleshooting

### All Retries Failing

**Symptom**: Jobs keep failing with same error

**Solutions**:
1. Check Tor is running: `sudo systemctl status tor`
2. Restart Tor: `sudo systemctl restart tor`
3. Check exit nodes: Review `notes/exit_nodes.json`
4. Increase interval: `--interval 30` for less aggressive retry

### Jobs Not Being Retried

**Symptom**: Status shows "Not yet scheduled"

**Solution**: Run retry once to schedule them:
```bash
python retry_failed_jobs.py
```

### Too Many Rate Limits

**Symptom**: Consistent "YouTube blocking" errors

**Solutions**:
1. Increase retry interval to 30+ minutes
2. Reduce parallel workers in main processing
3. Wait longer between processing batches
4. Restart Tor for fresh exit nodes

## Performance Tips

- **Batch processing**: Process fewer videos at once to avoid blocks
- **Off-peak hours**: Run retries during YouTube off-peak times
- **Monitor exit nodes**: Track which exit IPs get blocked
- **Progressive backoff**: Failed retries could increase interval (future enhancement)

## Future Enhancements

Potential improvements:
- [ ] Progressive backoff (increase interval after each failure)
- [ ] Max retry limit (stop after N attempts)
- [ ] Success rate tracking per video
- [ ] Integration with systemd timer (cron-like scheduling)
- [ ] Slack/Discord notifications for retry status
