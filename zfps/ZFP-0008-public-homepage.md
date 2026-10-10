---
zfp: 8
title: "公开首页留在工具包仓库"
type: Governance
authors:
  - "zrr1999"
created: 2026-09-30
supersedes: []
---

# ZFP-0008: 公开首页留在工具包仓库

## 摘要

zendev 的公开首页是 `zendev.zrr.dev` 上的一个英文单页，源码放在本仓库的
`homepage/`。不把它并入文档站，也不为它新建仓库。页面只做定位和出口；安装步骤、
指南和参考仍由 README 与 `docs/` 拥有。

## 动机

公开入口现在有两处，都不是首页。根 README 是 GitHub 和 PyPI 的落地页。
`docs/index.md` 是文档站入口，由 Zensical 投影到 `docs.zendev.zrr.dev`。
`docs/development/contributing.md` 禁止为文档站增加自定义 CSS、JavaScript 或插件。
根 `wrangler.toml` 只声明文档站域名。`pyproject.toml` 的 Homepage 指向 GitHub。

需要一个页面说明这是什么，以及接下来打开哪一份文档。把这个页面写成 `docs/` 里的
另一篇 Markdown，它仍然是文档站的一页，也不能在现有文档规则下单独设计版式。为这一页
新建仓库，会把命令名和文档链接的修改拆出本仓库的评审，并增加一套仓库权限和部署身份。
这一页没有独立工具链。PyPI 发布只在 tag 上发生，首页提交不会发布 wheel，新建仓库
也带不来发布隔离。

## 设计

首页目录与文档站并列，不进入 wheel，也不写入 `zensical.toml`：

```text
homepage/
├── index.html
├── 404.html
├── site.css
└── wrangler.toml
```

`homepage/wrangler.toml` 只声明 `zendev.zrr.dev`。根 `wrangler.toml` 继续只声明
`docs.zendev.zrr.dev`。不在本提案中增加部署 workflow；文档站目前也没有随仓库提交的
自动发布。页面可访问之前，不修改 `[project.urls] Homepage`。

### 页面

读者是还没有选定指南的人。语言使用英文，与 README 和 `docs/` 一致。

`index.html` 满足下面的内容。具体用词可以调整，事实和出口不能换：

- 标题表达 repository-native development workflows。
- 说明 Git 和已提交的仓库文件是事实来源，并点明四类工作：commits、pull-request
  messages、proposals、project evolution。
- 给出可复制的 `uvx zendev --help`。项目内安装只链接
  `https://docs.zendev.zrr.dev/getting-started/`，不在首页列出组件发行包。
- 四项工作各保留一条命令和一个指南链接：

| 工作 | 命令 | 指南 |
| --- | --- | --- |
| Commits | `zendev commit` | `https://docs.zendev.zrr.dev/guides/commits/` |
| Messages | `zendev message check` | `https://docs.zendev.zrr.dev/guides/message-checks/` |
| Proposals | `zendev proposal check` | `https://docs.zendev.zrr.dev/guides/proposals/` |
| Evolution | `zendev evolution check` | `https://docs.zendev.zrr.dev/guides/evolution/` |

- 用一节说明术语、模板、schema 和治理决定留在仓库，并链接
  `https://docs.zendev.zrr.dev/concepts/repository-native/`。
- 页脚链接文档站、`https://github.com/zendev-lab/zendev`、
  `https://pypi.org/project/zendev/` 和 `zfps/` 的 GitHub 目录。

版式约束：单栏阅读；命令使用等宽字体；不请求外部字体、图片或分析服务。复制命令的
脚本可以缺省，没有脚本时命令仍能被选中。不复用 Zensical 主题，也不修改它。正文对比度
需要能阅读，并尊重 `prefers-reduced-motion`。未知路径返回 `404.html`，其中有回到
`/` 的链接。

### 所有权

| 位置 | 拥有 |
| --- | --- |
| `homepage/` | 这一页的措辞和样式 |
| `README.md` | GitHub 与 PyPI 落地，以及安装入口 |
| `docs/` | 概念、指南、集成和参考 |
| `zfps/` | 设计与治理记录 |

首页可以出现命令和链接，因为它们是出口。它不复制包表、配置字段或指南步骤。

实现时在 `CONTRIBUTING.md` 的文档所有权表增加 `homepage/`，并链接本提案。

### 保留目录、不新建仓库

单独仓库能够隔离前端工具链。这一页没有工具链：一组静态文件，加一份只服务该主机的
Wrangler 配置。命令和指南链接的权威说明在本仓库；放在同一目录里，链接变更可以和
说明变更一起评审。

目录就是以后的拆分缝。当页面不再是上述单页，或者出现独立的前端工具链、资源管线或
多页内容时，再把 `homepage/` 整目录移出。组织站点要同时介绍 spark、cue 和 zendev，
那是另一个网站，不是本页。

只改 `docs/index.md` 不能产生文档站以外的地址，也不能绕过文档站的皮肤限制。只保留
README 也不能成为 `zendev.zrr.dev` 的响应。

## 兼容性

CLI、配置、文档 URL 和 tag 发布都不改变。删除 `homepage/` 不影响 wheel。Homepage
URL 仍指向 GitHub，直到 `https://zendev.zrr.dev/` 返回这一页；回滚是把该 URL 指回
GitHub。将来若整目录迁出，文档 URL 保持不变。

## 验证

`zendev proposal check` 通过。实现后的 `homepage/index.html` 包含上表四条命令、四条
指南链接和概念页链接，且不包含组件发行包表。`zensical.toml` 不引用 `homepage/`。
根 `wrangler.toml` 不声明 `zendev.zrr.dev`。用浏览器打开页面时，首屏能读到定位和
`uvx` 命令；窄宽度下正文不横向裁切；禁用脚本后命令仍可选择。未知路径展示 404，并
提供回首页的链接。
