/* Synapse AI - 主应用控制器 */

let chatManager = null;

/** 更新大脑状态指示器（侧边栏的状态灯+文字） */
function setStatus(status) {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    dot.className = 'status-dot';
    switch (status) {
        case 'ready':
            dot.classList.add('active');
            text.textContent = '就绪';
            break;
        case 'thinking':
            dot.classList.add('thinking');
            text.textContent = '思考中...';
            break;
        case 'error':
            dot.style.background = 'var(--neon-red)';
            dot.style.boxShadow = '0 0 10px var(--neon-red)';
            text.textContent = '错误';
            break;
        default:
            dot.classList.add('active');
            text.textContent = status;
    }
}

/** 清空思维链面板 */
function clearThoughtChain() {
    document.getElementById('thoughtChainList').innerHTML = `
        <div class="chain-placeholder">
            <div class="placeholder-icon">◌</div>
            暂无神经活动。<br>发送消息唤醒 AI 大脑。
        </div>
    `;
    document.getElementById('chainCount').textContent = '0';
}

/** 向思维链面板添加一条思考记录 */
function addThoughtToChain(thought) {
    const list = document.getElementById('thoughtChainList');
    const placeholder = list.querySelector('.chain-placeholder');
    if (placeholder) placeholder.remove();

    const node = document.createElement('div');
    node.className = `chain-node ${thought.type}`;
    const now = new Date();
    const time = now.toLocaleTimeString('zh-CN', { hour12: false });

    let content = thought.content || '';
    if (thought.metadata && thought.metadata.name) {
        const icon = TOOL_ICONS[thought.metadata.name] || '\u{1F527}';
        content = `<strong>${icon} ${thought.metadata.name}</strong><br>${content}`;
    }
    if (thought.metadata && thought.metadata.args) {
        const argsStr = JSON.stringify(thought.metadata.args)
            .replace(/[{}"]/g, '').replace(/,/g, ', ');
        content += `<br><span style="color:var(--text-muted);font-size:10px;">Args: ${argsStr}</span>`;
    }

    node.innerHTML = `
        <div class="node-header">
            <span class="node-type">${thought.type.replace('_', ' ')}</span>
            <span class="node-time">${time}</span>
        </div>
        <div class="node-content">${escapeHtml(content).replace(/\n/g, '<br>')}</div>
    `;

    list.appendChild(node);
    list.scrollTop = list.scrollHeight;

    updateChainCount();
}

function updateChainCount(count) {
    const el = document.getElementById('chainCount');
    if (count !== undefined) {
        el.textContent = count;
    } else {
        const nodes = document.querySelectorAll('.chain-node');
        el.textContent = nodes.length;
    }
}

// Thought Stream (overlay on brain)
/** 清空大脑面板上的思维流 */
function clearThoughtStream() {
    document.getElementById('thoughtStream').innerHTML = `
        <div class="thought-placeholder">
            <span class="neural-pulse"></span>
            正在处理神经信号...
        </div>
    `;
}

/** 向大脑面板思维流添加一个标签 */
function addThoughtToStream(thought) {
    const stream = document.getElementById('thoughtStream');
    const placeholder = stream.querySelector('.thought-placeholder');
    if (placeholder) placeholder.remove();

    const item = document.createElement('span');
    item.className = `thought-item ${thought.type}`;
    const icon = thought.type === 'tool_call' ? '⚙' :
                 thought.type === 'tool_result' ? '✔' :
                 thought.type === 'response' ? '◆' : '●';
    const text = (thought.content || '').substring(0, 55);
    item.textContent = `${icon} ${text}`;

    stream.appendChild(item);

    while (stream.children.length > 8) {
        stream.removeChild(stream.firstChild);
    }

    stream.scrollLeft = stream.scrollWidth;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

/** 保存配置按钮 — 更新API Key和模型 */
document.getElementById('saveConfigBtn').addEventListener('click', async () => {
    const apiKey = document.getElementById('apiKeyInput').value.trim();
    const model = document.getElementById('modelSelect').value;
    const btn = document.getElementById('saveConfigBtn');

    btn.textContent = '正在保存...';
    btn.disabled = true;

    try {
        const resp = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_key: apiKey || undefined,
                model: model,
            }),
        });
        const data = await resp.json();
        document.getElementById('modelName').textContent = data.model;
        setStatus('ready');
        showToast(`配置已更新 — 模型：${data.model}`, 'success');
    } catch (e) {
        showToast('配置更新失败：' + e.message, 'error');
    } finally {
        btn.textContent = '保存配置';
        btn.disabled = false;
    }
});

/** 切换大脑粒子背景的显示/隐藏 */
document.getElementById('toggleBrainBtn').addEventListener('click', function() {
    const canvas = document.getElementById('brainCanvas');
    const statusBar = document.getElementById('brainStatusBar');
    const isVisible = canvas.style.display !== 'none';
    if (isVisible) {
        canvas.style.display = 'none';
        statusBar.style.display = 'none';
        this.textContent = '可视化：关';
        this.style.borderColor = 'var(--border-subtle)';
    } else {
        canvas.style.display = '';
        statusBar.style.display = '';
        this.textContent = '可视化：开';
        this.style.borderColor = 'var(--neon-purple)';
        if (brainViz) brainViz.resize();
    }
});

// Chain clear button
document.getElementById('chainClearBtn').addEventListener('click', () => {
    clearThoughtChain();
});

// Keyboard shortcut - Escape to close modals
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay').forEach(m => m.style.display = 'none');
    }
});

// Mobile sidebar toggle
document.getElementById('mobileSidebarToggle').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('show-mobile');
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    brainViz = new BrainViz('brainCanvas');
    chatManager = new ChatManager();
    loadTools();
    setStatus('ready');
});
