# 原神自动签到与启动器 (Genshin Impact Auto-Starter)

现在很多启动器都有一键签到的功能，但不够轻量。本项目主要用于一键签到和启动，不需要额外点击。

游戏 Cookie 自动获取暂时只确认了 Chrome 浏览器适配，其它浏览器未经测试。含 stoken 的米游社 Cookie 通过扫码获取 stoken（在配置界面选择「扫码获取 stoken」）。

---

## 功能特性

- 自动每日签到：原神、崩坏：星穹铁道、绝区零、米游社社区
- 每天只执行一次签到（可在配置中关闭）
- 支持多账号
- Cookie 自动获取（Chrome）或手动粘贴
- 含 stoken 的米游社 Cookie 支持扫码获取
- 一键启动游戏，支持多种启动模式：
  - BetterGI 启动（含一条龙任务）
  - 直接启动原神
  - 外置启动器模式
  - Mod 启动模式（在主流程前运行指定程序并附加 `--auto-launch`）
- 签到结果弹窗提示，无错误时 5 秒自动关闭
- Cookie 使用 Windows DPAPI 加密本地存储

---

## 如何使用

1. 下载 Release 中的最新版本压缩包
2. 解压压缩包至一个空目录
3. 运行程序
4. 按照程序提示获取 Cookie（米游社 Cookie 通过扫码获取 stoken）
5. 原神，启动！

---

## 手动获取游戏 Cookie 方法

1. 打开浏览器，进入**无痕模式**（Edge 为「新建 InPrivate 窗口」）

2. 先登录 [https://bbs.mihoyo.com/ys/](https://bbs.mihoyo.com/ys/)  
   再登录 [https://user.mihoyo.com/](https://user.mihoyo.com/)  
   **（请严格按照步骤顺序登录，否则可能 Cookie 不全导致功能异常）**

3. 登录完成后按 `F12` 或右键「检查」进入开发者工具，点击「Console / 控制台」**（在第二个打开的网页上操作）**

4. 输入以下内容并回车执行，在弹出的确认窗口点击「确定」后 Cookie 将复制到剪贴板：

   ```javascript
   var cookie=document.cookie;var ask=confirm('要复制该cookie到剪贴板吗?\n\n'+cookie);if(ask==true){copy(cookie);msg=cookie}
   ```

---

## 启动模式说明

### BetterGI 模式（默认）

在配置界面启用 BetterGI 并填写路径后，程序会自动启动 BetterGI。若配置了「一条龙」任务，将先切换到对应一条龙配置，任务完成后再切换回原配置。

### 直接启动原神

在配置界面关闭 BetterGI，填写原神游戏路径后，程序会直接启动原神。

### 外置启动器模式

在配置界面开启「外置启动器模式」并填写启动器路径及启动参数后，程序会调用该启动器来启动游戏，可用于对接第三方启动器（如官方启动器）。

### Mod 启动模式

在配置界面开启「Mod 启动模式」并配置好程序路径后，启动器会在原有启动流程最前面先运行该程序，并附加参数 `--auto-launch`，然后继续按原流程启动 BetterGI / 原神。也可在命令行添加 `--mod-mode` 临时启用（见下方命令行参数）。

---

## 命令行参数

以命令行方式运行 `AutoStarter.exe` 时，支持以下参数：

| 参数 | 说明 |
|------|------|
| `--signin-only` / `-s` | 仅执行签到，不启动游戏 |
| `--mod` / `--mod-mode` | 临时强制启用 Mod 启动模式（无视配置） |
| `--no-onedragon` / `--skip-onedragon` | 跳过一条龙任务，直接按普通方式启动 BetterGI |

示例：

```bash
AutoStarter.exe --signin-only
AutoStarter.exe --mod-mode
AutoStarter.exe --no-onedragon
AutoStarter.exe --signin-only --no-onedragon
```

---

## 配置项说明

| 配置项 | 说明 |
|--------|------|
| BetterGI 路径 | BetterGI 可执行文件路径 |
| 一条龙配置 | 启动时切换到的一条龙任务配置名 |
| 一条龙完成后配置 | 一条龙完成后切换回的配置名 |
| 原神路径 | 原神游戏可执行文件路径（BetterGI 关闭时使用） |
| 外置启动器模式 | 使用第三方启动器启动游戏 |
| 外置启动器路径 | 第三方启动器可执行文件路径 |
| 外置启动器参数 | 传递给第三方启动器的启动参数 |
| Mod 启动模式 | 在主流程前运行指定程序（附加 `--auto-launch`） |
| Mod 程序路径 | Mod 程序可执行文件路径 |
| Mod 启动等待时间 | 运行 Mod 程序后等待的秒数（默认 6 秒） |
| 每天只签到一次 | 开启后同一天内再次运行不会重复签到 |
| 签到顺序 | 各游戏签到的执行顺序 |

---

## 配置文件说明（settings.json / accounts.json）

程序运行目录下会生成两个 JSON 文件用于持久化数据：

- `settings.json`：**全局设置**（启动模式、路径、签到顺序、每天只签到一次等）
- `accounts.json`：**账号列表**（格式为 `{"accounts": [...]}`）

### 旧版自动迁移（accounts.json 混存 settings）

旧版本可能会把账号与设置一起写在 `accounts.json` 中：

```jsonc
{
  "accounts": [...],
  "settings": {...}
}
```

新版启动时若检测到上述“混存格式”，且同目录下 **不存在** `settings.json`，会自动执行迁移：

1. 从旧 `accounts.json` 中提取 `settings` 写入 `settings.json`
2. 备份原 `accounts.json` 为 `accounts.json.bak`
3. 将 `accounts.json` 重写为仅包含 `accounts`

> 打包版（`AutoStarter.exe`）下，这些文件位于 exe 同目录；源码运行时位于 `autostarter/` 包所在目录（与 `autostarter/account_manager.py` 同级）。

---

## 安全说明

Cookie 使用 Windows DPAPI（`CryptProtectData`）加密后存储在本地配置文件中，仅当前 Windows 用户可解密，不会明文保存。

---

## 构建

依赖 Python 3.x，使用 PyInstaller 打包。主要依赖库：

- `tkinter`（GUI）
- `requests`（HTTP 请求）
- `selenium`（Cookie 自动获取）
- `Pillow`（图像处理）
- `pywin32`（Windows DPAPI 加密）

打包命令（参考 `AutoStarter.spec`）：

```bash
pyinstaller AutoStarter.spec
```

---

## 项目结构（开发者）

### 开发/调试文档

源码运行与调试步骤见：[DEV.md](DEV.md)（Windows）。

### 重构后的目录结构（`autostarter` 包）

核心逻辑已集中到 `autostarter/` 包内（即 `autostarter.*`），仓库根目录仅保留入口脚本与打包配置：

- `main.py`：主程序入口脚本（实际调用 `autostarter.app_main:main`）
- `gui.py`：配置界面入口脚本（薄入口）
  - 默认启动 GUI v2：`autostarter.gui_v2.app:main`
  - 传入 `--legacy` 或设置环境变量 `AUTOSTARTER_GUI=legacy` 可切回旧版 GUI：`autostarter.gui.app:main`
  - 可单独打包为 `AutoStarterConfig`，见 `AutoStarterConfig.spec`
- `autostarter/`：核心逻辑包（签到、启动、账号/配置、网络请求、日志等）
  - `app_main.py`：主流程 + 命令行参数解析
  - `gui/`：配置界面 GUI（已按 pages/widgets/style/bindings 拆分）
  - `gui_v2/`：配置界面 GUI v2（customtkinter，侧边栏 + 分区页面，优先易用）
  - `account_manager.py` / `account.py`：账号与配置管理
  - `mihoyo_api.py` / `mihoyobbs.py` / `request.py`：米游社相关 API 与请求封装
  - `qr_login_handler.py`：扫码登录获取 `stoken`
  - `launcher.py`：启动流程与等待逻辑
  - 其它模块：按功能拆分（安全、工具、驱动下载等）

---

## License

[MIT](LICENSE)
