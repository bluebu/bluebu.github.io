---
layout: post
title: DSL 开发实践（三）：IR 模型，用中间表示把语法和执行彻底解耦
date: '2026-04-17T09:00:00+08:00'
permalink: "/posts/dsl-ir-model"
categories: [ai]
---

[上一篇](/posts/dsl-antlr4-ir-codegen)提到我们在 ANTLR4 的 ParseTree 和执行逻辑之间插了一层 IR（Intermediate Representation）。这篇展开聊 IR 模型的设计——为什么要这么分层，IR 定义文件里到底写了什么，以及它如何成为整个三语言体系的"单一真相源"。

<!--more-->

## 为什么 ParseTree 不能直接当 IR 用

先回答一个常见的疑问：ANTLR4 已经给我们生成了 ParseTree，为什么不直接拿它当数据模型来执行？

原因有三个。

**语法糖需要脱糖。** 我们的 DSL 里有不少语法糖来降低用户的输入成本。比如 `ccs: $salary * 1.1 as bonus` 是"计算列 + 自动聚合"的缩写，等价于 `cc: $salary * 1.1 as bonus | sum:$bonus`。又比如 standalone 的 `group_by:$dept` 后面不接聚合管道时，默认行为是每组取首行。这些"等价展开"如果在执行阶段做，执行器就要理解所有语法变体；如果在 IR 构建阶段做，执行器只需要处理一组正交的基本操作。

**ParseTree 的结构是 Grammar 驱动的，不是语义驱动的。** Grammar 里为了消除歧义，经常会引入辅助规则。比如 `value_expr` 和 `cond` 的分离是为了区分"值表达式"和"布尔表达式"的优先级，但从执行角度看，它们都是"表达式"。ParseTree 保留了这些语法层面的区分，IR 可以按语义重新组织。

**ParseTree 是 ANTLR4 特有的。** 它的节点类型、遍历 API 都和 ANTLR4 的运行时绑定。如果哪天换解析器（虽然不太可能），ParseTree 层的代码全要重写。IR 是我们自己定义的，和任何解析器框架无关。

## 一切皆 Stmt：IR 的根节点

我们的 IR 定义写在一个独立的 `.dsl` 文件里。它本身就是一个小型 DSL，用来描述我们这门语言的类型体系。

设计 IR 的第一个决策是确定根节点。我们选了 `Stmt`（Statement）作为所有 IR 节点的公共基类。

这不是拍脑袋的命名。Statement 在编程语言理论里有非常明确的地位——它是"程序中最小的可执行单元"。回顾几乎所有主流语言的编译器或解释器，AST 的根节点都是某种形式的 Statement：C/Java 的编译器里，`if`、`for`、`return`、表达式语句都是 Statement 的子类；Python 的 AST 模块里，`ast.stmt` 是所有语句节点的基类；Rust 编译器的 HIR 里，`Stmt` 同样是核心抽象。甚至 SQL 也是如此——`SELECT`、`INSERT`、`CREATE TABLE` 在解析器里都是 Statement。

为什么所有语言都收敛到这个抽象？因为 Statement 回答了一个根本问题：**"这门语言里，什么东西是可以被独立执行的？"** 确定了这个边界，编译器/解释器的遍历、优化、代码生成就有了统一的操作单元。没有这个根，你面对的就是一堆散落的节点类型，每种都要单独处理。

我们的 IR 也遵循这个传统：

```
abstract stmt Stmt {}
abstract func Func extends Stmt {}
abstract expr Expr extends Stmt {}
abstract cond Cond extends Expr {}
```

这四行定义了整个 IR 的骨架。**一切皆 Stmt**——函数是 Stmt，表达式是 Stmt，条件也是 Stmt（通过 Expr 间接继承）。有了这个统一的根，Visitor 只需要一套遍历机制就能处理所有节点类型，Codegen 也只需要一套模板规则就能为所有节点生成代码。

从 Stmt 出发，IR 分成两大分支：**Func**（函数/操作）和 **Expr**（表达式/值）。Func 描述"对数据做什么操作"，Expr 描述"怎么计算一个值"。两者在 Pipeline 里的角色完全不同——Func 是管道里的节点，Expr 是 Func 内部的参数。这和通用编程语言里"语句包含表达式，表达式产生值"的经典关系一脉相承。

顶层结构很简单：

```
program Program {
  pipelines: Pipeline[]
}

pipeline Pipeline {
  funcs: Func[]
}
```

一个程序（Program）由多个管道（Pipeline）组成，每个管道是一系列 Func 的有序调用。

## Func 的两大分支：StreamFunc 和 CollectFunc

Func 继续往下分——这是整个 IR 设计里最关键的决策：

```
// 流式算子：逐行处理，不需要看全局
abstract func StreamFunc extends Func {}

// 聚合算子：改变数据维度，触发 detail 快照
abstract func CollectFunc extends Func {}
```

**StreamFunc** 是"逐行处理"的算子。filter、cc（计算列）、sort、select、top 都属于这类。它们的特点是**不改变数据的维度**——输入 N 行，输出 ≤N 行，每行的字段可能变多（cc 加列）或变少（select 裁列），但行的粒度不变。

**CollectFunc** 是"聚合"算子。sum、avg、group_by 属于这类。它们**改变数据的维度**——输入 N 行明细数据，输出 M 行聚合结果（M ≪ N）。这个区分不是学术上的分类癖，而是有实际的架构意义：CollectFunc 执行时会先对当前数据做一次"detail 快照"，保存聚合前的明细数据，供前端做钻取（drill-down）展示。

具体的函数节点都从这两个基类派生：

```
func FilterFunc extends StreamFunc {
  condition: Cond
}

func CcFunc extends StreamFunc {
  expr: Expr
}

func SortFunc extends StreamFunc {
  fields: SortField[]
}

func AggregateFunc extends CollectFunc {
  aggregates: AggregateExpr[]
}

func GroupByFunc extends CollectFunc {
  keys: Expr[]
  mode: "group" | "first" | "last" | "min" | "max"
  field: Expr
}
```

每个节点只声明它需要的字段，类型清晰，没有多余的东西。`FilterFunc` 只有一个 `condition`，`SortFunc` 只有一个排序字段列表。

## Expr 的特化：Cond 是 Expr 的子类型

前面说过，Stmt 的另一大分支是 Expr。Expr 下面又特化出 Cond（条件表达式）——**Cond 继承自 Expr，所有条件都是表达式，但反过来不成立**。具体的节点：

```
// 值表达式（直接继承 Expr）
expr ConstExpr { value: number | string | boolean | null }
expr VarExpr { name: string }
expr ArithmeticExpr { left: Expr, op: "+" | "-" | "*" | "/" | "%", right: Expr }
expr FuncCallExpr { name: string, args: Expr[] }
expr AssignExpr { name: string, value: Expr }
expr AggregateExpr { op: "sum" | "avg" | "max" | "min" | "count", expr: Expr }
expr TernaryExpr { condition: Cond, trueExpr: Expr, falseExpr: Expr }

// 条件表达式（继承 Expr，求值结果为布尔值）
cond CompareCond { left: Expr, op: "==" | "!=" | ">" | "<" | ..., right: Expr }
cond LogicalCond { left: Cond, op: "and" | "or", right: Cond }
cond IncludeCond { expr: Expr, op: "in" | "not in", values: Expr[] }
cond BooleanCond { value: boolean }
```

为什么是继承而不是两个平行的类型？因为 Cond 需要出现在 Expr 能出现的地方。比如三目表达式 `$a gt 0 ? $b : $c`——`condition` 是 Cond，`trueExpr` 和 `falseExpr` 是 Expr，而整个三目表达式本身又是一个 Expr，可以参与计算列赋值 `cc: ($a gt 0 ? $b : $c) as result`。如果 Cond 不是 Expr 的子类型，这种组合就需要额外的包装层。

同时，这个继承关系也提供了类型约束：`FilterFunc.condition` 的类型是 `Cond`，你不可能错把一个 `ArithmeticExpr` 塞进去——编译器帮你挡住。`LogicalCond` 的 left/right 类型是 `Cond`，保证逻辑运算的操作数一定是布尔值。**向上兼容，向下约束。**

## 事件模型：IR 里的 UI 关注点

我们的 DSL 不只是做数据处理，它还有可视化能力——高亮、隐藏列、画图表。这些操作不直接改变数据流，而是**向外部发出事件**，由 UI 层消费。

IR 里用泛型标记来表达这种关系：

```
func HdFunc<HdEvent> extends StreamFunc {
  fields: Expr[]
}

func PlotFunc<PlotEvent> extends StreamFunc {
  x: Expr
  y: Expr
  chartTypes: ChartType[]
}

func HighLightFunc<HighLightEvent> extends StreamFunc {
  condition: Cond
  columns: string[]
  color: string
}
```

`<HdEvent>` 这个泛型标记告诉 Codegen："这个函数执行时会产生一个 HdEvent 类型的事件。"事件本身也在 IR 里定义：

```
event HdEvent {
  columns: int[]
}

event PlotEvent {
  chartTypes: ChartType[]
  columns: string[]
  data: DataRow[]
}

event HighLightEvent {
  columns: int[]
  color: string
  rows: int[]
}
```

这种设计让执行引擎和 UI 完全解耦。引擎执行 `HdFunc` 时，不需要知道 UI 怎么隐藏列，只需要发出一个 `HdEvent`。在没有 UI 的场景（比如 Python 后端做批处理），事件直接丢弃，零开销。在有 UI 的场景（前端的表格组件），事件被监听并触发列隐藏、行高亮、图表渲染。

## 单一真相源的实际效果

这个 IR 定义文件大约 250 行，定义了所有的函数节点、表达式节点、条件节点、事件类型和枚举。它是整个三语言体系的**单一真相源**（Single Source of Truth）。

实际效果是什么？假设要加一个新函数——比如 `format:` 函数，对指定列做格式化。流程是五步：

**第一步**，在 IR 定义文件里加一行：`func FormatFunc extends StreamFunc { field: Expr, expr: Expr }`

**第二步**，跑 Codegen，三个语言的 IR 类自动多出 `FormatFunc` 的定义。

**第三步**，三个语言的 AstBuilder 各加一个 `visitFormatFunc` 方法，把 ParseTree 节点翻译成 `FormatFunc` IR 对象。

**第四步**，三个语言的 ExecutionVisitor 各加一个 `visitFormatFunc` 方法，实现格式化逻辑。

**第五步**，加测试用例（CSV 驱动），三个语言跑一遍，确认结果一致。

整个过程里，**不存在"我在 Java 里加了字段但忘了在 Python 里同步"**的问题，因为 IR 类是 Codegen 生成的。手写的部分（AstBuilder 和 Visitor）确实需要各写一份，但编译器会告诉你——你的 Visitor 没实现 `visitFormatFunc` 方法，编译不过。

这就是 IR 层的核心价值：它不是一个可有可无的"中间层"，而是**整个多语言架构的骨架**。Grammar 定义语法，IR 定义语义，Codegen 保证一致性。三者缺一不可。

下一篇聊 Codegen 的具体实现——怎么从 IR 定义生成三个语言的代码，Mustache 模板怎么写，以及 Protocol 层的设计。
