---
layout: post
title: DSL 开发实践（五）：三语言一致性保障，450 个测试用例怎么守住的
date: '2026-04-18T15:00:00+08:00'
permalink: "/posts/dsl-conformance"
categories: [ai]
---

[上一篇](/posts/dsl-codegen)讲了 Codegen 怎么从一份 IR 定义生成三个语言的代码。代码生成了，结构一致了，但有个问题还没回答：**三个语言跑出来的结果真的一样吗？**

Codegen 管得了"骨架"——IR 类的字段名、类型、继承关系三语言严格一致。但它管不了"血肉"——AstBuilder 和 ExecutionVisitor 是手写的，三个语言各有各的惯用写法：

- **Java** 用 Stream API 做 filter/map/collect
- **TypeScript** 用 Array 的链式调用
- **Python** 用列表推导和 sorted()

浮点精度、字符串比较、空值处理、排序稳定性……随便哪个点出现分歧，用户在 Java 后端和 Python 后端看到的结果就不一样。这种不一致比 bug 更危险——每个语言单独看都是"对的"，但放在一起就"不对了"。

这篇聊我们怎么用 450+ 个 CSV 驱动的测试用例，把三语言一致性从"应该一致"变成"CI 卡住不一致就不让合"。

<!--more-->

## 一份 CSV，三个语言跑

测试用例不是按语言分别写的，而是**共享同一组 CSV 文件**。每个 CSV 文件对应一个功能类别，格式统一：

```
SCRIPT,INPUT,OUTPUT,DESCRIPTION
```

实际的测试数据长这样：

```csv
"$age gt 0 | select: $age, $name","age=20;name=alice;city=sh|age=30;name=bob;city=bj","age=20;name=alice|age=30;name=bob","基本选择列——保留指定列，裁剪未指定列"
"$a gt 0 | sum:$a","a=1;b=1|a=2;b=2|a=3;b=3","sum_a=6","字段a的总和聚合"
```

编码约定很简单：行之间用 `|` 分隔，字段之间用 `;` 分隔，键值对用 `=` 连接。一行 CSV 就是一个完整的测试用例——脚本、输入数据、期望输出、描述，一目了然。

涉及 UI 事件的测试（隐藏列、高亮等）多一个 EVENT 列：

```csv
"$a gt 0 | hd: $b","a=1;b=2;c=3","a=1;b=2;c=3","HdEvent:columns=[1]","单列隐藏数据不变"
"$a gt 0 | hl: $a gt 1;$b;blue","a=1;b=2;c=3|a=3;b=4;c=5","a=1;b=2;c=3|a=3;b=4;c=5","HighLightEvent:columns=[1],color=blue,rows=[1]","单列高亮指定颜色"
```

数据不变，但要验证引擎是否正确发出了事件——隐藏了哪些列、高亮了哪些行、用什么颜色。

## 20 个类别，覆盖所有语法

450+ 个用例分布在 20 个 CSV 文件里，每个文件对应一个功能类别：

```
test/runtime/
├── filter.csv          # 行过滤
├── cc.csv              # 计算列
├── aggregate.csv       # 独立聚合（sum/max/min/avg/count）
├── group_by.csv        # 分组聚合
├── sort.csv            # 排序
├── select.csv          # 列选择
├── top.csv             # 取前/后 N 行
├── conditionals.csv    # 条件表达式
├── logical_ops.csv     # 逻辑运算（and/or/not）
├── functions.csv       # 内置函数（abs/round/min/max）
├── integration.csv     # 多步管道组合
├── ...                 # 其他十余个类别
```

从最基础的"过滤一个字段"到复杂的"分组聚合 + 计算列 + 排序 + 高亮"组合管道，每个语法点都有正向用例和边界用例。

## 三个 Test Runner，同一套断言逻辑

CSV 是共享的，但每个语言需要自己的 Test Runner。三个 Runner 遵循同一个执行契约：

```
读取 CSV → 解析 INPUT 构造数据表 → 执行 SCRIPT → 序列化结果 → 与 OUTPUT 做字符串比对
```

具体的测试框架各用各的——Java 是 JUnit 5 参数化测试，TypeScript 是 Jest `test.each()`，Python 是 pytest `parametrize`——但这不重要。重要的是**序列化格式必须三语言完全对齐**：行用 `|` 连接，字段用 `;` 连接，整数不带小数点（`6` 而不是 `6.0`）。

这是整个一致性方案的基石。如果序列化格式不统一，字符串比对就退化成了"比对格式差异"而不是"比对语义差异"——测试全绿，但结果可能根本不一样。

## CI 的一致性门禁

测试通过是底线，但还不够——还要保证**三个语言跑的用例数一样**。

每个语言的 CI 任务跑完测试后，从 JUnit XML 报告里提取测试用例数写入文件。然后有一个专门的 `check-test-result` 任务做交叉校验：

```bash
JAVA=$(cat test-count-java.txt)
TS=$(cat test-count-ts.txt)
PY=$(cat test-count-py.txt)

if [ "$JAVA" != "$TS" ] || [ "$JAVA" != "$PY" ]; then
  echo "三语言测试用例数不一致！Java=$JAVA TS=$TS Python=$PY"
  exit 1
fi
```

为什么要查数量？因为"少跑了一个类别"这种 bug 不会让测试失败——只是少了几十个用例，该测的没测到。之前踩过一次：Python 的 `ternary.csv` 漏了没注册到参数化列表里，Java 和 TypeScript 都跑了 450 个用例，Python 只跑了 430 个，全绿通过。但实际上 Python 的三目运算符实现有 bug，只是没被测到。加了这个数量校验之后，这种"遗漏"就会被卡住。

整个 CI 流水线的检查顺序是：

```
test-java ──┐
test-ts ────┤──→ check-test-result ──→ 允许合并
test-python ┘
```

三个语言的测试全部通过，且用例数严格相等，MR 才能合。

## Playground 里的 Test Runner

CI 保障的是"合并前不能出错"，但开发过程中想快速验证怎么办？我们在 Playground 里内置了一个 Test Runner 面板。

打开 Test Runner 页面，上面是类别选择器（可以勾选要跑哪些类别），下面是执行面板。点 Run，前端同时调用 Java、TypeScript、Python 三个后端，逐条执行 CSV 用例，实时显示进度：

```
Java:        450/450  (450✓ 0✗)  0.5s
TypeScript:  450/450  (450✓ 0✗)  0.4s
Python:      450/450  (449✓ 1✗)  0.6s
```

展开任意一条用例，能看到三个语言的实际输出和 diff。结果不一致的标红，三语言之间行为分歧的额外标红——这种比单纯的失败更危险，意味着同一个脚本在不同端产生了不同结果。支持 Pass/Fail 过滤，只看失败项。

它解决的是**反馈延迟**的问题。CI 跑完要几分钟，而 Playground 里点一下 Run，几秒钟就知道三个语言谁挂了、挂在哪、差异是什么。开发新语法时，这个即时反馈环比什么都重要。

## 一致性不是一次性的

一开始我以为一致性是"一次性搞定"的事——三个语言都写对了，以后就一直对。实际根本不是。每一次改动都可能在某个语言里引入分歧：

- 浮点精度的处理方式改了
- 空字符串和 null 的判断逻辑调了
- 排序碰到相同值时的稳定性不同了

这些微妙的分歧不会让测试直接报错，但会让用户在不同端看到不同的结果。

所以一致性保障不是"写完测试就完事了"，而是一个**持续运行的系统**——四层防线，缺一不可：

- **共享 CSV** — 唯一的用例源，三语言读同一份正确答案
- **三语言 Runner** — 统一的执行契约和序列化格式
- **CI 门禁** — 数量校验 + 全绿才能合并
- **Playground Test Runner** — 开发时的即时反馈环

每加一个新功能，第一件事不是写实现，而是先在 CSV 里加测试用例。三个语言还没开始写代码，正确答案就已经定义好了。

下一篇聊 AI 如何给整个 DSL 开发流程装上加速器。
