---
zfp: 8
title: "确定性消息转换与自动化接入"
type: Feature
authors:
  - "zrr1999"
created: 2026-10-25
supersedes: []
---

# ZFP-0008: 确定性消息转换与自动化接入

## 摘要

为缺少 emoji 且意图明确的消息提供确定性转换。校验默认只给建议，显式 `--fix`
可以写回 Git 提交消息；prek 和 PR 标题 Action 复用消息领域的同一规则。

## 动机

[ZFP-0006](./ZFP-0006-domain-architecture.md) 将类型与具体意图区分开，生成时要求
明确选择 emoji。当前检查器因此拒绝 `feat: add export`，也不能转换 ImgBot 的
`[ImgBot] Optimize images`。用户需要在提交和 PR 工作流中自动处理这些明确情况，
同时保留 `deps: change dependencies` 等不确定消息的人工选择。

这是新增修复接口和自动化写入契约，需要独立提案。继续只校验会保留重复手工操作；
用语言模型猜测任意正文会使离线结果不稳定，并扩大意图误判范围。

## 设计

### 消息领域

公开纯函数 `normalize_message` 返回候选文本、是否改变以及诊断，不读写文件、发现
配置或执行 Git。已有合法消息原样返回，包括用户选择的其他合法 emoji、shortcode
和 variation selector 写法。错误配对、未知类型、已有错误 emoji 和任意自然语言
不通过猜测修复。非 zendev profile 保留自己的语法，不自动改写。

缺少 emoji 的合法 Conventional Commit 按类型补入通用意图：

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

`deps` 没有默认方向。只对描述开头明确声明的 upgrade、downgrade、pin、add、remove
等依赖操作补入对应 emoji；单纯 change 或互相冲突的操作需要人工选择。保留原有
type、scope、breaking 标记、正文和 footer。转换结果必须重新通过现有策略校验，
不改变交互式生成必须明确选择意图的契约。

首版只为完整匹配的 `[ImgBot] Optimize images` 提供非 Conventional 消息规则，
转换为 `⚡️ perf(assets): optimize images`。不据此猜测其他 bot 或类似自然语言。

### CLI 与 prek

`message check` 默认只读。存在合法候选时，在原有诊断中增加候选提示并标记
`fixable`。`--fix` 适用于 title 或 commit，不适用于 PR body。文件输入只替换
有效消息的首行，保留注释、scissors、正文、footer 和换行形式；特殊 Git 消息
继续豁免。文本输入只返回候选，不写文件。不可确定或候选校验失败时保持原文并
返回内容错误；配置、读取或写入错误返回环境错误。

`--fix --format json` 沿用共享 v1 envelope，`summary` 包含 `changed` 和 `text`。
不带 `--fix` 的成功输出及 envelope 保持现有行为。重复修复不再改变文本。

现有 `zendev-message-check` hook 保持只读并显示建议；新增
`zendev-message-fix` 在 `commit-msg` 阶段运行相同命令及 `--fix`。消费仓库自行选择
其中一个，也可以给已有 hook 添加 `args: [--fix]`。

### PR 标题 Action

新增 `actions/normalize-title`，接受 token 和 profile，默认 profile 为 zendev，
不读取 PR 分支中的配置。支持 `pull_request` 及失败的 `workflow_run` 事件。
后者按来源仓库、分支及 head SHA 找到唯一、仍开放的 PR；缺少唯一匹配则跳过。

Action 读取实时标题，只有纯函数返回合法且改变的候选才 PATCH 标题。写入前再次
检查 PR 仍开放、head 与原始标题未变。合法、不可推断或已经过期的事件均不写入。
不可推断时输出提示；API 故障失败。输出 `changed` 和最终候选 `title`。

参考 [Rill workflow](https://github.com/zrr1999/rill/blob/9e786a6ecc99fbe2ed4d3c07aa2d22aabc1afda4/.github/workflows/automation-pr-title.yml)，
在失败的 policy run 完成后修复标题，并只在实际改名后重跑该 run。调用方提供
`pull-requests: write` 和重跑所需的 `actions: write`；特权工作流仅执行固定版本或
可信默认分支的 Action，不执行 PR head 代码或下载 run artifacts。

[GitHub 的 edited 事件不会因 GITHUB_TOKEN 修改而启动工作流](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)。
为避免重跑仍读取旧事件标题，`actions/validate-title` 新增可选的
`pull-request-number` 与 token 输入，实时读取指定 PR；与原有 `text` 二选一。
现有 text 调用仍检查传入原文。仓库 policy 改用实时读取模式。

## 兼容性

默认检查不写入，已有合法消息和三个 profile 的校验规则保持不变。自动转换是对
显式修复路径的补充，不恢复旧类型别名，也不把 deps 等同于升级。消费仓库需固定
包含实现的版本后再启用修复 hook 或 Action；移除修复选项即可恢复只读流程。

## 验证

观察类型补全、明确依赖操作、ImgBot 完整匹配、模糊及冲突输入、幂等性和其他
profile。通过真实 Git/prek 提交验证修复后提交消息及正文，证明只读 hook 不改写。
用隔离的 GitHub API 替身验证唯一匹配、实时标题、关闭或过期 PR、二次检查、权限
故障、实际改名才重跑，以及特殊字符始终作为数据处理。远端端到端行为在工作流
进入默认分支后验证；本地替身不代表 GitHub 已执行自动化。
