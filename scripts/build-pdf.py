#!/usr/bin/env python3
"""Combine Agent Harness drafts into a styled HTML with chapter navigation."""

import re, glob, os

DRAFTS = sorted(glob.glob("_drafts/*-agent-harness-*.md"))

CHAPTERS = {
    "pattern": ("一", "让 AI 写代码不翻车"),
    "tdd": ("二", "TDD 红绿灯"),
    "ddr": ("三", "DDR 自我审计"),
    "efficiency": ("四", "效率守卫"),
    "subagent": ("五", "Subagent 分工设计"),
    "skill": ("六", "Skill 编排设计"),
    "bootstrap": ("七", "从零开始搭建"),
}

STYLE = """<style>
body { font-family: "PingFang SC", "Helvetica Neue", sans-serif; font-size: 15px; line-height: 1.8; color: #333; max-width: 800px; margin: 0 auto; padding: 40px 20px; }
.cover-page { page-break-after: always; display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 80vh; text-align: center; }
.book-title { font-size: 36px; border: none; margin: 0; padding: 0; }
.book-subtitle { font-size: 18px; color: #666; margin-top: 15px; }
.toc-page { page-break-after: always; padding-top: 40px; }
.toc-page h2 { font-size: 22px; margin-bottom: 20px; }
.toc-item { display: block; font-size: 14px; color: #333; text-decoration: none; padding: 5px 0; border-bottom: 1px solid #f0f0f0; }
.toc-item:hover { color: #0066cc; }
.chapter { page-break-before: always; padding-top: 80px; }
h1 { font-size: 26px; margin-top: 0; margin-bottom: 40px; padding-bottom: 10px; border-bottom: 2px solid #333; }
h2 { font-size: 20px; margin-top: 40px; }
code { font-family: "SF Mono", Menlo, monospace; font-size: 13px; background: #f5f5f5; padding: 2px 5px; border-radius: 3px; }
pre { background: #f5f5f5; padding: 16px; border-radius: 6px; overflow-x: auto; font-size: 13px; line-height: 1.5; }
pre code { background: none; padding: 0; }
blockquote { border-left: 3px solid #ddd; margin-left: 0; padding-left: 20px; color: #555; }
hr { border: none; border-top: 1px solid #eee; margin: 30px 0; }
table { border-collapse: collapse; width: 100%; margin: 15px 0; }
th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; font-size: 14px; }
th { background: #f9f9f9; }
a { color: #333; text-decoration: none; }
@media print { body { max-width: none; padding: 0; } .cover-page { min-height: 100vh; } .chapter { page-break-before: always; padding-top: 80px; } }
</style>"""

def get_chapter_info(filepath):
    for key, (num, title) in CHAPTERS.items():
        if key in filepath:
            return num, title
    return None, None

# Build combined markdown
md = """---
title: ""
---

<div class="cover-page">
<h1 class="book-title">Agent Harness 实践</h1>
<p class="book-subtitle">让 AI 在约束下稳定地写代码</p>
</div>

<div class="toc-page">

## 目录

"""

ordered = []
for f in DRAFTS:
    num, title = get_chapter_info(f)
    if num:
        ordered.append((f, num, title))

for _, num, title in ordered:
    md += f'<a href="#ch{num}" class="toc-item">第{num}章 &nbsp; {title}</a>\n\n'

md += "</div>\n\n"

for filepath, num, title in ordered:
    with open(filepath, 'r') as f:
        content = f.read()
    content = re.sub(r'^---\n.*?---\n', '', content, flags=re.DOTALL)
    content = content.replace('<!--more-->', '')
    md += f'\n<div class="chapter" id="ch{num}">\n\n'
    md += f'# 第{num}章 &nbsp; {title}\n\n'
    md += content.strip()
    md += '\n\n</div>\n\n'

with open('/tmp/agent-harness-combined.md', 'w') as f:
    f.write(md)

with open('/tmp/agent-harness-style.html', 'w') as f:
    f.write(STYLE)

os.makedirs('dist', exist_ok=True)
os.system(
    'pandoc /tmp/agent-harness-combined.md -f markdown -t html --standalone '
    '--highlight-style=kate '
    '--include-in-header=/tmp/agent-harness-style.html '
    '-o dist/agent-harness.html'
)

print("Generated: dist/agent-harness.html")
