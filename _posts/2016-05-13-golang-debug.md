---
layout: post
title: Golang调试:Delve 和 golang-debug
date: '2016-05-13T10:00:39+08:00'
permalink: "/posts/golang-debug"
categories: [golang]
---

本文主要涉及两个工具:

**1. Delve**

[delve](https://github.com/derekparker/delve), golang的一个debug工具, 简单易用, 目前版本pre 1.0, 功能还在变化中, 但是能满足我们平常开发的大部分debug功能, 比较活跃, 平均每天10个左右commit
  ![Hi-Ruby.com Keychain Access钥匙串工具](/images/posts/golang-debug/commits.png)

**2. golang-debug**

[golang-debug](https://atom.io/packages/go-debug) 是 [Atom](https://atom.io)的一个插件, 基于[delve](https://github.com/derekparker/delve), 能够实现类似Eclipse下Java调试的功能

----

## 安装Devle

**linux下安装很方便, 直接运行即可**

```bash
go get github.com/derekparker/delve/cmd/dlv
go install github.com/derekparker/delve/cmd/dlv

dlv version
```

**但是Mac下安装涉及到一个验签的步骤, 很多人就因此而放弃, 本文着重说一下Mac下如何安装Devle, 其实就是验签的过程**

1. 打开钥匙串工具(Keychain Access)

    ![Hi-Ruby.com Keychain Access钥匙串工具](/images/posts/golang-debug/keychain.png)

2. 打开菜单, 点击 /钥匙串访问/证书助理/创建证书, 更改名称, 如下图:

    ![Hi-Ruby.com Mac下在安装Devle-2](/images/posts/golang-debug/2.png)

3. 有效期(天数)可以设为较长一点的值, 反正自己用

    ![Hi-Ruby.com Mac下在安装Devle-3](/images/posts/golang-debug/3.png)

4. 证书信息, 可以填写, 也可以直接点击继续

    ![Hi-Ruby.com Mac下在安装Devle-4](/images/posts/golang-debug/4.png)

5. 点击继续

    ![Hi-Ruby.com Mac下在安装Devle-5](/images/posts/golang-debug/5.png)

6. 点击继续

    ![Hi-Ruby.com Mac下在安装Devle-6](/images/posts/golang-debug/6.png)

7. 这个步骤要将存储位置改为`系统`, 然后点击创建

    ![Hi-Ruby.com Mac下在安装Devle-7](/images/posts/golang-debug/7.png)

8. 创建证书需要授权, 点击允许

    ![Hi-Ruby.com Mac下在安装Devle-8](/images/posts/golang-debug/8.png)

9. 创建证书成功

    ![Hi-Ruby.com Mac下在安装Devle-9](/images/posts/golang-debug/9.png)

10. 回到钥匙串访问工具, 找到我们刚刚创建的证书, 双击打开

    ![Hi-Ruby.com Mac下在安装Devle-10](/images/posts/golang-debug/10.png)

11. 将信任级别设为`始终信任`, 然后关闭

    ![Hi-Ruby.com Mac下在安装Devle-11](/images/posts/golang-debug/11.png)

再一次授权后, 这时我们的验签工作才算完成, 那么证书要怎么用呢？下面我们开始安装[delve](https://github.com/derekparker/delve)(貌似才入主题...)

如果你已经安装过delve, 但是无法使用, 需要删掉, 再按照以下方式安装:

```bash
mkdir $GOPATH/src/github.com/derekparker && cd $GOPATH/src/github.com/derekparker
git clone git@github.com:derekparker/delve.git && cd delve
CERT=dlv-cert make install
```

然后让我们试试:

```bash
$ dlv
Delve is a source level debugger for Go programs.

Delve enables you to interact with your program by controlling the execution of the process,
evaluating variables, and providing information of thread / goroutine state, CPU register state and more.

The goal of this tool is to provide a simple yet powerful interface for debugging Go programs.

Usage:
  dlv [command]

Available Commands:
  version     Prints version.
  run         Deprecated command. Use 'debug' instead.
  debug       Compile and begin debugging program.
  exec        Runs precompiled binary, attaches and begins debug session.
  trace       Compile and begin tracing program.
  test        Compile test binary and begin debugging program.
  attach      Attach to running process and begin debugging.
  connect     Connect to a headless debug server.

Flags:
      --accept-multiclient[=false]: Allows a headless server to accept multiple client connections. Note that the server API is not reentrant and clients will have to coordinate
      --api-version=1: Selects API version when headless
      --build-flags="": Build flags, to be passed to the compiler.
      --headless[=false]: Run debug server only, in headless mode.
  -h, --help[=false]: help for dlv
      --init="": Init file, executed by the terminal client.
  -l, --listen="localhost:0": Debugging server listen address.
      --log[=false]: Enable debugging server logging.

Use "dlv [command] --help" for more information about a command.
```

安装好Devle之后, 让我们来安装golang-debug

## 2. Atom上安装golang-debug

```bash
apm install golang-debug
```

## 3. 使用

无图无真相, 直接上图

![Hi-Ruby.com Mac下在安装Devle-golang-debug](/images/posts/golang-debug/screener.png)

在代码行号左侧可以添加、删除断点

右侧会出现golang-debug窗口:

- 上方点击debug后进入debug模式, 可以进行continue, next, stop, restart等常用的调试功能

- 下方可以查看堆栈信息, goroutine, 当前变量, 还有断点, 这样在一个IDE里面就可以对golang进行运行时调试, 不再需要加一堆打印之类的代码, 或者频繁去控制台重启项目了

点击下方, 查看介绍动画:

[Hi-Ruby.com Mac下在安装Devle-features](/images/posts/golang-debug/features.gif)
