---
zfp: 3
title: "规范化统一 CLI 与提案 check --fix"
type: Feature
authors:
  - "zrr1999"
created: 2026-09-02
supersedes: []
---

# ZFP-0003: 规范化统一 CLI 与提案 check --fix

## 摘要

把统一 `zendev` 命令分成 `commit`、`message`、`proposal` 三组。文案校验入口是
`zendev message check`：输入来源是 `FILE` 或 `--text`，检查范围是默认 auto、
`--title` 或 `--body`。完整 message 的 body 使用 commit 自由文本语义；PR 模板
schema 只在 `--body` 下运行。删除独立的 `proposal index` 子命令和
`zendev-proposal-index` hook。提案索引漂移由只读的 `zendev proposal check` 报告，
并用 `zendev proposal check --fix` 显式写回，形态与 `ruff check --fix` 相同。公开
hook 标识为 `zendev-proposal-check`。

## 动机

当前 `zendev --help` 把 `commit`、`commit-msg`、`validate-title`、`validate-body`
和 `proposal` 平铺在同一层。命令名不能看出它们分别属于创建提交、校验文案还是提
案仓库，截断后的帮助文本也无法补救。

提交说明、PR 标题和 PR 正文都是在校验一段文案，而且标题与提交说明共用 commit
profile。它们不应再拆成 `commit-msg` 和一对 `validate-*` 命令，也不应把
`title` / `body` 做成三个不同动作。`title` 和 `body` 是同一次 check 的范围。

换行可以决定检查 title 还是完整 message，但不能顺便决定 body 使用哪套 schema。
Git commit body 是自由文本；当前 PR body 检查的是模板 H2 schema。若
`zendev message check FILE` 看到换行就同时运行 PR body validator，`commit-msg`
hook 会把合法提交说明判失败。

提案索引另有 `index --check`、`index --write` 和 manual-stage hook
`zendev-proposal-index`。消费仓库因此要记 `prek run --stage manual`，而漂移诊断
指向第三条命令。检查与修复本应是同一条 `check` 路径上的只读默认值与显式
`--fix`，不需要第二个 hook 或第二个子命令。

已有未合并草案占用了 `ZFP-0002`，因此本提案使用 `ZFP-0003`。

## 设计

### 统一命令分组

`zendev --help` 只列出三个领域命令：

```text
commit    Create a git commit
message   Validate commit and pull-request messages
proposal  Validate repository-native proposals
```

各组命令为：

| 统一命令 | 行为 |
| --- | --- |
| `zendev commit` | 交互式创建提交 |
| `zendev message check [FILE]` | 按 auto 范围校验 FILE |
| `zendev message check --text TEXT` | 按 auto 范围校验参数文本 |
| `zendev message check --title` | 只运行 title validator |
| `zendev message check --body` | 只运行 PR 模板 body validator |
| `zendev proposal check` | 校验提案文档、图、历史和已提交索引 |
| `zendev proposal check --fix` | 在提案文档合法时写回确定性索引 |

`message check` 与 `proposal check` 使用相同的 noun-then-verb 词序。`proposal
check` 校验整个提案仓库，因此保持独立分组。不使用 `review` 或 `validate` 作为统
一文案入口：前者偏 PR 审查，后者无法表达与 `ruff check` 相同的只读检查动词。不
把文案校验收成 `zendev check title|body|message`：那会把范围做成并列动作，并打
破与 `proposal check` 的对称。

统一 CLI 不再提供 `commit-msg`、`validate-title`、`validate-body`，也不再提供
`proposal index`。不在统一命令树上保留隐藏别名，也不暴露 `--full`、
`--title-only` 或 `--body-only`。

### message check

两个正交维度：

```text
Input:  FILE | --text TEXT
Scope:  auto | --title | --body
```

`FILE` 与 `--text` 互斥。`--title` 与 `--body` 互斥。两者都必须提供输入来源。

默认 auto：

```text
one line     → TITLE
multi-line   → FULL
```

单行判定去掉至多一个末尾换行后再看输入中是否还有换行。因此 `✨ feat: add foo\n`
是 title；`✨ feat: add foo\n\nExplain why.\n` 是完整 message。

显式范围：

```text
--title  整个输入必须恰好是一行，只运行 title validator
--body   整个输入视为 PR body，只运行 PR 模板 validator
```

内部模型显式包含 CLI 不暴露的 `FULL`：

```text
AUTO
TITLE
BODY
FULL
```

解析规则：

```text
AUTO + single-line → TITLE
AUTO + multi-line  → FULL
TITLE              → TITLE
BODY               → BODY
FULL               → FULL
```

`FULL` 使用现有 commit-message 语义：title 走 commit convention，body 是可选自
由文本，并剥离 Git 注释行。`FULL` 不运行 PR 模板 validator。因此：

```shell
zendev message check .git/COMMIT_EDITMSG
```

对 `commit-msg` hook 安全。`--body` 是唯一采用 PR 模板 schema 的路径：

```shell
zendev message check --title --text "✨ feat: add foo"
zendev message check --body --text "$PR_BODY"
```

换行只选择 `TITLE` 还是 `FULL`，不选择 body schema。后续若增加 `--footer` 或把
title 建模成 `header`，仍落在同一组 scope 旗标上。

### 兼容 console script

组件发行包的独立入口保持现有名称，供 GitHub Action、hook `entry` 和只安装单个
组件的仓库使用：

- `zendev-commit`
- `zendev-commit-msg`
- `zendev-validate-title`
- `zendev-validate-body`
- `zendev-proposal check`
- `zendev-proposal check --fix`

`python -m zendev` 继续暴露与 `zendev` 相同的分组命令树。

### 提案 check 与 --fix

`check` 默认只读。提案文档、图或历史不合法时不检查也不写入索引。文档合法而索
引缺失或与确定性生成结果不是逐字节相同时，报告 `proposal.index.drift`，hint 为
当前调用路径加上 `--fix`，例如：

```text
hint: Run `zendev proposal check --fix` and commit the result.
```

独立命令 `zendev-proposal check` 的 hint 使用 `zendev-proposal check --fix`。

`--fix` 只在其余校验通过后写索引。索引已是期望内容时保持文件不变并以成功退
出。`--fix` 不修复 frontmatter、章节、图或历史错误。公开 hook 与 CI 不得传入
`--fix`。

删除 `zendev proposal index`、`zendev-proposal index --check` 和
`zendev-proposal index --write`。

### 公开 hook

`.pre-commit-hooks.yaml` 发布：

- `zendev-commit-msg`：行为不变
- `zendev-proposal-check`：运行 `zendev-proposal check`，`pre-commit` stage，只读

删除 `zendev-proposal` 和 `zendev-proposal-index`。不保留旧 hook id 别名。消费仓
库把 `{ id = "zendev-proposal" }` 改成 `{ id = "zendev-proposal-check" }`，并把本
地写索引步骤从 `prek run --stage manual zendev-proposal-index` 改成
`zendev proposal check --fix`。

## 兼容性

这是破坏性变更，随下一个发行版本生效：

- 统一 CLI 用户把 `zendev commit-msg`、`zendev validate-title` 和
  `zendev validate-body` 换成 `zendev message check FILE`、
  `zendev message check --title --text TEXT` 和
  `zendev message check --body --text TEXT`
- 提案用户把 `zendev proposal index --write` 换成 `zendev proposal check --fix`
- hook 用户把 `zendev-proposal` 换成 `zendev-proposal-check`，并停止安装
  `zendev-proposal-index`

不添加废弃期、旧 hook id 或 `index` 子命令别名。独立 console script 名称不变。

## 验证

`zendev --help` 只包含 `commit`、`message`、`proposal`。`zendev message --help`
列出 `check`。`zendev message check --help` 列出 `--text`、`--title`、`--body`。
`zendev proposal --help` 不再列出 `index`。

`zendev message check` 对多行 commit message 不得要求 PR H2；`--body` 才使用 PR
模板。`--title` 拒绝多行输入。`FILE` 与 `--text` 互斥，`--title` 与 `--body` 互
斥。

`zendev proposal check --fix` 在合法仓库中写回索引；无 `--fix` 时相同漂移不得改
文件，并给出可复制的 `--fix` 命令。校验失败时 `--fix` 不得写文件。

`prek validate-manifest .pre-commit-hooks.yaml` 接受 `zendev-proposal-check` 且不
再包含已删除的 hook id。`prek try-repo` 能运行 `zendev-proposal-check` 和
`zendev-commit-msg`，且不得改动干净工作树。仓库测试覆盖统一命令树、message
scope 解析、`zendev-proposal check --fix` 和 JSON 诊断中的 hint。
