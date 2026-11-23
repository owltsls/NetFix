# -*- coding: utf-8 -*-
"""UI 渲染验证：截图三个页面，确认中文字体与配色正常。"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
import netfix_gui

app = QApplication([])

# 显式加载微软雅黑，确保中文可见
font_db = QFontDatabase()
families = font_db.families()
cn = [f for f in families if "YaHei" in f or "微软雅黑" in f or "SimHei" in f or "黑体" in f]
print("可用中文字体族:", cn[:5])
chosen = "Microsoft YaHei" if "Microsoft YaHei" in families else (cn[0] if cn else "Sans Serif")
print("采用字体:", chosen)
app.setFont(QFont(chosen, 10))

# 覆盖 QSS 中的字体族为实际可用名称
netfix_gui.GLOBAL_QSS = netfix_gui.GLOBAL_QSS.replace(
    'font-family: "Microsoft YaHei", "Segoe UI", sans-serif;',
    f'font-family: "{chosen}";'
)
app.setStyleSheet(netfix_gui.GLOBAL_QSS)

w = netfix_gui.NetFixApp()
w.resize(1040, 720)

# 页面1：注入模拟体检结果，展示完整状态
demo = [
    {"key":"proxy_wininet","name":"系统代理 WinINET","level":"err","summary":"代理已启用但目标无响应","detail":"ProxyEnable=1  ProxyServer=127.0.0.1:7897"},
    {"key":"proxy_winhttp","name":"WinHTTP 代理","level":"ok","summary":"直连（系统服务通道正常）","detail":"直接访问(没有代理服务器)"},
    {"key":"env_proxy","name":"环境变量代理","level":"ok","summary":"无代理环境变量","detail":"均为空"},
    {"key":"dns","name":"DNS 配置","level":"warn","summary":"存在指向本机的 DNS(127.0.0.1)","detail":"本地连接*10 DNS=127.0.0.1"},
    {"key":"hosts","name":"hosts 文件","level":"ok","summary":"无自定义映射（干净）","detail":"所有行均为注释"},
    {"key":"nic","name":"网卡状态","level":"ok","summary":"检测到 2 个启用接口","detail":"WLAN 已连接"},
    {"key":"ports","name":"代理端口监听","level":"ok","summary":"无常见代理端口监听","detail":"已探测常见端口"},
    {"key":"browser","name":"浏览器代理痕迹","level":"warn","summary":"发现 1 处需留意项","detail":"Edge 扩展目录存在"},
]
w.scan_results = demo
w.render_scan_results(demo)
w.scan_summary.setText("体检完成：正常 5 · 注意 2 · 异常 1")
app.processEvents()
w.grab().save("ui_p1.png")

# 页面2
w.stack.setCurrentWidget(w.page_fix)
app.processEvents()
w.grab().save("ui_p2.png")

# 页面3
w.repair_log = ["[成功] 关闭系统代理(WinINET)：系统代理已关闭", "[成功] 刷新 DNS 缓存：已刷新"]
w.result_log.setText("\n".join(w.repair_log))
w.selftest_label.setText("✓ 自检通过：DNS 解析成功 · HTTP 200。浏览器应已恢复正常。")
w.result_sub.setText("已执行 2 项修复 · 快照：backup/20261123-2235")
w.stack.setCurrentWidget(w.page_result)
app.processEvents()
w.grab().save("ui_p3.png")

print("截图完成: ui_p1.png, ui_p2.png, ui_p3.png")
