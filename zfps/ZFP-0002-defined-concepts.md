---
zfp: 2
title: "可选的定义所有权校验"
type: Feature
authors:
  - "zrr1999"
created: 2026-09-02
supersedes: []
---

# ZFP-0002: 可选的定义所有权校验

## 摘要

为 `zendev-proposal` 增加可选的 `[defines]` 策略。开启后，提案与草稿中的概念
ID 必须与 HTML 锚点一一对应，并且一个概念在当前只能有一个所有者；所有权可以
沿 `supersedes` 替代链交接。

## 动机

提案仓库会把稳定概念写进 frontmatter，并在正文用锚点固定定义位置。这是仓库
机械约束，不是项目词表。若每个消费仓库各自写脚本，会重复同一套图遍历和锚点
计数。ZFP 自身不使用这套约定，因此该检查必须默认关闭。

## 设计

`proposal.toml` 增加可选表 `[defines]`：

```toml
[defines]
field = "defines"
anchor_prefix = "term-"
id_pattern = "[a-z][a-z0-9]*(?:-[a-z0-9]+)*"
```

三项均可省略，默认值如上。省略整张表时行为与 0.2.0 相同。开启后：

- `field` 列出的每个字符串必须对应恰好一个
  `<a id="{anchor_prefix}{id}"></a>` 锚点；
- 匹配该前缀与 `id_pattern` 的锚点必须出现在 `field` 中；
- 同一 ID 当前只能有一个所有者；被替代的旧提案仍可保留历史定义。若配置了
  `graph.supersedes_field`，所有权只能交给替代链上的现行提案：旧提案必须
  出现在现行提案的 `supersedes` 传递闭包里。

该策略不检查自然语言定义质量，也不引入项目词表。

## 兼容性

省略 `[defines]` 的仓库不受影响。开启该表的仓库必须在 frontmatter 与锚点上
满足上述机械规则。这是新增可选配置，不改变现有必选键。

## 验证

`zendev-proposal check` 在配置了 `[defines]` 时报告缺失锚点、未申报锚点和重复
所有者。针对 VEP fixture 的测试覆盖这三类失败，以及开启策略后的有效仓库。
