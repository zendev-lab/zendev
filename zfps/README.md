# Zendev Feature Proposals

ZFP 是记录 zendev 公开功能与治理设计的轻量、持久提案。提出或实现功能前，先阅读
[ZFP-0000](./ZFP-0000-governance.md)。

候选 ZFP 直接作为带编号文档的 pull request 提交；仓库不维护单独的草稿目录。
ZFP 不编码采纳或实现状态，合并只表示提案文本进入版本库。未合并的候选保留在关闭
的 pull request 中；实现 pull request 只需关联对应 ZFP，可以独立评审和合入。

ZFP pull request 复用仓库统一中文模板和 `zendev` title profile。title 使用
`docs(zfp)` scope，并以 `propose`、`revise` 或 `supersede` 表达本次文档变更；这些
动词是评审惯例，不是机器状态。

提交的[索引](../zfps-index.json)由提案 frontmatter 确定性生成，可用以下命令检查：

```shell
uv run zendev proposal check
uv run zendev proposal index --check
```
