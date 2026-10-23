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

把统一 `zendev` 命令分成 `commit`、`message`、`proposal` 三组。文案校验入口是 `zendev message check`：输入来源是 `FILE` 或 `--text`，检查范围是默认 auto、 `--title` 或 `--body`。完整 message 的 body 使用 commit 自由文本语义；PR 模板 schema 只在 `--body` 下运行。删除独立的 `proposal index` 子命令和旧 hook id。提案索引漂移由只读的 `zendev proposal check` 报告，并用 `zendev proposal check --fix` 显式写回，形态与 `ruff check --fix` 相同。公开 hook 为 `zendev-message-check` 和 `zendev-proposal-check`；需要写回时在 hook `args` 中补 `--fix`。

## 动机

当前 `zendev --help` 把 `commit`、`commit-msg`、`validate-title`、`validate-body` 和 `proposal` 平铺在同一层。命令名不能看出它们分别属于创建提交、校验文案还是提案仓库，截断后的帮助文本也无法补救。

提交说明、PR 标题和 PR 正文都是在校验一段文案，而且标题与提交说明共用 commit profile。它们不应再拆成 `commit-msg` 和一对 `validate-*` 命令，也不应把 `title` / `body` 做成三个不同动作。`title` 和 `body` 是同一次 check 的范围。

换行可以决定检查 title 还是完整 message，但不能顺便决定 body 使用哪套 schema。 Git commit body 是自由文本；当前 PR body 检查的是模板 H2 schema。若 `zendev message check FILE` 看到换行就同时运行 PR body validator，commit-msg hook 会把合法提交说明判失败。

提案索引另有 `index --check`、`index --write` 和 manual-stage hook `zendev-proposal-index`。消费仓库因此要记第三条入口。检查与修复本应是同一条 `check` 路径上的只读默认值与显式 `--fix`，不需要第二个 hook 或第二个子命令。公开 hook 也应与命令同形：`zendev-<noun>-check` 运行 `zendev <noun> check`，额外旗标用 hook `args` 传入。

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

| 统一命令 | 组件命令 | 行为 |
| --- | --- | --- |
| `zendev commit` | `zendev-commit` | 交互式创建提交 |
| `zendev message check [FILE]` | `zendev-message check [FILE]` | 按 auto 范围校验 FILE |
| `zendev message check --text TEXT` | `zendev-message check --text TEXT` | 按 auto 范围校验参数文本 |
| `zendev message check --title` | `zendev-message check --title` | 只运行 title validator |
| `zendev message check --body` | `zendev-message check --body` | 只运行 PR 模板 body validator |
| `zendev proposal check` | `zendev-proposal check` | 校验提案文档、图、历史和已提交索引 |
| `zendev proposal check --fix` | `zendev-proposal check --fix` | 在提案文档合法时写回确定性索引 |

`message check` 与 `proposal check` 使用相同的 noun-then-verb 词序。组件命令与统一命令同名，只是把第一个空格写成连字符。`python -m zendev` 暴露与 `zendev` 相同的分组命令树。

统一命令提供全局 `--version`：输出一行 `zendev <version>` 并以 0 退出，不执行子命令。版本取自已安装的 `zendev` 发行包元数据；同仓组件固定为同一版本，因此不逐个列出组件版本。组件命令不增加该选项。

不使用 `review` 或 `validate` 作为统一文案入口。不把文案校验收成 `zendev check title|body|message`。统一 CLI 不再提供 `commit-msg`、 `validate-title`、`validate-body` 或 `proposal index`。不保留这些旧命令名作为脚本、隐藏别名或兼容入口。

### message check

输入来源（`FILE` 或 `--text TEXT`）与检查范围（默认 `auto`、`--title` 或 `--body`）正交且各自互斥，调用时必须提供输入来源。内部范围模型为 `AUTO`、 `TITLE`、`BODY`、`FULL`（`FULL` 不直接暴露为 CLI 旗标）：

| 请求范围 | 输入形态 | 解析结果 | 校验语义 |
| --- | --- | --- | --- |
| 默认 `auto` | 单行（忽略至多一个末尾换行） | `TITLE` | 只运行 commit profile 的 title validator |
| 默认 `auto` | 多行 | `FULL` | title 走 commit profile，body 视为可选自由文本并剥离 Git 注释行 |
| `--title` | 必须为单行 | `TITLE` | 只运行 title validator |
| `--body` | 任意文本 | `BODY` | 只运行 PR 模板 H2 与可选 checklist validator |

换行只选择 `TITLE` 还是 `FULL`，不选择 body schema。因此 `zendev message check .git/COMMIT_EDITMSG` 对 `commit-msg` hook 安全；`--body` 是唯一采用 PR 模板 schema 的路径。

### 提案 check 与 --fix

`check` 默认只读。提案文档、图或历史不合法时不检查也不写入索引。文档合法而索引缺失或与确定性生成结果不是逐字节相同时，报告 `proposal.index.drift`，hint 为当前调用路径加上 `--fix`（例如 `zendev proposal check --fix` 或 `zendev-proposal check --fix`）。

`--fix` 只在其余校验通过后写索引。索引已是期望内容时保持文件不变并以成功退出。`--fix` 不修复 frontmatter、章节、图或历史错误。

### 公开 hook

`.pre-commit-hooks.yaml` 只发布与 check 命令同形的 hook，不保留旧 hook id 或 `--fix` / `index` 变体：

| id | entry | 默认 stage | 默认行为 |
| --- | --- | --- | --- |
| `zendev-message-check` | `zendev message check` | `commit-msg` | 按 `auto` 范围校验 Git 传入的 `COMMIT_EDITMSG` |
| `zendev-proposal-check` | `zendev proposal check` | `pre-commit` | 只读校验提案、图、历史和已提交索引（`pass_filenames: false`、`always_run: true`） |

消费仓库若要写回索引或覆盖其它 CLI 旗标，在 hook 配置里补 `args`：

```toml
[[repos]]
repo = "https://github.com/zendev-lab/zendev"
rev = "v0.3.0"
hooks = [
  { id = "zendev-message-check", args = ["--profile", "conventional"] },
  { id = "zendev-proposal-check", args = ["--fix"] },
]
```

## 兼容性

这是破坏性变更，随下一个发行版本生效：

- 统一 CLI 用户把 `zendev commit-msg`、`zendev validate-title` 和
  `zendev validate-body` 换成 `zendev message check`
- 组件用户把 `zendev-commit-msg`、`zendev-validate-title` 和
  `zendev-validate-body` 换成 `zendev-message check`
- 提案用户把 `zendev proposal index --write` 换成 `zendev proposal check --fix`
- hook 用户把 `zendev-commit-msg` 换成 `zendev-message-check`，把
  `zendev-proposal` 换成 `zendev-proposal-check`，并停止安装
  `zendev-proposal-index`；需要写索引时给 `zendev-proposal-check` 补
  `args = ["--fix"]`

不添加废弃期或旧名称别名。`--version` 是纯增量选项，不改变已有调用。

## 验证

`zendev --help` 只包含 `commit`、`message`、`proposal`。`zendev message --help` 列出 `check`。`zendev message check --help` 列出 `--text`、`--title`、`--body`。 `zendev proposal --help` 不再列出 `index`。组件入口为 `zendev-commit`、 `zendev-message` 和 `zendev-proposal`。

`zendev --version` 与 `python -m zendev --version` 输出 `zendev <version>` 并以 0 退出，版本与已安装的 `zendev` 发行包元数据一致；`zendev --help` 列出 `--version`。

`zendev message check` 对多行 commit message 不得要求 PR H2；`--body` 才使用 PR 模板。`--title` 拒绝多行输入。`FILE` 与 `--text` 互斥，`--title` 与 `--body` 互斥。

`zendev proposal check --fix` 在合法仓库中写回索引；无 `--fix` 时相同漂移不得改文件，并给出可复制的 `--fix` 命令。校验失败时 `--fix` 不得写文件。

`prek validate-manifest .pre-commit-hooks.yaml` 只接受 `zendev-message-check` 和 `zendev-proposal-check`。`prek try-repo` 能运行这两个 hook，默认不得改动干净工作树。给 `zendev-proposal-check` 传入 `args = ["--fix"]` 时，合法仓库中的索引漂移会被写回。仓库测试覆盖统一命令树、组件入口、message scope 解析、公开 hook id 和 JSON 诊断中的 hint。
