# DeskNest · 桌屿

一款轻量的 Windows 桌面收纳与快捷启动工具。把常用应用、文件、文件夹和网页快捷方式集中到分区卡片中，让日常查找与启动更方便。

使用 **Python + PySide6 + SQLite**，无需账号，应用功能离线可用；打开网页快捷方式时由默认浏览器访问网页。

**当前版本：v0.1.1（早期 MVP），项目会继续更新。** 欢迎通过 Issues 反馈问题、提出建议，或提交 Pull Request。

> 当前收纳方式为引用管理：不会移动、隐藏或删除桌面原文件，也不会自动清空桌面图标。

[下载 Windows 版](https://github.com/1CJA/DeskNest/releases/latest) · [新手使用教程](docs/USAGE.md) · [更新记录](CHANGELOG.md) · [参与贡献](CONTRIBUTING.md)

## 直接使用

普通用户无需安装 Python，请到 [Releases](https://github.com/1CJA/DeskNest/releases) 下载 `DeskNest-0.1.1-windows-x64.zip`：

- 将 zip 完整解压到一个固定文件夹，双击其中的 `DeskNest.exe`。
- 首次打开后点击「扫描桌面」，选择要添加的项目与分区；也可以直接从桌面或资源管理器拖入。
- 下载源码 zip 不包含可执行程序；开发者请参阅下方「开发运行」。
- 请保留同目录的 `_internal`，不要只复制 exe。接收者无需安装 Python、Qt 或数据库。
- 这是免安装 MVP，尚未提供签名安装包和自动更新。目标系统为 Windows 10/11 x64。

从旧版切换时，请先在旧版「更多 → 退出 DeskNest」退出，再运行新版或 `run.cmd`。正常启动沿用原来的本地数据，无需重新收纳；仅关闭窗口会留在托盘。

## 直接拖入桌面图标

- 在 Windows 桌面或资源管理器中选中一个或多个快捷方式、文件、文件夹，拖到窗口中间，即可收纳到当前分区。
- 拖到左侧分区名称，收纳到该分区；当前为「全部项目」或拖到「全部项目」时，收纳到左侧第一个分区（默认「常用」）。
- 空分区和搜索结果页也支持拖入。成功添加后会打开目标分区并清空搜索，显示新项目。
- 支持 `.lnk`、`.url`、普通文件和文件夹；仅保存引用，原文件保留。重复项目跳过，已有分类、收藏和置顶不改变。Ctrl+Z 可撤销整批添加。
- 不存在或无法读取的路径会提示；「此电脑」「回收站」等虚拟图标及浏览器地址拖入暂不支持。
- 请正常运行 DeskNest；Windows 会阻止从普通权限的资源管理器拖入以管理员权限运行的程序。

## 核心流程

1. 点击「扫描桌面」。软件读取 Windows 配置的个人桌面和公共桌面，包括已迁移、OneDrive 重定向的桌面。
2. 勾选要收纳的内容并选择分区。快捷方式默认勾选，实际文件和文件夹默认不勾选。
3. 左侧「+」创建分区；底部按钮重命名、删除；拖动分区可调整顺序。删除分区会把引用移到第一个保留的分区。
4. 单击卡片启动，或键盘选中后按 Enter。搜索框搜索全部分区的名称和路径。
5. 拖动卡片到分区分类，或拖到另一张卡片前排序。搜索状态不支持拖拽排序。置顶项目总是优先显示。
6. 右键卡片可收藏、置顶、打开所在位置或移除引用。
7. 「更多 → 立即备份 / 导出备份」保存应用布局；「恢复本地备份 / 从文件恢复」还原。Ctrl+Z 撤销最近的收纳、分区、排序、收藏及移除操作，保留最近 30 步，重启后仍可撤销。

## 安全与范围

**本 MVP 的收纳是引用管理：桌面原文件和快捷方式仍留在原位置。** 软件不会移动、隐藏或删除它们。因此目前能提供集中启动入口，但还不会自动把 Windows 桌面图标清走。

- 保留每个项目的原始路径，重复扫描不会重复导入，也不会重置已有分类、收藏或置顶。
- 启动原始 .lnk / .url 文件，由 Windows 保留参数、工作目录及关联程序；失效引用显示错误，不猜测替代启动目标。
- 批量收纳与撤销快照使用同一 SQLite 事务，失败会回滚。
- 恢复先检查数据库完整性、表结构、版本及外键，暂存验证通过后再替换当前数据库。
- 恢复前自动创建 `before-restore-*.db`；在恢复列表中可以找回恢复前的状态。
- 备份包含项目引用、分区、排序、收藏、置顶与设置。**不包含原文件内容、背景图片本体或 Windows 桌面图标坐标。**
- 撤销针对应用内整理；不会撤销已启动的程序，也不会改动系统开机启动设置。
- 安全移动快捷方式和恢复 Windows 桌面图标坐标留待后续实现，届时需要单独的文件操作日志和恢复方案。

## 其他功能

- 关闭窗口后驻留托盘；托盘菜单或「更多 → 退出 DeskNest」完全退出。
- Ctrl+Alt+Space 呼出窗口；若快捷键被占用会显示提示。Ctrl+F 聚焦搜索。
- 检测桌面目录变化并提示重新扫描，不自动导入或移动文件。
- 「更多」内切换浅色/深色、调整三档图标大小、选择或清除背景图片。
- 开机启动默认关闭，启用后只修改当前 Windows 用户的 Run 项，以托盘模式启动。
- 同一数据目录只允许一个进程打开，避免互相覆盖。
- 本项目不包含登录、云同步、多设备管理、远程配置、屏幕监控或网吧管理。

## 数据与日志

正常启动自动创建：

```text
%LOCALAPPDATA%/DeskNest/
  desknest.db       项目、分区、设置、撤销记录
  backups/          手动备份、恢复前的安全备份
  desknest.log      轮转错误日志
  background.*     用户选定背景的本地副本
```

这些文件不会提交到 GitHub。备份中的路径可能包含个人信息，分享源码时请不要附带个人数据库或测试数据。

支持独立数据目录，方便测试或便携使用：

```powershell
.\dist\0.1.1\DeskNest\DeskNest.exe --data-dir "E:\DeskNestData"
```

备份恢复保留本地路径，不用于另一台电脑迁移。背景原路径不可用时使用默认背景。

## 开发运行

如果本地已经准备了 `.runtime`，可直接运行（路径按实际位置调整）：

```powershell
cd D:\DeskNest
.\.runtime\python.exe main.py
```

从 GitHub 克隆源码后，安装 Python 3.10+（已验证 Python 3.12.10）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

依赖固定为 PySide6-Essentials 6.12.0 和 pywin32 312；Essentials 提供 Qt Widgets，不引入网页界面。`.runtime` 是开发环境，不随 Git 源码发布。

## 验证与打包

```powershell
.\.runtime\python.exe -X utf8 -m unittest discover -s tests -v
.\.runtime\python.exe -m pip install pyinstaller==6.22.3
.\.runtime\python.exe tools\build.py
```

标准 Python 环境可以将命令中的解释器换成 `.venv\Scripts\python.exe`。

`tools/build.py` 按版本生成 `dist/<版本号>/DeskNest/` 可执行目录与 zip，旧版本正在运行时仍可构建新版本。也可用 `build.ps1`；如果系统禁止 PowerShell 脚本，直接执行上面的 Python 命令即可，无需修改系统策略。

`tools/verify_windows.py` 会短暂打开测试窗口、生成测试快捷方式并验证真实 Windows 启动，全部样本在 `test-data/native` 中。普通单元测试只使用临时文件，不会整理真实桌面。

具体结果与尚未验证的范围见 [验证记录](docs/VALIDATION.md)。

## 项目结构

```text
main.py                        源码启动入口
run.cmd                        双击启动
requirements.txt               运行依赖
pyproject.toml                 Python 包配置
desknest/
  app.py                       应用生命周期、单实例、日志
  config.py                    数据目录
  models.py                    项目和分区模型
  storage/database.py          SQLite、事务、撤销、备份校验与恢复
  services/
    scanner.py                 只读扫描
    launcher.py                Windows Shell 启动
    backup.py                  备份用例
    monitor.py                 桌面变化提示
  windows/
    desktop.py                 真实桌面位置
    startup.py                 当前用户开机启动
    hotkey.py                  全局热键
  ui/
    main_window.py             主窗口和操作
    widgets.py                 卡片绘制、拖拽、背景
    dialogs.py                 收纳与恢复对话框
    theme.py                   浅色和深色主题
tests/                         核心流程和 Qt 交互验证
tools/                         打包与 Windows 验证
docs/                          架构、验证记录
dist/                          生成产物（Git 忽略）
```

业务逻辑、数据和系统接口独立于界面，便于后续增加本地功能。

## 后续更新

项目将持续迭代。后续方向包括拖放与界面体验优化、失效引用修复，以及更多本地整理能力。具体功能和发布时间以 Releases 与更新记录为准；真实文件移动、桌面图标坐标恢复目前尚未实现。

## 开源许可

DeskNest 自身源码采用 [MIT License](LICENSE)。第三方组件按各自许可证分发，详见 [第三方说明](docs/THIRD_PARTY.md)。
