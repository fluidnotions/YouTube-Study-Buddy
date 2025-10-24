# Manual Verification: Single Fetch with Auto-Categorization

## Purpose
Verify that auto-categorization only fetches the transcript once.

## Test Procedure

1. **Enable debug logging** to see all transcript fetches:
   ```bash
   uv run yt-study-buddy --debug-logging https://youtu.be/VIDEO_ID
   ```

2. **Check the log output** for transcript fetch calls:
   ```
   # Should see ONLY ONE of these:
   "Fetching transcript for auto-categorization..."
   "Using Tor provider..."
   "✓ Successfully fetched transcript on attempt X"

   # Should NOT see a second fetch in the pipeline:
   "[Job VIDEO_ID] Fetching transcript..."  # Should be skipped!

   # Should see this instead:
   "Using pre-fetched transcript from auto-categorization (skip fetch stage)"
   ```

3. **Expected log pattern**:
   ```
   ✓ Fetching transcript for auto-categorization...
   ✓ Using Tor provider...
   ✓ Successfully fetched transcript (Exit IP: XXX.XXX.XXX.XXX)
   ✓ Auto-categorizing video content...
   ✓ Detected subject: Machine Learning
   ✓ Using pre-fetched transcript from auto-categorization (skip fetch stage)
   ✓ [Job VIDEO_ID] Generating study notes...
   ```

4. **Count transcript fetches** in debug logs:
   ```bash
   grep "Successfully fetched transcript" debug_logs/session_*.log | wc -l
   ```
   **Expected:** 1 (not 2!)

## What Changed

### Before Fix:
- Line 147: `get_transcript()` → Fetch #1
- Pipeline: `fetch_transcript_and_title()` → Fetch #2
- **Result:** Same IP used twice → blocking

### After Fix:
- Line 151: `get_transcript()` → Fetch #1
- Store in `pre_fetched_transcript`
- Set `job.stage = TRANSCRIPT_FETCHED`
- Pipeline: Skips fetch (stage already set)
- **Result:** Single fetch → no blocking

## Success Criteria

✅ Only ONE "Successfully fetched transcript" message in logs
✅ Message "Using pre-fetched transcript from auto-categorization" appears
✅ NO second fetch in pipeline
✅ Job completes successfully with same exit IP

## Failure Indicators

❌ TWO "Successfully fetched transcript" messages
❌ Same exit IP used twice
❌ Second fetch fails with "You will find more information..."
