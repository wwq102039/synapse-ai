/* Synapse AI - 工具面板管理 */

// 工具中文名映射
const TOOL_NAMES = {
    file_read: '读取文件', file_list: '文件列表', file_write: '写入文件', file_search: '搜索文件',
    web_search: '网页搜索', web_fetch: '抓取网页', web_crawl: '网页爬虫',
    code_execute: '代码执行',
    calculator: '数学计算',
    system_info: '系统信息',
    weather: '天气查询',
    db_query: '数据库查询', db_memory: '键值记忆',
    text_process: '文本分析', text_transform: '文本转换',
    port_scan: '端口扫描', subdomain_enum: '子域名枚举', dir_bruteforce: '目录爆破',
    web_vuln_scan: '漏洞扫描', xss_test: 'XSS 检测', sqli_test: 'SQLi 检测', http_header_audit: '安全头审计',
    whois_lookup: 'WHOIS 查询', dns_enum: 'DNS 枚举', url_analyzer: 'URL 分析',
    hash_identifier: '哈希识别', password_audit: '密码审计',
    wifi_scan: 'WiFi扫描', wifi_profiles: 'WiFi配置', wifi_password: 'WiFi密码',
    wifi_brute: 'WiFi爆破', wifi_handshake_crack: '握手包破解', wifi_wps_check: 'WPS检测',
    wifi_default_passwords: '路由器默认密码', wifi_wps_pin: 'WPS PIN攻击', wifi_attack: 'WiFi全自动攻击',
    wifi_deauth: 'Deauth攻击', wifi_pmkid: 'PMKID捕获', wifi_probe_sniff: 'Probe嗅探', wifi_password_mutate: '密码变异',
};

// 工具图标映射（每个工具对应一个emoji图标）
const TOOL_ICONS = {
    file_read: '\u{1F4C4}', file_list: '\u{1F4C1}', file_write: '\u{270F}\u{FE0F}', file_search: '\u{1F50D}',
    web_search: '\u{1F310}', web_fetch: '\u{1F4E1}', web_crawl: '\u{1F577}\u{FE0F}',
    code_execute: '\u{1F4BB}',
    calculator: '\u{1F522}',
    system_info: '\u{1F5A5}\u{FE0F}',
    weather: '\u{2601}\u{FE0F}',
    db_query: '\u{1F5C3}\u{FE0F}', db_memory: '\u{1F9E0}',
    text_process: '\u{1F4DD}', text_transform: '\u{1F500}',
    port_scan: '\u{1F4E1}', subdomain_enum: '\u{1F50D}', dir_bruteforce: '\u{1F5C2}\u{FE0F}',
    web_vuln_scan: '\u{1F6E1}\u{FE0F}', xss_test: '⚠\u{FE0F}', sqli_test: '\u{1F489}', http_header_audit: '\u{1F4CB}',
    whois_lookup: '\u{1F4C7}', dns_enum: '\u{1F310}', url_analyzer: '\u{1F440}',
    hash_identifier: '\u{1F512}', password_audit: '\u{1F511}',
    wifi_scan: '\u{1F4F6}', wifi_profiles: '\u{1F4CB}', wifi_password: '\u{1F511}',
    wifi_brute: '\u{1F5DD}\u{FE0F}', wifi_handshake_crack: '\u{1F3AF}', wifi_wps_check: '\u{26A1}',
    wifi_default_passwords: '\u{1F4E6}', wifi_wps_pin: '\u{1F39B}\u{FE0F}', wifi_attack: '\u{1F680}',
    wifi_deauth: '\u{1F4A2}', wifi_pmkid: '\u{1F3B2}', wifi_probe_sniff: '\u{1F4E1}', wifi_password_mutate: '\u{1F9EC}',
};

// 工具分类颜色
const TOOL_COLORS = {
    file_read: '#a78bfa', file_list: '#a78bfa', file_write: '#a78bfa', file_search: '#a78bfa',
    web_search: '#06d6d0', web_fetch: '#06d6d0', web_crawl: '#06d6d0',
    code_execute: '#f472b6',
    calculator: '#fbbf24',
    system_info: '#818cf8',
    weather: '#38bdf8',
    db_query: '#34d399', db_memory: '#34d399',
    text_process: '#fb923c', text_transform: '#fb923c',
    port_scan: '#ef4444', subdomain_enum: '#f97316', dir_bruteforce: '#f59e0b',
    web_vuln_scan: '#dc2626', xss_test: '#ea580c', sqli_test: '#e11d48', http_header_audit: '#0891b2',
    whois_lookup: '#7c3aed', dns_enum: '#6366f1', url_analyzer: '#8b5cf6',
    hash_identifier: '#059669', password_audit: '#10b981',
    wifi_scan: '#06d6d0', wifi_profiles: '#a78bfa', wifi_password: '#f472b6',
    wifi_brute: '#dc2626', wifi_handshake_crack: '#f97316', wifi_wps_check: '#fbbf24',
    wifi_default_passwords: '#06d6d0', wifi_wps_pin: '#ef4444', wifi_attack: '#ef4444',
    wifi_deauth: '#dc2626', wifi_pmkid: '#f97316', wifi_probe_sniff: '#7c3aed', wifi_password_mutate: '#10b981',
};

/**
 * 从API加载工具列表并渲染到侧边栏
 * 每个工具项可点击，点击后自动填充提示词
 */
async function loadTools() {
    try {
        const resp = await fetch('/api/tools');
        const data = await resp.json();
        const container = document.getElementById('toolsList');
        document.getElementById('toolCount').textContent = data.count;

        container.innerHTML = '';
        for (const tool of data.tools) {
            const icon = TOOL_ICONS[tool.name] || '\u{1F527}';
            const color = TOOL_COLORS[tool.name] || '#a78bfa';
            const div = document.createElement('div');
            div.className = 'tool-item';
            div.id = 'tool-' + tool.name;
            const displayName = TOOL_NAMES[tool.name] || tool.name.replace(/_/g, ' ');
            div.innerHTML = `
                <span class="tool-icon" style="background:${color}20;color:${color};">${icon}</span>
                <div class="tool-info">
                    <span class="tool-name">${displayName}</span>
                    <span class="tool-desc">${tool.description}</span>
                </div>
            `;
            div.title = tool.description;
            // 点击工具项自动填充输入框
            div.addEventListener('click', () => {
                document.getElementById('chatInput').value =
                    `请使用 ${displayName} 工具帮我`;
                document.getElementById('chatInput').focus();
            });
            container.appendChild(div);
        }
    } catch (e) {
        console.error('工具列表加载失败:', e);
    }
}

/**
 * 高亮被AI调用的工具（闪烁动画）
 */
function highlightTool(name) {
    if (!name) return;
    const el = document.getElementById('tool-' + name);
    if (el) {
        el.classList.add('used');
        setTimeout(() => el.classList.remove('used'), 2000);
    }
}
