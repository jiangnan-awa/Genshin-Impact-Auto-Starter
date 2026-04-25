# 开发指南

本文档面向开发者，提供源码运行、调试和项目结构说明。用户使用请参阅 [README.md](README.md)。

## 环境准备

- Windows 10/11
- Python 3.10+
- Git（可选）
- Chrome/Edge/Firefox（用于自动获取 Cookie 功能）

## 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

## 运行方式

### 构建运行
```powershell
.\build.ps1
```

### 主程序
```powershell
python main.py
python -m autostarter
```

### 配置界面
```powershell
python gui.py
```

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--preset <id>` | 使用指定流程预设 |

示例：
```powershell
python main.py --preset <id>

说明：当前版本主程序仅支持通过 `--preset <id>` 启动；未提供该参数会直接退出并提示用法。
```

## 调试配置（VS Code）

1. 选择项目 `.venv` 作为解释器
2. 设置工作目录为项目根目录
3. 调试入口：
   - `main.py`（带参数调试）
   - `gui.py`（配置界面调试）
   - `-m autostarter`（包入口验证）

## 项目结构

- `main.py` - 主程序入口
- `gui.py` - 配置界面入口
- `autostarter/` - 核心包
  - `app_main.py` - 主流程和命令行解析
  - `gui/` - 配置界面 GUI
  - `account_manager.py` - 账号管理
  - `mihoyo_api.py` - 米游社 API
  - `qr_login_handler.py` - 扫码登录
  - `launcher.py` - 启动逻辑
  - `flow_presets.py` - 流程预设管理

## 配置文件

源码运行时配置文件位于 `autostarter/config/` 目录：
- `settings.json` - 全局设置
- `accounts.json` - 账号列表
- `presets.json` - 流程预设
