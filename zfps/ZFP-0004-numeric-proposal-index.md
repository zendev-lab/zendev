---
zfp: 4
title: "数值提案索引身份"
type: Feature
authors:
  - "zrr1999"
created: 2026-09-02
supersedes: []
---

# ZFP-0004: 数值提案索引身份

## 摘要

`zendev-proposal` 的索引只收录已有编号的正式提案，以 frontmatter 中的数值提案编号
作为仓库内唯一主键。生成器不再派生格式化 `id`；正向和反向提案关系在生成时统一归一为数值。索引配置增加
字符串字段 shorthand，减少同名 metadata 字段的重复声明。

## 动机

现有索引同时输出 `vep: 1` 和 `id: "VEP-0001"`，但后者完全由前者、`prefix`
和 `number_width` 派生，不能表达独立身份。关系边却使用格式化字符串，导致消费者
需要在两个等价键之间转换，才能连接索引图。配置还为每个同名 metadata 字段重复
声明 `name`、`source` 和 `key`，把 indexer 实现细节暴露给消费仓库。

## 设计

新索引格式只收录已有编号的正式提案，使用数值编号作为仓库内唯一 proposal key。
对于定义生命周期状态的消费仓库，正式提案即使处于 `Draft` 状态也收录；ZFP 本身
不使用状态字段。尚未编号的前期草稿不进入索引，因此编号字段
不会输出 `null`。删除 `index.include_drafts` 配置项，索引收录范围不再由该开关控制。

源文档仍可在文件名、正文
和关系 frontmatter 中使用 `VEP-0001` 等格式化标识符；indexer 在投影
`graph.fields` 和 `inverse` 字段时把它们归一为数值：

提案关系必须指向仓库内已编号的正式提案。格式错误、不存在的编号、未编号草稿和
外部引用均报诊断，禁止透传或静默丢弃边。任何关系错误都阻止索引生成和写入，
公开 Python 索引 API 也必须遵守此规则。外部引用可由普通 metadata 字段承载。

```json
{
  "version": 2,
  "veps": [
    {
      "vep": 1,
      "requires": [0],
      "required_by": []
    }
  ]
}
```

`index.fields` 接受字符串或 inline table。字符串 `"title"` 等价于
`{ name = "title", source = "metadata", key = "title" }`；非 metadata 来源与
重命名字段继续使用 table。`source = "identifier"` 从公共配置中删除：

`index.fields` 必须且只能投影一次 `proposal.number_field`，其 `source` 必须为
`metadata`，且 `name` 和 `key` 均等于该编号字段名。缺失、重命名或重复投影均报
配置错误；生成器不隐式注入主键。

```toml
[index]
version = 2
entries_key = "veps"
fields = [
  "vep",
  { name = "path", source = "path" },
  "title",
  "requires",
  { name = "required_by", source = "inverse", key = "requires" },
]
```

metadata 投影是否执行关系归一，由其 `key` 是否属于 `[graph].fields` 决定，
与输出字段的 `name` 无关。例如 `{ name = "dependencies", source = "metadata", key = "requires" }`
在 `requires` 属于 graph 字段时仍输出数值边；把普通 metadata 字段重命名为
`requires` 不会触发归一。`defines`、`authors` 等普通 metadata 数组保持原值。

生成器不再提供派生格式化身份的 `identifier` source。`id` 不是保留的特殊输出
字段名，也不禁止使用。消费仓库仍可投影同名 metadata；该字段不构成生成器定义的提案身份。

`index.version` 表示生成器定义的索引输出格式，只接受上述示例中的格式值，其他值
均报配置错误。它与配置文件顶层的版本含义不同；顶层版本保持不变。

## 兼容性

这是破坏性变更。旧索引版本、`source = "identifier"` 和 `index.include_drafts`
必须失败，不提供别名或兼容分支。消费仓库需要更新 `index.version`，
删除派生格式化 `id` 的字段配置及 `index.include_drafts`，按需改用
字符串 shorthand，重新生成并提交索引。读取关系边的消费者需要从格式化字符串
切换为数值键。

## 验证

VEP fixture 证明索引只保留数值 `vep`，并把正向、反向关系都生成为整数。SEP
fixture 证明无编号草稿不进入索引，已有编号且状态为 `Draft` 的正式提案仍被收录，
且 authors 等普通数组不被归一。重命名测试证明关系归一取决于 metadata `key`，
而非输出 `name`，并允许普通 `id` metadata 投影。配置测试覆盖字符串与 table 等价、
混合形式重复字段、空 shorthand、不支持的索引格式和已删除的 `identifier` source
及 `include_drafts` 配置项。ZFP、VEP 和 SEP 的 committed index 均由新版生成器
重新写入并通过 drift check。

失败路径覆盖错误引用、缺失目标、未编号草稿和外部引用，证明 CLI 与公开 Python
索引 API 均拒绝生成且不改写已有索引。配置测试覆盖主键缺失、重命名和重复投影。
