// Electron Preload Script - Security Context Bridge
const { contextBridge } = require('electron');

// Expose safe APIs to renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  version: process.versions.electron,
  node: process.versions.node,
  chrome: process.versions.chrome
});

console.log('Electron preload script loaded');
