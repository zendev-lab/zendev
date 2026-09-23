---
zfp: 7
title: "依赖升级类型别名"
type: Feature
authors:
  - "zrr1999"
created: 2026-09-23
supersedes: []
---

# ZFP-0007: 依赖升级类型别名

## 摘要

`zendev` profile 接受 `⬆️ deps` 作为 `⬆️ deps-up` 的兼容写法。别名只对应依赖
升级这一 Gitmoji 意图；规范类型和交互式提交选项继续使用 `deps-up`。

## 动机

Cue 等仓库的 Renovate 配置已生成 `⬆️ deps: Update dependencies (non-major)`。
当前校验器只接受 `⬆️ deps-up`，消费仓库因而需要覆盖机器人前缀，或错误地跳过
标题检查。接受这一个常见写法可以保留标题门禁，并避免各仓库单独改写同一前缀。

已有 ZFP 规定了组件责任和 message check 入口，尚未定义这个额外接受的标题形式。
本提案记录兼容别名的范围，而不是为机器人设置身份豁免。

## 设计

- 在 `zendev` profile 中，`deps` 与 `deps-up` 对应相同的依赖升级意图。
  接受 `⬆️ deps`、`⬆ deps` 和 `:arrow_up: deps`，沿用现有 scope、`!`、正文与
  footer 语法。
- 标题检查、完整 commit message 检查及 commit hook 使用相同规则。公开 schema
  pattern 同样接受别名；省略 emoji 的宽松 pattern 也识别 `deps`。
- `deps` 不能搭配下降、添加、删除或固定依赖的 emoji。`⬇️ deps`、`➕ deps`、
  `➖ deps` 和 `📌 deps` 仍然无效；其他 emoji/type 配对规则保持原样。
- 规范类型表、公开 `EMOJI_MAP` 和交互选择器继续保留每个 Gitmoji 的唯一规范类型。
  已有 `deps-up` 输入继续通过。直接向消息生成 API 提供 `deps` 时，使用升级
  emoji 并保留调用者的类型拼写；缺少 emoji 时的建议遵循相同规则。
- 帮助和提交指南说明这个别名。`conventional` 与 `gitmoji` profile 的契约不变，
  不增加用户配置、机器人特例或通用的依赖类型豁免。

## 兼容性

这是接受输入范围的扩展，既有合法消息仍合法，校验不会改写消息。依赖升级以外的
类型仍需对应其原有 emoji。旧版校验器会继续拒绝 `deps`；消费仓库需要升级到
包含本实现的版本，再移除临时的 `deps-up` 前缀覆盖。

## 验证

验证 Unicode、无变体选择符和 shortcode 形式，以及含 scope、breaking marker、
正文和 footer 的完整消息。校验器、schema pattern、消息生成、缺少 emoji 时的
建议、CLI 标题检查和 commit hook 应一致接受升级别名。负例验证错误 emoji 配对
和缺失 emoji 仍被拒绝；已有规范配对测试继续通过。
