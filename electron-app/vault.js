const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { app } = require('electron');

const vaultFile = path.join(app.getPath('userData'), 'vault.enc');

// We derive a static key from a static string for this MVP.
// In a real app, this should be a user-provided master password.
const MASTER_KEY = crypto.scryptSync('antigravity-master-password', 'salt', 32);
const ALGORITHM = 'aes-256-gcm';

function getVault() {
    if (!fs.existsSync(vaultFile)) return {};
    
    try {
        const encrypted = fs.readFileSync(vaultFile, 'utf8');
        const data = Buffer.from(encrypted, 'base64');
        const iv = data.subarray(0, 12);
        const tag = data.subarray(data.length - 16);
        const content = data.subarray(12, data.length - 16);

        const decipher = crypto.createDecipheriv(ALGORITHM, MASTER_KEY, iv);
        decipher.setAuthTag(tag);
        
        const decrypted = decipher.update(content) + decipher.final('utf8');
        return JSON.parse(decrypted);
    } catch (e) {
        console.error("Failed to decrypt vault:", e);
        return {};
    }
}

function saveVault(data) {
    const iv = crypto.randomBytes(12);
    const cipher = crypto.createCipheriv(ALGORITHM, MASTER_KEY, iv);
    
    const content = Buffer.from(JSON.stringify(data), 'utf8');
    const encrypted = Buffer.concat([cipher.update(content), cipher.final()]);
    const tag = cipher.getAuthTag();
    
    const finalData = Buffer.concat([iv, encrypted, tag]).toString('base64');
    fs.writeFileSync(vaultFile, finalData, 'utf8');
}

function savePassword(url, username, password) {
    const vault = getVault();
    const domain = new URL(url).hostname;
    
    if (!vault[domain]) vault[domain] = [];
    
    // Check if exists
    const existing = vault[domain].find(e => e.username === username);
    if (existing) {
        existing.password = password;
    } else {
        vault[domain].push({ username, password });
    }
    
    saveVault(vault);
}

function getPasswordsForUrl(url) {
    try {
        const domain = new URL(url).hostname;
        const vault = getVault();
        return vault[domain] || [];
    } catch {
        return [];
    }
}

module.exports = {
    savePassword,
    getPasswordsForUrl
};
