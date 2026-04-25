# 开发指南

本文档面向开发者，提供源码运行、调试和项目结构说明。普通用户使用请参阅 [README.md](README.md)。

## 环境准备

- Windows 10/11
- Python 3.10+
- Git（可选）
- Chrome（用于自动获取 Cookie 功能）

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
```

### 配置界面

```powershell
python gui.py
```

## 命令行参数

| 参数              | 说明       |
| --------------- | -------- |
| `--preset <id>` | 使用指定流程预设 |

示例：

```powershell
python main.py --preset <id>
```

<br />

## 项目结构

- `main.py` - 主程序入口
- `gui.py` - 配置界面入口
- `autostarter/` - 核心包
  - `__main__.py` - 包入口点
  - `app_main.py` - 主流程和命令行解析
  - `account.py` - 账号数据模型
  - `account_manager.py` - 账号管理
  - `captcha.py` - 验证码处理
  - `config.py` - 配置管理
  - `config_paths.py` - 配置文件路径
  - `cookie_login.py` - Cookie登录
  - `driver_downloader.py` - 浏览器驱动下载
  - `error.py` - 错误处理
  - `flow_executor.py` - 流程执行器
  - `flow_presets.py` - 流程预设管理
  - `gamecheckin.py` - 游戏签到
  - `launcher.py` - 启动逻辑
  - `log_actions.py` - 日志操作
  - `loghelper.py` - 日志助手
  - `login.py` - 登录逻辑
  - `mihoyo_api.py` `mihoyobbs.py`- 米游社 API
  - `qr_login_handler.py` - 扫码登录
  - `request.py` - HTTP请求
  - `secret_store.py` - 密钥存储
  - `security.py` - 安全相关
  - `setting.py` - 设置管理
  - `shortcut_utils.py` - 快捷方式工具
  - `tools.py` - 工具函数
  - `gui/` - 配置界面 GUI
    - `app.py` - GUI应用主入口
    - `autosave.py` - 自动保存
    - `bindings.py` - 数据绑定
    - `dpi.py` - DPI处理
    - `state.py` - 应用状态
    - `pages/` - 页面组件
      - `accounts.py` - 账号管理页面
      - `presets.py` - 预设管理页面
      - `signin.py` - 签到页面
      - `startup.py` - 启动设置页面
    - `widgets/` - 自定义组件
      - `forms.py` - 表单组件
      - `sidebar.py` - 侧边栏
      - `toast.py` - 通知组件

## 配置文件

源码运行时配置文件位于 `autostarter/config/` 目录：

- `settings.json` - 全局设置
- `accounts.json` - 账号列表
- `secret_store_dpapi.json - 账号加密`
- `presets.json` - 流程预设

