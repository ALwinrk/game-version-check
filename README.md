# 游戏版本自动排查工具 v5

导入 Excel 表格，自动查询 Google Play + 4 个 APK 站，比对游戏版本变化并写回结果。
**v5 新增：版本号 (version code) 列支持 + 桌面 GUI 应用。**

## 新特性 (v5)

- **版本号对比** — 新增"当前后台版本号"列，优先对比整数 version code，解决版本名不变但实际有更新的假阴性问题
- **桌面 GUI** — 基于 CustomTkinter 的图形界面，文件选择 → 一键排查 → 表格展示结果
- **打包分发** — PyInstaller 单文件 .exe，同组同事无需安装 Python 环境
- **增强解析器** — 10 个正则模式覆盖更多 APK 站的 version code 格式

## 新特性 (v4)

- **并发查询** — 5 个数据源同时请求，单个游戏查询时间从 ~5s 降至 ~2s
- **模块化架构** — 拆分 HTTP / 解析 / 数据源 / Excel / CLI，易于维护和扩展
- **自动重试** — 网络异常时自动重试（指数退避），提高成功率
- **Proper Logging** — 分级日志输出，便于排查问题
- **环境变量配置** — 支持 `GVC_*` 环境变量覆盖所有配置（见 [gvc/config.py](gvc/config.py)）
- **单元测试** — pytest 测试覆盖核心逻辑

## 功能

| 模式 | 命令 | 说明 |
|------|------|------|
| GUI 桌面 | `python run_gui.py` 或双击 .exe | 图形界面，推荐同事使用 |
| 导入表格 | `python game_version_checker.py 表格.xlsx` | 命令行全表排查 |
| 单独排查 | `python game_version_checker.py --check 包名 --current 版本` | 命令行查单个/多个包名 |

也可以直接**双击 `启动工具.bat`**，交互式选择模式。

## Excel 表格格式

| 游戏名 | 游戏包名 | 当前后台版本名 | 当前后台版本号 | 日期列... |
|--------|---------|-------------|-------------|-----------|
| PUBG MOBILE | com.tencent.ig | 4.4.0 | 12345678 | - |
| 原神 | com.miHoYo.GenshinImpact | 6.6.0 | 98765432 | 6.5.0→6.6.0 |

> **注意**: D 列（当前后台版本号）为 v5 新增列。首次运行 GUI 或迁移脚本时会自动插入并填充。

脚本读取后会在右侧新增日期列，填入排查结果：
- `-` — 无变化
- `vc:100→200` — 版本号有更新（优先展示 version code 变化）
- `4.3.0→4.4.0 (vc:200)` — 版本名+版本号均有变化（黄色标记）
- 首次运行且 C/D 列为空 → 自动填充版本名和版本号

## 数据源

| 数据源 | 技术 |
|--------|------|
| Google Play | google-play-scraper |
| APKPure | requests + BeautifulSoup |
| APKCombo | requests + curl_cffi |
| APKVision | requests + curl_cffi |
| APKMirror | requests + curl_cffi |

版本判定：≥2 个源一致才采纳，否则优先 Google Play。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 示例

```bash
# GUI 桌面（推荐）
python run_gui.py

# 排查 Excel 表格（命令行）
python game_version_checker.py 海外游戏版本表.xlsx

# 单独查 PUBG，对比后台版本 4.3.0
python game_version_checker.py --check com.tencent.ig --current 4.3.0

# 批量查
python game_version_checker.py -c "com.tencent.ig,com.roblox.client"
```

## 打包为 EXE

```bash
# 一键构建（双击 build_exe.bat 或运行）
pip install pyinstaller
pyinstaller --clean --noconfirm gvc_gui.spec

# 输出: dist/游戏版本排查工具.exe
```

构建出的 .exe 可以分发给同事，无需安装 Python。

> 💡 **网络问题？** 大部分 APK 站点在中国大陆无法直连。在 GUI 中打开「设置 → 选项」，配置 HTTP/HTTPS 代理即可（支持 clash/v2ray 等本地代理，如 `http://127.0.0.1:7890`）。

## 开发

```bash
pip install -e ".[dev]"   # 安装开发依赖
pytest                    # 运行测试
ruff check .              # 代码检查
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GVC_MAX_GAME_WORKERS` | 3 | 并发游戏数 |
| `GVC_MAX_SOURCE_WORKERS` | 5 | 每个游戏并发数据源数 |
| `GVC_MAX_RETRIES` | 3 | HTTP 请求重试次数 |
| `GVC_LOG_LEVEL` | INFO | 日志级别 |
| `GVC_HTTP_PROXY` | (空) | HTTP 代理地址 |
| `GVC_HTTPS_PROXY` | (空) | HTTPS 代理地址 |
