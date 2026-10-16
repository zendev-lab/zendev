# Zendev Feature Proposals

ZFP 是记录 zendev 公开功能与治理设计的轻量、持久提案。治理边界、提案门槛与
作者身份见 [ZFP-0000](./ZFP-0000-governance.md)。

## 编写与提交

候选 ZFP 直接作为带编号文档的 pull request 提交；仓库不维护单独的草稿目录。

1. 将 [`templates/zfp.md`](../templates/zfp.md) 复制为
   `zfps/ZFP-NNNN-<slug>.md`。
2. 按 [`schemas/zfp.schema.json`](../schemas/zfp.schema.json) 和
   [`zendev.toml`](../zendev.toml) 填写元数据与正文：
   - frontmatter 的 `zfp` 与已提交的[索引](../zfps-index.json)使用整数编号；
   - 文件名、正文一级标题 `# ZFP-NNNN: <title>` 与 `supersedes` 引用使用格式化
     标识符 `ZFP-NNNN`；
   - frontmatter 的 `title` 不含 `ZFP-NNNN:` 前缀；
   - `authors` 填写实际作者的小写 GitHub 用户名。
3. 检查提案并写回确定性索引：

```shell
uv run zendev proposal check
uv run zendev proposal check --fix
```

ZFP 不编码采纳或实现状态，合并只表示提案文本进入版本库。未合并的候选保留在关闭
的 pull request 中；实现 pull request 关联对应 ZFP 后可独立评审和合入。

## Pull request 约定

ZFP 的 pull request 复用仓库中文 PR 模板，标题使用 `docs(zfp)` 与以下评审动词
（非机器状态）：

- `📝 docs(zfp): propose <topic>`
- `📝 docs(zfp): revise <topic>`
- `📝 docs(zfp): supersede ZFP-NNNN with <topic>`

新提案与修订标题只写主题，不写提案编号；替代类标题写明被替代的 `ZFP-NNNN` 和新
主题，不写新提案编号。
