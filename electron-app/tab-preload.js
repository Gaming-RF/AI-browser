const { ipcRenderer } = require('electron');

// Apply Force Dark Mode synchronously to prevent flash of white
const isDarkMode = ipcRenderer.sendSync('get-force-dark');
if (isDarkMode) {
    const style = document.createElement('style');
    style.textContent = `
        html { filter: invert(1) hue-rotate(180deg) !important; background: #121212 !important; }
        img, video, iframe, canvas { filter: invert(1) hue-rotate(180deg) !important; }
    `;
    // documentElement is available immediately in preload
    if (document.documentElement) {
        document.documentElement.appendChild(style);
    } else {
        document.addEventListener('DOMContentLoaded', () => document.documentElement.appendChild(style));
    }
}


// We listen to user interactions in the web page and notify the main process
document.addEventListener('mousedown', (e) => {
    // Only trigger for primary clicks
    if (e.button === 0) {
        ipcRenderer.send('tab-audio-event', 'click');
    }
}, true);

document.addEventListener('keydown', (e) => {
    // Don't trigger for modifiers only
    if (['Shift', 'Control', 'Alt', 'Meta'].includes(e.key)) return;
    ipcRenderer.send('tab-audio-event', 'type');
}, true);

// Add hover sounds for links and buttons
document.addEventListener('mouseover', (e) => {
    if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON' || e.target.closest('a') || e.target.closest('button')) {
        ipcRenderer.send('tab-audio-event', 'hover');
    }
}, true);

// ─── Password Manager Logic ───
window.addEventListener('DOMContentLoaded', async () => {
    try {
        const url = window.location.href;
        const savedLogins = await ipcRenderer.invoke('get-passwords', url);
        
        if (savedLogins && savedLogins.length > 0) {
            // Find password fields
            const pwdFields = document.querySelectorAll('input[type="password"]');
            pwdFields.forEach(pwdField => {
                // Find a nearby text/email field for username
                const form = pwdField.closest('form') || document;
                const userField = form.querySelector('input[type="text"], input[type="email"], input[name*="user"], input[name*="login"]');
                
                if (userField && savedLogins[0].username) {
                    userField.value = savedLogins[0].username;
                    pwdField.value = savedLogins[0].password;
                    // Trigger events for React/Vue frameworks
                    userField.dispatchEvent(new Event('input', { bubbles: true }));
                    pwdField.dispatchEvent(new Event('input', { bubbles: true }));
                }
            });
        }
    } catch (e) {
        console.error("Autofill error:", e);
    }
});

// Intercept form submissions
document.addEventListener('submit', (e) => {
    const form = e.target;
    const pwdField = form.querySelector('input[type="password"]');
    if (pwdField && pwdField.value) {
        const userField = form.querySelector('input[type="text"], input[type="email"], input[name*="user"], input[name*="login"]');
        const username = userField ? userField.value : 'unknown';
        const password = pwdField.value;
        const url = window.location.href;
        
        // Send to main process to save
        ipcRenderer.send('save-password', { url, username, password });
    }
}, true);

