---
layout: default
title: DSL 开发实践
permalink: "/dsl-design/"
---

<h1>DSL 开发实践</h1>
<p class="muted">一门交易 DSL 的设计、实现与演进全记录。</p>


<ul class="articles">
  <li>
    <h2><a href="/posts/dsl-parser-evolution">一、三代解析器演进，从正则到 ANTLR4</a></h2>
    <div class="content">正则硬拆 → JFlex + JavaCUP → ANTLR4，每一次重写背后的业务驱动力</div>
  </li>
  <li>
    <h2><a href="/posts/dsl-antlr4-ir-codegen">二、ANTLR4 实战，从 Grammar 到 IR 和 Codegen</a></h2>
    <div class="content">Lexer/Parser Grammar 写法，ParseTree 的局限，以及为什么需要 IR 和 Codegen</div>
  </li>
  <li>
    <h2><a href="/posts/dsl-ir-model">三、IR 模型，用中间表示把语法和执行彻底解耦</a></h2>
    <div class="content">StreamFunc/CollectFunc 分类、Expr/Cond 体系、事件模型、单一真相源</div>
  </li>
  <li>
    <h2><a href="/posts/dsl-codegen">四、Codegen，一份 IR 定义生成三个语言的代码</a></h2>
    <div class="content">IR 解析 → 模板选择 → Mustache 渲染 → Java/TypeScript/Python 代码输出</div>
  </li>
  <li>
    <h2><a href="/posts/dsl-conformance">五、三语言一致性保障，450 个测试用例怎么守住的</a></h2>
    <div class="content">共享 CSV 用例、三语言 Test Runner、CI 数量门禁、Playground 实时验证</div>
  </li>
  <li>
    <h2><a href="/posts/dsl-ai-acceleration">六、AI 加速，三周干完三个月的活</a></h2>
    <div class="content">Playground、Demo、组件库——AI + Agent Harness 如何让"懒得做"变成"做了"</div>
  </li>
</ul>
