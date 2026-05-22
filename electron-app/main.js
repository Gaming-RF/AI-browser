const { app, BrowserWindow, WebContentsView, ipcMain, dialog, clipboard, Menu, nativeTheme, globalShortcut } = require('electron');
const { autoUpdater } = require('electron-updater');
const path = require('path');
const { spawn } = require('child_process');
const { ElectronBlocker } = require('@cliqz/adblocker-electron');
const fetch = require('cross-fetch');
const fs = require('fs');

let mainWindow;
let tabs = new Map(); // tabId -> { view: WebContentsView, url: string, title: string, groupId: string, workspaceId: string }
let activeTabId = null;
let activeWorkspaceId = 'personal'; // Default workspace
let tabCounter = 0;
let pythonServerProcess = null;
let mixerWindow = null;

// Native Sidebar Overlay State
const sidebarPanels = new Map();
let activeSidebarPanel = null;
let sidebarPanelWidth = 300;

// Storage paths
const userDataPath = app.getPath('userData');
const bookmarksFile = path.join(userDataPath, 'bookmarks.json');
const historyFile = path.join(userDataPath, 'history.json');

let bookmarks = [];
let browserHistory = [];

try { if (fs.existsSync(bookmarksFile)) bookmarks = JSON.parse(fs.readFileSync(bookmarksFile, 'utf8')); } catch (e) {}
try { if (fs.existsSync(historyFile)) browserHistory = JSON.parse(fs.readFileSync(historyFile, 'utf8')); } catch (e) {}

function saveBookmarks() { fs.writeFileSync(bookmarksFile, JSON.stringify(bookmarks, null, 2)); }
function saveHistory() { fs.writeFileSync(historyFile, JSON.stringify(browserHistory.slice(0, 500), null, 2)); }

// Experimental Shaders & Force Dark Mode (global state)
let globalForceDark = false;
let globalShader = 'none';

function startPythonServer() {
    console.log("Starting Python Backend...");
    
    if (app.isPackaged) {
        // In production, run the compiled executable
        const backendExe = path.join(process.resourcesPath, 'backend', 'backend.exe');
        pythonServerProcess = spawn(backendExe, [], {
            cwd: path.join(process.resourcesPath, 'backend')
        });
    } else {
        // In development, run the python script via .venv
        const serverPath = path.join(__dirname, '..', 'server.py');
        const pythonExe = path.join(__dirname, '..', '.venv', 'Scripts', 'python.exe');
        pythonServerProcess = spawn(pythonExe, [serverPath], {
            cwd: path.join(__dirname, '..')
        });
    }

    pythonServerProcess.stdout.on('data', (data) => {
        console.log(`Python Backend: ${data}`);
    });

    pythonServerProcess.stderr.on('data', (data) => {
        console.error(`Python Backend Error: ${data}`);
    });
}

// ─── Module-level tab management functions ───
// These need to be accessible from both createWindow() and the Panic Button handler.

function createTab(url = null, parentTabId = null, isIncognito = false) {
    if (!mainWindow) return null;
    
    if (!url) {
        url = `file://${path.join(__dirname, 'newtab.html')}`;
    }
    const tabId = `tab-${tabCounter++}`;
    
    const webPreferences = {
        preload: path.join(__dirname, 'tab-preload.js'),
        nodeIntegration: false,
        contextIsolation: false
    };

    if (isIncognito) {
        webPreferences.partition = 'in-memory';
    }

    const view = new WebContentsView({ webPreferences });
    
    let groupId = `group-${tabId}`;
    let workspaceId = activeWorkspaceId;
    if (parentTabId && tabs.has(parentTabId)) {
        const parent = tabs.get(parentTabId);
        groupId = parent.groupId;
        workspaceId = parent.workspaceId;
        if (parent.isIncognito) isIncognito = true; // Inherit incognito
    }
    
    tabs.set(tabId, { view, url, title: 'New Tab', groupId, workspaceId, isIncognito });
    
    view.webContents.on('did-start-navigation', (e, newUrl) => {
        const tab = tabs.get(tabId);
        if (tab) tab.url = newUrl;
        if (activeTabId === tabId) {
            mainWindow.webContents.send('url-changed', newUrl);
        }
    });
    
    // Handle links that open in a new window/tab
    view.webContents.setWindowOpenHandler(({ url }) => {
        createTab(url, tabId);
        return { action: 'deny' };
    });
    
    view.webContents.on('did-finish-load', () => {
        const isActive = (activeTabId === tabId);
        view.webContents.executeJavaScript(`window.__isActiveTab = ${isActive};`).catch(() => {});
        
        // Inject Force Dark Mode if enabled
        if (globalForceDark) {
            applyShader(tabId, 'dark');
        }
        if (globalShader !== 'none') {
            applyShader(tabId, globalShader);
        }
    });
    
    view.webContents.on('page-title-updated', (e, title) => {
        const tab = tabs.get(tabId);
        if (tab) {
            tab.title = title;
            // Add to history
            if (!tab.isIncognito && tab.url && !tab.url.startsWith('devtools://') && !tab.url.startsWith('file://')) {
                browserHistory.unshift({ url: tab.url, title: title, time: Date.now() });
                saveHistory();
            }
        }
        mainWindow.webContents.send('tabs-updated', getTabsState());
    });

    view.webContents.loadURL(url);
    switchTab(tabId);
    return tabId;
}

function switchTab(tabId) {
    if (!tabs.has(tabId) || !mainWindow) return;
    const tab = tabs.get(tabId);
    
    // Ensure we are in the correct workspace
    if (tab.workspaceId !== activeWorkspaceId) {
        activeWorkspaceId = tab.workspaceId;
    }
    
    // Remove old view
    if (activeTabId && tabs.has(activeTabId)) {
        const oldView = tabs.get(activeTabId).view;
        mainWindow.contentView.removeChildView(oldView);
        oldView.webContents.executeJavaScript('window.__isActiveTab = false;').catch(() => {});
    }
    
    activeTabId = tabId;
    const activeView = tab.view;
    mainWindow.contentView.addChildView(activeView);
    activeView.webContents.executeJavaScript('window.__isActiveTab = true;').catch(() => {});
    resizeView();
    
    // Notify UI
    mainWindow.webContents.send('tabs-updated', getTabsState());
    mainWindow.webContents.send('url-changed', tab.url);
}

function switchWorkspace(workspaceId) {
    activeWorkspaceId = workspaceId;
    
    // Hide all views first
    if (activeTabId && tabs.has(activeTabId)) {
        mainWindow.contentView.removeChildView(tabs.get(activeTabId).view);
        activeTabId = null;
    }
    
    // Find a tab in this workspace to show
    let foundTab = null;
    for (const [id, tab] of tabs.entries()) {
        if (tab.workspaceId === workspaceId) {
            foundTab = id;
            break;
        }
    }
    
    if (foundTab) {
        switchTab(foundTab);
    } else {
        // Create a new tab if workspace is empty
        createTab();
    }
}

function closeTab(tabId) {
    if (!tabs.has(tabId)) return;
    const tab = tabs.get(tabId);
    
    if (activeTabId === tabId) {
        mainWindow.contentView.removeChildView(tab.view);
        activeTabId = null;
    }
    
    // Destroy the web contents to free resources
    tab.view.webContents.close();
    
    // Find next tab to switch to
    tabs.delete(tabId);
    if (tabs.size > 0 && !activeTabId) {
        // Try to find a tab in the current workspace first
        let nextTabId = null;
        for (const [id, t] of tabs.entries()) {
            if (t.workspaceId === activeWorkspaceId) {
                nextTabId = id;
                break;
            }
        }
        if (!nextTabId) {
            nextTabId = Array.from(tabs.keys())[0];
        }
        switchTab(nextTabId);
    } else if (tabs.size === 0) {
        // All tabs closed — create a new one
        createTab();
    } else {
        mainWindow.webContents.send('tabs-updated', getTabsState());
    }
}

function getTabsState() {
    const state = [];
    for (const [id, tab] of tabs.entries()) {
        if (tab.workspaceId === activeWorkspaceId) {
            state.push({ id, title: tab.title, url: tab.url, active: id === activeTabId, groupId: tab.groupId, isIncognito: tab.isIncognito });
        }
    }
    return state;
}

function resizeView() {
    if (!mainWindow) return;
    const bounds = mainWindow.getContentBounds();
    // Left offset = Workspace (50) + GX sidebar (48) = 98
    // Top offset = tabs bar (40) + toolbar (50) = 90
    const x = 98;
    const y = 90;
    
    if (activeTabId && tabs.has(activeTabId)) {
        tabs.get(activeTabId).view.setBounds({ x, y, width: bounds.width - x, height: bounds.height - y });
    }
    
    if (activeSidebarPanel && sidebarPanels.has(activeSidebarPanel)) {
        sidebarPanels.get(activeSidebarPanel).setBounds({ x, y, width: sidebarPanelWidth, height: bounds.height - y });
    }
}

function applyShader(targetTabId, shaderType) {
    if (!tabs.has(targetTabId)) return;
    const webContents = tabs.get(targetTabId).view.webContents;
    
    let css = '';
    if (shaderType === 'dark') {
        css = `
            html { filter: invert(1) hue-rotate(180deg) !important; background: #121212 !important; }
            img, video, iframe, canvas { filter: invert(1) hue-rotate(180deg) !important; }
        `;
    } else if (shaderType === 'crt') {
        css = `
            html { 
                animation: crtFlicker 0.15s infinite; 
                text-shadow: 1px 0 0 red, -1px 0 0 blue; 
            }
            @keyframes crtFlicker {
                0% { opacity: 0.95; }
                50% { opacity: 1; }
                100% { opacity: 0.95; }
            }
            body::after {
                content: " ";
                display: block;
                position: fixed;
                top: 0; left: 0; bottom: 0; right: 0;
                background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
                z-index: 999999;
                background-size: 100% 2px, 3px 100%;
                pointer-events: none;
            }
        `;
    }
    
    if (css) {
        webContents.insertCSS(css).catch(err => console.error("Shader injection failed:", err));
    }
}


function getPanelUrl(id) {
    if (id === 'ai') return 'http://localhost:8000';
    if (id === 'discord') return 'https://discord.com/app';
    if (id === 'twitch') return 'https://m.twitch.tv';
    if (id === 'whatsapp') return 'https://web.whatsapp.com';
    if (id === 'player') return `file://${path.join(__dirname, 'player.html')}`;
    if (id === 'gx-control') return `file://${path.join(__dirname, 'gx-control.html')}`;
    return null;
}

function initSidebarPanel(id) {
    if (sidebarPanels.has(id)) return sidebarPanels.get(id);

    const view = new WebContentsView({
        webPreferences: {
            nodeIntegration: id === 'gx-control',
            contextIsolation: id !== 'gx-control',
        }
    });
    view.webContents.loadURL(getPanelUrl(id));
    
    if (id === 'whatsapp') {
        view.webContents.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
    }
    
    sidebarPanels.set(id, view);
    return view;
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            webviewTag: true,
            preload: path.join(__dirname, 'preload.js')
        },
        titleBarStyle: 'hidden', // Modern look for custom title bar
        titleBarOverlay: {
            color: '#1a1a24',
            symbolColor: '#ffffff'
        }
    });

    // Load the browser shell UI
    mainWindow.loadFile('browser.html');
    
    initSidebarPanels();

    // Create the hidden Audio Mixer Window
    mixerWindow = new BrowserWindow({
        show: false,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });
    mixerWindow.loadFile('mixer.html');

    mainWindow.on('resize', resizeView);
    mainWindow.once('ready-to-show', () => {
        createTab('https://google.com');
    });

    // IPC Handlers for UI to control the view
    ipcMain.on('toggle-panel', (e, panelId) => {
        if (activeSidebarPanel === panelId) {
            if (activeSidebarPanel && sidebarPanels.has(activeSidebarPanel)) {
                mainWindow.contentView.removeChildView(sidebarPanels.get(activeSidebarPanel));
            }
            activeSidebarPanel = null;
        } else {
            if (activeSidebarPanel && sidebarPanels.has(activeSidebarPanel)) {
                mainWindow.contentView.removeChildView(sidebarPanels.get(activeSidebarPanel));
            }
            activeSidebarPanel = panelId;
            const view = initSidebarPanel(activeSidebarPanel);
            mainWindow.contentView.addChildView(view);
        }
        resizeView();
        mainWindow.webContents.send('panel-toggled', { activePanelId: activeSidebarPanel, panelWidth: sidebarPanelWidth });
    });

    ipcMain.on('resize-panel', (e, width) => {
        sidebarPanelWidth = width;
        resizeView();
        mainWindow.webContents.send('panel-toggled', { activePanelId: activeSidebarPanel, panelWidth: sidebarPanelWidth });
    });

    ipcMain.on('navigate', (event, url) => {
        if (!activeTabId) return;
        if (!url.startsWith('http://') && !url.startsWith('https://') && !url.startsWith('file://')) {
            url = 'https://' + url;
        }
        tabs.get(activeTabId).view.webContents.loadURL(url);
    });

    ipcMain.on('go-back', () => { if (activeTabId && tabs.has(activeTabId)) tabs.get(activeTabId).view.webContents.goBack() });
    ipcMain.on('go-forward', () => { if (activeTabId && tabs.has(activeTabId)) tabs.get(activeTabId).view.webContents.goForward() });
    ipcMain.on('reload', () => { if (activeTabId && tabs.has(activeTabId)) tabs.get(activeTabId).view.webContents.reload() });
    
    ipcMain.on('new-tab', (e, args = {}) => createTab(args.url, null, args.isIncognito));
    ipcMain.on('close-tab', (e, tabId) => closeTab(tabId));
    ipcMain.on('switch-tab', (e, tabId) => switchTab(tabId));
    
    ipcMain.on('switch-workspace', (e, workspaceId) => switchWorkspace(workspaceId));
    
    // Audio Routing Pipeline to Mixer
    ipcMain.on('tab-audio-event', (event, type) => {
        if (mixerWindow) {
            mixerWindow.webContents.send('play-audio', type);
        }
    });

    ipcMain.on('get-force-dark', (event) => {
        event.returnValue = globalForceDark;
    });

    ipcMain.on('toggle-force-dark', (e, enabled) => {
        globalForceDark = enabled;
        if (activeTabId) applyShader(activeTabId, globalForceDark ? 'dark' : 'none');
    });

    ipcMain.on('set-shader', (e, shaderName) => {
        globalShader = shaderName;
        if (activeTabId) applyShader(activeTabId, shaderName);
    });
    
    ipcMain.on('show-tab-context-menu', (event, tabId) => {
        nativeTheme.themeSource = 'dark'; // Force dark context menu
        const template = [
            { label: 'New tab', accelerator: 'CmdOrCtrl+T', click: () => createTab() },
            { label: 'Reload', accelerator: 'CmdOrCtrl+R', click: () => { if(tabs.has(tabId)) tabs.get(tabId).view.webContents.reload() } },
            { label: 'Copy page address', click: () => { if(tabs.has(tabId)) clipboard.writeText(tabs.get(tabId).url || '') } },
            { type: 'separator' },
            { label: 'Duplicate tab', click: () => {
                if(tabs.has(tabId)) {
                    const currentTab = tabs.get(tabId);
                    createTab(currentTab.url, tabId);
                }
            }},
            { type: 'separator' },
            { label: 'Close tab', accelerator: 'CmdOrCtrl+W', click: () => closeTab(tabId) },
            { label: 'Close other tabs', click: () => {
                for (const [id] of tabs) {
                    if (id !== tabId) closeTab(id);
                }
            }}
        ];
        const menu = Menu.buildFromTemplate(template);
        menu.popup(BrowserWindow.fromWebContents(event.sender));
    });
    
    // Themes Handlers
    ipcMain.on('set-theme', (e, { name, color }) => {
        mainWindow.webContents.send('theme-changed', color);
        for (const tab of tabs.values()) {
            tab.view.webContents.send('theme-changed', color);
        }
    });

    ipcMain.on('open-settings', () => {
        createTab(`file://${path.join(__dirname, 'settings.html')}`);
    });

    const vault = require('./vault');
    ipcMain.handle('get-passwords', (e, url) => vault.getPasswordsForUrl(url));
    ipcMain.on('save-password', (e, data) => vault.savePassword(data.url, data.username, data.password));

    // Resource Limits (Phase 20)
    ipcMain.handle('apply-resource-limit', async (e, { tabId, action }) => {
        if (!tabs.has(tabId)) return { error: 'Tab not found' };
        const view = tabs.get(tabId).view;
        const pid = view.webContents.getOSProcessId();
        
        try {
            const resp = await fetch('http://localhost:8000/api/system/limit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pid, action })
            });
            return await resp.json();
        } catch (error) {
            console.error('Failed to apply resource limit:', error);
            return { error: error.message };
        }
    });

    // Recording Logic
    const recorderScript = `
        if (!window.__aiRecorder) {
            window.__aiRecorder = {
                events: [],
                recording: false,
                recordEvent(type, target, value) {
                    if(!this.recording) return;
                    this.events.push({ type, target, value, time: Date.now() });
                }
            };

            document.addEventListener('click', (e) => {
                if(!window.__aiRecorder.recording) return;
                let path = [];
                let el = e.target;
                while(el && el.tagName && path.length < 3) {
                    let id = el.id ? '#' + el.id : '';
                    let cls = el.className && typeof el.className === 'string' ? '.' + el.className.split(' ').join('.') : '';
                    path.unshift(el.tagName.toLowerCase() + id + cls);
                    el = el.parentElement;
                }
                window.__aiRecorder.recordEvent('click', path.join(' > '), null);
            }, true);
            
            document.addEventListener('change', (e) => {
                if(!window.__aiRecorder.recording) return;
                if(e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                    window.__aiRecorder.recordEvent('type', e.target.tagName, e.target.value);
                }
            }, true);
        }
        window.__aiRecorder.recording = true;
        window.__aiRecorder.events = [];
    `;

    ipcMain.on('start-recording', () => {
        if (!activeTabId) return;
        const view = tabs.get(activeTabId).view;
        view.webContents.executeJavaScript(recorderScript).catch(() => {});
    });

    ipcMain.on('stop-recording', async () => {
        if (!activeTabId) return;
        const view = tabs.get(activeTabId).view;
        try {
            const events = await view.webContents.executeJavaScript(`
                window.__aiRecorder.recording = false;
                window.__aiRecorder.events;
            `);
            
            if (events && events.length > 0) {
                console.log('Workflow recorded:', events);
                // Send to python backend
                fetch('http://localhost:8000/api/record_workflow', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ events, url: tabs.get(activeTabId).url })
                }).catch(err => console.error('Failed to save workflow:', err));
            }
        } catch (e) {
            console.error('Failed to stop recording:', e);
        }
    });

    // Bookmarks and History IPC handlers
    ipcMain.handle('check-bookmark', (e, url) => {
        return bookmarks.some(b => b.url === url);
    });

    ipcMain.on('toggle-bookmark', (e, data) => {
        const { url, title } = data;
        const index = bookmarks.findIndex(b => b.url === url);
        if (index >= 0) {
            bookmarks.splice(index, 1);
        } else {
            bookmarks.push({ url, title, time: Date.now() });
        }
        saveBookmarks();
    });

    ipcMain.handle('get-bookmarks', () => bookmarks);
    ipcMain.handle('get-history', () => browserHistory);

    // "Fake My History" Injector
    ipcMain.on('fake-history', () => {
        browserHistory.length = 0; // Wipe array
        
        const fakeUrls = [
            { url: "https://docs.aws.amazon.com/lambda/", title: "AWS Lambda Documentation" },
            { url: "https://stackoverflow.com/questions/11227809", title: "Why is processing a sorted array faster?" },
            { url: "https://en.wikipedia.org/wiki/Kubernetes", title: "Kubernetes - Wikipedia" },
            { url: "https://leetcode.com/problemset/all/", title: "Problems - LeetCode" },
            { url: "https://github.com/microsoft/vscode", title: "microsoft/vscode: Visual Studio Code" },
            { url: "https://react.dev/learn", title: "Quick Start – React" },
            { url: "https://developer.mozilla.org/en-US/docs/Web/JavaScript", title: "JavaScript | MDN" },
            { url: "https://news.ycombinator.com/", title: "Hacker News" }
        ];
        
        // Bulk insert multiple copies with different times to make it look full
        let timeOffset = Date.now() - (1000 * 60 * 60 * 24); // Start 24 hours ago
        for (let i = 0; i < 50; i++) {
            const fake = fakeUrls[i % fakeUrls.length];
            browserHistory.unshift({
                url: fake.url,
                title: fake.title,
                time: timeOffset + (i * 1000 * 60 * 15) // +15 mins between visits
            });
        }
        
        saveHistory();
    });

    ipcMain.on('clear-browsing-data', async () => {
        const { session } = require('electron');
        try {
            await session.defaultSession.clearStorageData();
            browserHistory = [];
            bookmarks = [];
            saveHistory();
            saveBookmarks();
            console.log("Browsing data cleared.");
        } catch (err) {
            console.error("Failed to clear data:", err);
        }
    });

    ipcMain.handle('import-history', async () => {
        try {
            const { canceled, filePaths } = await dialog.showOpenDialog({
                title: 'Import History JSON',
                filters: [{ name: 'JSON Files', extensions: ['json'] }],
                properties: ['openFile']
            });
            if (canceled || filePaths.length === 0) return { canceled: true };
            
            const data = fs.readFileSync(filePaths[0], 'utf8');
            const imported = JSON.parse(data);
            
            if (!Array.isArray(imported)) throw new Error('Invalid format. Expected an array of history items.');
            
            let addedCount = 0;
            imported.forEach(item => {
                if (item.url && !browserHistory.some(h => h.url === item.url)) {
                    browserHistory.push({ url: item.url, title: item.title || item.url, time: item.time || Date.now() });
                    addedCount++;
                }
            });
            
            browserHistory.sort((a, b) => b.time - a.time);
            saveHistory();
            return { success: true, count: addedCount };
        } catch (e) {
            console.error('Import failed:', e);
            return { success: false, error: e.message };
        }
    });
}

app.commandLine.appendSwitch('remote-debugging-port', '9222');

app.whenReady().then(() => {
    startPythonServer();
    createWindow();

    // Start Ad Blocker
    const { session } = require('electron');
    ElectronBlocker.fromPrebuiltAdsAndTracking(fetch).then((blocker) => {
        blocker.enableBlockingInSession(session.defaultSession);
        app.on('session-created', (newSession) => {
            blocker.enableBlockingInSession(newSession);
        });
        console.log("Ad Blocker Activated");
    }).catch(err => console.error("Ad Blocker Error:", err));

    // Download Manager Hook
    session.defaultSession.on('will-download', (event, item, webContents) => {
        const fileName = item.getFilename();
        const url = item.getURL();
        const id = Date.now().toString();

        if (mainWindow) {
            mainWindow.webContents.send('download-started', { id, fileName, url });
        }

        item.on('updated', (event, state) => {
            if (!mainWindow) return;
            if (state === 'interrupted') {
                mainWindow.webContents.send('download-updated', { id, state: 'interrupted' });
            } else if (state === 'progressing') {
                if (item.isPaused()) {
                    mainWindow.webContents.send('download-updated', { id, state: 'paused' });
                } else {
                    const received = item.getReceivedBytes();
                    const total = item.getTotalBytes();
                    mainWindow.webContents.send('download-updated', { id, state: 'progressing', received, total });
                }
            }
        });

        item.once('done', (event, state) => {
            if (!mainWindow) return;
            if (state === 'completed') {
                mainWindow.webContents.send('download-updated', { id, state: 'completed', savePath: item.getSavePath() });
            } else {
                mainWindow.webContents.send('download-updated', { id, state: `failed` });
            }
        });
    });

    // Auto-Updater Logic
    if (app.isPackaged) {
        autoUpdater.checkForUpdatesAndNotify();
        
        autoUpdater.on('update-available', () => {
            if (mainWindow) mainWindow.webContents.send('updater-msg', 'Update available. Downloading...');
        });
        
        autoUpdater.on('update-downloaded', () => {
            if (mainWindow) mainWindow.webContents.send('updater-msg', 'Update downloaded. Restarting...');
            setTimeout(() => autoUpdater.quitAndInstall(), 3000);
        });
    }

    // PANIC BUTTON: Instantly jump to work workspace, mute audio, load safe page
    globalShortcut.register('F12', () => {
        console.log("PANIC BUTTON TRIGGERED!");
        
        // Mute all web contents
        for (const tab of tabs.values()) {
            tab.view.webContents.setAudioMuted(true);
        }
        
        // Instantly switch to work workspace
        if (mainWindow) {
            mainWindow.webContents.send('force-switch-workspace', 'work');
        }
        
        // Find or create a safe tab in the 'work' workspace
        let safeTabId = null;
        for (const [id, tab] of tabs.entries()) {
            if (tab.workspaceId === 'work' && tab.url && tab.url.includes('docs.google.com')) {
                safeTabId = id;
                break;
            }
        }
        
        // Switch to work workspace internally
        activeWorkspaceId = 'work';
        
        // Hide current view
        if (activeTabId && tabs.has(activeTabId)) {
            mainWindow.contentView.removeChildView(tabs.get(activeTabId).view);
            activeTabId = null;
        }
        
        if (safeTabId) {
            switchTab(safeTabId);
        } else {
            // Create a new tab for Google Docs in the work workspace
            createTab('https://docs.google.com');
        }
    });

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('will-quit', () => {
    globalShortcut.unregisterAll();
});

app.on('window-all-closed', () => {
    if (pythonServerProcess) {
        pythonServerProcess.kill();
    }
    if (process.platform !== 'darwin') {
        app.quit();
    }
});
