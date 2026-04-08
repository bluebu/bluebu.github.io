---
layout: post
title: DSL 开发实践（四）：Codegen，一份 IR 定义生成三个语言的代码
date: '2026-04-18T09:00:00+08:00'
permalink: "/posts/dsl-codegen"
categories: [ai]
---

[上一篇](/posts/dsl-ir-model)聊了 IR 模型的设计哲学。这篇讲 Codegen——怎么从一份 IR 定义文件，自动生成 Java、TypeScript、Python 三个语言的 IR 类、Visitor 接口、引擎 API 和 Protocol 定义。

<!--more-->

## 没有 Codegen 的日子

先说为什么非做不可。

IR 定义文件里有大约 30 个类型：Program、Pipeline、十几个 Func 节点、七八个 Expr/Cond 节点、三个 Event、一个枚举。每个类型在三个语言里都需要对应的类定义。如果手写，就是 90 个类，每加一个字段改三个地方。

实际比"改三个地方"更麻烦。Java 用 `record`，TypeScript 用 `class`，Python 用 `dataclass`——三种语言的惯用写法不同，类型注解语法不同，甚至命名约定都不同。手工维护这种跨语言一致性，靠人肉 review 是不可靠的。

更要命的是 Visitor 接口。IR 里每个 Func 和 Expr 节点都需要一个对应的 `visit` 方法。加一个新的 IR 节点，Visitor 接口就要多一个方法签名，三个语言的 Visitor 都要同步更新。漏了一个？编译能过（因为基类有默认实现），运行时静默跳过——这种 bug 能查半天。

所以 Codegen 不是"锦上添花"，而是**保证三语言结构一致性的唯一可靠手段**。

## Codegen 的流水线

整个代码生成分四步：

```
IR 定义文件
  ↓ ① 解析
类型 AST（内存中的类型描述树）
  ↓ ② 路由
模板选择（根据语言 + 类型类别）
  ↓ ③ 渲染
Mustache 模板填充
  ↓ ④ 输出
生成的源文件（Java/TypeScript/Python）
```

### 第一步：解析 IR 定义

IR 定义文件本身是个小型 DSL，我们写了一个专门的 Parser 来解析它。解析结果是一棵类型 AST，每个节点描述一个 IR 类型的名称、字段、继承关系、泛型标记等。

比如这段 IR 定义：

```
func FilterFunc extends StreamFunc {
  condition: Cond
}
```

解析后得到的类型描述大致是：

```json
{
  "kind": "func",
  "name": "FilterFunc",
  "parent": "StreamFunc",
  "fields": [
    { "name": "condition", "type": "Cond", "array": false }
  ]
}
```

事件关联通过泛型标记处理：

```
func HdFunc<HdEvent> extends StreamFunc {
  fields: Expr[]
}
```

解析器会提取 `<HdEvent>` 标记，Codegen 据此生成事件发布相关的代码。

### 第二步：模板选择

模板按语言和类型类别组织：

```
templates/
├── java/
│   ├── model/          # DslIr 内的 record 定义
│   │   ├── model.mustache
│   │   ├── enum_model.mustache
│   │   ├── event_model.mustache
│   │   └── DslIr.mustache
│   ├── visitor/        # ExecutionVisitor 接口
│   ├── engine/         # DslEngine + DslRequest
│   └── protocol/       # DataRow, DataTable, Context 等
├── typescript/
│   ├── model/
│   ├── visitor/
│   ├── engine/
│   └── protocol/
└── python/
    ├── model/
    ├── visitor/
    ├── engine/
    └── protocol/
```

每种 IR 类型根据它的 `kind`（func、expr、cond、event、enum）匹配到对应的模板。比如 `FilterFunc` 是 `func` 类型，会匹配 `model/model.mustache`。

### 第三步：Mustache 渲染

模板用 Mustache 语法，逻辑极少，基本就是"填空"。看 Java 的 model 模板：

{% raw %}
```mustache
{{> _doc}}
  public record {{className}}({{#fields}}{{type}}{{#array}}[]{{/array}} {{name}}{{^last}}, {{/last}}{{/fields}}){{#interfaces}} implements {{interfaces}}{{/interfaces}} {}
```
{% endraw %}

翻译成人话：生成一个 Java record，类名是 `className`，构造参数是 `fields` 列表，数组类型加 `[]`，有接口就 `implements`。

`FilterFunc` 通过这个模板渲染后变成：

```java
/** 函数模型：数据过滤操作。接受一个 Cond 条件表达式作为输入 */
public record FilterFunc(Cond condition) implements StreamFunc {}
```

外层的 DslIr 容器模板把所有 record 包进一个大类：

{% raw %}
```mustache
@Generated("dsl-codegen")
public class DslIr {
{{#codeBlock}}
{{{.}}}{{/codeBlock}}
}
```
{% endraw %}

最终生成的 `DslIr.java` 是一个包含所有 IR 类型的巨型类，几十个 record 嵌套在一起，一个文件搞定。

TypeScript 模板类似但生成的是 class：

```typescript
export class FilterFunc implements StreamFunc {
  constructor(public readonly condition: Cond) {}
}
```

Python 生成 dataclass：

```python
@dataclass(frozen=True)
class FilterFunc(StreamFunc):
    condition: Cond
```

三种写法不同，但结构完全对齐——字段名、字段类型、继承关系一模一样。

### 第四步：输出

生成的文件直接写入各语言的 `generated/` 目录，文件头带 `@Generated` 标记（或等价的注释），明确告诉开发者不要手改。

```
impl/java/src/main/java/.../generated/DslIr.java
impl/typescript/src/generated/DslIr.ts
impl/python/src/generated/DslIr.py
```

## 不只是 Model：Visitor、Engine、Protocol

Codegen 生成的不只是 IR 的数据类，还包括三个关键部分。

**ExecutionVisitor** — IR 的遍历接口。每个 Func/Expr/Cond 节点对应一个 `visit` 方法：

```java
// 自动生成
public interface ExecutionVisitor {
    Context visitFilterFunc(DslIr.FilterFunc func, Context ctx);
    Context visitCcFunc(DslIr.CcFunc func, Context ctx);
    Context visitSortFunc(DslIr.SortFunc func, Context ctx);
    // ... 每个 IR 节点一个方法
}
```

手写的 `ExecutionVisitorImpl` 实现这个接口。新加一个 IR 节点，接口自动多一个方法，实现类如果没跟上就编译报错。

**DslEngine + DslRequest** — 引擎的公开 API。`DslRequest` 是不可变的请求对象（Builder 模式），封装了脚本文本和数据源注册。这层 API 的生成保证了三语言的调用方式一致：

```java
// Java
DslRequest request = DslRequest.builder()
    .script("$pnl gt 0 | sum:$pnl")
    .dataTable("TRADE", () -> tradeRows)
    .build();
DslResult result = engine.execute(request);
```

```typescript
// TypeScript
const request = DslRequest.builder()
    .script("$pnl gt 0 | sum:$pnl")
    .dataTable("TRADE", () => tradeRows)
    .build();
const result = engine.execute(request);
```

```python
# Python
request = (DslRequest.builder()
    .script("$pnl gt 0 | sum:$pnl")
    .data_table("TRADE", lambda: trade_rows)
    .build())
result = engine.execute(request)
```

**Protocol** — 数据接口定义。`DataRow`、`DataTable`、`FilterableDataTable`、`Context` 这些是引擎和外部系统的交互协议。它们定义在一个独立的 Protocol 定义文件里，同样通过 Codegen 生成三语言的接口/抽象类。

```
// Protocol 定义片段
interface DataTable {
  loadData(): DataRow[]
}

interface FilterableDataTable extends DataTable {
  loadData(filters: Filter[]): DataRow[]
}
```

Protocol 的意义是**契约先行**。先定义接口，再写实现。三个语言的集成方式由 Protocol 约束，不会出现"Java 版需要传 Context 参数但 Python 版不需要"这种不一致。

## Codegen 的边界

有一点要说清楚：Codegen 生成的是**结构代码**，不是**逻辑代码**。

IR 的类定义、Visitor 接口的方法签名、Engine 的 API 骨架——这些是可以从类型信息机械推导出来的，适合自动生成。但 AstBuilder（怎么把 ParseTree 翻译成 IR）和 ExecutionVisitorImpl（怎么执行每个 IR 节点）是业务逻辑，必须手写。

这个边界很重要。试图让 Codegen 生成执行逻辑是过度设计——三个语言的运行时特性不同（Java 的 Stream API、TypeScript 的 async/await、Python 的列表推导），硬要统一只会生成出四不像的代码。正确的做法是让 Codegen 管"骨架一致"，让人管"血肉各异"。

## 实际数字

当前的 Codegen 从 250 行的 IR 定义 + 50 行的 Protocol 定义生成：

```
Java:        ~800 行（DslIr.java + ExecutionVisitor.java + Protocol 接口）
TypeScript:  ~900 行
Python:      ~700 行
合计:        ~2400 行自动生成代码
```

这 2400 行代码如果手写，不是工作量的问题——是**三语言之间微妙不一致的风险**。Codegen 把这个风险降到了零。

下一篇聊三语言一致性保障——Codegen 保证了结构一致，但三个语言跑出来的结果真的一样吗？
