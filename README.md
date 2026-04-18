# Financial Intelligence Push

本仓库目前是一个可运行的本地预览版，用来演示“美股宏观与大盘观察哨”最终会如何输出到 Obsidian。

## 当前能演示什么

- 一天三篇简报：`开盘前`、`午盘`、`收盘后`
- 每篇包含：
  - 关键结论
  - 情景分析
  - 原始信号摘要
  - 原文链接
- 输出为 Obsidian 兼容 Markdown
- 支持两种输入模式：
  - `--demo` 使用内置样例信号
  - `--live` 抓取内置 RSS 源

## 运行预览

```bash
python3 -m unittest -v
python3 -m fin_inform_push.cli --demo --date 2026-04-17
python3 -m fin_inform_push.cli --live --date 2026-04-17
```

不传 `--date` 时，脚本会自动使用当天日期：

```bash
python3 -m fin_inform_push.cli --live --obsidian
```

推送到 Obsidian Local REST API：

```bash
export OBSIDIAN_API_KEY="your-api-key"
export OBSIDIAN_FOLDER="Macro Briefings"
python3 -m fin_inform_push.cli --live --date 2026-04-17 --obsidian
```

可选环境变量：

```bash
export OBSIDIAN_BASE_URL="https://127.0.0.1:27124"
```

如果你更喜欢显式传参，也可以：

```bash
python3 -m fin_inform_push.cli \
  --live \
  --date 2026-04-17 \
  --obsidian \
  --obsidian-api-key "your-api-key" \
  --obsidian-folder "Macro Briefings"
```

生成结果会落在：

```text
demo_output/2026-04-17/
```

## 当前内置真实源

- Federal Reserve
- MarketWatch Top Stories
- Yahoo Finance

## 下一步会接什么

- 公开宏观与市场分析源
- 去重与优先级策略
- 定时刷新与固定时点推送
