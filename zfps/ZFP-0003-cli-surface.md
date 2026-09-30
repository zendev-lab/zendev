---
zfp: 3
title: "Zendev CLI 命令面"
type: Feature
authors:
  - "zrr1999"
created: 2026-09-02
supersedes: []
---

# ZFP-0003: Zendev CLI 命令面

## 摘要

本提案是 zendev 命令行公开形态的唯一记录，覆盖统一命令树、组件入口、命名规则、
输入来源、选项互斥与适用范围、输出格式与输出流、退出码、帮助与版本，以及公开
hook。领域规则仍由各自的提案拥有：消息、配置与诊断模型见 ZFP-0006，提案修复见
ZFP-0005，项目演进见 ZFP-0007。本提案只规定这些规则如何出现在命令行上。之后
新增命令、选项、输出格式或退出码时提交新的 ZFP，并遵守这里的约定。

## 动机

0.3.0 之前，`zendev --help` 把 `commit`、`commit-msg`、`validate-title`、
`validate-body` 和 `proposal` 平铺在同一层，命令名看不出它们属于创建提交、校验
文案还是提案仓库。提案索引另有 `index --check`、`index --write` 和 manual-stage
hook，检查与写回分成两条入口。本提案最初把命令按领域分组为 noun-then-verb，并把
写回收进 `check --fix`。

此后 ZFP-0005 扩展 `--fix` 并增加 `--diff`、`--select`、`--partial`；ZFP-0006
增加 `message check --commit`、`--format` 和统一退出码；ZFP-0007 增加 `evolution`
命令组与 hook。命令面的现行状态因此分散在四份提案和使用文档中，新增命令时没有
一份完整规则可以对照，实现也出现了不一致：

- `zendev proposal check` 的 JSON `command` 是 `check`，其他检查是
  `message check`、`evolution check`。
- `--select` 未与 `--fix` 或 `--diff` 同用时被静默忽略，同类的 `--partial` 则报
  用法错误。
- `evolution` 命令按 UTF-8 输出；`message check` 与 `proposal check` 使用宿主
  编码，在非 UTF-8 的 stdout 上输出非 ASCII 字符时以 traceback 退出 `1`，与内容
  错误无法区分。
- `zendev --help` 中 `message` 的说明是 “Create and validate”，但该组只做校验；
  `evolution` 的说明在 80 列终端中被截断；多数选项在 `--help` 中没有说明。

本修订把现行命令面收拢为一份完整记录，校正上述不一致，并为统一命令增加
`--version`。

## 设计

### 范围

本提案拥有：

- 命令树、命令名和组件入口名；
- 每个命令接受的参数、选项和环境变量，以及它们的组合规则；
- 输入读取、输出格式、输出流和退出码；
- `--help` 与 `--version`；
- `.pre-commit-hooks.yaml` 发布的 hook。

规则内容不在这里重复定义。commit profile、Git 消息与 PR body 规则、配置发现与
配置格式、诊断字段由 [ZFP-0006](./ZFP-0006-domain-architecture.md) 定义，本提案
只记录它们在命令行上的形态；提案校验、修复规则和写回安全约束由
[ZFP-0005](./ZFP-0005-proposal-repairs.md) 定义；`EVOLUTION.md` 的结构由
[ZFP-0007](./ZFP-0007-project-evolution.md) 定义。Python API、配置键和
composite Actions 的 inputs 不属于命令面；Actions 只是调用
`zendev-message check --title|--body --format github` 的适配器。

### 命令树

```text
zendev [--version]
├── commit [--config PATH] [--profile PROFILE]
├── message
│   └── check (FILE | --text TEXT) [OPTIONS]
├── proposal
│   └── check [OPTIONS]
└── evolution
    ├── init --from PATH [--file PATH] [--format FORMAT]
    ├── list [--file PATH] [--format FORMAT]
    └── check [--file PATH] [--format FORMAT]
```

每个命令和命令组都接受 `--help`。`python -m zendev` 暴露同一棵命令树，程序名同为
`zendev`。`zendev --help` 按以下顺序为每个领域列出一个条目；说明措辞可以调整：

```text
commit     Compose a message interactively and run git commit.
message    Validate commit and pull-request messages.
proposal   Validate and repair repository-native proposals.
evolution  Initialize, list, and check an EVOLUTION.md record.
```

### 命名规则

- 命令组是领域名词，动作是其下的动词：`zendev <noun> <verb>`。`commit` 是唯一的
  顶层动作，它包装 `git commit`；消息校验属于 `message` 领域。
- 只读校验的动词统一为 `check`。写回、预览和规则选择是 `check` 的选项，不另设
  `fix`、`index`、`validate` 或 `review` 子命令。
- 组件入口把统一命令的第一个空格写成连字符：`zendev message check` 对应
  `zendev-message check`，`zendev commit` 对应 `zendev-commit`。
- 公开 hook id 为 `zendev-<noun>-check`，entry 为对应的统一命令。
- 选项只有 kebab-case 长形式，不提供单字母短选项。可覆盖配置的布尔选项成对提供
  肯定与否定形式；两者都省略时使用配置值。
- 会被 hook 追加文件名的命令以位置参数 `FILE` 接受输入，例如 `message check FILE`；
  其他路径输入使用具名选项，例如 `--file`、`--from`、`--template` 和 `--config`。
- 不提供 shell completion 安装选项。旧命令名不保留为脚本、隐藏别名或兼容入口。

### 组件入口

| 可执行文件 | 发行包 | 等价的统一命令 |
| --- | --- | --- |
| `zendev` | `zendev` | — |
| `zendev-commit` | `zendev-message` | `zendev commit` |
| `zendev-message` | `zendev-message` | `zendev message` |
| `zendev-proposal` | `zendev-proposal` | `zendev proposal` |
| `zendev-evolution` | `zendev-evolution` | `zendev evolution` |

`zendev-core` 和 `zendev-log` 不提供可执行文件。组件入口与对应的统一命令接受相同
参数，输出和退出码相同；差别只在帮助与用法中的程序名，以及建议执行命令的 hint
（见“诊断与 hint”）。

### 输入与环境

- 命令行中的相对路径相对当前工作目录解析；配置文件中的路径相对配置文件所在目录
  解析（ZFP-0006）。
- 文件与标准输入按 UTF-8 解码，读取或解码失败属于环境错误。
- `commit`、`message check` 和 `proposal check` 接受 `--config PATH`，指定唯一
  配置来源；省略时按 ZFP-0006 从当前目录向上发现。`evolution` 不读取配置。
- `PROPOSAL_BASE_REF` 在省略 `--base-ref` 时提供其值。这是 zendev 命令定义的唯一
  环境变量。
- `commit` 执行 `git commit`；`message check` 以 commit 范围检查 `FILE` 时读取
  Git 的 `core.commentChar`；`proposal check` 只在给出基线时读取 Git 历史。其他
  命令不调用 Git。
- `commit` 从终端交互读取回答；只有 `evolution init --from -` 读取标准输入。
  `message check` 的输入只来自 `FILE` 或 `--text`。

### 输出格式与输出流

`message check`、`proposal check` 和三个 `evolution` 命令接受
`--format human|json|github`，默认 `human`。`commit` 是交互命令，不接受
`--format`。

| 格式 | 无诊断 | 有诊断 |
| --- | --- | --- |
| `human` | 成功文本写入 stdout | 诊断写入 stderr |
| `json` | envelope 写入 stdout | envelope 写入 stdout |
| `github` | 成功文本写入 stdout | 注解写入 stdout |

所有输出按 UTF-8 编码，不随宿主 locale 或控制台编码变化。

human 诊断每条一行 `LOCATION: CODE: MESSAGE`，有 hint 时下一行缩进写
`hint: HINT`。`LOCATION` 为 `PATH` 或 `PATH:LINE`；诊断没有路径时使用 JSON 中的
`command`，例如 `message check:1`。github 格式为每条诊断输出一个 `::error`
workflow command，有路径或行号时带 `file`、`line` 属性，并转义换行与属性分隔符。
成功文本、human 措辞和注解正文不是机器契约。

JSON 为单行 UTF-8 对象，键按字母序，保留非 ASCII 字符：

```json
{"command": "message check", "diagnostics": [], "ok": true, "schema_version": 1, "summary": null}
```

- `schema_version` 为 `1`；`ok` 在没有诊断时为 `true`。
- `command` 是与入口无关的领域命令：`message check`、`proposal check`、
  `evolution init`、`evolution list` 或 `evolution check`。
- `diagnostics` 的每一项包含 `code`、`message`、`path`、`line`、`hint` 和
  布尔值 `fixable`；`path`、`line` 与 `hint` 缺失时为 `null`，`line` 从 1 开始。
- `summary` 由各命令定义；没有摘要时为 `null`。

`proposal check --diff` 在 human 与 github 格式下先把 unified diff 写入 stdout，
再输出报告；JSON 格式只在 `summary.diff` 中携带补丁。

### 诊断与 hint

诊断 `code` 是稳定的自动化契约，前缀表示所有者：`config.` 为共享配置，
`message.`、`proposal.` 和 `evolution.` 为对应领域。建议执行命令的 hint 使用实际
调用路径：`zendev proposal check` 的索引漂移提示 `zendev proposal check --fix`，
`zendev-proposal check` 提示 `zendev-proposal check --fix`。

### 退出码

`message check`、`proposal check` 和 `evolution` 命令使用同一组退出码：

| 退出码 | 含义 |
| --- | --- |
| `0` | 检查通过或写入成功，以及 `--help`、`--version` |
| `1` | 输入内容违反规则，包括提案索引漂移和 `--title` 收到多行输入 |
| `2` | 用法、配置、I/O、编码或 Git 环境错误 |

用法错误分两类。参数解析阶段发现的错误，例如未知命令或选项、缺少必需选项、非法
取值，由解析器把用法与错误写入 stderr，不受 `--format` 影响。解析之后才能判断的
组合错误，例如输入来源互斥、范围互斥、选项不适用，以诊断形式按所选格式输出。
不带子命令调用命令组时，帮助写入 stderr 并以 `2` 退出。

`commit` 在调用 Git 之前因配置或消息草稿无效而失败时退出 `2`，用户取消提示时
退出 `1`，否则返回 `git commit` 的退出码。

### 帮助与版本

`--help` 输出纯文本，不使用 rich markup。每个命令、参数和选项都有一句说明；命令
组列表中的说明在 80 列终端内不被截断。说明措辞不是机器契约。

统一命令提供全局 `--version`：向 stdout 输出一行 `zendev <version>` 并以 `0`
退出。它在解析子命令之前处理，其后的参数不再解析或执行。版本取自已安装的
`zendev` 发行包元数据；同仓组件固定为同一版本（ZFP-0006），因此不逐个列出组件
版本。

组件入口和子命令组不接受 `--version`。组件命令组同时挂载在统一命令树中，若在组
上提供该选项，就会出现 `zendev message --version` 这类含义不清的入口。单独安装
组件时，用包管理器查看其版本。

### commit

```text
zendev commit [--config PATH] [--profile zendev|conventional|gitmoji]
```

按生效 profile 交互收集提交说明：zendev profile 依次询问类型、该类型允许的
intention、scope、摘要、正文、是否 breaking 与 footer；conventional 以文本输入
类型且不询问 intention；gitmoji 不询问类型、breaking 与 footer。渲染并校验消息
后，在当前目录执行 `git commit -m MESSAGE`。它只提交已暂存内容，Git hook 照常
运行，不接受或转发其他 Git 参数。`--profile` 覆盖配置中的 profile。

### message check

```text
zendev message check (FILE | --text TEXT) [--title | --body | --commit] [OPTIONS]
```

输入来源与检查范围是两个正交维度：

```text
Input:  FILE | --text TEXT
Scope:  auto | --title | --body | --commit
```

`FILE` 与 `--text` 必须恰好提供一个；`--title`、`--body` 和 `--commit` 至多选一。
`--text ""` 是空消息，按内容错误处理。

默认 auto 范围只按行数选择：单行为 title，多行为 commit。单行判定先去掉至多一个
末尾换行（`\r\n`、`\n` 或 `\r`），再看输入中是否还有换行。因此
`✨ feat: add foo\n` 是 title，`✨ feat: add foo\n\nExplain why.\n` 是 commit。
换行从不选择 body。

| 范围 | 检查 |
| --- | --- |
| title | 输入必须恰好一行，按原文检查 profile 语法；多行报 `message.title.multiline` |
| commit | Git 提交说明语义：剥离注释与 scissors，接受 Git 生成的特殊消息，body 为自由文本 |
| body | 按 PR 模板的 H2 schema 与可选 checklist 检查整个输入 |

commit 范围对 `FILE` 使用 Git 的 `core.commentChar`，对 `--text` 固定使用 `#`。
只有 `--body` 使用 PR 模板，commit 范围永不要求 PR H2。commit-msg hook 使用显式
`--commit`，使单行的 Git 生成消息也按 commit 语义处理。

| 选项 | 适用范围 | 含义 |
| --- | --- | --- |
| `--config PATH` | 全部 | 指定唯一配置来源 |
| `--profile zendev\|conventional\|gitmoji` | title、commit | 覆盖配置的 profile |
| `--template PATH` | body | 覆盖配置的 PR 模板 |
| `--require-checklist` / `--no-require-checklist` | body | 覆盖是否要求模板中的勾选行 |
| `--checklist-section TITLE` | body | 覆盖 checklist 所在的 H2 |
| `--fail-on-empty-checklist` / `--allow-empty-checklist` | body | 覆盖模板没有勾选行时是否失败 |
| `--format human\|json\|github` | 全部 | 输出格式 |

输入来源冲突报 `message.input`，范围冲突报 `message.scope`；`--profile` 与
`--body` 同用，或 body 专用选项用于其他范围，报 `message.options`。这些错误和
模板读取失败（`message.template`）、输入读取失败（`message.input.read`）都退出
`2`。`FILE` 输入的内容诊断带文件路径，`--text` 输入的内容诊断没有路径。
`summary` 为 `null`。

### proposal check

```text
zendev proposal check [--config PATH] [--base-ref REF] [--fix] [--diff]
                      [--select RULES] [--partial] [--format FORMAT]
```

默认只读：校验配置、提案文档、关系图、可选历史和已提交索引。文档合法而索引缺失
或与确定性生成结果不逐字节相同时，报告可修复的 `proposal.index.drift`，hint 为
调用路径加上 `--fix`。

| 选项 | 含义 |
| --- | --- |
| `--config PATH` | 指定唯一配置来源 |
| `--base-ref REF` | 以精确的本地 Git ref 为基线校验历史；省略且未设置 `PROPOSAL_BASE_REF` 时不检查历史 |
| `--fix` | 候选仓库整体合法时写入源文件修复并重建索引 |
| `--diff` | 预览源文件修复与索引补丁，不写文件；与 `--fix` 同用时优先 |
| `--select RULES` | 逗号分隔的修复规则，限定 `--fix` 或 `--diff` 使用的规则 |
| `--partial` | 允许写入独立安全的修复，即使仓库仍有其他错误 |
| `--format human\|json\|github` | 输出格式 |

修复规则集合与安全约束由 ZFP-0005 定义。`--select` 与 `--partial` 必须与
`--fix` 或 `--diff` 同用，否则报 `proposal.fix.options`；未知或空的规则名报
`proposal.fix.rule`；无法解析的基线报 `proposal.history.git`。这些错误都退出
`2`。索引已是期望内容时 `--fix` 不改文件并成功退出。`--diff` 的退出码反映实际
仓库状态，而不是候选状态。

`summary` 包含 `formal_proposals`、`drafts` 和 `index`；`index` 取
`not-checked`、`drifted`、`up-to-date` 或 `updated`。使用 `--fix` 或 `--diff`
时另含 `fixed_files`、`pending_files`、`repairs`、`candidate_diagnostics` 和
`diff`。配置与环境错误的 `summary` 为 `null`；写入失败报 `proposal.fix.write`
并退出 `2`，此时 `summary` 为 `written_files`、`rolled_back_files` 和
`recovery_files`。

### evolution

```text
zendev evolution init --from PATH [--file PATH] [--format FORMAT]
zendev evolution list [--file PATH] [--format FORMAT]
zendev evolution check [--file PATH] [--format FORMAT]
```

三个命令操作 `--file` 指定的单个文档，默认是当前目录的 `EVOLUTION.md`，不向上
查找。`init` 从 `--from PATH` 读取初始意图正文，`--from -` 读取标准输入，并以
独占创建方式写入目标；目标已存在时退出 `2`。human 格式下，`list` 向 stdout 每行
输出 `PATH:LINE: TITLE`。`list` 与 `check` 不写文件。`summary` 包含 `path` 和
通过完整校验的 `sections`（每项含 `title` 与 `line`），无效文档的 `sections`
为空。文档规则与 `init` 的输入约束由 ZFP-0007 定义。

### 公开 hook

`.pre-commit-hooks.yaml` 只发布与 check 命令同形的 hook：

| id | entry | stage | 文件参数 |
| --- | --- | --- | --- |
| `zendev-message-check` | `zendev message check --commit` | `commit-msg` | Git 传入的提交说明文件 |
| `zendev-proposal-check` | `zendev proposal check` | `pre-commit` | 不传；`always_run: true` |
| `zendev-evolution-check` | `zendev evolution check` | `pre-commit` | 不传；`always_run: true` |

hook 以 `language: python` 安装所 pin 版本的完整 `zendev` 发行包，并把 hook `args`
追加到 entry 之后。`zendev-proposal-check` 在只删除提案的提交中也会运行；
`zendev-evolution-check` 是可选 hook，每次都校验目标，应在文档创建后启用。hook
默认只读，不另设 `--fix` 或 index 变体；需要写回或覆盖选项时在 `args` 中补充：

```toml
[[repos]]
repo = "https://github.com/zendev-lab/zendev"
rev = "<release>"
hooks = [
  { id = "zendev-message-check", args = ["--profile", "conventional"] },
  { id = "zendev-proposal-check", args = ["--fix"] },
  { id = "zendev-evolution-check", args = ["--file", "docs/EVOLUTION.md"] },
]
```

### 扩展规则

之后改变命令面的 ZFP 遵守以下规则，或在提案中说明偏离的理由：

- 新领域以名词命令组加入统一命令树和 `zendev --help`，并提供同名组件入口；只读
  校验命名为 `check`，写回是 `check` 的选项。
- 新的检查命令支持 `--format human|json|github`、共享 JSON envelope 与本提案的
  退出码，读取配置时接受 `--config`。
- 发布 hook 时使用 `zendev-<noun>-check`，entry 为统一命令，默认只读。
- 新增选项、`summary` 键或诊断 `code` 是兼容变化。删除或改名命令、选项、JSON 键
  或诊断 `code`，或改变退出码、默认范围、默认输出流的含义，都是破坏性变化。
- JSON envelope 的结构变化需要新的 `schema_version`。

这些规则只判断兼容性，不决定是否需要提案；是否需要提案按 ZFP-0000 判断。

## 兼容性

0.3.0 采用分组命令树时一次性移除了旧入口，不设废弃期或别名：

| 移除的入口 | 替代 |
| --- | --- |
| `zendev commit-msg`、`zendev validate-title`、`zendev validate-body` | `zendev message check` |
| `zendev-commit-msg`、`zendev-validate-title`、`zendev-validate-body` | `zendev-message check` |
| `proposal index --check`、`proposal index --write` | `proposal check`、`proposal check --fix` |
| hook `zendev-commit-msg`、`zendev-proposal` | `zendev-message-check`、`zendev-proposal-check` |
| hook `zendev-proposal-index` | `zendev-proposal-check` 加 `args = ["--fix"]` |

ZFP-0006 此后把 `--json` 换成 `--format json`，并让 commit-msg hook 显式使用
`--commit`。本次修订对现有实现有以下变化，随下一个发行版本生效：

- `zendev --version` 是新增选项，不改变已有调用。
- 破坏性变更：`proposal check` 的 JSON `command` 由 `check` 改为
  `proposal check`，与其他检查一致；没有路径的 human 诊断位置随之变化。按
  `command` 分派的 JSON 消费者需要更新。envelope 结构不变，`schema_version` 仍为
  `1`。
- 破坏性变更：未与 `--fix` 或 `--diff` 同用的 `--select` 从被静默忽略改为报
  `proposal.fix.options` 并退出 `2`。这类调用原本不产生任何效果，删除该选项即可。
- `message check` 与 `proposal check` 改为按 UTF-8 输出。UTF-8 终端上的输出不变。
- `--help` 补齐命令与选项说明，修正 `message` 与 `evolution` 的简述。帮助措辞
  不是机器契约。

其余命令、选项、默认值、输出流和退出码保持现状。回滚只需恢复实现；本修订不改变
配置、索引或文档格式。

## 验证

- `zendev --help` 与 `python -m zendev --help` 按顺序列出 `commit`、`message`、
  `proposal`、`evolution` 和 `--version`，80 列终端中说明不被截断；每个命令的
  `--help` 为所有参数和选项给出说明，且不列出任何已移除的旧命令。
- `zendev --version` 与 `python -m zendev --version` 向 stdout 输出
  `zendev <version>` 并以 `0` 退出，版本等于已安装 `zendev` 的发行包元数据；
  `zendev-message --version` 与 `zendev message --version` 是用法错误。
- 每个组件入口与对应统一命令对相同输入给出相同的 JSON 输出和退出码，只有 hint
  中的调用路径不同。
- `message check` 覆盖输入来源与范围的全部互斥组合、body 专用选项与 `--profile`
  的适用范围、auto 范围的单行判定、`--title` 拒绝多行输入，以及多行 commit 消息
  不要求 PR H2。
- `proposal check` 在干净仓库中只读；索引漂移时退出 `1` 且给出按调用路径生成的
  `--fix` hint；`--fix` 写回后再次检查无变化；`--diff` 不写文件且退出码反映实际
  状态；未与 `--fix` 或 `--diff` 同用的 `--select` 或 `--partial` 退出 `2`。
- 各检查的 JSON 输出含本提案列出的 envelope 字段，`command` 取值与本提案一致；
  human 格式的诊断写入 stderr，json 与 github 格式写入 stdout；stdout 与 stderr
  的编码不是 UTF-8 时，非 ASCII 的诊断仍按 UTF-8 输出，退出码不变。
- `prek validate-manifest .pre-commit-hooks.yaml` 只接受三个 hook id；
  `prek try-repo` 运行三个 hook 不改动干净工作树，给 `zendev-proposal-check`
  传入 `args = ["--fix"]` 时写回合法仓库中的索引漂移。
