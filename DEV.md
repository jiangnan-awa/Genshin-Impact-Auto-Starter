# 开发指南（Windows）

本文档面向在 Windows 上直接运行/调试源码的开发者。若只是使用成品，请看 README 的「如何使用」。

---

## 1. 环境准备

- Windows 10/11
- Python 3.x（建议 3.10+）
- （可选）Git
- （可选）Chrome / Edge / Firefox（用于「自动获取 Cookie」功能的 Selenium 浏览器自动化）

> GUI 依赖 `tkinter`：一般随 Python Windows 安装包自带；若你的 Python 精简版缺少 `tkinter`，GUI/自动获取 Cookie 会报错。

---

## 2. 安装依赖

在项目根目录（包含 `requirements.txt`、`main.py`、`gui.py` 的目录）执行：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

### GUI v2 依赖（customtkinter）

新版 GUI（v2）基于 `customtkinter`，需要额外安装：

```powershell
python -m pip install customtkinter
```

---

## 3. 运行方式（源码）

### 3.1 主程序（签到 + 启动）

两种启动方式等价（都进入 `autostarter.app_main:main`）：

```powershell
python main.py
python -m autostarter
```

### 3.2 配置 GUI（单独打开配置界面）

```powershell
python gui.py
```

说明：
- 根目录 `gui.py` 是薄入口（用于保持 `python gui.py` 与 PyInstaller 入口兼容）
- GUI v2 实际代码位于 `autostarter/gui_v2/`（默认）
- legacy GUI 位于 `autostarter/gui/`（可回退）

#### GUI v2 / legacy 切换

- 默认启动 GUI v2（`autostarter/gui_v2/`）
- 如需切回旧版（legacy GUI，`autostarter/gui/`），可使用：

```powershell
python gui.py --legacy
```

或通过环境变量：

```powershell
$env:AUTOSTARTER_GUI="legacy"
python gui.py
```

---

## 4. 常用命令行参数

主程序（`python main.py` / `python -m autostarter`）支持以下参数（解析逻辑在 `autostarter/app_main.py`）：

| 参数 | 说明 |
|------|------|
| `--signin-only` / `-s` | 仅执行签到，不启动游戏 |
| `--mod` / `--mod-mode` | 临时强制启用 Mod 启动模式（无视配置） |
| `--no-onedragon` / `--skip-onedragon` | 跳过一条龙任务，直接按普通方式启动 BetterGI |
| `--preset <id>` / `--preset=<id>` | 使用指定「启动预设」启动（来自 `presets.json`）。传入后将**不弹出** Windows 的“本次临时开关”窗口 |

示例：

```powershell
python -m autostarter --signin-only
python main.py --mod-mode
python main.py --no-onedragon
python main.py --signin-only --no-onedragon
python main.py --preset <id>
```

### 4.1 Windows：无 preset 才弹窗的“临时开关”

在 Windows 上，如果**未**传入 `--preset`，主程序启动时会弹出一个简易窗口让用户选择“仅本次运行生效”的临时开关（仅签到 / 跳过一条龙 / 强制 Mod），并且**不会写入** `settings.json`。

当传入 `--preset <id>` 时，为了便于桌面快捷方式/计划任务等无交互场景，上述弹窗会被抑制。

---

## 5. 调试建议（VS Code）

1. 选择解释器为项目的 `.venv`
2. 以项目根目录作为工作目录（`cwd`）
3. 常用调试入口：
   - `main.py`（带参数调试）
   - `gui.py`（调试配置界面）
   - `-m autostarter`（验证包入口）

示例 `launch.json`（按需取用）：

```jsonc
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run main.py",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/main.py",
      "cwd": "${workspaceFolder}",
      "args": ["--signin-only"]
    },
    {
      "name": "Run gui.py",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/gui.py",
      "cwd": "${workspaceFolder}"
    },
    {
      "name": "Run -m autostarter",
      "type": "python",
      "request": "launch",
      "module": "autostarter",
      "cwd": "${workspaceFolder}"
    }
  ]
}
```

---

## 6. 配置文件（settings.json / accounts.json）

程序会在“运行目录”生成/读取以下文件：

- `settings.json`：全局设置（dict）
- `accounts.json`：账号列表（`{"accounts": [...]}`）

### 6.1 源码运行时的文件位置

源码直接运行（`python main.py` / `python -m autostarter`）时，配置文件默认写在 `autostarter/` 包目录下（与 `autostarter/account_manager.py` 同级）。

### 6.2 旧版自动迁移与备份

若检测到旧版 `accounts.json` 同时包含 `accounts` + `settings`，且同目录不存在 `settings.json`，程序会自动：

1. 生成 `settings.json`（从旧文件拆分出来）
2. 备份原 `accounts.json` 为 `accounts.json.bak`
3. 将 `accounts.json` 重写为仅含 `accounts`

---

## 7. 启动预设（presets.json）

启动预设用于保存“启动相关设置”的多个方案（BetterGI/外置启动器/Mod 等），便于一键启动或做桌面快捷方式。

- 实现：`/workspace/Genshin-Impact-Auto-Starter-clean/autostarter/presets.py`（`PresetManager`）
- 文件名：`presets.json`
- 位置：与 `settings.json` / `accounts.json` 同目录
  - frozen（PyInstaller 打包）环境：`sys.executable` 所在目录
  - 源码运行：`autostarter/` 包目录

数据结构（`version=1`）：

```jsonc
{
  "version": 1,
  "active_preset_id": "",
  "presets": [
    {
      "id": "uuid-hex",
      "name": "显示名称",
      "settings": { "bettergi_enabled": true, "...": "..." },
      "created_at": "2026-04-16T00:00:00Z",
      "updated_at": "2026-04-16T00:00:00Z"
    }
  ]
}
```

### GUI v2：预设页

GUI v2 的预设页位于：`/workspace/Genshin-Impact-Auto-Starter-clean/autostarter/gui_v2/pages/presets.py`，提供：

- 预设管理（新建/从当前配置生成/复制/重命名/删除）
- `▶ 一键启动`：直接调用 `game_launcher.launch(settings=preset_settings)`（后台线程）
- Windows 打包版生成桌面快捷方式：仅 `sys.platform == "win32"` 且 `sys.frozen == True` 时可用  
  - 通过 PowerShell + `WScript.Shell` 生成 `.lnk`，参数为 `--preset <id>`
