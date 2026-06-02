# 游戏版本自动排查工具 v5.2

导入 Excel 表格，自动查询 **6 个 APK 数据源**，比对游戏版本变化并写回结果。
**CLI + GUI 双界面，支持 APK 自动下载。**

## 新特性 (v5.2)

| 特性 | 说明 |
|------|------|
| **Scrapling 双后端** | Fetcher (curl_cffi, 快速) + StealthySession (Chromium, CF 绕过) |
| **6 源全激活** | Google Play + APKPure + APKCombo + APKMirror + APKVision + APKDL |
| **APK 自动下载** | 支持 FDM / IDM / aria2 / Motrix 外部管理器 + 内置下载 |
| **站点适配** | APKPure 搜索→详情页两步提取, APKCombo API 重定向解析 |
| **CF 超时保护** | StealthySession 45s 硬超时，防止 Cloudflare turnstile 无限等待 |
| **Windows UTF-8** | 终端日志兼容 GBK/UTF-8，PyInstaller GUI 模式无报错 |

## 数据源

| 数据源 | 后端 | 代理 | 说明 |
|--------|------|------|------|
| Google Play | google-play-scraper | 需要 | 最权威来源，始终可用 |
| APKPure | Fetcher | 需要 | 搜索页→详情页两步提取 |
| APKCombo | Fetcher | 需要 | /api/app 重定向到详情页 |
| APKMirror | Fetcher / StealthySession | 需要 | CF 保护，Fetcher 可能被拦 |
| APKVision | StealthySession | 部分需要 | CF non-interactive turnstile |
| APKDL | StealthySession | 部分需要 | 域名已停放，暂不可用 |

版本判定：≥2 个源一致直接采纳，否则优先 Google Play，最后取数字最大版本。

## 功能

| 模式 | 命令 | 说明 |
|------|------|------|
| GUI 桌面 | `python run_gui.py` 或双击 .exe | 图形界面，推荐同事使用 |
| 导入表格 | `python game_version_checker.py 表格.xlsx` | 命令行全表排查 |
| 单独排查 | `python game_version_checker.py --check 包名` | 命令行查单个/多个包名 |

也可以直接**双击 `启动工具.bat`**，交互式选择模式。

## Excel 表格格式

| 游戏名 | 游戏包名 | 当前后台版本名 | 当前后台版本号 | 日期列... |
|--------|---------|-------------|-------------|-----------|
| Honor of Kings | com.levelinfinite.sgameGlobal | 11.3.1.3 | 1013719 | - |
| PUBG MOBILE | com.tencent.ig | 4.4.0 | 12345678 | vc:12345678→12345680 |

脚本读取后会在右侧新增日期列，填入排查结果：
- `-` — 无变化
- `vc:100→200` — 版本号有更新
- `4.3.0→4.4.0` — 版本名变化
- 首次运行且 C/D 列为空 → 自动填充

## 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium-headless-shell   # StealthySession 浏览器后端
```

## 示例

```bash
# GUI 桌面（推荐）
python run_gui.py

# 排查 Excel 表格
python game_version_checker.py 海外游戏版本表.xlsx

# 单独查包名（走代理）
set GVC_HTTP_PROXY=http://127.0.0.1:7897
set GVC_HTTPS_PROXY=http://127.0.0.1:7897
python game_version_checker.py --check com.levelinfinite.sgameGlobal

# 禁用慢速源（仅查快速源，更快）
set GVC_DISABLE_STEALTH=1
python game_version_checker.py --check com.levelinfinite.sgameGlobal
```

## 打包为 EXE

```bash
pip install pyinstaller
pyinstaller --distpath ./dist --workpath ./build gvc_gui.spec

# 输出: dist/游戏版本排查工具.exe (~185 MB, 含 Chromium)
```

构建出的 .exe 自包含 Python + Chromium + 全部依赖，无需安装任何环境即可运行。

> **代理提示**：大部分 APK 站点在中国大陆无法直连。GUI 启动时已默认预填 `127.0.0.1:7897`，可在「设置 → 选项」中修改。

## 开发

```bash
pip install -e ".[dev]"
pytest                    # 69 个单元测试
ruff check .              # 代码检查
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GVC_HTTP_PROXY` | (空) | HTTP 代理 |
| `GVC_HTTPS_PROXY` | (空) | HTTPS 代理 |
| `GVC_DISABLE_STEALTH` | (空) | 设为 1 禁用慢速源 |
| `GVC_MAX_GAME_WORKERS` | 3 | 并发游戏数 |
| `GVC_MAX_SOURCE_WORKERS` | 5 | 并发数据源数 |
| `GVC_REQUEST_TIMEOUT` | 10 | HTTP 超时(秒) |
| `GVC_STEALTH_TIMEOUT` | 15 | 慢速源超时(秒) |
| `GVC_JS_RENDER_TIMEOUT` | 20 | JS 渲染超时(秒) |
| `GVC_MAX_RETRIES` | 3 | 重试次数 |
| `GVC_LOG_LEVEL` | INFO | 日志级别 |
| `GVC_DOWNLOAD_DIR` | ./downloads | APK 下载目录 |
| `GVC_DOWNLOAD_MANAGER` | auto | fdm / idm / aria2 / motrix |
| `GVC_ALLOW_32BIT` | 0 | 设为 1 允许下载 32 位 APK |

## 项目结构

```
gvc/              核心库 (12 模块)
  config.py         全局配置 (环境变量可覆盖)
  http_client.py    Scrapling 双后端 HTTP 客户端
  sources.py        6 数据源并发查询
  parser.py         版本号/版本名 HTML 解析 (10 正则模式)
  version.py        版本标准化/比较/最佳版本判定
  downloader.py     APK 下载 (管理器 + 内置)
  excel_handler.py  Excel 读写
  models.py         数据结构
  cli.py            CLI 命令行
  history.py        版本历史持久化
  logging_setup.py  日志配置
gvc_gui/          GUI 桌面应用 (6 模块)
tests/            69 个单元测试
```
