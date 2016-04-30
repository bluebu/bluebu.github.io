---
layout: default
title: 分类存档
permalink: "/categories/"
---

<ul class="breadcrumb">
  <li><a href="/">首页</a> <span class="divider">/</span></li>
  <li class="active">{{page.title}}</li>
</ul>

{% for category in site.categories %}
<h2>{{ category | first }}</h2>
<ul class="articles">
  {% for post in category.last %}
    <li>
      <a class="post-link" href="{{ post.url }}" title="{{ post.title }}">{{ post.title }}</a>
      <time style="float:right;">{{ post.date | date:"%Y-%m-%d"}}</time>
    </li>
  {% endfor %}
</ul>
{% endfor %}
