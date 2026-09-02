---
zfp: 3
title: "数值提案索引身份"
type: Feature
authors:
  - "zrr1999"
created: 2026-09-02
supersedes: []
---

# ZFP-0003: 数值提案索引身份

## 摘要

`zendev-proposal` 的索引以 frontmatter 中的数值提案编号作为唯一主键。索引不再
同时保存格式化 `id`；正向和反向提案关系在生成时统一归一为数值。索引配置增加
字符串字段 shorthand，并把格式升级为 version 2。

## 动机

version 1 同时输出 `vep: 1` 和 `id: "VEP-0001"`，但后者完全由前者、`prefix`
和 `number_width` 派生，不能表达独立身份。关系边却使用格式化字符串，导致消费者
需要在两个等价键之间转换，才能连接索引图。配置还为每个同名 metadata 字段重复
声明 `name`、`source` 和 `key`，把 indexer 实现细节暴露给消费仓库。

## 设计

索引格式 version 2 使用数值编号作为唯一 proposal key。源文档仍可在文件名、正文
和关系 frontmatter 中使用 `VEP-0001` 等格式化标识符；indexer 在投影
`graph.fields` 和 `inverse` 字段时把它们归一为数值：

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

只有 `[graph].fields` 中的正向关系执行数值归一。`defines`、`authors` 等普通
metadata 数组保持原值。

## 兼容性

这是随 0.3.0 发布的破坏性变更。version 1 和 `source = "identifier"` 必须失败，
不提供别名或兼容分支。消费仓库需要把 `index.version` 改为 2，删除格式化 `id`
字段，按需改用字符串 shorthand，重新生成并提交索引。读取关系边的消费者需要从
格式化字符串切换为数值键。

## 验证

VEP fixture 证明索引只保留数值 `vep`，并把正向、反向关系都生成为整数。SEP
fixture 证明无编号草稿仍输出 `null`，且 authors 等普通数组不被归一。配置测试覆盖
字符串与 table 等价、混合形式重复字段、空 shorthand、version 1 和已删除的
`identifier` source。ZFP、VEP 和 SEP 的 committed index 均由 version 2 生成器
重新写入并通过 drift check。
