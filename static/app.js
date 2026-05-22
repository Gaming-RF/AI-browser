/* ═══════════════════════════════════════════════════════════
   AI Browser — Client-side WebSocket + Chat Rendering
   ═══════════════════════════════════════════════════════════ */

(() => {
    "use strict";

    // ── DOM Refs ──────────────────────────────────────────
    const chatArea        = document.getElementById("chat-area");
    const welcomeScreen   = document.getElementById("welcome-screen");
    const taskInput       = document.getElementById("task-input");
    const sendBtn         = document.getElementById("send-btn");
    const stopBtn         = document.getElementById("stop-btn");
    const modelSelector   = document.getElementById("model-selector");
    const ollamaGroup     = document.getElementById("ollama-models");
    const customSection   = document.getElementById("custom-endpoint-section");
    const customBaseUrl   = document.getElementById("custom-base-url");
    const customModelName = document.getElementById("custom-model-name");
    const apiKeyInput     = document.getElementById("api-key-input");
    const displayModeSelector = document.getElementById("display-mode-selector");
    const visionToggle    = document.getElementById("vision-toggle");
    const maxStepsSlider  = document.getElementById("max-steps-slider");
    const maxStepsValue   = document.getElementById("max-steps-value");
    const connectionDot   = document.getElementById("connection-dot");
    const connectionText  = document.getElementById("connection-text");
    const historyList     = document.getElementById("history-list");
    const newChatBtn      = document.getElementById("new-chat-btn");
    const lightbox        = document.getElementById("lightbox");
    const lightboxImg     = document.getElementById("lightbox-img");
    const sidebarToggle   = document.getElementById("sidebar-toggle");
    const sidebar         = document.getElementById("sidebar");
    const welcomeExamples = document.getElementById("welcome-examples");
    const themeSelector   = document.getElementById("theme-selector");

    // ── State ─────────────────────────────────────────────
    let ws = null;
    let isRunning = false;
    let reconnectTimer = null;
    let thinkingEl = null;

    // ── WebSocket ─────────────────────────────────────────

    function connectWS() {
        const protocol = location.protocol === "https:" ? "wss:" : "ws:";
        ws = new WebSocket(`${protocol}//${location.host}/ws`);

        ws.onopen = () => {
            setConnectionStatus(true);
            clearTimeout(reconnectTimer);
        };

        ws.onclose = () => {
            setConnectionStatus(false);
            // Auto-reconnect
            reconnectTimer = setTimeout(connectWS, 2000);
        };

        ws.onerror = () => {
            ws.close();
        };

        ws.onmessage = (event) => {
            let data;
            try {
                data = JSON.parse(event.data);
            } catch {
                return;
            }
            handleServerMessage(data);
        };
    }

    function sendMessage(obj) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(obj));
        }
    }

    function setConnectionStatus(connected) {
        connectionDot.className = "connection-dot " + (connected ? "connected" : "disconnected");
        connectionText.textContent = connected ? "Connected" : "Reconnecting...";
    }

    // ── Message Handling ──────────────────────────────────

    function handleServerMessage(data) {
        switch (data.type) {
            case "thinking":
                showThinking(data.step);
                break;
            case "step":
                removeThinking();
                renderStepMessage(data);
                break;
            case "completed":
                removeThinking();
                renderCompletionMessage(data);
                setRunning(false);
                break;
            case "cancelled":
                removeThinking();
                renderSystemMessage("⏹ Task cancelled.", "warning");
                setRunning(false);
                break;
            case "error":
                removeThinking();
                renderErrorMessage(data);
                setRunning(false);
                break;
            case "max_steps":
                removeThinking();
                renderSystemMessage(`⚠ Reached step limit (${data.steps} steps). Task may be incomplete.`, "warning");
                setRunning(false);
                break;
            case "models":
                populateOllamaModels(data.models || []);
                break;
            case "history":
                populateHistory(data.history || []);
                break;
            default:
                break;
        }
    }

    // ── Render Functions ──────────────────────────────────

    function hideWelcome() {
        if (welcomeScreen) {
            welcomeScreen.style.display = "none";
        }
    }

    function showWelcome() {
        if (welcomeScreen) {
            welcomeScreen.style.display = "";
        }
    }

    function renderUserMessage(text) {
        hideWelcome();
        const msg = document.createElement("div");
        msg.className = "message user";
        msg.innerHTML = `
            <div class="message-avatar">👤</div>
            <div class="message-content">
                <div class="message-bubble">${escapeHtml(text)}</div>
            </div>
        `;
        chatArea.appendChild(msg);
        scrollToBottom();
    }

    function showThinking(step) {
        removeThinking();
        const msg = document.createElement("div");
        msg.className = "message assistant";
        msg.id = "thinking-msg";
        msg.innerHTML = `
            <div class="message-avatar">🌐</div>
            <div class="message-content">
                <div class="thinking-indicator">
                    <div class="thinking-dots">
                        <span></span><span></span><span></span>
                    </div>
                    Thinking${step ? ` (step ${step})` : ""}...
                </div>
            </div>
        `;
        chatArea.appendChild(msg);
        thinkingEl = msg;
        scrollToBottom();
    }

    function removeThinking() {
        if (thinkingEl) {
            thinkingEl.remove();
            thinkingEl = null;
        }
        const existing = document.getElementById("thinking-msg");
        if (existing) existing.remove();
    }

    function renderStepMessage(data) {
        const result = data.result || {};
        const step = data.step || "?";
        const action = result.action || "—";
        const reasoning = extractReasoning(data.ai_response);
        const actionResult = result.result || "";
        const success = result.success !== false;
        const screenshot = data.screenshot;

        const msg = document.createElement("div");
        msg.className = "message assistant";

        // Determine action badge class
        const badgeClass = getBadgeClass(action);

        let html = `
            <div class="message-avatar">🌐</div>
            <div class="message-content">
        `;

        // Reasoning bubble
        if (reasoning) {
            html += `<div class="message-bubble">${escapeHtml(reasoning)}</div>`;
        }

        // Action card
        html += `
                <div class="action-card">
                    <div class="action-header">
                        <span class="action-badge ${badgeClass}">${escapeHtml(action)}</span>
                        ${!success ? '<span class="action-badge error">FAILED</span>' : ''}
                        <span class="action-step">Step ${step}</span>
                    </div>
                    <div class="action-result">${escapeHtml(truncate(String(actionResult), 300))}</div>
                </div>
        `;

        // Screenshot
        if (screenshot) {
            const imgSrc = `data:image/png;base64,${screenshot}`;
            html += `
                <div class="screenshot-container" onclick="window.__openLightbox('${imgSrc}')">
                    <img src="${imgSrc}" alt="Browser screenshot after step ${step}" loading="lazy">
                    <div class="screenshot-label">Step ${step}</div>
                </div>
            `;
        }

        html += `</div>`;
        msg.innerHTML = html;
        chatArea.appendChild(msg);
        scrollToBottom();
    }

    function renderCompletionMessage(data) {
        const msg = document.createElement("div");
        msg.className = "message assistant";
        msg.innerHTML = `
            <div class="message-avatar">🌐</div>
            <div class="message-content">
                <div class="completion-card">
                    <div class="completion-header">✨ Task Completed</div>
                    <div class="completion-result">${escapeHtml(data.result || "Done!")}</div>
                </div>
                ${data.steps ? `<div style="font-size:11px;color:var(--text-muted);margin-top:6px;">Completed in ${data.steps} step(s)</div>` : ""}
            </div>
        `;
        chatArea.appendChild(msg);
        scrollToBottom();
    }

    function renderErrorMessage(data) {
        const msg = document.createElement("div");
        msg.className = "message assistant";
        msg.innerHTML = `
            <div class="message-avatar">🌐</div>
            <div class="message-content">
                <div class="error-card">
                    <div class="error-header">❌ Error</div>
                    <div class="error-detail">${escapeHtml(data.error || "Something went wrong.")}</div>
                </div>
            </div>
        `;
        chatArea.appendChild(msg);
        scrollToBottom();
    }

    function renderSystemMessage(text, variant = "info") {
        const msg = document.createElement("div");
        msg.className = "message assistant";
        const color = variant === "warning" ? "var(--warning)" : "var(--text-secondary)";
        msg.innerHTML = `
            <div class="message-avatar">🌐</div>
            <div class="message-content">
                <div class="message-bubble" style="color: ${color}; border-color: ${color}20;">
                    ${escapeHtml(text)}
                </div>
            </div>
        `;
        chatArea.appendChild(msg);
        scrollToBottom();
    }

    // ── Helpers ────────────────────────────────────────────

    function extractReasoning(aiResponse) {
        if (!aiResponse) return "";
        try {
            const start = aiResponse.indexOf("{");
            const end = aiResponse.lastIndexOf("}");
            if (start === -1 || end === -1) return aiResponse.trim();
            const obj = JSON.parse(aiResponse.substring(start, end + 1));
            return obj.reasoning || obj.next_steps || "";
        } catch {
            // If the response isn't valid JSON, try to extract text before the JSON
            const start = aiResponse.indexOf("{");
            if (start > 0) {
                const preamble = aiResponse.substring(0, start).trim();
                if (preamble.length > 10) return preamble;
            }
            return "";
        }
    }

    function getBadgeClass(action) {
        const map = {
            navigate: "navigate",
            click: "click",
            type_text: "type_text",
            completed: "completed",
        };
        return map[action] || "default";
    }

    function escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function truncate(str, max) {
        if (str.length <= max) return str;
        return str.substring(0, max) + "…";
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            chatArea.scrollTop = chatArea.scrollHeight;
        });
    }

    // ── Task Execution ────────────────────────────────────

    function startTask(taskText) {
        if (!taskText.trim() || isRunning) return;

        // Parse model selection
        const selected = modelSelector.value;
        let provider, model, baseUrl;

        if (selected === "custom") {
            provider = "openai";
            model = customModelName.value.trim() || "default";
            baseUrl = customBaseUrl.value.trim() || null;
        } else {
            const parts = selected.split(":");
            provider = parts[0];
            model = parts.slice(1).join(":");
            baseUrl = provider === "ollama" ? "http://localhost:11434/v1" : null;
            if (provider === "ollama") provider = "openai"; // Ollama uses OpenAI-compatible API
        }

        // Gather settings
        const apiKey = apiKeyInput.value.trim() || null;
        const headless = displayModeSelector.value === "screenshot";
        const visionMode = visionToggle.checked;
        const maxSteps = parseInt(maxStepsSlider.value, 10);

        renderUserMessage(taskText);
        taskInput.value = "";

        sendMessage({
            type: "start_task",
            task: taskText,
            provider,
            model,
            base_url: baseUrl,
            api_key: apiKey,
            headless,
            vision_mode: visionMode,
            max_steps: maxSteps,
        });

        setRunning(true);
    }

    function stopTask() {
        sendMessage({ type: "stop" });
    }

    function setRunning(running) {
        isRunning = running;
        sendBtn.style.display = running ? "none" : "flex";
        stopBtn.style.display = running ? "flex" : "none";
        taskInput.placeholder = running
            ? "Send a follow-up instruction..."
            : "Tell me what to do on the web...";
    }

    // ── Model Selector ────────────────────────────────────

    modelSelector.addEventListener("change", () => {
        const isCustom = modelSelector.value === "custom";
        customSection.style.display = isCustom ? "block" : "none";
    });

    function populateOllamaModels(models) {
        ollamaGroup.innerHTML = "";
        if (models.length === 0) {
            const opt = document.createElement("option");
            opt.disabled = true;
            opt.textContent = "(Ollama not detected)";
            ollamaGroup.appendChild(opt);
            return;
        }
        models.forEach((m) => {
            const opt = document.createElement("option");
            opt.value = `ollama:${m.name || m}`;
            opt.textContent = m.name || m;
            ollamaGroup.appendChild(opt);
        });
    }

    // ── History ────────────────────────────────────────────

    function populateHistory(history) {
        historyList.innerHTML = "";
        if (history.length === 0) {
            historyList.innerHTML = '<div style="padding: 12px; font-size: 12px; color: var(--text-muted);">No tasks yet</div>';
            return;
        }
        history.forEach((h) => {
            const item = document.createElement("div");
            item.className = "history-item";
            item.innerHTML = `
                <div class="history-task">${escapeHtml(h.description || h.task_description || "")}</div>
                <div class="history-meta">
                    <span class="history-status ${h.status || ""}"></span>
                    ${h.status || ""} · ${formatTime(h.timestamp)}
                </div>
            `;
            historyList.appendChild(item);
        });
    }

    function formatTime(ts) {
        if (!ts) return "";
        try {
            const d = new Date(ts);
            return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
        } catch {
            return ts;
        }
    }

    // ── Max Steps Slider ──────────────────────────────────
    maxStepsSlider.addEventListener("input", () => {
        maxStepsValue.textContent = maxStepsSlider.value;
    });

    // ── Theme Switching ───────────────────────────────────

    function setTheme(themeName) {
        document.documentElement.setAttribute("data-theme", themeName);
        try {
            localStorage.setItem("ai-browser-theme", themeName);
        } catch {
            // localStorage unavailable
        }
    }

    function loadSavedTheme() {
        try {
            const saved = localStorage.getItem("ai-browser-theme");
            if (saved) {
                document.documentElement.setAttribute("data-theme", saved);
                if (themeSelector) themeSelector.value = saved;
            }
        } catch {
            // localStorage unavailable
        }
    }

    if (themeSelector) {
        themeSelector.addEventListener("change", () => {
            setTheme(themeSelector.value);
        });
    }

    // ── Lightbox ──────────────────────────────────────────
    window.__openLightbox = function(src) {
        lightboxImg.src = src;
        lightbox.style.display = "flex";
    };

    lightbox.addEventListener("click", () => {
        lightbox.style.display = "none";
        lightboxImg.src = "";
    });

    // ── Sidebar Toggle (mobile) ───────────────────────────
    sidebarToggle.addEventListener("click", () => {
        sidebar.classList.toggle("open");
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener("click", (e) => {
        if (window.innerWidth <= 768 &&
            sidebar.classList.contains("open") &&
            !sidebar.contains(e.target) &&
            e.target !== sidebarToggle) {
            sidebar.classList.remove("open");
        }
    });

    // ── New Chat ──────────────────────────────────────────
    newChatBtn.addEventListener("click", () => {
        // Clear chat messages (keep welcome)
        chatArea.innerHTML = "";
        chatArea.appendChild(welcomeScreen);
        showWelcome();
        setRunning(false);

        // Reload history
        fetchHistory();
    });

    // ── Welcome Examples ──────────────────────────────────
    welcomeExamples.addEventListener("click", (e) => {
        const example = e.target.closest(".welcome-example");
        if (example) {
            const task = example.dataset.task;
            if (task) {
                taskInput.value = task;
                startTask(task);
            }
        }
    });

    // ── Keyboard ──────────────────────────────────────────
    taskInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (isRunning) {
                // Send as redirect instruction
                const text = taskInput.value.trim();
                if (text) {
                    renderUserMessage(text);
                    sendMessage({ type: "redirect", message: text });
                    taskInput.value = "";
                }
            } else {
                startTask(taskInput.value);
            }
        }
        if (e.key === "Escape" && isRunning) {
            stopTask();
        }
    });

    sendBtn.addEventListener("click", () => {
        startTask(taskInput.value);
    });

    stopBtn.addEventListener("click", () => {
        stopTask();
    });

    // ── Fetch initial data ────────────────────────────────

    async function fetchModels() {
        try {
            const res = await fetch("/api/models");
            const data = await res.json();
            populateOllamaModels(data.ollama || []);
        } catch {
            // Ollama not available
        }
    }

    async function fetchHistory() {
        try {
            const res = await fetch("/api/history");
            const data = await res.json();
            populateHistory(data.history || []);
        } catch {
            // Ignore
        }
    }

    // ── Init ──────────────────────────────────────────────

    function init() {
        loadSavedTheme();
        connectWS();
        fetchModels();
        fetchHistory();
        taskInput.focus();
    }

    // Start when DOM is ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
