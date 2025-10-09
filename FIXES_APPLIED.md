# YouTube Study Buddy - Fixes Applied

## Summary
Fixed 4 critical bugs preventing proper functionality of the YouTube Study Buddy application.

---

## Bug 1: Missing Assessment Files ❌→✅

### Problem
Assessment files were not being generated when processing videos through the Streamlit web interface.

### Root Cause
The Streamlit app initialized `assessment_generator` but never called it to generate assessment files.

### Fix
Added assessment generation code to `streamlit_app.py:229-242`:
```python
# Generate assessment if enabled
if processor.assessment_generator:
    try:
        status_text.text("📝 Generating assessment...")
        assessment_content = processor.assessment_generator.generate_assessment(
            transcript, study_notes, video_title, original_url
        )
        assessment_filename = processor.assessment_generator.create_assessment_filename(video_title)
        assessment_path = os.path.join(processor.output_dir, assessment_filename)

        with open(assessment_path, 'w', encoding='utf-8') as f:
            f.write(assessment_content)
    except Exception as e:
        st.warning(f"⚠️ Assessment generation failed: {e}")
```

**Files Modified**: `streamlit_app.py`

---

## Bug 2: No Obsidian Links Between Documents ❌→✅

### Problem
Files had no `[[Obsidian Links]]` between related documents, breaking the knowledge graph.

### Root Cause
**Escaped newline characters** in `study_notes_generator.py:137`:
```python
# BEFORE (broken):
markdown_content = f"# {title}\\n\\n[YouTube Video]({video_url})\\n\\n---\\n\\n{study_notes}"
```

This wrote literal `\n\n` text instead of actual newlines, causing:
- Files to contain literal `\n\n` as text
- Title extraction regex to fail (grabbed entire file header as "title")
- ObsidianLinker couldn't match titles between files
- No cross-reference links were created

### Fix Applied
1. **Fixed escaped newlines** in `study_notes_generator.py:137`:
   ```python
   # AFTER (fixed):
   markdown_content = f"# {title}\n\n[YouTube Video]({video_url})\n\n---\n\n{study_notes}"
   ```

2. **Fixed CLI linking** in `cli.py:116-135`:
   - Removed calls to non-existent methods (`obsidian_linker.add_links()`, `knowledge_graph.add_note()`)
   - Now correctly calls `obsidian_linker.process_file(filepath)`

3. **Repaired existing files**:
   - Created and ran `fix_existing_notes.py`
   - Fixed all 7 existing notes in `notes/` directory

**Files Modified**:
- `src/yt_study_buddy/study_notes_generator.py`
- `src/yt_study_buddy/cli.py`

**Files Created**:
- `fix_existing_notes.py` (repair script for existing broken notes)

---

## Bug 3: File Names Using Video IDs Instead of Titles ❌→✅

### Problem
Files were named `Video_50tzzaOvcO0.md` instead of using actual video titles like `Claude Sonnet 4.5 & Claude Code 2.0 Complete Guide.md`

### Root Cause
The `get_video_title()` method in Tor transcript provider was timing out or failing, returning fallback value `f"Video_{video_id}"`. However, Claude's AI was generating notes with the correct title in the content.

### Fix Applied
Added intelligent title extraction in `study_notes_generator.py:129-163`:

```python
@staticmethod
def extract_title_from_notes(study_notes):
    """
    Extract the video title from Claude's generated notes.
    Claude generates notes starting with '# Video Study Notes: <title>'
    """
    import re
    match = re.search(r'^#\s+(?:VIDEO\s+)?[Vv]ideo\s+[Ss]tudy\s+[Nn]otes:\s*(.+)$',
                      study_notes, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None
```

The `create_markdown_file()` method now:
1. First tries to extract title from Claude's generated notes
2. Falls back to the `title` parameter if extraction fails
3. Uses `Video_{video_id}` only as last resort

**Files Modified**: `src/yt_study_buddy/study_notes_generator.py`

---

## Bug 4: Docker Permission Issues ❌→✅

### Problem
Files created by Docker container were owned by `root:root` with no write permissions for host user:
```
-rw-r--r-- 1 root   root   17424 Oct  9 17:56 Video_50tzzaOvcO0.md
```

### Root Cause
Docker containers run as root by default, creating files owned by root when writing to mounted volumes.

### Fix Applied

1. **Updated `docker-compose.yml`**:
   - Fixed incorrect Dockerfile reference (`Dockerfile.app-only` → `Dockerfile`)
   - Added user mapping to run container as host user:
     ```yaml
     user: "${USER_ID:-1000}:${GROUP_ID:-1000}"
     ```

2. **Added user mapping to `.env`**:
   ```bash
   # Docker user mapping
   USER_ID=1000
   GROUP_ID=1000
   ```

3. **Created permission fix script** (`fix_permissions.sh`):
   ```bash
   sudo chown -R justin:justin /home/justin/Documents/vaults/yt_notes/
   ```

**Files Modified**:
- `docker-compose.yml`
- `.env`

**Files Created**:
- `fix_permissions.sh` (to fix existing root-owned files)

---

## How to Apply Fixes

### For Existing Files

1. **Fix permissions on existing Docker-created files**:
   ```bash
   ./scripts/fix_permissions.sh
   ```

2. **Rebuild Docker containers** (to apply user mapping):
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

### For New Videos

All new videos processed will automatically:
- ✅ Generate assessment files
- ✅ Create Obsidian `[[links]]` between related notes
- ✅ Use actual video titles for filenames
- ✅ Create files with correct user permissions

---

## Verification

To verify fixes are working:

1. **Check a generated file**:
   ```bash
   head -20 notes/Your_Video_Title.md
   ```
   Should see:
   - Proper filename (not `Video_<ID>.md`)
   - Proper newlines (not literal `\n\n`)
   - Obsidian links like `[[Other Note Title]]`

2. **Check for assessment file**:
   ```bash
   ls notes/*_Assessment.md
   ```

3. **Check file ownership**:
   ```bash
   ls -la notes/
   ```
   Should show your username, not `root`

---

## Technical Details

### Code Changes Summary
- **4 files modified**: `streamlit_app.py`, `study_notes_generator.py`, `cli.py`, `docker-compose.yml`
- **3 utility scripts created**: `fix_existing_notes.py`, `fix_permissions.sh`, `FIXES_APPLIED.md`
- **~150 lines of code changed/added**

### Testing Performed
- ✅ ObsidianLinker successfully creates links on test notes
- ✅ Knowledge graph extracts concepts from all notes (6 notes, 60 concepts)
- ✅ Title extraction regex tested on generated notes
- ✅ Existing broken notes repaired (7 files fixed)

### Remaining Manual Steps
1. Run `./scripts/fix_permissions.sh` to fix existing file ownership
2. Rebuild Docker containers to apply user mapping
3. Process new videos to verify all fixes work end-to-end

---

## Files Summary

### Modified
- `src/yt_study_buddy/study_notes_generator.py` - Fixed newlines, added title extraction
- `src/yt_study_buddy/cli.py` - Fixed Obsidian linking
- `streamlit_app.py` - Added assessment generation
- `docker-compose.yml` - Fixed Dockerfile reference, added user mapping
- `.env` - Added USER_ID and GROUP_ID

### Created
- `fix_existing_notes.py` - Repairs broken notes with escaped newlines
- `fix_permissions.sh` - Fixes Docker-created file permissions
- `FIXES_APPLIED.md` - This documentation

### Can Be Deleted (cleanup scripts)
- `fix_existing_notes.py` (after running once on existing notes)
