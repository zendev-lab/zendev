---
zfp: 6
title: "消息与提案领域及共享基础"
type: Feature
authors:
  - "zrr1999"
created: 2026-09-24
supersedes: []
---

# ZFP-0006: 消息与提案领域及共享基础

## 摘要

ZenDev 由消息、提案两个领域和一套共享基础构成。合并 commit/review 发行包，
统一配置发现、Markdown 事实与诊断；类型表达变更分类，emoji 表达具体意图。
提案检查、修复计划与文件写回分离。所有公开变化在一个版本中迁移。

## 动机

现有 emoji 与 75 个类型一一对应，`deps` 又通过代码别名解释为 `deps-up`，使
“依赖变更”和“依赖升级”的边界不清。校验、正则、消息生成和帮助各自解释策略。
commit/review 的包边界把同一个消息领域拆开，CLI 同时承担配置、校验和输出。

PR 正文的字符串扫描与提案的 Markdown 解析不一致，代码示例和 HTML 注释可能
被当成有效章节。提案索引和校验双向依赖，修复调用私有校验函数，CLI 负责候选
选择与事务编排。这些问题需要明确规则所有者，而不是增加兼容分支。

## 设计

### 发行与模块边界

五个发行包共享一个版本：`zendev` 组合 CLI；`zendev-message` 拥有消息解析、
策略、生成与 PR 检查；`zendev-proposal` 拥有提案规则与修复；`zendev-core`
仅提供配置发现、源位置、诊断及 Markdown 事实；`zendev-log` 保留独立日志工具。
消息与提案依赖 core，core 不依赖领域包、Typer 或 Git 命令。

保留 `zendev commit`、`zendev message check`、`zendev proposal check`。
消息发行包提供 `zendev-commit` 和 `zendev-message`，提案发行包提供
`zendev-proposal`。根发行包依赖全部组件；同仓组件的 wheel 依赖固定到相同版本。

### 配置

`zendev.toml` 顶层与 `pyproject.toml` 的 `[tool.zendev]` 等价，版本为 1。
消息使用 `[message]` 和 `[message.body]`；提案使用 `[proposal]` 及子表。
原 proposal policy 的辅助表移入 proposal 命名空间，索引路径使用
`proposal.index.path`。模板和 JSON Schema 继续独立保存。

`--config` 显式指定唯一来源；否则从调用目录向上查找最近配置，在 Git 工作树根
停止。没有 `[tool.zendev]` 的 pyproject 不截断查找。同目录两份配置报错，不合并。
路径相对配置目录解析；显式 CLI 选项覆盖配置。领域仅加载自身资源。
旧配置报迁移错误，不静默回退。提案检查必须有提案配置，消息默认 profile 为 zendev。

### 消息模型

固定分类为 `feat`、`fix`、`docs`、`style`、`refactor`、`perf`、`test`、
`build`、`ci`、`chore`、`deps`、`revert`。分类只约束 zendev profile；
conventional 和 gitmoji profile 保持各自语法。

Gitmoji 目录记录上游事实，随包 TOML 单独记录允许配对。校验、交互、帮助与建议
共用此表；上游新增条目必须显式分类。Unicode、无 variation selector 写法与
shortcode 均受支持。初始目录的完整分类为：

| 允许类型 | Gitmoji |
| --- | --- |
| feat | ✨ |
| fix | 🐛 🚑 🩹 🥅 🦖 👽 |
| docs | 📝 ✏️ 📄 💡 💬 👥 |
| style | 🎨 |
| refactor | ♻️ 🏗️ ⚰️ 🚚 |
| perf | ⚡️ |
| test | ✅ 🤡 📸 🧪 |
| build | 📦 |
| ci | 👷 💚 🚀 |
| chore | 🎉 🔖 🔧 🔀 🙈 💸 🧐 |
| deps | ⬆️ ⬇️ 📌 ➕ ➖ |
| revert | ⏪️ |
| build, ci, chore | 🔨 🧱 🧑‍💻 |
| fix, style | 🚨 |
| 所有类型 | 🚧 💩 🍻 |
| 所有类型，必须声明 breaking | 💥 |
| feat, fix, refactor, perf, chore | 🔥 💄 🔒 🔐 📈 🌐 🍱 ♿️ 🗃️ 🔊 🔇 🚸 📱 🥚 ⚗️ 🔍 🏷️ 🌱 🚩 💫 🗑️ 🛂 👔 🩺 🧵 🦺 ✈️ |

`deps-up` 等旧类型不再接受，诊断说明新分类。生成必须明确选择 emoji，不把
deps 默认解释为升级。breaking 是独立属性，通过 `!` 或合法 footer 声明。
删除 `schema_pattern()`，结构化解析与检查是唯一权威。纯函数不发现配置、打印
或执行 Git；交互与 Git 执行属于适配层。

增加 `message check --commit` 供 commit-msg hook 显式选择 Git 消息语义。
默认 auto 仍按单行 title、多行 commit 分派。Git 注释、scissors 与特殊消息
例外只适用于 commit 范围；title 严格检查单行原文。

Markdown 使用共用语法解析，PR 章节只统计顶层标题，任务只统计指定章节中的
真实任务项。代码、引用和注释不能满足要求。列表标记与复选框大小写不影响匹配，
任务正文一致才匹配。模板缺失报配置错误，不隐式使用英文默认章节。

### 诊断与提案流程

共享诊断字段 `code/message/path/line/hint/fixable`，复用 proposal JSON v1
envelope。各检查提供 `--format human|json|github`，默认 human，Actions 显式
选择 github。退出码 0 为成功，1 为内容错误，2 为配置或环境错误。
诊断位置来自源结构，不能从错误文案反推。

提案应用流程为加载快照、解析、校验、规划候选、校验候选、生成源文件及索引
变更计划、显式执行。关系和引用规则不由索引拥有；校验、索引和修复共同复用它们。
CLI 只处理参数与呈现，不决定候选是否安全或直接写文件。

一次运行持有配置、文档、模板、本地 schema 引用、链接目标和指定 Git 基线。
解析事实在同一运行的同一版本复用，不建立跨运行缓存。候选不能混读旧文件。
`ChangePlan` 记录基线、前后字节、规则和诊断，全部写入通过统一边界。

保留 ZFP-0005 的 `--fix/--diff/--select/--partial` 行为。默认候选整体合法才写；
partial 有剩余错误仍失败且不更新索引；输入变化使计划失效；普通 I/O 失败尝试
回滚并准确报告残留。不承诺跨文件的崩溃原子性，不重新序列化整篇 YAML/Markdown。

### 与其他提案的关系

本提案调整 ZFP-0001 的发行边界和 ZFP-0003 的输入/输出选项，保留 ZFP-0005 的
规则与修复安全约束。尚未合并的 PR #24 中的 IDE 服务与 schema profile 不纳入
本次实现；其后续设计应复用本提案的配置与诊断，不建立第二份解释器。

## 兼容性

一次迁移：停止发布旧 commit/review 的新版本，不保留 Python 转发模块或旧类型
别名。既有历史发行物和 Git 历史不修改。用户迁移到 message 发行包、新配置和
结构化消息 API；`--json` 改为 `--format json`，hook 显式加 `--commit`。
旧提案字段、图、schema 和索引版本 2 的语义保持不变。提供逐项迁移文档。
其他消费仓库不在本次实现中直接修改。

## 验证

验证全部目录条目、token 变体、配对拒绝、breaking、生成后重解析及三个 profile。
复现并修复空描述、scope、Markdown 示例与隐藏 checklist 的误判。
两种配置载体等价，覆盖冲突、嵌套目录、工作树和旧配置错误。

提案既有回归保持通过，检查与 diff 零写入，修复幂等，并注入输入变化、准备、
替换和回滚失败。构建并在隔离环境实际安装五个 wheel，验证 namespace 不重叠、
数据和类型信息齐全、独立命令与公开 hook 可用。CI 和 check 只读，格式化显式执行。
