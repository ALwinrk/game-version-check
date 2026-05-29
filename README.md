# 游戏版本自动排查工具 v3

导入 Excel 表格，自动查询 Google Play + 4 个 APK 站，比对游戏版本变化并写回结果。

## 功能

| 模式 | 命令 | 说明 |
|------|------|------|
| 导入表格 | `python game_version_checker.py 表格.xlsx` | 全表排查，结果写入新列 |
| 单独排查 | `python game_version_checker.py --check 包名 --current 版本` | 查单个/多个包名，比对后台版本 |

也可以直接**双击 `启动工具.bat`**，交互式选择模式。

## Excel 表格格式

| 游戏名 | 游戏包名 | 当前后台版本名 |
|--------|---------|-------------|
| PUBG MOBILE | com.tencent.ig | 4.4.0 |
| 原神 | com.miHoYo.GenshinImpact | 6.6.0 |

脚本读取后会在右侧新增日期列，填入排查结果：
- `-` — 无变化
- `4.3.0→4.4.0` — 有更新（黄色标记）
- 首次运行且 C 列为空 → 自动填充版本名

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
# 排查 Excel 表格
python game_version_checker.py 海外游戏版本表.xlsx

# 单独查 PUBG，对比后台版本 4.3.0
python game_version_checker.py --check com.tencent.ig --current 4.3.0

# 批量查
python game_version_checker.py -c "com.tencent.ig,com.roblox.client"
```
