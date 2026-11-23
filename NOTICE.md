# NOTICE — NetFix

Copyright 2026 TheSun_Also_Rises

本仓库中的原创源码、图标、文档与交互原型以 **Apache License 2.0** 授权，许可全文见 [LICENSE](LICENSE)。

## 第三方组件

本项目的 GUI 与打包依赖以下第三方组件，它们各自按其许可授权，不属于本项目的 Apache 2.0 授权范围：

| 组件 | 参考版本 | 许可 | 用途 | 许可全文 / 来源 |
| --- | --- | --- | --- | --- |
| Python | 3.13.14 | PSF License Agreement | 运行时 / 开发语言 | https://docs.python.org/3/license.html |
| PySide6 | 6.12.0 | LGPLv3 / GPLv3（双许可） | GUI 框架（Qt for Python 官方绑定） | https://doc.qt.io/qtforpython/licenses.html |
| Qt | 随 PySide6 | LGPLv3 / GPLv3 | PySide6 底层 GUI/事件库 | https://www.qt.io/licensing/ |
| PyInstaller | 6.22.3 | GPLv2 with exception | 打包为单文件 exe（仅构建期使用） | https://pyinstaller.org/en/stable/license.html |
| Pillow | 用于图标生成 | HPND License | 图标生成脚本 `gen_icons.py` 使用 | https://pillow.readthedocs.io/en/stable/ |

> 参考版本为本项目的开发与验证环境；使用更新版本通常兼容，但不在本项目测试范围内。

## 二进制分发说明

- **加载方式**：程序运行时通过 `import PySide6` 动态加载 Qt 库；打包版由 PyInstaller 将 Python 解释器与 PySide6/Qt 动态链接库一并捆绑进单个 exe（`--onefile`）。
- **仓库内容**：本仓库**不提交** `dist/`、`build/`、`__pycache__/`、`*.exe` 等构建产物，仅提交源码与资源。
- **PySide6 / Qt 的 LGPL 合规要求**：若你分发捆绑了 PySide6/Qt 的 exe，需注意：
  1. 随分发物附上 LGPLv3 许可全文及 Qt 版权声明；
  2. 告知用户所用 Qt 组件及获取对应源码的途径；
  3. 保证用户能够替换/重新链接 LGPL 库（PyInstaller 打包的可执行文件需提供可替换库的方式，或使用动态外部库形式）。
  
  如无法满足上述要求，建议以 GPLv3 条款分发，或将 GUI 层改用其它许可更宽松的框架重写。
- **商用提示**：若计划纯 Apache 2.0 商用分发、避免 copyleft 义务，建议将 GUI 层改用 C#/WinForms 等方案重写（详见 `docs/PRD-网络异常修复工具.md` 的方案比选）。
- **测试素材来源**：图标由 `assets/icons/gen_icons.py` 用 Pillow 程序化绘制生成（原创，无外部素材授权问题）；界面截图/线稿为本项目自制。

## 联系方式

作者：TheSun_Also_Rises　|　微信：TheSun_Also_Rises
