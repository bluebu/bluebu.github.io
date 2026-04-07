# Hi-Ruby 博客

Jekyll 静态博客，部署在 GitHub Pages。

## 目录结构

```
_posts/          已发布文章（.html / .md）
_drafts/         草稿（本地 make serve 可预览，线上不生成）
_layouts/        页面布局模板
_includes/       可复用 HTML 片段（header, sidebar, user_card 等）
_sass/           样式（_backup.scss 为主样式文件）
categories/      分类页（每个分类一个 .md）
css/             主入口 main.scss
images/          静态图片
scripts/         工具脚本（build-pdf.py）
dist/            构建产物（gitignore）
```

## 常用命令

```bash
make serve       # 本地预览（Docker，含 future + drafts）
make stop        # 停止
make pdf         # 生成 Agent Harness 系列 HTML
```

## 配置

- `_config.yml` — Jekyll 配置，`future: false` 控制未来日期文章不上线
- `docker-compose.yml` — 本地预览环境（ruby:3.4.1）
- `plugins: jekyll-paginate, jekyll-sitemap`

## 分类

| 分类 | 路径 | 说明 |
|------|------|------|
| ai | /categories/ai/ | AI 相关 |
| ops | /categories/ops/ | 系统运维 |
| db | /categories/db/ | 数据库 |
| front-end | /categories/front-end/ | 前端开发 |

## 系列文章

- Agent Harness 实践（8 篇）— 索引页 `/agent-harness/`，草稿在 `_drafts/`

## 写作约定

- 文章用中文双引号 `""`，不用直引号 `""`
- frontmatter 中的值用直引号（YAML 语法要求）
- 代码块内引号不做替换
