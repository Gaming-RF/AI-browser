const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    navigate: (url) => ipcRenderer.send('navigate', url),
    goBack: () => ipcRenderer.send('go-back'),
    goForward: () => ipcRenderer.send('go-forward'),
    reload: () => ipcRenderer.send('reload'),
    onUrlChanged: (callback) => ipcRenderer.on('url-changed', callback),
    onTitleChanged: (callback) => ipcRenderer.on('title-changed', callback),
    
    // Panels and Sidebars
    togglePanel: (panelId) => ipcRenderer.send('toggle-panel', panelId),
    resizePanel: (width) => ipcRenderer.send('resize-panel', width),
    onPanelToggled: (callback) => ipcRenderer.on('panel-toggled', callback),
    
    // Tab & Workspace management
    newTab: (url, isIncognito) => ipcRenderer.send('new-tab', { url, isIncognito }),
    closeTab: (tabId) => ipcRenderer.send('close-tab', tabId),
    switchTab: (tabId) => ipcRenderer.send('switch-tab', tabId),
    switchWorkspace: (workspaceId) => ipcRenderer.send('switch-workspace', workspaceId),
    onForceSwitchWorkspace: (callback) => ipcRenderer.on('force-switch-workspace', callback),
    showTabContextMenu: (tabId) => ipcRenderer.send('show-tab-context-menu', tabId),
    onTabsUpdated: (callback) => ipcRenderer.on('tabs-updated', callback),
    
    // Theme management
    setTheme: (name, color) => ipcRenderer.send('set-theme', { name, color }),
    onThemeChanged: (callback) => ipcRenderer.on('theme-changed', callback),
    
    // Downloads
    onDownloadStarted: (callback) => ipcRenderer.on('download-started', callback),
    onDownloadUpdated: (callback) => ipcRenderer.on('download-updated', callback),
    
    // Audio and Shaders
    onPlayAudio: (callback) => ipcRenderer.on('play-audio', callback),
    toggleForceDark: (enabled) => ipcRenderer.send('toggle-force-dark', enabled),
    setShader: (name) => ipcRenderer.send('set-shader', name),
    
    // Recording management
    startRecording: () => ipcRenderer.send('start-recording'),
    stopRecording: () => ipcRenderer.send('stop-recording'),
    
    // Bookmarks and History
    toggleBookmark: (url, title) => ipcRenderer.send('toggle-bookmark', {url, title}),
    checkBookmark: (url) => ipcRenderer.invoke('check-bookmark', url),
    getBookmarks: () => ipcRenderer.invoke('get-bookmarks'),
    getHistory: () => ipcRenderer.invoke('get-history'),
    fakeHistory: () => ipcRenderer.send('fake-history'),
    
    // Audio Routing
    sendAudioEvent: (type) => ipcRenderer.send('tab-audio-event', type),
    
    // Settings & Import
    openSettings: () => ipcRenderer.send('open-settings'),
    importHistory: () => ipcRenderer.invoke('import-history'),
    clearBrowsingData: () => ipcRenderer.send('clear-browsing-data'),
    setBlockAds: (enabled) => ipcRenderer.send('set-block-ads', enabled),
    setBlockTrackers: (enabled) => ipcRenderer.send('set-block-trackers', enabled),
    setDoNotTrack: (enabled) => ipcRenderer.send('set-do-not-track', enabled),
    injectUserScript: (tabId, script) => ipcRenderer.send('inject-user-script', { tabId, script }),
    injectCustomCss: (tabId, css) => ipcRenderer.send('inject-custom-css', { tabId, css }),
    setProxy: (proxyRules) => ipcRenderer.send('set-proxy', proxyRules),
    
    // Resource Limits
    applyResourceLimit: (tabId, action) => ipcRenderer.invoke('apply-resource-limit', { tabId, action })
});
