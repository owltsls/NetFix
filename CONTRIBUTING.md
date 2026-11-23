# 贡献指南（CONTRIBUTING）

感谢你关注 **NetFix** —— 一款本地离线、可回滚的 Windows 网络异常一键修复工具。

## 开发环境

- 操作系统：Windows 10 / 11 x64
- 运行时：Python 3.10+（验证环境 3.13.14）
- GUI 与打包依赖见下方安装命令（PySide6 / PyInstaller）

## 本地搭建

```bash
# 创建虚拟环境（可选但推荐）
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install PySide6 PyInstaller
```

## 本地运行

```bash
cd src
python netfix_gui.py
```

## 本地构建

```bash
cd src
python -m PyInstaller build.spec --noconfirm
# 产物：src\dist\NetFix.exe
```

> 打包产物不入库。图标由 `assets/icons/gen_icons.py` 生成。

## 运行验证

```bash
# 语法检查
python -m py_compile src/netfix_core.py src/netfix_gui.py

# 只读体检冒烟测试（不触发任何修复）
cd src
python -c "import netfix_core as c; [print(r['name'], r['level']) for r in c.run_scan()]"

# UI 渲染验证（offscreen 截图三个页面）
python verify_ui.py
```

## 提交规范

- 保持"**先备份后修改、可回滚、默认不碰 hosts 与防火墙、全程离线**"的核心承诺，任何改动不应破坏它。
- 新增检查通道或修复项时，必须同时提供只读判断逻辑与判断依据（detail），并保证可回滚。
- 涉及功能变更请同步更新 README 与相关文档。
- 提交前请跑通上述验证命令。
- 新增高风险修复能力前，请先在 Issue 中讨论必要性与回滚方案。

## 问题反馈与 PR

- 提交 Issue 时请说明 Windows 版本、Python/PySide6 版本、复现步骤与预期行为；如涉及网络故障，附上体检结果（"依据"内容）。
- PR 请聚焦单一改动，描述变更动机与验证方式。
