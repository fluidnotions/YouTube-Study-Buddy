# Debug Logging Guide

Comprehensive logging system to analyze title fetching issues and API responses.

## Quick Start

Enable debug logging with the `--debug-logging` flag:

```bash
# Single video with debug logging
yt-study-buddy --debug-logging https://youtube.com/watch?v=xyz

# Parallel processing with debug logging
yt-study-buddy --debug-logging --parallel --workers 3 URL1 URL2 URL3

# With debug_cli.py
# Edit debug_cli.py to include '--debug-logging' in CLI_ARGS
python debug_cli.py
```

## What Gets Logged

### 1. Session Log (`debug_logs/session_TIMESTAMP.log`)
Human-readable log with:
- Title fetch attempts for each video
- HTTP status codes and errors
- Success/failure for each attempt
- Circuit rotations
- Exit IP assignments
- Final results for each video

### 2. API Response Log (`debug_logs/api_responses_TIMESTAMP.jsonl`)
Machine-readable JSONL (one JSON object per line) with:
- Full API request details (URL, video_id, worker)
- HTTP status codes
- Complete response data
- Error messages
- Timestamps
- Attempt numbers

## Analyzing Logs

### Automatic Analysis

At the end of processing, an automatic analysis is displayed:

```
============================================================
API RESPONSE ANALYSIS
============================================================

Total API calls: 9
Successes: 3 (33.3%)
Failures: 6 (66.7%)

By Video:
  2VauS2awvMw: 1/3 successful
    → Failed attempts: 2
  3le-v1Pme44: 1/3 successful
    → Failed attempts: 2
  g80Q1sVtikE: 1/3 successful
    → Failed attempts: 2

By Worker:
  worker-0: 1/3 (33.3% success)
  worker-1: 1/3 (33.3% success)
  worker-2: 1/3 (33.3% success)

By Attempt Number:
  Attempt 1: 3/3 (100.0% success)
  Attempt 2: 0/3 (0.0% success)
  Attempt 3: 0/3 (0.0% success)

Failed Responses Details (6 total):
  2VauS2awvMw (attempt 2, worker worker-0)
    Status: 429, Error: HTTP 429
  ...
```

### Manual Analysis

#### View Session Log
```bash
# Real-time monitoring
tail -f debug_logs/session_*.log

# Search for specific video
grep "2VauS2awvMw" debug_logs/session_*.log

# Find all failures
grep "FAILED" debug_logs/session_*.log

# Count successes
grep "✓ Title fetched" debug_logs/session_*.log | wc -l
```

#### Analyze API Responses with jq
```bash
cd debug_logs

# Pretty-print all responses
cat api_responses_*.jsonl | jq .

# Show only failed requests
cat api_responses_*.jsonl | jq 'select(.success == false)'

# Group by status code
cat api_responses_*.jsonl | jq -r '.status_code' | sort | uniq -c

# Show all HTTP 429 (rate limit) responses
cat api_responses_*.jsonl | jq 'select(.status_code == 429)'

# Extract all successful titles
cat api_responses_*.jsonl | jq -r 'select(.success == true) | .response.title'

# Count attempts by video
cat api_responses_*.jsonl | jq -r '.video_id' | sort | uniq -c

# Show timeline of requests
cat api_responses_*.jsonl | jq -r '[.timestamp, .video_id, .worker, .status_code] | @tsv'
```

## Common Patterns to Look For

### Pattern 1: First Succeeds, Rest Fail
```
Video A: Attempt 1 ✓, Attempt 2 ✗, Attempt 3 ✗
Video B: Attempt 1 ✓, Attempt 2 ✗, Attempt 3 ✗
Video C: Attempt 1 ✓, Attempt 2 ✗, Attempt 3 ✗
```
**Likely cause**: Rate limiting after first request
**Solution**: Increase delays between requests

### Pattern 2: All Workers Fail on Same Video
```
Worker 0: Video A ✗
Worker 1: Video A ✗
Worker 2: Video A ✗
```
**Likely cause**: Video-specific issue (private, deleted, restricted)
**Solution**: Check video availability manually

### Pattern 3: Specific Worker Fails Consistently
```
Worker 0: ✓ ✓ ✓
Worker 1: ✗ ✗ ✗
Worker 2: ✓ ✓ ✓
```
**Likely cause**: Bad Tor exit node for that worker
**Solution**: Force circuit rotation, check exit IP

### Pattern 4: HTTP 429 (Rate Limit)
```
Status: 429, Error: "HTTP 429"
```
**Likely cause**: Too many requests from same IP
**Solution**:
- Ensure unique exit IPs per worker
- Increase delays
- Reduce worker count

### Pattern 5: Timeouts
```
Error: "Timeout after 30.0s"
```
**Likely cause**: Slow Tor circuit or network issues
**Solution**:
- Increase timeout values
- Check Tor connectivity
- Rotate circuit

## Understanding the Logs

### Session Log Format
```
2025-10-17 08:30:15 - yt_study_buddy_debug - INFO - [worker-0] Fetching title for 2VauS2awvMw (attempt 1/3)
2025-10-17 08:30:16 - yt_study_buddy_debug - INFO - [worker-0] ✓ Title fetched for 2VauS2awvMw: 'Video Title Here' (attempt 1, status 200)
2025-10-17 08:30:18 - yt_study_buddy_debug - WARNING - [worker-1] ✗ Title fetch failed for 3le-v1Pme44: status=429, error=HTTP 429 (attempt 2)
2025-10-17 08:30:20 - yt_study_buddy_debug - INFO - [worker-0] FINAL: 2VauS2awvMw → 'Video Title Here' (succeeded after 1 attempt(s))
```

### API Log Format (JSONL)
```json
{
  "timestamp": "2025-10-17T08:30:15.123456",
  "video_id": "2VauS2awvMw",
  "worker": "worker-0",
  "attempt": 1,
  "url": "https://www.youtube.com/oembed?url=...",
  "status_code": 200,
  "success": true,
  "response": {
    "title": "Video Title Here",
    "author_name": "Channel Name",
    "author_url": "https://youtube.com/@channel",
    "type": "video",
    "height": 270,
    "width": 480,
    "version": "1.0",
    "provider_name": "YouTube",
    "provider_url": "https://youtube.com/",
    "thumbnail_height": 360,
    "thumbnail_width": 480,
    "thumbnail_url": "https://i.ytimg.com/vi/...",
    "html": "<iframe ...>"
  },
  "error": null
}
```

## Debugging Workflow

1. **Run with debug logging**:
   ```bash
   yt-study-buddy --debug-logging --parallel <urls>
   ```

2. **Check automatic analysis** at the end of output

3. **Review session log** for high-level overview:
   ```bash
   less debug_logs/session_*.log
   ```

4. **Analyze API responses** for patterns:
   ```bash
   cat debug_logs/api_responses_*.jsonl | jq 'select(.success == false)'
   ```

5. **Identify the issue**:
   - Rate limiting (HTTP 429)?
   - Timeouts?
   - Bad exit IPs?
   - Video-specific issues?

6. **Apply fix** based on pattern found

7. **Test again** with logging enabled

## Example: Diagnosing "First Works, Rest Fail"

```bash
# 1. Run with logging
yt-study-buddy --debug-logging --parallel URL1 URL2 URL3

# 2. Check analysis output - notice pattern:
#    Attempt 1: 100% success
#    Attempt 2-3: 0% success

# 3. Look for HTTP 429 in API log
cat debug_logs/api_responses_*.jsonl | jq 'select(.status_code == 429)'

# 4. Confirmed: Rate limiting after first request

# 5. Check if workers have unique IPs
grep "exit IP" debug_logs/session_*.log

# 6. Solution: If IPs are same, fix Tor pool configuration
#    If IPs are unique, increase delays between requests
```

## Tips

1. **Keep logs organized**: Logs are timestamped, but clean up old logs periodically
2. **Compare runs**: Run same videos with different settings, compare logs
3. **Monitor in real-time**: Use `tail -f` to watch logs as they happen
4. **Export for sharing**: JSONL format is easy to share with others
5. **Automate analysis**: Write scripts to parse JSONL for custom analysis

## Log Files Location

```
debug_logs/
├── session_20251017_083015.log        # Human-readable session log
├── api_responses_20251017_083015.jsonl # Machine-readable API data
├── session_20251017_091234.log        # Next session
└── api_responses_20251017_091234.jsonl
```

## Cleanup

```bash
# Remove old logs (older than 7 days)
find debug_logs/ -name "*.log" -mtime +7 -delete
find debug_logs/ -name "*.jsonl" -mtime +7 -delete

# Remove all logs
rm -rf debug_logs/
```

---

**Use this logging to identify exactly when and why title fetching fails!** 🔍
