---
layout: post
title: Mac下Golang开发环境搭建
date: '2016-04-29T10:00:39+08:00'
permalink: "/posts/golang-dev"
categories: [golang]
---

话说工欲善其事, 必先利其器, 要想写一手好代码怎能不需要一个好用的开发环境?

本文用来记录第一次安装go环境遇到问题, 以防遗忘

#### 1. 安装Go

```shell
brew install go
```

本文写作时go版本为1.6, 其余没什么可说的, 略过

#### 2. 配置GOPATH

将以下代码添加到 .bashrc 或者 .zshrc

```shell
export GOPATH=/home/bluebu/go
export PATH=$PATH:$GOPATH/bin
```

注: GOPATH即我们以后的workspace, 建议在home目录下创建该目录

GOPATH下将会生成3个目录

* src 将来我们存放源码的地方, 包括第三方的包, 和自己的包, 比如 .go .c .h等
* pkg 编译后生成的文件, 一般是各种 .a
* bin 编译后生成的可执行文件

#### 3. IDE搭建

1. ST3

2. GoSublime golang的扩展包, 支持代码补全, 快速跳转, snippets, 自动添加删除包依赖, 还有最有用的一堆快捷键.

    项目地址: https://github.com/DisposaBoy/GoSublime

    其中代码自动补全功能依赖 `gocode`, 需要执行 `go get github.com/nsf/gocode`

-------

这样开发环境基本差不多了, 下一步打算:

1. go get的详(Fan)细(Qiang)用法
2. go package的依赖, 有木有类似我们大ruby的bundler
3. 一个golang项目应该长什么样
4. golang常用工具和框架
