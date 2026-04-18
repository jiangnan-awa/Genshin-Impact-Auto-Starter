# 开发指南（Windows）

本文档面向在 Windows 上直接运行/调试源码的开发者。若只是使用成品，请看 README.

---

## 1. 环境准备

- Windows 10/11
- Python 3.x（建议 3.10+）
- （可选）Git
- （可选）Chrome / Edge / Firefox（用于「自动获取 Cookie」功能的 Selenium 浏览器自动化）

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
构建运行：
```powershell
.\build.ps1
```
### 3.1 主程序（签到 + 启动）

两种启动方式等价：

```powershell
python main.py
python -m autostarter
```

### 3.2 配置 GUI（单独打开配置界面）

```powershell
python gui.py
```

---

## 4. 常用命令行参数

主程序（`python main.py` / `python -m autostarter`）支持以下参数（解析逻辑在 `autostarter/app_main.py`）：

| 参数 | 说明 |
|------|------|
| `--signin-only` / `-s` | 仅签到 |
| `--mod` / `--mod-mode` | 临时启用 Mod 启动模式 |
| `--no-onedragon` / `--skip-onedragon` | 跳过一条龙任务，直接按普通方式启动 BetterGI |
| `--preset <id>` / `--preset=<id>` | 使用指定「流程预设」启动（来自 `config/presets.json`）。|

示例：

```powershell
python -m autostarter --signin-only
python main.py --mod-mode
python main.py --no-onedragon
python main.py --signin-only --no-onedragon
python main.py --preset <id>
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

## 6. 配置文件（config/）

程序会在“运行目录”生成/读取 `config/` 子目录下的文件（避免根目录混乱）：

- `config/settings.json`：全局设置（dict）
- `config/accounts.json`：账号列表
- `config/presets.json`：流程预设（flow）

### 6.1 源码运行时的文件位置

源码直接运行（`python main.py` / `python -m autostarter`）时，配置文件默认写在 `autostarter/` 包目录下的 `config/` 中（与 `autostarter/account_manager.py` 同级）。

---

## 7. 流程预设（config/presets.json）

流程预设用于保存“启动步骤顺序 + 等待时间”的多个方案（外置启动器/Mod/BetterGI/一条龙/直接原神/等待），便于一键启动或做桌面快捷方式。

- 实现：`autostarter/flow_presets.py`（`FlowPresetManager`）
- 文件名：`config/presets.json`
- 位置：与 `config/settings.json` / `config/accounts.json` 同目录
  - frozen（PyInstaller 打包）环境：`sys.executable` 所在目录
  - 源码运行：`autostarter/` 包目录

数据结构（`version=2`）：

```jsonc
{
  "version": 2,
  "active_preset_id": "",
  "presets": [
    {
      "id": "uuid-hex",
      "name": "显示名称",
      "flow": [
        {"type":"external_launcher"},
        {"type":"wait","seconds":5},
        {"type":"mod"}
      ],
      "created_at": "2026-04-16T00:00:00Z",
      "updated_at": "2026-04-16T00:00:00Z"
    }
  ]
}
```
