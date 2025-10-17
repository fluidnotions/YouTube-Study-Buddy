# Electron Desktop App Setup

This directory contains the Electron wrapper to run YouTube Study Buddy as a native desktop application.

## Quick Start

### 1. Install Node.js Dependencies

```bash
# From project root
npm install
```

This installs:
- `electron`: Desktop app framework
- `wait-on`: Wait for Streamlit server to start
- `electron-builder`: Build installers (dev dependency)

### 2. Run in Development Mode

```bash
# Start with DevTools open
npm run dev

# Or production mode
npm start
```

### 3. Build Installer

```bash
# Build for current platform
npm run build

# Platform-specific builds
npm run build:linux    # Creates .AppImage and .deb
npm run build:mac      # Creates .dmg
npm run build:win      # Creates .exe installer
```

Output will be in `dist-electron/` directory.

## What Happens When You Run

1. **Electron starts** (`main.js`)
2. **Spawns Streamlit** process: `uv run streamlit run streamlit_app.py`
3. **Waits for server** to respond on http://localhost:8501
4. **Creates window** and loads Streamlit app
5. **On exit**, kills Streamlit process cleanly

## File Structure

```
electron/
├── main.js       # Main process (Node.js)
│                 # - Spawns Streamlit
│                 # - Creates window
│                 # - Handles lifecycle
├── preload.js    # Security bridge (limited APIs)
├── icon.png      # App icon (512x512 PNG)
├── icon.icns     # macOS icon
└── icon.ico      # Windows icon
```

## Requirements

Users need:
- Python 3.13+ (with UV package manager)
- Node.js 18+ (only for development/building)

The built app requires:
- Python + UV installed on user's machine
- All Python dependencies (via `uv sync`)

## Customization

### Change Port

Edit `STREAMLIT_PORT` in `main.js`:

```javascript
const STREAMLIT_PORT = 8502;  // Use different port
```

### Window Size

Edit in `createWindow()`:

```javascript
mainWindow = new BrowserWindow({
  width: 1600,   // Wider
  height: 1000,  // Taller
  // ...
});
```

### App Icon

Replace icon files:
- `icon.png` - Linux/general (512x512)
- `icon.icns` - macOS (create with iconutil)
- `icon.ico` - Windows (256x256 or multiple sizes)

## Building for Distribution

### Linux AppImage (Recommended)

```bash
npm run build:linux
```

Creates: `dist-electron/YouTube Study Buddy-1.0.0.AppImage`

Users can run directly:
```bash
chmod +x YouTube\ Study\ Buddy-1.0.0.AppImage
./YouTube\ Study\ Buddy-1.0.0.AppImage
```

### Debian Package

Also creates `.deb`:
```bash
sudo dpkg -i dist-electron/youtube-study-buddy_1.0.0_amd64.deb
```

## Troubleshooting

### "Streamlit failed to start"

**Problem:** Electron opens but shows connection error

**Check:**
1. Is UV installed? `uv --version`
2. Are dependencies installed? `uv sync`
3. Can Streamlit run manually? `uv run streamlit run streamlit_app.py`
4. Is port 8501 available? `lsof -i :8501`

**Fix:** Increase timeout in `main.js`:
```javascript
const opts = {
  timeout: 60000,  // 60 seconds instead of 30
  // ...
};
```

### "Module 'wait-on' not found"

**Problem:** Node dependencies not installed

**Fix:**
```bash
npm install
```

### Large Bundle Size

**Problem:** `.AppImage` is 300MB+

**Expected:** Electron + Python deps = 150-200MB normally

**Reduce:**
- Use `electron-builder` compression options
- Exclude test files/docs in `package.json` files list
- Consider external Python approach (not bundling Python)

## Development Tips

### Live Reload Streamlit

Streamlit auto-reloads when code changes. Just edit and save!

Reload Electron window: `Ctrl+R` (or Cmd+R on Mac)

### Debug Streamlit Process

Check console for Streamlit output:
```
[Streamlit] Network URL: http://localhost:8501
[Streamlit] External URL: http://192.168.1.x:8501
```

### Enable DevTools

Already enabled in dev mode (`npm run dev`).

In production, add to menu or keyboard shortcut.

## Next Steps

1. **Add app icon**: Replace placeholder icons
2. **Test builds**: Build for your platform
3. **Code signing**: For distribution (macOS/Windows require this)
4. **Auto-updates**: Use electron-updater for production

See main `docs/electron-desktop-app.md` for full guide.
