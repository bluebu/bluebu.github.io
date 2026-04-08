---
layout: post
title: DSL 开发实践（二）：ANTLR4 实战，从 Grammar 到 IR 和 Codegen
date: '2026-04-16T09:00:00+08:00'
permalink: "/posts/dsl-antlr4-ir-codegen"
categories: [ai]
---

[上一篇](/posts/dsl-parser-evolution)讲了我们的 DSL 解析器从正则到 ANTLR4 的三代演进。这篇聊 ANTLR4 到底怎么用，以及用着用着为什么会自然引出 IR 模型和 Codegen 这两个东西。

<!--more-->

## ANTLR4 的核心概念：两个文件搞定一门语言

ANTLR4 的工作流程很直白：你写 Grammar 文件，它生成 Lexer 和 Parser 代码。Grammar 分两部分——词法规则（Lexer Grammar）定义 token 长什么样，语法规则（Parser Grammar）定义 token 怎么组合。

我们的词法规则在 `Lexer.g4` 里。看几个典型的 token 定义：

```g4
// 变量：$开头
VAR: '$' [a-zA-Z_][a-zA-Z0-9_]*;

// 关键字
FILTER: 'filter' | 'fl';
SORT: 'sort' | 'st';
CC: 'cc';
SUM: 'sum';
AVG: 'avg';

// 比较操作符
GT: 'gt';
LT: 'lt';
EQ: 'eq';
LIKE: 'like';

// 管道符
PIPE: '|';
```

语法规则在 `Parser.g4` 里，描述这些 token 怎么拼成合法的脚本：

```g4
// 一个程序由多个 pipeline 组成
program
    : NEWLINE* (pipeline NEWLINE*)+ EOF
    ;

// pipeline：load 数据 → 若干 func 通过管道连接
pipeline
    : load func? (PIPE load? func)*
    ;

// 过滤函数：可以显式写 filter:，也可以直接写条件
func_filter: FILTER COLON cond
           | cond;

// 排序函数：逗号分隔的排序字段，方向可省略（默认 ASC）
func_sort : SORT COLON sort_field (COMMA sort_field)* ;
sort_field : var (ASC | DESC)? ;
```

写完 Grammar，跑一行命令：

```bash
antlr4 -Dlanguage=Java Lexer.g4 Parser.g4
antlr4 -Dlanguage=TypeScript Lexer.g4 Parser.g4
antlr4 -Dlanguage=Python3 Lexer.g4 Parser.g4
```

三个语言的 Lexer 和 Parser 就全生成了。用户输入一行脚本，ANTLR4 会把它解析成一棵 ParseTree，结构和 Grammar 规则严格对应。

## ParseTree 够用但不好用

ANTLR4 生成的 ParseTree 是一棵具体语法树（CST），每个节点对应 Grammar 里的一条规则。比如 `$pnl gt 0` 这个条件，ParseTree 里大概长这样：

```
func_filter
  └── cond
      └── GreaterThanCond
          ├── value_expr → VarRefExpr → var: $pnl
          ├── GT
          └── value_expr → ConstRefExpr → Number: 0
```

要遍历这棵树，ANTLR4 提供了 Visitor 模式。你继承生成的 `BaseVisitor`，重写每个规则对应的 `visit` 方法：

```java
@Override
public Object visitGreaterThanCond(DslParser.GreaterThanCondContext ctx) {
    // ctx.value_expr(0) → 左操作数
    // ctx.value_expr(1) → 右操作数
    // 在这里构建你的业务对象...
}
```

这套机制能用，但用着用着会发现两个问题。

**第一，ParseTree 太"语法化"了。** 它忠实地反映 Grammar 的结构，但 Grammar 是为了解析方便而设计的，不一定和业务语义对齐。比如我们有一个语法糖 `ccs: $salary * 1.1 as new_salary`，它等价于 `cc: $salary * 1.1 as new_salary | sum:$new_salary`。在 ParseTree 里，`ccs` 是一个独立的节点类型；但从执行语义上看，它应该被展开成"一个 CcFunc + 一个 AggregateFunc"。这种"脱糖"逻辑如果写在 Visitor 里，Visitor 就不再是纯粹的遍历者了，它同时承担了语义转换的职责。

**第二，三个语言各写一遍 Visitor。** ParseTree 的节点类型是 ANTLR4 根据 Grammar 自动生成的，Java 版、TypeScript 版、Python 版各有各的类名和 API 风格。你不能共享一个 Visitor 实现，只能分别写三份。如果执行逻辑直接写在 ParseTree Visitor 里，那三个语言不仅要各写一份 Visitor，还要保证它们的行为严格一致。450 个测试用例能兜底，但维护成本摆在那儿。

## 自然引出的两层：IR 和 Codegen

解决上面两个问题的思路是：**在 ParseTree 和执行逻辑之间插一层中间表示（IR）**。

```
ANTLR4 ParseTree（语法结构，自动生成，三语言不同）
      ↓  AstBuilder（手写，三语言各一份）
IR Objects（语义模型，三语言结构相同）
      ↓  ExecutionVisitor（手写，三语言各一份）
执行结果
```

AstBuilder 的职责是把 ParseTree 翻译成 IR。这一步做两件事：一是**脱糖**（desugar），把语法糖展开成基本操作；二是**语义归一化**，把 Grammar 层面不同的写法统一成相同的 IR 结构。比如：

- `ccs: $expr as name` → `CcFunc($expr as name)` + `AggregateFunc(sum:$name)`
- standalone `group_by:$keys`（后面不接聚合）→ `GroupByFunc(keys, mode="first")`
- `not ($a gt 0 and $b lt 10)` → 应用 De Morgan 律展开为 `$a lte 0 or $b gte 10`

脱糖之后，ExecutionVisitor 只需要处理一组干净的、正交的 IR 节点，不用关心语法层面有几种写法。

但 IR 的类（`FilterFunc`、`CcFunc`、`CompareCond`、`ArithmeticExpr` 等）有几十个，三个语言要各定义一套。手写三遍？不现实。这就是 **Codegen 的由来**——用一份 IR 定义文件自动生成三个语言的 IR 类。

我们设计了一个 IR 定义 DSL（对，用 DSL 来构建 DSL），专门描述 IR 的类型体系：

```
// 流式算子：逐行处理
abstract func StreamFunc extends Func {}

// 聚合算子：改变数据维度
abstract func CollectFunc extends Func {}

// 过滤函数
func FilterFunc extends StreamFunc {
  condition: Cond
}

// 计算列
func CcFunc extends StreamFunc {
  expr: Expr
}

// 比较条件
cond CompareCond {
  left: Expr
  op: "==" | "!=" | ">" | "<" | ">=" | "<=" | "like" | "!like"
  right: Expr
}
```

Codegen 读取这个文件，解析成类型 AST，然后用 Mustache 模板为每种语言生成对应的代码。Java 生成 `record`，TypeScript 生成 `interface` + `class`，Python 生成 `dataclass`。生成的代码带 `@Generated` 注解，不允许手工修改。

```
ir.dsl 定义
    ↓ Codegen（Mustache 模板）
├── Java:       DslIr.java（records）
├── TypeScript: DslIr.ts（classes）
└── Python:     DslIr.py（dataclasses）
```

## 这套架构解决了什么

回到前面的两个问题：

**ParseTree 太语法化** → AstBuilder 负责脱糖和归一化，IR 只表达语义，和 Grammar 的具体写法解耦。

**三语言各写 Visitor** → IR 的类由 Codegen 自动生成，三个语言结构完全一致。手写的部分只有 AstBuilder（把 ParseTree 翻译成 IR）和 ExecutionVisitor（拿 IR 跑业务逻辑）。这两部分确实要各写一份，但它们面对的是统一的 IR 类型体系，逻辑结构高度相似，维护起来比直接操作 ParseTree 轻松得多。

整个架构的分工变成了：

```
ANTLR4     → 管"语法对不对"（自动生成，零维护）
AstBuilder → 管"语义怎么归一"（手写，但逻辑简单）
ir.dsl     → 管"IR 长什么样"（单一真相源）
Codegen    → 管"三语言 IR 类一致"（自动生成，零维护）
Visitor    → 管"业务怎么跑"（手写，核心逻辑）
```

每一层只做一件事，改动的传播路径清晰可控。加一个新的 DSL 函数，流程是：改 Grammar → 改 IR 定义 → 跑 Codegen → 三语言各改 AstBuilder 和 Visitor → 跑测试。听着步骤不少，但每一步都是确定性的，不存在"改了 A 不知道会不会影响 B"的恐惧。

下一篇专门聊 IR 模型的设计细节——为什么要区分 StreamFunc 和 CollectFunc，事件模型怎么做，以及这个"元 DSL"本身的设计考量。
