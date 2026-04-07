---
layout: post
title: 用 Traefik 替代 Nginx 做服务发现，聊聊我们踩过的坑
date: '2026-04-07T11:00:00+08:00'
permalink: "/posts/traefik-service-discovery"
categories: [ai]
---

之前团队用 Kubernetes 跑了一年多，说实话有点受够了。我们的业务规模根本用不到 K8s 那套东西，但 Helm chart、Ingress controller、Service mesh 这些东西一个都少不了，运维复杂度远超业务本身的复杂度。后来下决心砍掉 K8s，退回 Docker Compose——就是一个 `docker-compose.yml`，`up -d` 就跑，挂了 `restart: always` 自己拉起来，够用了。

但 Compose 有个绕不开的问题：服务发现。K8s 里 Service + Ingress 天然解决了这事，退回 Compose 之后你得自己搞。最开始用 Nginx，每次加个服务都要改配置然后 reload，烦了。后来换成 Traefik v3，它的 Docker Provider 能自动感知容器变化，服务起来就有路由，停掉就没了，不用碰任何配置文件。算是在 Compose 这套简单粗暴的架构上，把服务发现这块短板补上了。

<!--more-->

## 整体思路

Traefik 在我们项目里承担唯一入口网关的角色，监听 80（HTTP）、443（HTTPS）和 9000（TCP，跑 FIX 协议）。所有服务都跑在同一个 Docker bridge 网络里，Traefik 通过挂载 docker.sock 来感知谁上线了、谁下线了。

但光靠 Docker 一个数据源不够用。实际跑下来我们用了三个 Provider，各管一摊事：

## 三个 Provider 各司其职

**Docker Provider** 是主力。配置很简单：

```yaml
providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
```

`exposedByDefault: false` 这个一定要加，不然所有容器都会被暴露出去。加了之后，只有在 docker-compose 里显式写了 `traefik.enable=true` 的服务才会被发现。

一个典型的服务声明长这样：

```yaml
labels:
  traefik.enable: true
  traefik.http.routers.grafana.rule: Host(`grafana.example.com`)
  traefik.http.routers.grafana.entrypoints: https
  traefik.http.services.grafana.loadbalancer.server.port: 3000
```

四行搞定。容器一起来 Traefik 就知道了，不需要任何人工介入。

**HTTP Provider** 解决的是动态路由的问题。我们有一批实例需要根据业务状态动态生成路由规则，靠 Docker labels 写死是不行的。做法是让 n8n 工作流暴露一个 webhook，返回 Traefik 格式的路由配置，Traefik 定期去拉：

```yaml
providers:
  http:
    endpoint: "http://n8n:5678/webhook/traefik-zhouyi-config"
```

这样业务侧注册了新实例，n8n 自动更新配置，Traefik 热加载，全程不用重启。

**File Provider** 最简单，就是放一些全局共享的中间件定义，比如跨域配置。写在 `traefik-dynamic.yml` 里，Docker labels 里通过 `@file` 引用：

```yaml
labels:
  - "traefik.http.routers.sonar.middlewares=no-cors@file"
```

三个 Provider 的分工很清晰：Docker 管常规服务发现，HTTP 管动态业务路由，File 管共享中间件。互不干扰。

## Labels 里能玩的花样不少

最常用的是路径匹配加中间件。比如前端请求 `/api/users`，后端服务实际监听的是 `/users`，用 stripprefix 中间件把前缀去掉：

```yaml
labels:
  - "traefik.http.routers.api.rule=Host(`app.example.com`) && PathPrefix(`/api`)"
  - "traefik.http.routers.api.middlewares=api_strip"
  - "traefik.http.middlewares.api_strip.stripprefix.prefixes=/api"
```

条件可以组合，`&&` 和 `||` 随便拼：

```yaml
- "traefik.http.routers.demo.rule=Host(`demo.example.com`) && (PathPrefix(`/http`) || PathPrefix(`/rest`) || PathPrefix(`/api/v3`))"
```

TCP 也能路由，我们用来跑 FIX 协议。`tls.passthrough=true` 让 TLS 终止交给后端处理，Traefik 只做四层转发：

```yaml
labels:
  - "traefik.tcp.routers.fix.rule=HostSNI(`fix.example.com`)"
  - "traefik.tcp.routers.fix.entrypoints=tcp"
  - "traefik.tcp.routers.fix.tls.passthrough=true"
  - "traefik.tcp.services.fix.loadbalancer.server.port=9994"
```

## 证书这块基本不用操心

用 ACME 配合阿里云 DNS Challenge，申请通配符证书，一张证书覆盖所有子域：

```yaml
certificatesResolvers:
  acmeresolver:
    acme:
      storage: "/traefik/acme.json"
      dnsChallenge:
        provider: alidns
        resolvers:
          - 223.5.5.5:53
          - 223.6.6.6:53

tls:
  stores:
    default:
      defaultGeneratedCert:
        resolver: acmeresolver
        domain:
          main: example.com
          sans:
            - "*.example.com"
            - "*.dev38.example.com"
            - "*.uat.example.com"
```

新加服务不用管证书的事，自动匹配。我们十几个子域环境（dev、uat、staging、pre……）都是这一套配置覆盖的。

## 多环境复用

同一份 docker-compose 通过环境变量适配不同环境：

```yaml
labels:
  - "traefik.http.routers.app.rule=Host(`app.${ENV_ID}.example.com`)"
  - "traefik.http.routers.app.entrypoints=${HTTP_ENDPOINT}"
```

dev 环境 `HTTP_ENDPOINT=http`，线上 `HTTP_ENDPOINT=https`，compose 文件不用改。

## 回头看

从 Nginx 切到 Traefik 大概两周，最明显的变化是加服务的心智负担没了。以前是改配置、测配置、reload、祈祷别写错；现在是写好 labels、`docker compose up -d`、完事。

当然 Traefik 也有它的问题，比如 labels 写多了可读性很差（看看上面那个 Clash 的路由就知道了），排查问题的时候不如 Nginx 配置文件直观。但对于 Docker Compose 这种部署方式来说，服务发现这件事它确实做得比 Nginx 好很多。
