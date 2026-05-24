# 日记存储目录

此目录存放 AI 每日反思日记文件。

## 文件格式

- 文件名: `YYYY-MM-DD.md`
- 内容格式: Markdown，由 LLM 生成

## 自动管理

日记文件由 `app/diary.py` 的 `DiaryManager` 自动创建和管理。
每天在配置的时间（默认 23:00）自动生成。

## 配置

在 `app/config.yaml` 中配置：

```yaml
diary:
  enabled: true              # 是否启用
  time: "23:00"              # 每天执行时间
  max_context_items: 30      # 最多回顾记忆条数
```
