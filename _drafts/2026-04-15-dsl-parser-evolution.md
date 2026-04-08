---
layout: post
title: DSL 开发实践（一）：三代解析器演进，从正则到 ANTLR4
date: '2026-04-15T09:00:00+08:00'
permalink: "/posts/dsl-parser-evolution"
categories: [ai]
---

我们内部有个 DSL，用来做交易数据的实时过滤、聚合和可视化。用户在前端输入一行脚本，比如 `@TRADE $pnl gt 0 | sum:$pnl`，引擎就能把数据表里的行过滤出来再聚合求和。听起来不复杂，但这个"解析用户输入"的部分，我们前后重写了三次。

<!--more-->

## 第一代：正则表达式，能用就行

最早的版本没什么架构可言。需求很简单——用户输入 `$age gt 12`，后端把它拆成"字段、操作符、值"三元组，然后硬编码 if-else 去过滤数据行。

```java
// 第一代：正则硬拆
Pattern p = Pattern.compile("\\$(\\w+)\\s+(gt|lt|eq)\\s+(\\S+)");
Matcher m = p.matcher(input);
if (m.find()) {
    String field = m.group(1);
    String op = m.group(2);
    String value = m.group(3);
    // ... 手工构建过滤逻辑
}
```

这种做法的好处是启动快——半天就能写完，不依赖任何第三方库。坏处是脆弱到离谱。用户一旦写出 `$pnl gt 0 and $name like btc` 这种组合条件，正则就撑不住了。加上管道语法 `|`、聚合操作 `sum:`、排序 `sort:` 之后，正则匹配的代码膨胀到上千行，每加一个新功能都像在拆炸弹。

更致命的问题是**没有语法校验**。用户输入写错了，系统不报错，只是默默返回空结果或者错误结果。交易员拿着错误数据做决策，这不是 bug，是事故。

正则大概撑了几个月。当需求要支持嵌套表达式（`cc: $a + $b * 2 as total`）的时候，大家都意识到字符串操作这条路走不通了，需要一个真正的 Parser。

## 第二代：JFlex + JavaCUP，正经但笨重

第二次重写选了 JFlex + JavaCUP 的组合。这个方案是老板提的——他早年用 C 语言做过类似的事情，Lex + Yacc 那套经典搭配，JFlex + JavaCUP 就是它的 Java 移植版。JFlex 负责词法分析（把输入拆成 token），JavaCUP 负责语法分析（按文法规则组装成语法树）。为了搞明白这套东西，我又翻出了编译原理的"龙书"温习了一遍。

先说好的地方。有了正式的词法和语法定义之后，解析器的行为变得可预测了。用户写错语法会得到明确的报错信息，不再是静默失败。嵌套表达式、运算符优先级这些之前搞不定的东西，用 BNF 文法规则几行就能描述清楚。

但问题也很快暴露出来。

**工具链老旧。** JFlex 的文档停留在 2000 年代的风格，JavaCUP 的最后一次正式发布是 2015 年。遇到问题能搜到的资料有限，Stack Overflow 上的回答大多也是十年前的。相比之下，同期的 ANTLR 已经出到 4.x，生态活跃度完全不在一个量级。

**调试体验差。** JavaCUP 生成的解析器是一个状态机，出了 shift-reduce 冲突，给你的错误信息是一堆状态号和 token 名的组合。要理解冲突在哪，得自己脑补状态转移过程，或者去翻那个几千行的生成代码。ANTLR4 用的是 LL(\*) 算法，冲突处理对人类友好得多。

**只支持 Java。** 这在当时不是问题——后端本来就是 Java。但后来前端团队想直接在浏览器里做语法校验和自动补全，JFlex + JavaCUP 就没辙了。总不能让前端引一个 Java Runtime 吧。

我把当时考虑过的几个方案做个对比：

```
框架              算法        多语言    社区活跃度    调试体验
─────────────────────────────────────────────────────────
JFlex + JavaCUP   LALR(1)     仅Java    低           差
ANTLR4            LL(*)       10+语言   高           好
JavaCC             LL(k)      仅Java    中           中
PEG.js            PEG         仅JS      中           中
Xtext             LL(*)       Java/JS   中           好（IDE集成）
```

JFlex + JavaCUP 的优势是"正统"——Lex/Yacc 家族几十年的积淀，编译原理教科书里的标配。但"正统"不是技术选型的好理由。它能解决"正确解析"的问题，却解决不了"多语言支持"和"开发效率"的问题。

这一代大概用了一年多。真正触发第三次重写的，是一个业务需求：Python 团队也需要用这个 DSL 做量化回测。维护两套独立的解析器？不现实。

## 第三代：ANTLR4，一次定义到处生成

切到 ANTLR4 是个"早该做"的决定。

ANTLR4 的核心卖点是**一份 Grammar 文件生成多语言解析器**。我们的词法规则（`Lexer.g4`）和语法规则（`Parser.g4`）各一个文件，用 ANTLR4 的命令行工具一跑，Java、TypeScript、Python 三个语言的 Lexer 和 Parser 就全有了。

```g4
// Parser.g4 片段
pipeline
    : load func? (PIPE load? func)*
    ;

func_filter: FILTER COLON cond
           | cond;

func_sort : SORT COLON sort_field (COMMA sort_field)* ;

sort_field : var (ASC | DESC)? ;
```

语法长什么样，文法规则就怎么写。`pipeline` 由 `load` 和 `func` 通过管道符连接，`func_sort` 是 `sort:` 后面跟逗号分隔的排序字段。读起来几乎就是自然语言描述。

ANTLR4 用的是自适应 LL(\*) 算法（ALL(\*)），不需要像 LALR 那样手工解决冲突。大部分文法歧义它能自动处理，实在处理不了的会给出清晰的报错，告诉你哪两条规则冲突了、在什么输入下会触发。调试时还能用 `grun`（Grammar Test Rig）工具可视化解析树，一目了然。

迁移过程中最大的收获不是"多语言"本身，而是**被迫重新审视了整个架构**。用 JFlex + JavaCUP 的时候，解析和执行是混在一起的——语法动作（semantic action）里直接写业务逻辑。切到 ANTLR4 之后，我们做了一次彻底的分层：

```
Lexer.g4 → Token 流
     ↓
Parser.g4 → ParseTree（ANTLR4 生成）
     ↓
AstBuilder → IR Objects（自己写的中间表示）
     ↓
ExecutionVisitor → 执行结果
```

ParseTree 是 ANTLR4 自动生成的，结构和文法规则一一对应，但不适合直接用来执行——节点太细碎，遍历起来啰嗦。于是我们引入了一层 IR（Intermediate Representation），用一个自定义 DSL 来定义语义模型，再通过 Codegen 自动生成三个语言的 IR 类。

这个架构的好处是**关注点彻底分离**。Grammar 只管语法对不对，AstBuilder 只管把 ParseTree 翻译成 IR，ExecutionVisitor 只管拿着 IR 跑业务逻辑。改语法不影响执行，改执行不影响解析。三个语言共享同一套 Grammar 和 IR 定义，实现层各写各的，然后用 450+ 个 CSV 驱动的测试用例来保证行为一致。

## 三代对比

```
维度          正则           JFlex+CUP       ANTLR4
──────────────────────────────────────────────────
开发速度      快（半天）     中（一周）       中（一周）
维护成本      极高           高               低
语法校验      无             有               有
错误提示      无             差               好
多语言        不可能         不可能           原生支持
表达式嵌套    不支持         支持             支持
社区生态      -              几乎停滞         活跃
调试工具      printf         状态机日志       可视化ParseTree
```

回头看这三次重写，每一次都不是"闲得没事想重构"，而是业务需求逼出来的。正则撑不住组合条件，JFlex+CUP 撑不住多语言。如果一开始就用 ANTLR4 呢？也未必。当时需求简单，正则确实是投入产出比最高的方案。技术选型不是挑最强的，是挑当下最合适的——但前提是你得知道"不合适"的信号是什么，以及下一步该往哪走。

下一篇聊 ANTLR4 的具体用法，以及我们为什么在 ParseTree 之上又搞了一层 IR。
