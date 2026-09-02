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

把统一 `zendev` 命令按发行包职责分成 `commit`、`review`、`proposal` 三组，删除
独立的 `proposal index` 子命令和 `zendev-proposal-index` hook。提案索引漂移由只
读的 `zendev proposal check` 报告，并用 `zendev proposal check --fix` 显式写回，
形态与 `ruff check --fix` 相同。公开 hook 标识为 `zendev-proposal-check`。

## 动机

当前 `zendev --help` 把 `commit`、`commit-msg`、`validate-title`、`validate-body`
和 `proposal` 平铺在同一层。命令名不能看出它们分别属于提交、PR 审查还是提案仓
库，截断后的帮助文本也无法补救。

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
review    Validate pull-request titles and bodies
proposal  Validate repository-native proposals
```

各组子命令为：

| 统一命令 | 行为 |
| --- | --- |
| `zendev commit` | 交互式创建提交；无子命令时执行该默认动作 |
| `zendev commit check FILE` | 校验 Git 提供的提交说明文件 |
| `zendev review title` | 校验一个 PR 标题 |
| `zendev review body` | 校验 PR 正文 |
| `zendev proposal check` | 校验提案文档、图、历史和已提交索引 |
| `zendev proposal check --fix` | 在提案文档合法时写回确定性索引 |

统一 CLI 不再提供 `commit-msg`、`validate-title`、`validate-body`，也不再提供
`proposal index`。不在统一命令树上保留隐藏别名。

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
  `zendev validate-body` 换成上表中的分组命令
- 提案用户把 `zendev proposal index --write` 换成 `zendev proposal check --fix`
- hook 用户把 `zendev-proposal` 换成 `zendev-proposal-check`，并停止安装
  `zendev-proposal-index`

不添加废弃期、旧 hook id 或 `index` 子命令别名。独立 console script 名称不变。

## 验证

`zendev --help` 只包含 `commit`、`review`、`proposal`。`zendev proposal --help`
不再列出 `index`。`zendev proposal check --fix` 在合法仓库中写回索引；无 `--fix`
时相同漂移不得改文件，并给出可复制的 `--fix` 命令。校验失败时 `--fix` 不得写
文件。

`prek validate-manifest .pre-commit-hooks.yaml` 接受 `zendev-proposal-check` 且不
再包含已删除的 hook id。`prek try-repo` 能运行 `zendev-proposal-check` 和
`zendev-commit-msg`，且不得改动干净工作树。仓库测试覆盖统一命令树、
`zendev-proposal check --fix` 和 JSON 诊断中的 hint。
