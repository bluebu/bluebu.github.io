---
layout: post
title: 修复 Stata-MCP 在 Claude Code 中的连接问题
date: '2026-03-21T09:00:00+08:00'
permalink: "/posts/stata-mcp-fix"
categories: [ai]
---

最近在 Claude Code 里通过 MCP 连接 Stata，结果一上来就报错：`'str' object has no attribute 'mkdir'`。记录一下排查过程，也许能帮到遇到同样问题的人。

<!--more-->

---

## 报错信息

```
File "stata_mcp/config.py", line 340
    cwd.mkdir(parents=True, exist_ok=True)
AttributeError: 'str' object has no attribute 'mkdir'
```

我的 `.mcp.json` 配置很常规，通过 `STATA_MCP_CWD` 环境变量指定工作目录：

```json
{
  "mcpServers": {
    "stata-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--directory", "/path/to/project", "stata-mcp"],
      "env": {
        "STATA_MCP_CWD": "/path/to/project"
      }
    }
  }
}
```

## 原因

翻了一下 `stata-mcp` 的 `config.py` 源码，问题出在 `WORKING_DIR` 属性里：

```python
def WORKING_DIR(self) -> Path:
    cwd = self._get_config_value(
        config_keys=["PROJECT", "WORKING_DIR"],
        env_var="STATA_MCP__CWD",          # 双下划线，注意不是 STATA_MCP_CWD
        default=os.getenv("STATA_MCP_CWD", Path.cwd()),
        converter=self._to_path,
    )
    cwd.mkdir(parents=True, exist_ok=True)  # 这里炸了
```

执行流程是这样的：

1. 先找环境变量 `STATA_MCP__CWD`（双下划线）——没设置
2. 再找 toml 配置文件——也没配
3. 两个都没有，直接返回 `default` 值，**跳过了 `converter`**
4. `default` 通过 `os.getenv("STATA_MCP_CWD")` 拿到的是**字符串**
5. 字符串没有 `.mkdir()` 方法，报错

说白了就是 `_get_config_value` 在走 default 分支时不会调用 `converter`，而 `os.getenv()` 返回的是 `str` 不是 `Path`。

## 修复

改一行就行，把 default 值包一层 `Path()`：

```python
# 修复前
default=os.getenv("STATA_MCP_CWD", Path.cwd()),

# 修复后
default=Path(os.getenv("STATA_MCP_CWD", str(Path.cwd()))),
```

文件在 uv 缓存目录里：

```
~/.cache/uv/archive-v0/.../lib/python3.12/site-packages/stata_mcp/config.py
```

改完之后重新连接，正常了。

## 注意

这个修复改的是 uv 缓存里的文件，`uv cache clean` 或包更新之后会丢失。治本的办法是给上游提个 PR，让 `_get_config_value` 的 default 值也过一遍 converter。
