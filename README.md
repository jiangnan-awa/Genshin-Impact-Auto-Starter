# 原神自动签到与启动器 (Genshin Impact Auto-Starter)
***
# ⚠️ 警告：禁止传播
 
本项目**严禁**在以下平台传播：
- 视频平台（如B站、YouTube等）
- 社交媒体（如微博、小红书、QQ等）
***
现在很多启动器都有一键签到的功能，但不够便捷。本项目主要用于一键签到和启动，不需要额外点击。

***

## 功能特性

- 后台静默运行，配置完成一键启动
- 支持签到：原神、崩坏：星穹铁道、绝区零、米游社社区
- 支持多账号
- Cookie 自动获取（Chrome），米游社签到 Cookie 支持扫码获取
- 日志文件记录签到和启动
- 一键启动游戏，支持多种启动模式：
  - BetterGI 启动
  - 直接启动原神
  - 外置启动器
  - Mod 启动
- Cookie 使用 Windows DPAPI 加密本地存储

***

## 如何使用

1. 下载 Release 中最新版本
2. 解压至一个空目录
3. 运行AutoStarterConfig.exe
4. 配置好各项参数
5. 运行设置好的预设或直接启动AutoStarter.exe

***

## 获取 Cookie方法：

游戏 Cookie 自动获取只适配 Chrome 浏览器。
其它浏览器按照 手动获取游戏 Cookie 方法 获取 Cookie。
含 stoken 的米游社 Cookie 通过扫码获取 stoken（在配置界面选择「扫码获取 stoken」）。

### 手动获取游戏 Cookie 方法

1. 打开浏览器，进入**无痕模式**（Edge 为「新建 InPrivate 窗口」）
2. **先**登录 <https://bbs.mihoyo.com/ys/>\
   **再**登录 <https://user.mihoyo.com/>\
   **（请严格按照步骤顺序登录，否则可能 Cookie 不全导致功能异常）**
3. 登录完成后按 `F12` 进入开发者工具，点击「Console / 控制台」**（在第二个打开的网页上操作）**
4. 输入以下内容并回车执行，在弹出的确认窗口点击「确定」后 Cookie 将复制到剪贴板：
   ```javascript
   var cookie=document.cookie;var ask=confirm('要复制该cookie到剪贴板吗?\n\n'+cookie);if(ask==true){copy(cookie);msg=cookie}
   ```

**Cookie 使用 Windows DPAPI（`CryptProtectData`）加密后存储在本地配置文件中，仅当前 Windows 用户可解密，不会明文保存。**

***

## 配置说明

### BetterGI 模式

在配置界面启用 BetterGI 并填写路径后，程序会使用 BetterGI 启动游戏。

- 若启用「一条龙模式」且填写了「一条龙配置名称」，程序会通过命令行调用 `BetterGI.exe startOneDragon <配置名称>` 运行指定配置。
- 若未填写配置名称，则会运行 BetterGI 页面当前选中的一条龙配置。
- 「第二个一条龙配置」填入后检测到第一个配置结束后运行此配置。

### 直接启动原神

关闭 BetterGI，填写原神路径后，程序会直接启动原神。

### 外置启动器模式

开启「外置启动器模式」并填写启动器路径及启动参数后，程序会调用该启动器。（使用例：FufuLauncher注入）

### Mod 启动模式

开启「Mod 启动模式」并配置好程序路径后，启动器会运行该程序，并附加参数 `--auto-launch`。（该项只适配GIML，项目地址<https://github.com/CHN-HelloWorld/GIML）>

### 预设

进入「预设」页：

- 预设列表管理：新建/复制/重命名/删除/设为默认
- 流程编辑：添加步骤 / 上移下移 / 删除 / 编辑“等待秒数”
- `▶ 一键启动`：严格按该预设的 flow 顺序启动（后台线程执行并 toast 提示）
- Windows 打包版：可为任意预设「生成桌面快捷方式」（`.lnk`）
  - 快捷方式实质等价于：`AutoStarter.exe --preset <id>`

当传入 `--preset <id>` 时,主程序将从 `config/presets.json` 读取该预设的 flow 执行

## 命令行参数

支持的命令行参数详见[开发指南](DEV.md#4-常用命令行参数)。

***

## 配置文件

程序会在运行目录下创建 `config/` 子目录存储配置文件。

***

## 开发者信息

源码运行、调试和项目结构说明详见[开发指南](DEV.md)。

***

## License

[MIT](LICENSE)
