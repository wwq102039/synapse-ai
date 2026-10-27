/* Synapse AI - 聊天界面 & 命令系统 */

class ChatManager {
    constructor() {
        this.messagesContainer = document.getElementById('chatMessages');
        this.input = document.getElementById('chatInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.clearBtn = document.getElementById('clearChatBtn');
        this.historyBtn = document.getElementById('historyBtn');
        this.saveChatBtn = document.getElementById('saveChatBtn');
        this.exportChatBtn = document.getElementById('exportChatBtn');
        this.shortcutsBtn = document.getElementById('shortcutsBtn');
        this.chips = document.querySelectorAll('.chip');
        this.history = [];
        this.isProcessing = false;
        this.ws = null;
        this.wsReconnectTimer = null;
        this.streamingEl = null;     // 当前流式渲染的 bubble DOM
        this.streamingText = '';     // 累积的流式文本

        this.init();
    }

    init() {
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
            if (e.ctrlKey && e.key === 'k') {
                e.preventDefault();
                this.showShortcuts();
            }
        });
        this.input.addEventListener('input', () => this.autoResize());

        this.clearBtn.addEventListener('click', () => this.clearChat());
        this.historyBtn.addEventListener('click', () => this.showHistory());
        this.saveChatBtn.addEventListener('click', () => this.saveConversation());
        this.exportChatBtn.addEventListener('click', () => this.exportConversation());
        this.shortcutsBtn.addEventListener('click', () => this.showShortcuts());

        this.chips.forEach(chip => {
            chip.addEventListener('click', () => {
                const msg = chip.dataset.msg;
                this.input.value = msg;
                this.sendMessage();
            });
        });

        this.connectWebSocket();
    }

    connectWebSocket() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${location.host}/ws/chat`;
        try {
            this.ws = new WebSocket(wsUrl);
            this.ws.onopen = () => {
                if (this.wsReconnectTimer) {
                    clearTimeout(this.wsReconnectTimer);
                    this.wsReconnectTimer = null;
                }
            };
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWSMessage(data);
            };
            this.ws.onclose = () => {
                if (!this.wsReconnectTimer) {
                    this.wsReconnectTimer = setTimeout(() => this.connectWebSocket(), 3000);
                }
            };
            this.ws.onerror = () => {
                this.ws.close();
            };
        } catch (e) {
            console.warn('WebSocket unavailable, using REST fallback');
            this.ws = null;
        }
    }

    /** 处理 WebSocket 消息：thought / token / done / response(兼容旧版) */
    handleWSMessage(data) {
        switch (data.type) {
            case 'thought':
                addThoughtToChain(data.data);
                addThoughtToStream(data.data);
                if (brainViz) {
                    brainViz.pulse();
                    if (data.data.type === 'tool_call') {
                        brainViz.setExcitement(0.85);
                        highlightTool(data.data.metadata?.name);
                    } else if (data.data.type === 'tool_result') {
                        brainViz.setExcitement(0.5);
                    } else if (data.data.type === 'response') {
                        brainViz.setExcitement(0.25);
                    }
                }
                break;

            case 'token':
                if (!this.streamingEl) {
                    if (this.currentThinkingId) {
                        this.removeThinkingBubble(this.currentThinkingId);
                        this.currentThinkingId = null;
                    }
                    this.streamingEl = this.createStreamingBubble();
                }
                this.streamingText += data.content;
                this.streamingEl.querySelector('.bubble').innerHTML =
                    this.formatMarkdown(this.streamingText);
                this.scrollToBottom();
                break;

            case 'done':
                this.finalizeStreamingResponse(data.data);
                break;

            case 'response':
                // 兼容旧版非流式格式
                if (this.currentThinkingId) {
                    this.removeThinkingBubble(this.currentThinkingId);
                    this.currentThinkingId = null;
                }
                if (this.streamingEl) {
                    this.finalizeStreamingResponse(data.data);
                } else {
                    this.addResponseBubble(data.data.response, data.data);
                }
                this.isProcessing = false;
                this.updateSendButton();
                setStatus('ready');
                if (brainViz) brainViz.setExcitement(0.08);
                break;
        }
    }

    /** 创建流式输出 bubble（空壳，token 逐步填充） */
    createStreamingBubble() {
        const div = document.createElement('div');
        div.className = 'message assistant';
        div.innerHTML = `
            <div class="avatar">AI</div>
            <div class="bubble"></div>
        `;
        this.messagesContainer.appendChild(div);
        this.scrollToBottom();
        return div;
    }

    /** 流式输出完成，记录历史并清理状态 */
    finalizeStreamingResponse(data) {
        const finalText = data.response || this.streamingText;
        this.history.push({ role: 'assistant', content: finalText, time: new Date().toISOString() });

        if (this.streamingEl) {
            let extraHtml = '';
            if (data.tool_calls_count > 0) {
                const toolCalls = (data.thoughts || []).filter(t => t.type === 'tool_call');
                extraHtml += '<div style="margin-top:10px;">';
                for (const tc of toolCalls) {
                    const icon = TOOL_ICONS[tc.metadata?.name] || '\u{1F527}';
                    extraHtml += `<span class="tool-call-badge">${icon} ${tc.metadata?.name || 'tool'}</span>`;
                }
                extraHtml += '</div>';
            }
            this.streamingEl.querySelector('.bubble').innerHTML =
                this.formatMarkdown(finalText) + extraHtml;
        }

        this.streamingEl = null;
        this.streamingText = '';
        this.isProcessing = false;
        this.updateSendButton();
        setStatus('ready');
        updateChainCount(data.thoughts ? data.thoughts.length : 0);
        if (brainViz) brainViz.setExcitement(0.08);
    }

    async sendMessage() {
        const message = this.input.value.trim();
        if (!message || this.isProcessing) return;

        if (message.startsWith('/')) {
            this.handleCommand(message);
            this.input.value = '';
            this.autoResize();
            return;
        }

        this.isProcessing = true;
        this.updateSendButton();
        this.input.value = '';
        this.autoResize();

        this.addUserBubble(message);
        this.history.push({ role: 'user', content: message, time: new Date().toISOString() });

        const welcome = this.messagesContainer.querySelector('.welcome-message');
        if (welcome) welcome.remove();

        clearThoughtChain();
        clearThoughtStream();
        setStatus('thinking');
        if (brainViz) {
            brainViz.setExcitement(0.6);
            brainViz.pulse();
        }

        this.currentThinkingId = this.addThinkingBubble();

        try {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({
                    message: message,
                    history: this.history.slice(0, -1),
                }));
            } else {
                // REST fallback
                const resp = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: message,
                        history: this.history.slice(0, -1),
                    }),
                });
                const data = await resp.json();

                if (data.error) throw new Error(data.error);

                for (const thought of data.thoughts) {
                    addThoughtToChain(thought);
                    addThoughtToStream(thought);
                    if (brainViz) {
                        brainViz.pulse();
                        if (thought.type === 'tool_call') {
                            brainViz.setExcitement(0.85);
                            highlightTool(thought.metadata?.name);
                        }
                    }
                }

                this.removeThinkingBubble(this.currentThinkingId);
                this.currentThinkingId = null;
                this.addResponseBubble(data.response, data);
                this.isProcessing = false;
                this.updateSendButton();
                setStatus('ready');
                updateChainCount(data.thoughts ? data.thoughts.length : 0);
                if (brainViz) brainViz.setExcitement(0.08);
            }
        } catch (err) {
            if (this.currentThinkingId) {
                this.removeThinkingBubble(this.currentThinkingId);
                this.currentThinkingId = null;
            }
            if (this.streamingEl) {
                this.streamingEl.remove();
                this.streamingEl = null;
                this.streamingText = '';
            }
            this.addErrorBubble(err.message);
            this.isProcessing = false;
            this.updateSendButton();
            setStatus('error');
            if (brainViz) brainViz.setExcitement(0);
        }
    }

    handleCommand(command) {
        const parts = command.split(/\s+/);
        const cmd = parts[0].toLowerCase();

        switch (cmd) {
            case '/help':
                this.showShortcuts();
                break;
            case '/clear':
                this.clearChat();
                this.addSystemMessage('对话已清空。');
                break;
            case '/tools':
                this.listToolsInChat();
                break;
            case '/model':
                this.showModelInfo();
                break;
            case '/history':
                this.showHistory();
                break;
            case '/save':
                this.saveConversation(parts[1]);
                break;
            case '/export':
                this.exportConversation();
                break;
            default:
                this.addSystemMessage(`未知命令：${cmd}。输入 /help 查看可用命令。`);
        }
    }

    async listToolsInChat() {
        try {
            const resp = await fetch('/api/tools');
            const data = await resp.json();
            let msg = `<strong>可用工具（${data.count} 个）：</strong>\n`;
            for (const tool of data.tools) {
                const icon = TOOL_ICONS[tool.name] || '\u{1F527}';
                msg += `\n${icon} <strong>${tool.name}</strong> — ${tool.description}`;
            }
            this.addSystemMessage(msg);
        } catch (e) {
            this.addSystemMessage('加载工具列表失败，请检查服务器连接。');
        }
    }

    showModelInfo() {
        const modelEl = document.getElementById('modelName');
        this.addSystemMessage(`当前模型：<strong style="color:var(--neon-cyan)">${modelEl.textContent}</strong>`);
    }

    addSystemMessage(text) {
        const div = document.createElement('div');
        div.className = 'message assistant';
        div.innerHTML = `
            <div class="avatar" style="background:var(--gradient-3);">⚡</div>
            <div class="bubble" style="font-size:13px;">${text}</div>
        `;
        this.messagesContainer.appendChild(div);
        this.scrollToBottom();
    }

    addUserBubble(text) {
        const div = document.createElement('div');
        div.className = 'message user';
        div.innerHTML = `
            <div class="avatar">U</div>
            <div class="bubble">${this.escapeHtml(text)}</div>
        `;
        this.messagesContainer.appendChild(div);
        this.scrollToBottom();
    }

    addResponseBubble(text, data) {
        this.history.push({ role: 'assistant', content: text, time: new Date().toISOString() });

        let extraHtml = '';
        if (data && data.tool_calls_count > 0) {
            const toolCalls = (data.thoughts || []).filter(t => t.type === 'tool_call');
            extraHtml += '<div style="margin-top:10px;">';
            for (const tc of toolCalls) {
                const icon = TOOL_ICONS[tc.metadata?.name] || '\u{1F527}';
                extraHtml += `<span class="tool-call-badge">${icon} ${tc.metadata?.name || 'tool'}</span>`;
            }
            extraHtml += '</div>';
        }

        const div = document.createElement('div');
        div.className = 'message assistant';
        div.innerHTML = `
            <div class="avatar">AI</div>
            <div class="bubble">${this.formatMarkdown(text)}${extraHtml}</div>
        `;
        this.messagesContainer.appendChild(div);
        this.scrollToBottom();
    }

    addThinkingBubble() {
        const id = 'thinking-' + Date.now();
        const div = document.createElement('div');
        div.className = 'message assistant';
        div.id = id;
        div.innerHTML = `
            <div class="avatar">AI</div>
            <div class="bubble">
                <div class="thinking-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        this.messagesContainer.appendChild(div);
        this.scrollToBottom();
        return id;
    }

    removeThinkingBubble(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    addErrorBubble(errorText) {
        const div = document.createElement('div');
        div.className = 'message assistant';
        div.innerHTML = `
            <div class="avatar" style="background:var(--neon-red);">!</div>
            <div class="bubble" style="color:var(--neon-red);border-color:rgba(239,68,68,0.2);">
                <strong>错误：</strong> ${this.escapeHtml(errorText)}
            </div>
        `;
        this.messagesContainer.appendChild(div);
        this.scrollToBottom();
    }

    clearChat() {
        this.history = [];
        this.messagesContainer.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">
                    <div class="welcome-icon-core"></div>
                </div>
                <h2>欢迎来到 Synapse AI</h2>
                <p class="subtitle">
                    一个能够<strong>感知</strong>、<strong>决策</strong>、<strong>行动</strong>的 AI 智能体。
                    <br>搭载 <strong>26+ 种神经工具</strong> — 权威扫描、舆情分析、情报综合、高考预测、文件操作、网页搜索等。
                </p>
                <div class="suggestion-chips">
                    <button class="chip" data-msg="分析2026年四川省高考理科650分可以报考哪些大学，推荐冲刺、稳妥和保底院校">🎓 高考志愿分析</button>
                    <button class="chip" data-msg="搜索教育部关于2026年研究生招生最新政策，分析政策变化趋势">📋 教育政策追踪</button>
                    <button class="chip" data-msg="分析公众对人工智能专业的就业前景评价和舆情倾向">📊 社会舆情分析</button>
                    <button class="chip" data-msg="核实'四川大学2026年将在全国扩招1000人'这个说法是否属实">🔍 信息真实性核实</button>
                    <button class="chip" data-msg="对比四川大学、电子科技大学、西南交通大学在综合排名、就业率、学术实力方面的优劣">⚖ 多维度对比</button>
                    <button class="chip" data-msg="搜索2026年最新的AI新闻">📰 搜索AI新闻</button>
                    <button class="chip" data-msg="北京现在天气怎么样？">🌤 北京天气</button>
                    <button class="chip" data-msg="计算 2的10次方 + 根号144 × 3.14">🔢 数学计算</button>
                </div>
            </div>
        `;
        clearThoughtChain();
        clearThoughtStream();
        this.rebindChips();
    }

    rebindChips() {
        this.chips = document.querySelectorAll('.chip');
        this.chips.forEach(chip => {
            chip.addEventListener('click', () => {
                this.input.value = chip.dataset.msg;
                this.sendMessage();
            });
        });
    }

    showHistory() {
        const modal = document.getElementById('historyModal');
        const content = document.getElementById('historyContent');
        const exportBtn = document.getElementById('historyExportBtn');
        const clearBtn = document.getElementById('historyClearBtn');

        if (this.history.length === 0) {
            content.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px;">No messages yet.</p>';
        } else {
            content.innerHTML = this.history.map((msg, i) => {
                const isUser = msg.role === 'user';
                const color = isUser ? 'var(--neon-pink)' : 'var(--neon-cyan)';
                const label = isUser ? '用户' : 'AI';
                const time = msg.time ? new Date(msg.time).toLocaleString() : '';
                return `
                    <div class="history-item ${isUser ? 'user-msg' : 'ai-msg'}">
                        <div class="history-role ${isUser ? 'user' : 'ai'}" style="color:${color}">${label} ${time ? '· '+time : ''}</div>
                        <div>${this.escapeHtml(msg.content).substring(0, 200)}${msg.content.length > 200 ? '...' : ''}</div>
                    </div>
                `;
            }).join('');
        }

        modal.style.display = 'flex';

        const closeHandler = () => { modal.style.display = 'none'; };
        document.getElementById('historyClose').onclick = closeHandler;
        modal.onclick = (e) => { if (e.target === modal) closeHandler(); };

        exportBtn.onclick = () => { this.exportConversation(); modal.style.display = 'none'; };
        clearBtn.onclick = () => {
            this.history = [];
            content.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px;">历史记录已清空。</p>';
        };
    }

    showShortcuts() {
        const modal = document.getElementById('shortcutsModal');
        modal.style.display = 'flex';
        const closeHandler = () => { modal.style.display = 'none'; };
        document.getElementById('shortcutsClose').onclick = closeHandler;
        modal.onclick = (e) => { if (e.target === modal) closeHandler(); };
    }

    saveConversation(filename) {
        if (!filename) filename = `conversation-${new Date().toISOString().slice(0, 10)}.json`;
        const data = JSON.stringify(this.history, null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
        showToast(`已保存到 ${filename}`, 'success');
    }

    exportConversation() {
        const data = {
            exported: new Date().toISOString(),
            model: document.getElementById('modelName').textContent,
            messages: this.history,
        };
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `synapse-export-${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('对话已导出！', 'success');
    }

    updateSendButton() {
        this.sendBtn.disabled = this.isProcessing;
    }

    autoResize() {
        this.input.style.height = 'auto';
        this.input.style.height = Math.min(this.input.scrollHeight, 130) + 'px';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    formatMarkdown(text) {
        // 代码块（优先处理，避免内部格式被解析）
        const codeBlocks = [];
        text = text.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
            const idx = codeBlocks.length;
            const langLabel = lang ? `<div style="font-size:10px;color:var(--text-muted);padding:4px 0;">${lang}</div>` : '';
            codeBlocks.push(`${langLabel}<pre><code>${this.escapeHtml(code.trim())}</code></pre>`);
            return `%%CODEBLOCK_${idx}%%`;
        });

        // 表格
        text = text.replace(/\|(.+)\|\n\|[-| :]+\|\n((?:\|.+\|\n?)*)/g, (match, header, rows) => {
            const headers = header.split('|').map(h => h.trim()).filter(Boolean);
            const rowLines = rows.trim().split('\n').map(r =>
                r.split('|').map(c => c.trim()).filter(Boolean)
            );
            let tableHtml = '<table style="width:100%;border-collapse:collapse;font-size:12px;margin:8px 0;">';
            tableHtml += '<thead><tr>' + headers.map(h => `<th style="border:1px solid var(--border-subtle);padding:6px 10px;text-align:left;color:var(--neon-cyan);">${h}</th>`).join('') + '</tr></thead>';
            tableHtml += '<tbody>' + rowLines.map(row =>
                '<tr>' + row.map(c => `<td style="border:1px solid var(--border-subtle);padding:6px 10px;">${c}</td>`).join('') + '</tr>'
            ).join('') + '</tbody></table>';
            return tableHtml;
        });

        // 标题
        text = text.replace(/^### (.+)$/gm, '<h4 style="color:var(--neon-purple);margin:10px 0 4px;font-size:13px;">$1</h4>');
        text = text.replace(/^## (.+)$/gm, '<h3 style="color:var(--neon-cyan);margin:12px 0 6px;font-size:14px;border-bottom:1px solid var(--border-subtle);padding-bottom:4px;">$1</h3>');
        text = text.replace(/^# (.+)$/gm, '<h2 style="color:var(--neon-cyan);margin:14px 0 8px;font-size:15px;">$1</h2>');

        // 水平分割线
        text = text.replace(/^---$/gm, '<hr style="border:none;border-top:1px solid var(--border-subtle);margin:10px 0;">');

        // 无序列表
        text = text.replace(/^[\-\*] (.+)$/gm, '<li style="margin-left:16px;color:var(--text-secondary);">$1</li>');

        // 粗体 / 斜体 / 内联代码
        text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
        text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

        // 链接
        text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" style="color:var(--neon-cyan);text-decoration:none;">$1</a>');

        // 换行
        text = text.replace(/\n/g, '<br>');

        // 恢复代码块
        codeBlocks.forEach((block, idx) => {
            text = text.replace(`%%CODEBLOCK_${idx}%%`, block);
        });

        return text;
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
}

function showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'toastOut 0.3s ease-in forwards';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}
