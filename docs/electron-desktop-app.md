# Wrapping Streamlit App as Electron Desktop App

## Overview

**Difficulty: EASY** (2-3 hours for first-time setup)

Electron wraps your Streamlit app in a native desktop window with:
- Native OS window decorations
- System tray integration
- Auto-start Streamlit server
- Clean shutdown handling
- Cross-platform (Windows, macOS, Linux)

## How It Works

```
┌─────────────────────────────────────┐
│   Electron Desktop Window           │
│  ┌───────────────────────────────┐  │
│  │   Chromium Browser            │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  Streamlit App          │  │  │
│  │  │  (localhost:8501)       │  │  │
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
│                                     │
│  Node.js spawns Python process:    │
│  > uv run streamlit run app.py     │
└─────────────────────────────────────┘
```

## Quick Start

### Prerequisites

```bash
# Install Node.js (if not already installed)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version  # Should be v18+
npm --version
```

### Option 1: Using Electron-Packager (Recommended)

**Pros**: Simple, fast, good for development
**Cons**: Manual updates, basic installer

```bash
# Navigate to project root
cd /path/to/ytstudybuddy

# Initialize electron project
npm init -y

# Install dependencies
npm install --save-dev electron electron-packager
```

### Option 2: Using Electron-Builder (Production)

**Pros**: Auto-updates, professional installers (MSI, DMG, AppImage)
**Cons**: More complex setup

```bash
npm install --save-dev electron electron-builder
```

### Option 3: Using PyInstaller + Electron (Fully Standalone)

**Pros**: No Python required on user's machine
**Cons**: Large bundle size (200-300MB), complex build

## Implementation

### Step 1: Create Package Structure

```
ytstudybuddy/
├── electron/
│   ├── main.js           # Electron main process
│   ├── preload.js        # Security preload script
│   ├── icon.png          # App icon (512x512)
│   └── icon.icns         # macOS icon
├── streamlit_app.py      # Your Streamlit app
├── package.json          # Node.js config
└── electron-builder.yml  # Builder config (optional)
```

### Step 2: Create main.js

```javascript
// electron/main.js
const { app, BrowserWindow, Menu, Tray } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const waitOn = require('wait-on');

let mainWindow;
let streamlitProcess;
const STREAMLIT_PORT = 8501;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'icon.png'),
    title: 'YouTube Study Buddy'
  });

  // Load Streamlit after server starts
  mainWindow.loadURL(`http://localhost:${STREAMLIT_PORT}`);

  // Open DevTools in development
  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
  }
}

function startStreamlit() {
  console.log('Starting Streamlit server...');

  // Spawn Streamlit process
  streamlitProcess = spawn('uv', [
    'run',
    'streamlit',
    'run',
    'streamlit_app.py',
    '--server.port',
    STREAMLIT_PORT.toString(),
    '--server.headless',
    'true',
    '--browser.gatherUsageStats',
    'false'
  ], {
    cwd: path.join(__dirname, '..'),
    shell: true
  });

  streamlitProcess.stdout.on('data', (data) => {
    console.log(`Streamlit: ${data}`);
  });

  streamlitProcess.stderr.on('data', (data) => {
    console.error(`Streamlit Error: ${data}`);
  });

  streamlitProcess.on('close', (code) => {
    console.log(`Streamlit process exited with code ${code}`);
  });

  // Wait for Streamlit to be ready
  const opts = {
    resources: [`http://localhost:${STREAMLIT_PORT}`],
    delay: 1000,
    timeout: 30000,
    interval: 100
  };

  waitOn(opts)
    .then(() => {
      console.log('Streamlit is ready!');
      createWindow();
    })
    .catch((err) => {
      console.error('Streamlit failed to start:', err);
      app.quit();
    });
}

app.whenReady().then(() => {
  startStreamlit();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  // Kill Streamlit process on exit
  if (streamlitProcess) {
    streamlitProcess.kill();
  }
});
```

### Step 3: Create preload.js

```javascript
// electron/preload.js
const { contextBridge } = require('electron');

// Expose safe APIs to renderer
contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  version: process.versions.electron
});
```

### Step 4: Update package.json

```json
{
  "name": "youtube-study-buddy",
  "version": "1.0.0",
  "description": "YouTube Study Notes Generator",
  "main": "electron/main.js",
  "scripts": {
    "start": "electron .",
    "dev": "NODE_ENV=development electron .",
    "build": "electron-builder",
    "build:win": "electron-builder --win",
    "build:mac": "electron-builder --mac",
    "build:linux": "electron-builder --linux"
  },
  "build": {
    "appId": "com.yourdomain.youtube-study-buddy",
    "productName": "YouTube Study Buddy",
    "directories": {
      "output": "dist"
    },
    "files": [
      "electron/**/*",
      "streamlit_app.py",
      "src/**/*",
      "notes/**/*",
      "pyproject.toml",
      "uv.lock"
    ],
    "linux": {
      "target": ["AppImage", "deb"],
      "category": "Education"
    },
    "mac": {
      "target": "dmg",
      "category": "public.app-category.education"
    },
    "win": {
      "target": ["nsis", "portable"],
      "icon": "electron/icon.ico"
    }
  },
  "dependencies": {
    "wait-on": "^7.0.1"
  },
  "devDependencies": {
    "electron": "^28.0.0",
    "electron-builder": "^24.9.1"
  }
}
```

### Step 5: Install Additional Dependencies

```bash
npm install --save wait-on
npm install --save-dev electron electron-builder
```

### Step 6: Run Development Build

```bash
# Start in dev mode (with DevTools)
npm run dev

# Or production mode
npm start
```

### Step 7: Build Installers

```bash
# Build for current platform
npm run build

# Build for specific platform
npm run build:linux    # Creates .AppImage and .deb
npm run build:mac      # Creates .dmg
npm run build:win      # Creates .exe installer
```

## Advanced: Fully Standalone (No Python Required)

Use PyInstaller to bundle Python + dependencies into executable:

### Step 1: Create PyInstaller Spec

```python
# youtube_study_buddy.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['streamlit_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src', 'src'),
        ('.streamlit', '.streamlit'),
    ],
    hiddenimports=[
        'streamlit',
        'anthropic',
        'youtube_transcript_api',
        'sentence_transformers',
        'weasyprint',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='youtube-study-buddy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='youtube-study-buddy',
)
```

### Step 2: Build PyInstaller Bundle

```bash
# Install PyInstaller
uv pip install pyinstaller

# Build standalone executable
uv run pyinstaller youtube_study_buddy.spec

# Output in dist/youtube-study-buddy/
```

### Step 3: Update main.js for Bundled Python

```javascript
function startStreamlit() {
  const pythonPath = app.isPackaged
    ? path.join(process.resourcesPath, 'python', 'youtube-study-buddy')
    : 'uv';

  const args = app.isPackaged
    ? ['run', 'streamlit_app.py']
    : ['run', 'streamlit', 'run', 'streamlit_app.py'];

  streamlitProcess = spawn(pythonPath, args, { /* ... */ });
}
```

## Pros & Cons Comparison

### Simple Electron Wrapper (Recommended)

**Pros:**
- ✅ Fast development (2-3 hours)
- ✅ Small bundle size (~150MB)
- ✅ Easy updates (just update Python code)
- ✅ Uses system Python/UV

**Cons:**
- ❌ Requires Python + UV installed
- ❌ User must manage dependencies

**Best for:** Personal use, development teams, technical users

### PyInstaller + Electron (Standalone)

**Pros:**
- ✅ No Python required on user's machine
- ✅ True standalone app
- ✅ Professional installers

**Cons:**
- ❌ Large bundle (300-500MB)
- ❌ Complex build process
- ❌ Slower startup
- ❌ Platform-specific builds required

**Best for:** Distribution to non-technical users, commercial apps

## Distribution

### Linux (AppImage - Recommended)

```bash
npm run build:linux

# Creates: dist/YouTube Study Buddy-1.0.0.AppImage
# Users run: chmod +x *.AppImage && ./YouTube\ Study\ Buddy-1.0.0.AppImage
```

### macOS (DMG)

```bash
npm run build:mac

# Creates: dist/YouTube Study Buddy-1.0.0.dmg
# Users drag to Applications folder
```

### Windows (NSIS Installer)

```bash
npm run build:win

# Creates: dist/YouTube Study Buddy Setup 1.0.0.exe
# Standard Windows installer
```

## Auto-Updates (Optional)

Use electron-updater for automatic updates:

```bash
npm install --save electron-updater
```

```javascript
// In main.js
const { autoUpdater } = require('electron-updater');

app.whenReady().then(() => {
  autoUpdater.checkForUpdatesAndNotify();
});
```

## Troubleshooting

### Streamlit Won't Start

**Problem:** Electron window opens but shows "Cannot connect"

**Solutions:**
- Check if port 8501 is available: `lsof -i :8501`
- Increase `waitOn` timeout in main.js
- Run Streamlit manually first: `uv run streamlit run streamlit_app.py`

### Large Bundle Size

**Problem:** Electron app is 300MB+

**Solutions:**
- Use electron-builder's compression
- Exclude unnecessary files in package.json
- Use external Python (simple wrapper approach)

### Cross-Platform Issues

**Problem:** App works on Linux but not Windows

**Solutions:**
- Use `path.join()` for all paths (not `/` or `\\`)
- Test on target platform before distributing
- Use electron-builder's platform-specific configs

## Security Considerations

1. **Never bundle API keys** in the Electron app
2. Use environment variables: app reads from `.env`
3. Enable `contextIsolation` and disable `nodeIntegration`
4. Validate all file paths
5. Use code signing for production builds

## Estimated Effort

| Task | Time | Difficulty |
|------|------|------------|
| Basic Electron setup | 1 hour | Easy |
| Streamlit integration | 1 hour | Easy |
| Icon and branding | 30 min | Easy |
| Testing on platforms | 2 hours | Medium |
| PyInstaller bundling | 4 hours | Hard |
| Auto-updates | 2 hours | Medium |
| Code signing | 3 hours | Hard |

**Total for simple wrapper**: ~3-4 hours
**Total for standalone app**: ~12-16 hours

## Alternatives

### 1. PyWebView (Pure Python)

```python
import webview
import threading
import subprocess

def start_streamlit():
    subprocess.run(['uv', 'run', 'streamlit', 'run', 'streamlit_app.py'])

if __name__ == '__main__':
    t = threading.Thread(target=start_streamlit)
    t.daemon = True
    t.start()

    webview.create_window('YouTube Study Buddy', 'http://localhost:8501')
    webview.start()
```

**Pros:** Pure Python, no Node.js
**Cons:** Limited features, less polished

### 2. Tauri (Rust + Web)

Like Electron but smaller and faster.

**Pros:** Tiny bundle size (10-20MB)
**Cons:** Requires Rust, steeper learning curve

### 3. Progressive Web App (PWA)

Streamlit can be installed as PWA in Chrome.

**Pros:** Zero build, works everywhere
**Cons:** Not a "real" desktop app

## Recommendation

**For your use case (YouTube Study Buddy):**

**Use Option 1: Simple Electron Wrapper**

Why:
- ✅ Quick to implement (3 hours)
- ✅ Easy to maintain
- ✅ Works great for technical users
- ✅ Small bundle size
- ✅ Users likely have Python anyway

Only consider PyInstaller + Electron if:
- Distributing to non-technical users
- Users unlikely to have Python
- Need professional installer experience

## Next Steps

Want me to create the actual Electron wrapper files for this project?
