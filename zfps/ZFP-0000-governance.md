---
zfp: 0
title: "Zendev 功能提案治理"
type: Governance
authors:
  - "zrr1999"
created: 2026-08-26
supersedes: []
---

# ZFP-0000: Zendev 功能提案治理

## 摘要

每项改变 zendev 公开契约的功能都从一份轻量的 Zendev Feature Proposal
（ZFP）开始。ZFP 保存提案文本，Git 和对应的 pull request 记录讨论与变更；ZFP
不编码提案是否采纳或功能是否实现。

## 动机

Zendev 已经包含多个 CLI 工作流、发行包和仓库策略。短小而持久的提案能让公开
契约保持可评审，同时不引入数据库、审批服务或额外的状态流程。

## 设计

新增 CLI 或选项、公开 Python API、配置或 schema 格式、发行包边界，以及用户
可见的工作流行为时，必须先提交 ZFP。恢复既有契约的缺陷修复、测试、文档、依赖
维护和不改变公开行为的内部重构不需要 ZFP；无法确定时，优先撰写短提案。

ZFP 使用仓库模板，并通过只包含提案的 pull request 评审。合并只表示提案文本进入
版本库，不代表采纳、排期或实现。未合并的候选保留在关闭的 pull request 中。实现
pull request 只需关联对应 ZFP，可以独立评审和合入。

`Feature` ZFP 描述公开功能，`Governance` ZFP 描述 zendev 自身的提案、发布或
协作规则。ZFP 默认使用中文正文，但作者可以根据读者选择英文；编号、类型、代码、
命令和技术标识保持英文。schema 和校验器不检查自然语言，也不维护 `language`
字段。

ZFP pull request 复用仓库统一中文模板和 `zendev` title profile。新提案、修订和
替代分别使用 `propose`、`revise` 和 `supersede`；这些动词帮助人类识别变更意图，
不构成机器状态或合并门禁。title 只写主题，不包含提案编号。

提案永久保留在 Git 中。后续提案替代旧提案时，在新文档的 `supersedes` 中引用旧
提案；索引据此派生 `superseded_by`。不改变提案含义的编辑修订可以直接更新原记录。

## 兼容性

本治理规则只适用于 ZFP-0000 之后提出的功能。既有行为和 pull request #12 不需要
追溯补写提案。`Process` 类型在首次发布前直接替换为 `Governance`，ZFP 状态字段也
在首次发布前删除，均不保留别名或迁移层。

## 验证

`zendev-proposal check` 校验当前 ZFP 元数据、模板章节、关系和确定性索引。仓库 hook
运行相同的快照检查，但不会从 Git 历史、实现 diff 或 pull request 文本推断提案
状态与采纳结果。
