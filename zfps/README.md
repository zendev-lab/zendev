# Zendev Feature Proposals

ZFP 是记录 zendev 公开功能与治理设计的轻量、持久提案。提出或实现功能前，先阅读
[ZFP-0000](./ZFP-0000-governance.md)。

先判断是否引入已有提案尚未覆盖的公共契约或治理决定。新增接口、默认行为、格式
或治理规则需要提案；实现已有 ZFP、恢复既定行为的修复和保持语义的维护可以直接
提交 PR。完整边界与实例见 [ZFP-0000 的提案门槛](./ZFP-0000-governance.md#何时需要提案)。
不能仅凭代码量或 PR 标签判断。

`authors` 填写实际作者的小写 GitHub 用户名，例如 `zrr1999`，不带 `@`，不使用
显示名称、邮箱或 URL。格式和作者责任见
[作者身份](./ZFP-0000-governance.md#作者身份)；从模板开始时替换示例账号。

候选 ZFP 直接作为带编号文档的 pull request 提交；仓库不维护单独的草稿目录。
ZFP 不编码采纳或实现状态，合并只表示提案文本进入版本库。未合并的候选保留在关闭
的 pull request 中；实现 pull request 只需关联对应 ZFP，可以独立评审和合入。

ZFP 的 pull request 复用仓库统一中文模板和 `zendev` 标题约定。新提案、修订和
替代分别使用 `propose`、`revise` 和 `supersede`；这些动词是评审惯例，不是机器
状态。新提案和修订的标题只写主题，不写提案编号；替代类标题须写明被替代的
`ZFP-NNNN` 和新提案主题，形如 `supersede ZFP-NNNN with <topic>`，但不写新提案
编号。新提案编号只出现在文件名、frontmatter 和索引中。

提交的[索引](../zfps-index.json)由提案 frontmatter 确定性生成。检查或写回索引：

```shell
uv run zendev proposal check
uv run zendev proposal check --fix
```
