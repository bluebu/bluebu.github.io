---
description: 博客文章 Markdown 写作规范
globs: ["_posts/**", "_drafts/**"]
---

# Markdown 写作规范

## 引号

- 正文使用中文双引号 `""`，禁止使用 ASCII 直引号 `""`
- YAML frontmatter 中使用直引号（语法要求）
- 代码块（`` ` `` 和 ``` ``` ```）内不做引号替换

## 结构

- 用 `<!--more-->` 标记摘要分割点，放在第一段之后
- 正文标题用 `##`（h2），不用 `#`（h1 留给文章标题）
- 标题层级不跳级（h2 → h3，不要 h2 → h4）

## 格式

- 加粗+破折号格式用于并列要点：`**关键词** — 说明文字`
- 流程步骤用引用块（`>`）或代码块展示，不挤在段落里
- 表格优先用代码块等宽格式，markdown 表格在移动端显示差

## 脱敏

- 不出现内部域名、项目代号、密钥
- 示例域名用 `example.com`
- 示例环境变量用通用名称（`ENV_ID`、`HTTP_ENDPOINT`）

## frontmatter

```yaml
---
layout: post
title: 文章标题
date: 'YYYY-MM-DDTHH:MM:SS+08:00'
permalink: "/posts/slug"
categories: [分类]
---
```

- permalink 使用 `/posts/` 前缀
- categories 从 ai / ops / db / front-end 中选
- 草稿放 `_drafts/`，日期设为未来以控制发布时间
