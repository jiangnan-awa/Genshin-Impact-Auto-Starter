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
- GUI 实际代码位于 `autostarter/gui/`

---

## 4. 常用命令行参数

主程序（`python main.py` / `python -m autostarter`）支持以下参数（解析逻辑在 `autostarter/app_main.py`）：

| 参数 | 说明 |
|------|------|
| `--signin-only` / `-s` | 仅执行签到，不启动游戏 |
| `--mod` / `--mod-mode` | 临时强制启用 Mod 启动模式（无视配置） |
| `--no-onedragon` / `--skip-onedragon` | 跳过一条龙任务，直接按普通方式启动 BetterGI |

示例：

```powershell
python -m autostarter --signin-only
python main.py --mod-mode
python main.py --no-onedragon
python main.py --signin-only --no-onedragon
```

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
