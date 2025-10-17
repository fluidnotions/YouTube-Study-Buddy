// Electron Main Process - YouTube Study Buddy Desktop App
const { app, BrowserWindow, Menu } = require('electron');
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
    title: 'YouTube Study Buddy',
    backgroundColor: '#0E1117' // Streamlit dark theme background
  });

  // Create application menu
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'Reload',
          accelerator: 'CmdOrCtrl+R',
          click: () => mainWindow.reload()
        },
        { type: 'separator' },
        {
          label: 'Exit',
          accelerator: 'CmdOrCtrl+Q',
          click: () => app.quit()
        }
      ]
    },
    {
      label: 'View',
      submenu: [
        {
          label: 'Toggle DevTools',
          accelerator: 'CmdOrCtrl+Shift+I',
          click: () => mainWindow.webContents.toggleDevTools()
        },
        { type: 'separator' },
        { role: 'resetzoom' },
        { role: 'zoomin' },
        { role: 'zoomout' }
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'About',
          click: () => {
            const { dialog } = require('electron');
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'About YouTube Study Buddy',
              message: 'YouTube Study Buddy v1.0.0',
              detail: 'AI-powered study notes generator from YouTube videos\n\n' +
                      'Built with Streamlit, Anthropic Claude, and Electron'
            });
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);

  // Load Streamlit after server starts
  mainWindow.loadURL(`http://localhost:${STREAMLIT_PORT}`);

  // Open DevTools in development
  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
  }

  // Handle window close
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });
}

function startStreamlit() {
  console.log('Starting Streamlit server...');

  // Determine project root (parent of electron/)
  const projectRoot = path.join(__dirname, '..');

  // Spawn Streamlit process using UV
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
    'false',
    '--server.fileWatcherType',
    'none'  // Disable file watcher for better performance
  ], {
    cwd: projectRoot,
    shell: true,
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
  });

  streamlitProcess.stdout.on('data', (data) => {
    const output = data.toString().trim();
    if (output) {
      console.log(`[Streamlit] ${output}`);
    }
  });

  streamlitProcess.stderr.on('data', (data) => {
    const output = data.toString().trim();
    if (output && !output.includes('Keyboard interrupt received')) {
      console.error(`[Streamlit Error] ${output}`);
    }
  });

  streamlitProcess.on('error', (error) => {
    console.error('Failed to start Streamlit:', error);
    const { dialog } = require('electron');
    dialog.showErrorBox(
      'Streamlit Failed to Start',
      `Could not start Streamlit server:\n\n${error.message}\n\n` +
      'Make sure Python and UV are installed:\n' +
      'https://docs.astral.sh/uv/getting-started/installation/'
    );
    app.quit();
  });

  streamlitProcess.on('close', (code) => {
    console.log(`Streamlit process exited with code ${code}`);
    if (code !== 0 && code !== null) {
      console.error(`Streamlit crashed with exit code ${code}`);
    }
  });

  // Wait for Streamlit to be ready
  const opts = {
    resources: [`http://localhost:${STREAMLIT_PORT}`],
    delay: 1000,        // Initial delay
    timeout: 30000,     // 30 second timeout
    interval: 500,      // Check every 500ms
    validateStatus: (status) => status >= 200 && status < 400
  };

  console.log('Waiting for Streamlit server to start...');

  waitOn(opts)
    .then(() => {
      console.log('✓ Streamlit is ready!');
      createWindow();
    })
    .catch((err) => {
      console.error('✗ Streamlit failed to start:', err);
      const { dialog } = require('electron');
      dialog.showErrorBox(
        'Streamlit Startup Failed',
        `Streamlit server did not start within 30 seconds.\n\n` +
        `Error: ${err.message}\n\n` +
        'Check the console for more details.'
      );
      app.quit();
    });
}

// App lifecycle
app.whenReady().then(() => {
  startStreamlit();

  app.on('activate', () => {
    // macOS: Re-create window when dock icon is clicked
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  // Quit app when all windows are closed (except macOS)
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  console.log('Shutting down Streamlit...');

  // Kill Streamlit process on exit
  if (streamlitProcess && !streamlitProcess.killed) {
    streamlitProcess.kill('SIGTERM');

    // Force kill if not dead after 2 seconds
    setTimeout(() => {
      if (streamlitProcess && !streamlitProcess.killed) {
        streamlitProcess.kill('SIGKILL');
      }
    }, 2000);
  }
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});
