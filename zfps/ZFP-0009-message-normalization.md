---
zfp: 9
title: "Conventional 消息转换与可配置特例"
type: Feature
authors:
  - "zrr1999"
created: 2026-10-25
supersedes: []
---

# ZFP-0009: Conventional 消息转换与可配置特例

## 摘要

默认仅为缺少 emoji 的合法 Conventional Commit 提供确定性转换。非 Conventional
消息只能由仓库在 TOML 中显式声明精确匹配特例。校验默认只给建议，显式 `--fix`
可以写回 Git 提交消息；prek 和 PR 标题 Action 复用同一配置与转换规则。

## 动机

[ZFP-0006](./ZFP-0006-domain-architecture.md) 将类型与具体意图区分开，生成时要求
明确选择 emoji。`feat: add export` 已声明分类，可以补入该分类的通用 emoji；
`[ImgBot] Optimize images` 没有声明类型或 scope，不能从标题推断 `perf(assets)`。
后者只能由消费仓库根据自己的约定配置特例。本次修订依用户明确要求收紧默认范围，
不再内置任何 bot 名称或自由文本规则。

这是新增修复接口、配置及自动化写入契约，需要独立提案。保留纯校验会留下重复手工
操作；使用语言模型或内置 bot 名称猜测任意正文，则会扩大意图误判范围。

## 设计

### 处理顺序与匹配范围

公开纯函数 `normalize_message` 返回候选文本、是否改变以及诊断，不读写文件、发现
配置或执行 Git。它接受适配层传入的 `replacements` 映射，默认为空。交互式生成仍
要求明确选择意图；已有校验规则不变。

转换严格按以下顺序进行，不循环应用规则：

1. 非 zendev profile 不应用转换或特例，保留各自的语法。所选 profile 下已经合法
   的消息也原样返回，包括作者选择的 emoji、shortcode 和 variation selector。
2. 对尚未合法的 zendev 消息，先按有效首行查找显式 `replacements` 特例。命中后
   使用完整替换首行，保留其他文本，并校验完整候选。候选不合法时保持原文并报错，
   不退回默认规则，也不匹配替换后的内容。
3. 未命中特例时，仅尝试完整 Conventional Commit 解析。解析失败、类型未知或
   依赖操作不明确时保持原文并报错。已有错误 emoji 不通过默认规则修复。
4. 解析成功且类型具有默认 emoji 时，只在原首行前添加 emoji 和一个空格，再次
   校验完整候选。type、scope、`!`、描述、正文与 footer 均保留。

title 使用单行原文。commit 使用既有 Git 清理规则定位有效首行后匹配；注释、
scissors 和特殊 Git 消息豁免仍仅适用于 commit，豁免消息保持原样。修复只替换
原文件的有效首行，其余文本及换行形式保持不变。

### Conventional 默认规则

缺少 emoji 的合法 Conventional Commit 按类型补入以下通用意图：

| 类型 | 默认 emoji |
| --- | --- |
| feat | ✨ |
| fix | 🐛 |
| docs | 📝 |
| style | 🎨 |
| refactor | ♻️ |
| perf | ⚡️ |
| test | ✅ |
| build | 📦 |
| ci | 👷 |
| chore | 🔧 |
| revert | ⏪️ |

类型名按现有语法和小写策略精确匹配，不替换旧类型别名、不改变大小写，也不从
scope 或自然语言推断分类。breaking 由原有 `!` 或 footer 声明，不据此改用 💥。
例如 `feat(api)!: add export` 补 ✨ 并保留 `!`。emoji 使用随包目录中的规范写法。

`deps` 没有默认方向。仅在合法 Conventional `deps` 消息中，将描述转为小写并按
空白切分，首个词必须完整匹配下表单词，且至少有一个后续词：

| 描述首词 | emoji |
| --- | --- |
| upgrade、update、bump | ⬆️ |
| downgrade | ⬇️ |
| pin | 📌 |
| add | ➕ |
| remove | ➖ |

`update` 或 `bump` 的描述中包含独立的 `from` 词时不转换，避免把未比较的版本变化
当作升级。描述中在 `and`、`or`、`then`、`,`、`&`、`/` 或 `;` 后紧接另一个操作词，
且对应 emoji 与首操作不同时，也不转换。相同方向的操作不冲突。连接词按普通词
边界匹配，允许连接符与操作词间有空白；不进行同义词、中文、否定或版本顺序推断。
`do not upgrade`、`change dependencies`、`update foo from v2 to v1` 和
`upgrade foo, remove bar` 均保持错误。

### TOML 中的精确特例

统一配置增加可选的 `[message.normalization.replacements]` 字符串映射，默认为空。
`pyproject.toml` 使用同等的 `[tool.zendev.message.normalization.replacements]`：

```toml
version = 1

[message.normalization.replacements]
"[ImgBot] Optimize images" = "⚡️ perf(assets): optimize images"
```

此例是消费仓库明确声明的策略，不是 Zendev 的内置知识。删除该条目后同一标题
不会转换。键是完整的原始有效首行，区分大小写和空白，不支持子串、glob、正则、
模板变量或模糊匹配。值是完整、单行的合法 zendev 标题，须显式包含 emoji、type
及可选 scope，不是待进一步推断的 Conventional 文本。替换只发生一次。

键和值须为非空字符串，不能含任何换行；值在加载配置时即按 zendev 策略校验。
空白键、非法配对、未知配置项、非表结构、错误值类型或重复 TOML 键均为配置错误，
即使当前消息不匹配也不能静默忽略。其他 profile 不应用特例，但配置仍须有效。
配置来源、冲突检测、版本与 CLI 覆盖规则沿用既有契约，不合并不同来源的规则。

未配置的 `[ImgBot] Optimize images`、大小写不同的 `[ImgBot] optimize images`
和额外追加文字的标题均不转换。只有仓库声明上述完整映射时，才会发生对应替换。
特例优先于默认补全，但不会覆盖已经合法的消息；错误的特例不会被默认规则掩盖。

### CLI 与 prek

`message check` 默认只读，复用既有配置发现或显式 `--config`。存在合法候选时，
在原有诊断中增加候选提示并标记 `fixable`。`--fix` 适用于 title 或 commit，不适用
于 PR body。文件输入只替换有效首行；文本输入只返回候选，不写文件。不可确定或
候选校验失败时保持原文并返回内容错误；配置、读取或写入错误返回环境错误。

`--fix --format json` 沿用共享 v1 envelope，`summary` 包含 `changed` 和 `text`。
不带 `--fix` 的成功输出及 envelope 保持既有行为。重复修复不再改变文本。

现有 `zendev-message-check` hook 保持只读并显示建议；新增 `zendev-message-fix`
在 `commit-msg` 阶段运行相同命令及 `--fix`。消费仓库自行选择其中一个，也可以给
已有 hook 添加 `args: [--fix]`。两种 hook 使用同一份 TOML 特例配置。

### PR 标题 Action

新增 `actions/normalize-title`，接受 token、可选 profile 和可选 `config` 路径。
不指定 profile 时使用配置，未配置则为 zendev；显式 profile 覆盖有效配置。
支持 `pull_request` 及失败的 `workflow_run` 事件。后者按来源仓库、分支及 head SHA
找到唯一且仍开放的 PR；缺少唯一匹配则跳过。

确认目标 PR 后，将目标仓库默认分支解析为一次不可变提交 SHA，使用 GitHub API
仅将该提交中的 TOML 作为数据读取。默认发现根目录的 `zendev.toml` 或
`pyproject.toml` 中的 `[tool.zendev]`，重复定义仍报冲突；均无配置时使用默认值。
显式 `config` 是仓库内相对 TOML 路径，只选择该文件，不考虑其他来源，缺失时报错。
拒绝绝对路径、路径穿越以及提案专用入口。配置格式及替换规则复用本地加载器。
配置或 API 故障均失败，不回退到忽略特例或未知配置的行为。

Action 不读取 fork/PR head 的配置，不 checkout 仓库，不下载或执行消费仓库脚本。
调用方提供 `contents: read` 以读取默认分支的 ref 和配置。配置进入默认分支后，
本地 hook 和 Action 才采用相同的仓库规则；PR 中尚未合入的配置不参与特权自动化。

Action 读取实时标题，只有纯函数返回合法且改变的候选才 PATCH 标题。写入前再次
检查 PR 仍开放、head 与原始标题未变。合法、不可推断或过期事件均不写入。
不可推断时输出提示；API 或配置故障失败。输出 `changed` 和最终候选 `title`。

参考 [Rill workflow](https://github.com/zrr1999/rill/blob/9e786a6ecc99fbe2ed4d3c07aa2d22aabc1afda4/.github/workflows/automation-pr-title.yml)，
在失败的 policy run 完成后修复标题，只在实际改名后重跑该 run。调用方提供
`pull-requests: write` 和重跑所需的 `actions: write`；特权工作流仅执行固定版本
的 Action，不执行 PR head 代码或下载 run artifacts。

[GitHub 的 edited 事件不会因 GITHUB_TOKEN 修改而启动工作流](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)。
为避免重跑仍读取旧事件标题，`actions/validate-title` 新增可选的
`pull-request-number` 与 token 输入，实时读取指定 PR；与原有 `text` 二选一。
既有 text 调用仍检查传入原文。仓库 policy 改用实时读取模式。

## 兼容性

默认检查不写入，已有合法消息和三个 profile 的校验规则保持不变。自动转换是对
显式修复路径的补充，不恢复旧类型别名，也不把 deps 等同于升级。特例表默认为空，
因此不会自动转换任意自由文本。消费仓库需固定包含实现的版本后再启用修复 hook
或 Action；移除修复选项即可恢复只读流程。

## 验证

观察 Conventional 类型补全、依赖操作的全部边界、未配置自由文本不转换、显式特例
的精确匹配及优先级、无递归、非法配置、幂等性和其他 profile。通过真实 Git/prek
提交验证 TOML 特例和正文保留，证明只读 hook 不改写。
用隔离的 GitHub API 替身验证唯一匹配、实时标题、关闭或过期 PR、二次检查、权限
故障、默认分支固定 SHA 配置来源、与本地加载一致、PR 配置不生效、实际改名才重跑，
以及特殊字符始终作为数据处理。远端端到端行为在工作流进入默认分支后验证；本地
替身不代表 GitHub 已执行自动化。
