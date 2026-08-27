# Zendev Feature Proposals

ZFP 是记录 zendev 公开功能与治理规则的轻量、持久决策。提出或实现功能前，先阅读
[ZFP-0000](./ZFP-0000-governance.md)。

候选 ZFP 直接作为带编号文档的 pull request 提交；仓库不维护单独的草稿目录。
第一个提交使用 `Draft`，评审通过后在后续提交中改为 `Accepted`。

提交的[索引](../zfps-index.json)由提案 frontmatter 确定性生成，可用以下命令检查：

```console
$ uv run zendev-proposal check
$ uv run zendev-proposal index --check
```
