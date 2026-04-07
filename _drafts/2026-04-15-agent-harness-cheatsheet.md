---
layout: post
title: Agent Harness 实践（终篇）：速查手册
date: '2026-04-15T09:00:00+08:00'
permalink: "/posts/agent-harness-cheatsheet"
categories: [ai]
---

前七篇讲了为什么、怎么想的、踩了什么坑。这篇只讲怎么做。不解释，不举例，直接上结构。

以下是 Agent Harness 的最小可用骨架。实际生产中我们还叠加了业务相关的 rules 和 hooks，但与具体业务耦合过深，这里只保留框架层面可复用的部分。

<!--more-->

## 四层架构

```
反馈循环    定期回顾 → 识别低效 → 沉淀回规则
护栏约束    TDD / Git / 效率守卫 / 按路径加载
流程编排    Skill（工作流模板）= Intake + 步骤 + Review
上下文管理  Subagent × 文件权限表 × model 选择
```

## Subagent 定义模板

```markdown
---
description: 一句话职责
model: opus / sonnet
tools: Read, Edit, Bash, ...
---

## 角色定义
你是 XXX，负责 YYY。

## 核心文件
- path/to/file1  （每次启动必读）
- path/to/file2

## 文件权限
| 路径 | 权限 | 说明 |
|------|------|------|
| src/module/ | 读写 | 主战场 |
| src/generated/ | 只读 | 不要动 |
| test/ | 只读 | 只看不改 |

## 工作流程
### 场景A：新功能（TDD: strict）
1. 红：make test，确认失败
2. 绿：写最小实现，make test 通过
3. 重构，再跑 make test

### 场景B：Bug 修复（TDD: fix）
1. 复现：make test，确认失败
2. 修复
3. 验证：make test 通过

## 命令速查
make build / make test / make lint

## 规范约束
- 不修改 generated/ 目录
- 不删除测试用例
- 保持与其他语言行为一致
```

## 拆分原则

- 一个文件只归一个 Agent 写
- 按产出物拆，不按技能拆
- opus 给设计决策，sonnet 给常规实现

## Skill 定义模板

```markdown
---
description: 一句话描述
user-invocable: true
---

Review: step / final / none

## Intake 字段表
| 字段 | 必须 | 推断规则 |
|------|------|----------|
| 功能描述 | 是 | — |
| 作用域 | 是 | 从描述推断 |

## 流程
| 步骤 | 委派 | 验收命令 |
|------|------|----------|
| 1 | agent-a | make test_a |
| 2 | agent-b | make test_b |
| 3 | — | /push |
```

## Review 三种模式

| 模式 | 适用场景 | 行为 |
|------|----------|------|
| step | 不可逆操作多 | 每步确认 |
| final | 中间可逆 | 只确认最终结果 |
| none | 全确定性流程 | 全自动 |

## TDD 协议

**strict（新功能）**：红 → 绿 → 重构，每步跑测试

**fix（修 Bug）**：复现 → 修复 → 验证

铁律：
- 不跳红
- 实现 Agent 不改测试文件
- 禁止删用例
- 单语言闭环（通过再进下一种）

## DDR 协议

```
Detect     采集事实，不判断
Diagnose   分析根因，输出 plan 文件（不动手）
Remediate  人确认 plan 后逐项执行
```

plan 文件存 `.claude/plans/`，可跨会话。

## 效率守卫

**碎片化需求** — 连续 3 条短消息追加需求 → 暂停，要求一次说完

**确认循环** — 同一文件修改 3 次以上 → 暂停，先定方案

**美化漩涡** — 出现"丑""不好看" → 要求提供参考

**理解偏差** — 出现"不对""不是这意思" → 结构化确认

**过度讨论** — 连续 5 轮问答无代码产出 → 先做再说

**流程膨胀** — 非功能性工作占比超 50% → 提醒切回产品功能

## 落地节奏

```
第 1 周    CLAUDE.md + 1 Agent + 1 条 TDD 规则
第 2 周    拆第 2 个 Agent + Git 规范 + 第 1 个 Skill
第 3 周    拆语言 Agent + 效率守卫 + 核心 Skill
第 4 周    DDR 落地，体系成型
```

## 目录结构

```
.claude/
├── agents/          Subagent 定义（每个一个 .md）
├── skills/          Skill 定义（每个目录一个 SKILL.md）
├── commands/        Command 定义（比 Skill 更小的执行单元）
├── rules/           规范文件（按路径自动加载）
├── plans/           跨 Agent 交接物（plan 文件）
└── hooks/           生命周期钩子（pre-commit、post-deploy 等）
```

完。
