---
zfp: 0
title: "Zendev 功能提案治理"
status: Accepted
type: Governance
authors:
  - "zrr1999"
created: 2026-08-26
supersedes: []
---

# ZFP-0000: Zendev 功能提案治理

## 摘要

每项改变 zendev 公开契约的功能都从一份轻量的 Zendev Feature Proposal
（ZFP）开始。ZFP 记录已经接受的决策，Git 和对应的 pull request 记录讨论与
接受过程。

## 动机

Zendev 已经包含多个 CLI 工作流、发行包和仓库策略。短小而持久的设计记录能让
公开契约保持可评审，同时不引入数据库、审批服务或复杂的状态流程。

## 设计

新增 CLI 或选项、公开 Python API、配置或 schema 格式、发行包边界，以及用户
可见的工作流行为时，必须先提交 ZFP。恢复既有契约的缺陷修复、测试、文档、依赖
维护和不改变公开行为的内部重构不需要 ZFP；无法确定时，优先撰写短提案。

ZFP 使用仓库模板，并通过只包含提案的 pull request 接受。第一个提案提交必须为
`Draft`；评审形成接受决策后，在同一 pull request 的后续提交中改为 `Accepted`。
只有状态为 `Accepted` 的提案 pull request 才能合并，合并后它才进入默认分支的
规范记录。被拒绝或撤回的候选以 `Draft` 状态保留在关闭的 pull request 中。实现
可以作为依赖提案的 Draft pull request 提前准备，但必须在对应 ZFP 接受后才能合并。

`Feature` ZFP 定义公开功能，`Governance` ZFP 定义 zendev 自身的提案、发布或
协作规则。ZFP 默认使用中文正文，但作者可以根据读者选择英文；编号、状态、类型、
代码、命令和技术标识保持英文。schema 和校验器不检查自然语言，也不维护
`language` 字段。

已接受的决策永久保留在 Git 中。替代提案把旧记录更新为 `Superseded`，并在
`supersedes` 中引用它；不改变决策的编辑修订可以直接更新原记录。ZFP-0000 也按
本规则先以 `Draft` 提交，再在评审后转为 `Accepted`，没有启动例外。

## 兼容性

本治理规则只适用于 ZFP-0000 之后提出的功能。既有行为和 pull request #12 不需要
追溯补写提案。`Process` 类型在首次发布前直接替换为 `Governance`，不保留别名或
迁移层。

## 验证

`zendev-proposal check` 校验 ZFP 元数据、模板章节、关系和确定性索引。pull request
CI 传入准确的 base SHA；校验器依次检查从 base 到 HEAD 的每个已提交状态以及工作区
状态，确保新提案从 `Draft` 开始，且只发生允许的状态转换。仓库 hook 不尝试从实现
diff 推断是否需要 ZFP。
