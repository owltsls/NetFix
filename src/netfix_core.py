# -*- coding: utf-8 -*-
"""
NetFix 核心逻辑模块
职责：只读体检 / 快照备份 / 分项修复 / 回滚 / 连通性自检
原则：先备份后修改、可回滚、默认不碰 hosts 与防火墙、全程离线
"""
import os
import sys
import json
import socket
import subprocess
import datetime
import winreg

# ---------- 路径与常量 ----------
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Local"))
BASE_DIR = os.path.join(LOCALAPPDATA, "NetFix")
BACKUP_ROOT = os.path.join(BASE_DIR, "backup")
LOG_DIR = os.path.join(BASE_DIR, "logs")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

INET_SETTINGS = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
ENVIRONMENT = r"Environment"
HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"

DEFAULT_PROXY_PORTS = [7890, 7897, 1080, 10809, 2080, 10808, 7891, 33210]

CREATE_NO_WINDOW = 0x08000000


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


import ctypes  # noqa: E402  (is_admin 用到)


def ensure_dirs():
    for d in (BASE_DIR, BACKUP_ROOT, LOG_DIR, REPORT_DIR):
        os.makedirs(d, exist_ok=True)


def _decode(raw):
    """稳健解码 Windows 命令输出：优先 UTF-8，回退 GBK，自动识别乱码。"""
    if not raw:
        return ""
    # 中文 Windows 控制台命令默认 OEM/GBK 代码页，优先 cp936
    for enc in ("cp936", "gbk", "utf-8", "mbcs"):
        try:
            text = raw.decode(enc)
            # 乱码特征：出现大量替换符或 CJK 乱码区，视为失败
            if "\ufffd" in text:
                continue
            return text
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def _run(cmd, timeout=20):
    """执行命令并返回 (returncode, stdout+stderr)，兼容中文编码。"""
    try:
        p = subprocess.run(
            cmd, shell=True, capture_output=True, timeout=timeout,
            creationflags=CREATE_NO_WINDOW
        )
        return p.returncode, _decode(p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "命令超时"
    except Exception as e:
        return -1, str(e)


def _ts():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def _reg_get(path, name, hive=winreg.HKEY_CURRENT_USER):
    try:
        with winreg.OpenKey(hive, path) as k:
            val, _ = winreg.QueryValueEx(k, name)
            return val
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _reg_set(path, name, value, vtype=winreg.REG_DWORD, hive=winreg.HKEY_CURRENT_USER):
    with winreg.CreateKeyEx(hive, path, 0, winreg.KEY_WRITE) as k:
        winreg.SetValueEx(k, name, 0, vtype, value)


def _reg_del(path, name, hive=winreg.HKEY_CURRENT_USER):
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_WRITE) as k:
            winreg.DeleteValue(k, name)
    except FileNotFoundError:
        pass


# ============================================================
# 一、只读体检
# ============================================================
def check_wininet():
    """系统代理 WinINET（HaX：浏览器读取的通道）"""
    enable = _reg_get(INET_SETTINGS, "ProxyEnable")
    server = _reg_get(INET_SETTINGS, "ProxyServer") or ""
    pac = _reg_get(INET_SETTINGS, "AutoConfigURL") or ""
    detail = f"ProxyEnable={enable}  ProxyServer={server or '(空)'}  AutoConfigURL={pac or '(空)'}"
    if enable == 1:
        alive = _port_alive(server)
        if server and not alive:
            return _item("系统代理 WinINET", "err", "代理已启用但目标无响应",
                         detail + "\n→ 该代理端口无监听，浏览器请求会全部失败", "proxy_wininet")
        return _item("系统代理 WinINET", "warn", "代理已启用",
                     detail + "\n→ 若你正在使用代理软件，请勿关闭", "proxy_wininet")
    if pac:
        return _item("系统代理 WinINET", "warn", "启用了自动配置脚本(PAC)",
                     detail, "proxy_wininet")
    return _item("系统代理 WinINET", "ok", "未使用代理（直连）", detail, "proxy_wininet")


def _port_alive(server):
    """探测代理地址端口是否有程序监听。"""
    if not server:
        return False
    host, _, port = server.partition(":")
    if not port:
        return False
    try:
        port = int("".join(ch for ch in port if ch.isdigit()))
    except Exception:
        return False
    s = socket.socket()
    s.settimeout(0.4)
    try:
        return s.connect_ex((host or "127.0.0.1", port)) == 0
    finally:
        s.close()


def check_winhttp():
    rc, out = _run("netsh winhttp show proxy")
    if "直接访问" in out or "direct access" in out.lower() or "没有代理服务器" in out:
        return _item("WinHTTP 代理", "ok", "直连（系统服务通道正常）", out[:400], "proxy_winhttp")
    return _item("WinHTTP 代理", "warn", "检测到 WinHTTP 代理", out[:400], "proxy_winhttp")


def check_env_proxy():
    found = []
    for scope, hive in (("用户", winreg.HKEY_CURRENT_USER), ("系统", winreg.HKEY_LOCAL_MACHINE)):
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            v = _reg_get(ENVIRONMENT, name, hive)
            if v:
                found.append(f"{scope} {name}={v}")
    if found:
        return _item("环境变量代理", "warn", f"发现 {len(found)} 处残留环境变量代理",
                     "\n".join(found), "env_proxy")
    return _item("环境变量代理", "ok", "无代理环境变量", "HTTP_PROXY/HTTPS_PROXY/ALL_PROXY 均为空", "env_proxy")


def check_dns():
    rc, out = _run("netsh interface ip show dnsservers")
    lines = [l for l in out.splitlines() if l.strip()]
    loopback = "127.0.0.1" in out
    detail = "\n".join(lines[:14])
    if loopback:
        return _item("DNS 配置", "warn", "存在指向本机的 DNS(127.0.0.1)",
                     detail + "\n→ 常见于代理软件 TUN 残留", "dns")
    return _item("DNS 配置", "ok", "DNS 配置正常", detail or "未获取到 DNS 信息", "dns")


def check_hosts():
    try:
        with open(HOSTS_PATH, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return _item("hosts 文件", "warn", "读取失败", str(e), "hosts")
    active = [l.strip() for l in lines if l.strip() and not l.lstrip().startswith("#")]
    if active:
        return _item("hosts 文件", "warn", f"有 {len(active)} 条自定义映射",
                     "\n".join(active[:8]) + "\n→ 本工具默认不修改 hosts", "hosts")
    return _item("hosts 文件", "ok", "无自定义映射（干净）", "所有行均为注释或空行", "hosts")


def check_nic():
    rc, out = _run("netsh interface show interface")
    lines = [l for l in out.splitlines() if l.strip()]
    up = sum(1 for l in lines if "已启用" in l or "Enabled" in l)
    return _item("网卡状态", "ok", f"检测到 {up} 个启用接口",
                 "\n".join(lines[:12]) or "未获取到网卡信息", "nic")


def check_proxy_ports():
    alive = []
    for port in DEFAULT_PROXY_PORTS:
        s = socket.socket()
        s.settimeout(0.15)
        try:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                alive.append(port)
        finally:
            s.close()
    if alive:
        return _item("代理端口监听", "warn", f"本机有 {len(alive)} 个代理端口在监听",
                     "127.0.0.1 端口: " + ", ".join(map(str, alive)) + "\n→ 可能有代理软件在运行", "ports")
    return _item("代理端口监听", "ok", "无常见代理端口监听",
                 "已探测 " + ", ".join(map(str, DEFAULT_PROXY_PORTS)), "ports")


def check_browser_traces():
    """检查 Edge 快捷方式是否带 --proxy-server 参数 / 代理扩展目录。"""
    traces = []
    shortcuts = [
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), r"Desktop"),
    ]
    for base in shortcuts:
        if not os.path.isdir(base):
            continue
        for root, _, files in os.walk(base):
            for fn in files:
                if fn.lower().endswith(".lnk") and "edge" in fn.lower():
                    traces.append(f"Edge 快捷方式: {fn}")
    ext_dirs = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Edge\User Data\Default\Extensions"),
    ]
    for d in ext_dirs:
        if os.path.isdir(d):
            try:
                n = len(os.listdir(d))
                traces.append(f"Edge 扩展目录存在（{n} 项）: {d}")
            except Exception:
                pass
    if traces:
        return _item("浏览器代理痕迹", "warn", f"发现 {len(traces)} 处需留意项",
                     "\n".join(traces) + "\n→ 本工具不改动浏览器配置，需人工核对", "browser")
    return _item("浏览器代理痕迹", "ok", "未发现明显代理痕迹", "Edge 快捷方式与扩展目录无异常", "browser")


def _item(name, level, summary, detail, key):
    return {
        "key": key, "name": name, "level": level,
        "summary": summary, "detail": detail,
    }


def run_scan():
    """执行全部只读体检，返回检查结果列表。"""
    checks = [
        check_wininet, check_winhttp, check_env_proxy, check_dns,
        check_hosts, check_nic, check_proxy_ports, check_browser_traces,
    ]
    results = []
    for fn in checks:
        try:
            results.append(fn())
        except Exception as e:
            results.append(_item(fn.__name__, "warn", "检查异常", str(e), fn.__name__))
    return results


# ============================================================
# 二、快照备份
# ============================================================
def create_backup():
    """创建配置快照，返回快照目录路径。"""
    ensure_dirs()
    stamp = _ts()
    dest = os.path.join(BACKUP_ROOT, stamp)
    os.makedirs(dest, exist_ok=True)

    manifest = {"created": datetime.datetime.now().isoformat(), "items": []}

    # 1. 注册表：Internet Settings
    rc, out = _run(f'reg export "HKCU\\{INET_SETTINGS}" "{dest}\\inet_settings.reg" /y')
    if rc == 0:
        manifest["items"].append("inet_settings.reg")

    # 2. 注册表：环境变量（用户）
    rc, out = _run(f'reg export "HKCU\\{ENVIRONMENT}" "{dest}\\environment.reg" /y')
    if rc == 0:
        manifest["items"].append("environment.reg")

    # 3. hosts 文件
    try:
        with open(HOSTS_PATH, "rb") as f:
            data = f.read()
        with open(os.path.join(dest, "hosts.bak"), "wb") as f:
            f.write(data)
        manifest["items"].append("hosts.bak")
    except Exception:
        pass

    # 4. 网络配置文本快照
    for name, cmd in (
        ("winhttp.txt", "netsh winhttp show proxy"),
        ("dns.txt", "netsh interface ip show dnsservers"),
    ):
        rc, out = _run(cmd)
        with open(os.path.join(dest, name), "w", encoding="utf-8") as f:
            f.write(out)
        manifest["items"].append(name)

    # 5. 代理环境变量的当前值（便于精确回滚）
    env_snapshot = {}
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env_snapshot[name] = _reg_get(ENVIRONMENT, name)
    manifest["env_values"] = env_snapshot

    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return dest


def list_backups():
    ensure_dirs()
    result = []
    try:
        for name in sorted(os.listdir(BACKUP_ROOT), reverse=True):
            p = os.path.join(BACKUP_ROOT, name)
            if os.path.isdir(p) and os.path.exists(os.path.join(p, "manifest.json")):
                result.append(p)
    except Exception:
        pass
    return result


# ============================================================
# 三、修复动作（每项独立、可勾选）
# ============================================================
REPAIRS = [
    {"key": "proxy_wininet", "label": "关闭系统代理(WinINET)", "default": True,
     "desc": "将 ProxyEnable 置 0，清空 ProxyServer / AutoConfigURL", "admin": False},
    {"key": "proxy_winhttp", "label": "重置 WinHTTP 为直连", "default": True,
     "desc": "netsh winhttp reset proxy", "admin": True},
    {"key": "env_proxy", "label": "清除环境变量代理", "default": True,
     "desc": "删除用户级 HTTP_PROXY/HTTPS_PROXY/ALL_PROXY 等", "admin": False},
    {"key": "flush_dns", "label": "刷新 DNS 缓存", "default": True,
     "desc": "ipconfig /flushdns", "admin": False},
    {"key": "winsock", "label": "重置 Winsock / TCP-IP", "default": False,
     "desc": "netsh winsock reset + netsh int ip reset（需重启生效）", "admin": True},
    {"key": "dns_loopback", "label": "清理本机回环 DNS(127.0.0.1)", "default": False,
     "desc": "将无法连接的虚拟网卡 DNS 改为自动获取", "admin": True},
]


def apply_repair(key):
    """执行单项修复，返回 (success, message)。"""
    try:
        if key == "proxy_wininet":
            _reg_set(INET_SETTINGS, "ProxyEnable", 0)
            _reg_set(INET_SETTINGS, "ProxyServer", "", winreg.REG_SZ)
            _reg_set(INET_SETTINGS, "AutoConfigURL", "", winreg.REG_SZ)
            return True, "系统代理已关闭"

        if key == "proxy_winhttp":
            rc, out = _run("netsh winhttp reset proxy")
            return (rc == 0), (out or "已重置")

        if key == "env_proxy":
            removed = []
            for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
                if _reg_get(ENVIRONMENT, name) is not None:
                    _reg_del(ENVIRONMENT, name)
                    removed.append(name)
            _broadcast_env_change()
            return True, ("已清除: " + ", ".join(removed)) if removed else "无需清除"

        if key == "flush_dns":
            rc, out = _run("ipconfig /flushdns")
            return (rc == 0), (out or "已刷新")

        if key == "winsock":
            rc1, o1 = _run("netsh winsock reset")
            rc2, o2 = _run("netsh int ip reset")
            ok = rc1 == 0 and rc2 == 0
            return ok, (o1 + "\n" + o2 + "\n→ 请重启电脑使重置完全生效")[:500]

        if key == "dns_loopback":
            # 仅对处于断开状态、且 DNS 为 127.0.0.1 的网卡改为自动获取 DNS
            rc, out = _run(
                'powershell -NoProfile -Command '
                '"Get-NetIPConfiguration | Where-Object {$_.DNSServer.ServerAddresses -contains \'127.0.0.1\'} '
                '| ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.InterfaceIndex -ResetServerAddresses; '
                'Write-Output (\'reset ifindex \' + $_.InterfaceIndex)}"'
            )
            return True, (out or "已处理")[:400]

        return False, "未知修复项"
    except PermissionError:
        return False, "权限不足，请以管理员身份运行"
    except Exception as e:
        return False, f"执行失败: {e}"


def _broadcast_env_change():
    try:
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF, 0x001A, 0, "Environment", 0x0002, 3000, None
        )
    except Exception:
        pass


# ============================================================
# 四、回滚
# ============================================================
def rollback(backup_dir):
    """从快照恢复配置，返回 (success, message)。"""
    if not backup_dir or not os.path.isdir(backup_dir):
        return False, "快照目录不存在"
    messages = []
    try:
        # 注册表
        reg_files = [("inet_settings.reg",), ("environment.reg",)]
        for (fn,) in reg_files:
            p = os.path.join(backup_dir, fn)
            if os.path.exists(p):
                rc, out = _run(f'reg import "{p}"')
                messages.append(f"{fn}: {'OK' if rc == 0 else out}")

        # hosts
        hosts_bak = os.path.join(backup_dir, "hosts.bak")
        if os.path.exists(hosts_bak):
            try:
                with open(hosts_bak, "rb") as f:
                    data = f.read()
                with open(HOSTS_PATH, "wb") as f:
                    f.write(data)
                messages.append("hosts: OK")
            except Exception as e:
                messages.append(f"hosts: 失败({e})")

        _broadcast_env_change()
        return True, "\n".join(messages)
    except Exception as e:
        return False, f"回滚失败: {e}"


# ============================================================
# 五、连通性自检
# ============================================================
def self_test():
    """返回 (dns_ok, dns_msg, http_ok, http_msg)。"""
    # DNS 解析
    try:
        socket.setdefaulttimeout(6)
        ip = socket.gethostbyname("www.baidu.com")
        dns_ok, dns_msg = True, f"解析成功: {ip}"
    except Exception as e:
        dns_ok, dns_msg = False, f"解析失败: {e}"

    # HTTP 访问
    try:
        import urllib.request
        req = urllib.request.Request("https://www.baidu.com", headers={"User-Agent": "NetFix/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            code = resp.getcode()
        http_ok, http_msg = True, f"HTTP {code}"
    except Exception as e:
        http_ok, http_msg = False, f"访问失败: {e}"
    finally:
        socket.setdefaulttimeout(None)

    return dns_ok, dns_msg, http_ok, http_msg


# ============================================================
# 六、报告导出
# ============================================================
def export_report(scan_results, repair_log, backup_dir, path):
    """导出 HTML 报告。"""
    ensure_dirs()
    level_cn = {"ok": "正常", "warn": "注意", "err": "异常"}
    level_color = {"ok": "#0D9488", "warn": "#D97706", "err": "#C0392B"}

    rows = []
    for it in scan_results:
        detail = it["detail"].replace("<", "&lt;").replace("\n", "<br>")
        rows.append(
            f'<tr><td>{it["name"]}</td>'
            f'<td style="color:{level_color[it["level"]]};font-weight:600">{level_cn[it["level"]]}</td>'
            f'<td>{it["summary"]}</td><td style="font-size:12px;color:#6B7280">{detail}</td></tr>'
        )
    log_rows = "".join(
        f"<li>{l.replace('<','&lt;')}</li>" for l in repair_log
    ) or "<li>无修复操作</li>"

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<title>NetFix 网络诊断报告</title><style>
body{{font-family:"Microsoft YaHei",sans-serif;color:#1F2937;max-width:960px;margin:32px auto;padding:0 20px}}
h1{{color:#3B6EA8}} table{{border-collapse:collapse;width:100%;margin:16px 0}}
th,td{{border:1px solid #E5E7EB;padding:8px 10px;text-align:left;font-size:13px}}
th{{background:#F6F8FC}} .meta{{color:#6B7280;font-size:13px}}
footer{{margin-top:28px;border-top:1px solid #E5E7EB;padding-top:12px;color:#6B7280;font-size:12px}}
</style></head><body>
<h1>NetFix 网络诊断报告</h1>
<p class="meta">生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
快照目录：{backup_dir or '无'}</p>
<h2>一、体检结果</h2>
<table><tr><th>通道</th><th>状态</th><th>摘要</th><th>依据</th></tr>{''.join(rows)}</table>
<h2>二、修复记录</h2><ul>{log_rows}</ul>
<footer>NetFix 网络异常修复工具 · 原型设计作者 · 微信号：TheSun_Also_Rises</footer>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
