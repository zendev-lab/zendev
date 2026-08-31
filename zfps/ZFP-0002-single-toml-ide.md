---
zfp: 2
title: "统一提案配置与 IDE 集成契约"
type: Feature
authors:
  - "zrr1999"
created: 2026-08-31
supersedes: []
---

# ZFP-0002: 统一提案配置与 IDE 集成契约

## 摘要

让 `proposal.toml` 成为提案仓库的单一配置入口。常见的无状态 Feature Proposal
仓库通过版本化的 `feature-proposal/v1` metadata profile 描述 frontmatter，不再在
每个仓库复制 `schemas/fp.schema.json`。需要特殊约束的仓库仍可引用本地 JSON
Schema；两种模式最终归一化为同一个只读校验模型。

同时定义供 IDE 集成使用的稳定、与编辑器无关的查询和单文档校验契约。IDE 插件只
负责工作区发现、进程管理和界面呈现，配置解释、profile 展开、Markdown/frontmatter
解析及诊断语义继续由 `zendev-proposal` 单独拥有。

## 动机

当前 `proposal.toml` 已经描述编号、目录、模板、关系、历史和索引，但
`proposal.schema` 仍要求仓库额外提交一份 JSON Schema。使用相同轻量 FP 模型的
仓库会反复复制编号、标题、类型、作者、日期和 `supersedes` 约束，仅替换前缀、字段
名和 `$id`。重复文件不易阅读，也会让配置、schema、模板、关系和索引分别演化。

这种分裂对 IDE 集成更加不利。插件若直接读取 JSON Schema 和 TOML，就必须重新实现
zendev 的默认值、路径安全、profile 语义、模板类型、关系规则和错误处理；插件若只在
保存后运行全仓 `check`，则无法校验未保存的缓冲区，也无法可靠提供配置与 frontmatter
补全。不同编辑器最终会形成多个不一致的校验器。

单纯把 JSON Schema 的每个关键字翻译成 TOML 不能解决所有权问题，只是新造一套不完整
的 schema 语言。远程 schema URL 又会引入网络、缓存、供应链和不可复现行为。zendev
需要的是一个小而版本化的公共 profile，以及跨进程使用同一校验实现的 IDE 契约。

## 设计

### 单一配置与 metadata source

`proposal.toml` 增加配置格式版本 2，并以 `[metadata]` 选择 frontmatter 约束来源：

```toml
version = 2

[proposal]
prefix = "FP"
number_field = "fp"
documents_dir = "fps"
index = "fps-index.json"
metadata_title = "plain"

[metadata]
profile = "feature-proposal/v1"

[templates]
Feature = "templates/fp.md"
Governance = "templates/fp.md"

[graph]
fields = ["supersedes"]

[index]
version = 1
entries_key = "fps"
include_drafts = false

[[index.fields]]
name = "fp"
source = "metadata"
key = "fp"

[[index.fields]]
name = "id"
source = "identifier"

[[index.fields]]
name = "path"
source = "path"

[[index.fields]]
name = "title"
source = "metadata"
key = "title"

[[index.fields]]
name = "type"
source = "metadata"
key = "type"

[[index.fields]]
name = "authors"
source = "metadata"
key = "authors"

[[index.fields]]
name = "created"
source = "metadata"
key = "created"

[[index.fields]]
name = "supersedes"
source = "metadata"
key = "supersedes"

[[index.fields]]
name = "superseded_by"
source = "inverse"
key = "supersedes"
```

`[metadata]` 必须且只能设置以下一种 source：

- `profile = "feature-proposal/v1"`：使用 zendev 内置、不可变且带版本的公共 profile；
- `schema = "schemas/custom.schema.json"`：继续使用仓库内的 JSON Schema。

不读取远程 schema，不按 package 版本静默切换 profile。未来改变现有 profile 的约束时
必须发布新的 profile 标识，例如 `feature-proposal/v2`，并由仓库显式迁移。配置格式
版本和 profile 版本相互独立：前者描述 TOML 语法，后者描述 metadata 契约。

配置版本 1 及其现有 `proposal.schema` 行为继续受支持。版本 2 不隐式读取
`proposal.schema`，避免同一仓库出现两个 schema owner。未知配置键、未知 profile、同时
设置 `profile` 与 `schema`，以及缺失的本地 schema 都以配置错误失败。

### `feature-proposal/v1`

该 profile 只覆盖已经在 ZFP 和通用 FP 仓库中出现的无状态提案模型，不成为任意设计
记录流程的通用 schema 语言。它根据已解析配置生成内存中的 JSON Schema，并继续复用
现有 JSON Schema validator：

- `proposal.number_field` 必填，为从 0 到 `10 ^ number_width - 1` 的整数；
- `proposal.title_field` 必填，为非空字符串，并遵守 `metadata_title`；
- `proposal.type_field` 必填，取值为 `[templates]` 的键；
- `authors` 必填，为至少包含一个非空字符串且元素唯一的数组；
- `created` 必填，为 `YYYY-MM-DD` 字符串；
- 每个 `[graph].fields` 字段必填，为元素唯一的 canonical proposal ID 数组；
- 不接受未声明的 frontmatter 字段。

编号宽度、标题前缀和 proposal ID pattern 从 `prefix`、`number_width` 与字段配置派生，
不在 profile 中固化 `FP`、`ZFP` 或某个仓库名。该 profile 要求 `[templates]` 非空，
且不允许配置 `[drafts]`；需要 formal/draft 两套 metadata 形状的仓库在首个版本中继续
使用本地 JSON Schema。模板、术语、正文语言、生命周期、历史迁移和 waiver 仍归消费
仓库所有。

如果后续真实仓库需要 profile 无法表达的 `oneOf`、条件约束或额外字段，优先使用本地
JSON Schema。只有至少两个仓库出现同一种稳定模型时，才另行提案新的 profile；本提案
不增加逐字段 TOML schema DSL，也不支持 profile overlay。

### 归一化模型

配置加载后，profile 和本地 schema 都转换为同一个不可变的 normalized policy。该模型
包含仓库根目录、文档选择范围、字段角色、模板、关系、历史、索引及编译后的
frontmatter JSON Schema。仓库校验、索引和 IDE 查询都消费此模型，不分别解释 TOML。

profile 编译结果只存在于内存中，不在仓库生成派生 schema 文件。使用 profile 时，schema
配置和编译诊断指向 `proposal.toml` 及对应 TOML key；使用本地 schema 时继续指向 schema
文件。frontmatter 校验沿用稳定的 `proposal.frontmatter.schema` 诊断代码。

### IDE 公共边界

`zendev-proposal` 提供编辑器无关的只读工具协议，IDE 插件不得链接或重写内部 Python
实现。协议首先通过普通 CLI 进程提供，保持 VS Code、JetBrains、Zed、Neovim 和其他
客户端都可使用：

```console
$ zendev proposal describe --config proposal.toml --json
$ zendev proposal check-document --config proposal.toml --path fps/example.md --stdin --json
```

`describe` 返回带独立 `schema_version` 的 workspace description，包括：

- 配置格式版本、profile 标识和 zendev 版本；
- 仓库根目录及相对的正式文档、draft、模板和索引位置；
- 编译后的 frontmatter JSON Schema；
- prefix、编号宽度、字段角色、允许的 proposal type 和 graph 字段；
- 可用于关联 Markdown 文件的确定性 selector。

所有路径在协议中使用相对仓库根目录、以 `/` 分隔的形式。输出不包含网络地址、绝对
缓存路径或 Python 类型名称。协议 schema 版本与 `proposal.toml` 版本分开演进；新增可选
字段不改变既有字段含义，删除或重解释字段必须提升协议 schema 版本。

`check-document` 从标准输入读取未保存的完整 Markdown 文本，以 `--path` 选择正式文档
或 draft 规则。校验时读取其余仓库状态，但以标准输入覆盖该 path 的磁盘内容，使未保存
的关系引用也能参与图校验。它不得写文件、索引或 Git 状态。输出复用仓库
`check --json` 的诊断代码，并为 IDE 增加 1-based 的 `line`、`column`、`end_line`、
`end_column`；无法确定范围时允许只有 path 和 message。相同磁盘内容经单文档与全仓
校验得到的同类诊断必须一致。

zendev 同时发布配置版本 2 的静态 JSON Schema，供 IDE 在 `proposal.toml` 尚未有效时
完成键名补全和基础类型检查。`describe` 提供动态的 frontmatter schema；插件不复制
profile 表。静态配置 schema 是 zendev package 内的只读资源，不要求消费仓库提交副本。

### IDE 插件职责

IDE 插件负责：

- 从当前文件向上寻找最近的 `proposal.toml`，并隔离多根 workspace；
- 选择和启动用户或 workspace 配置的 zendev executable，显示版本或启动错误；
- 缓存 `describe`，监听配置、模板和 schema 文件变化后失效；
- 对缓冲区内容做 debounce 后调用 `check-document`，将稳定范围映射为编辑器诊断；
- 使用静态配置 schema 和动态 frontmatter schema 提供补全、悬停和枚举说明；
- 把全仓 `check` 与 `index --check` 暴露为显式 workspace action。

插件不得拥有 profile 定义、修改提案、自动写索引、自动下载 zendev、从 pull request 推断
状态，或在 CLI 失败时退回一个较宽松的本地校验器。找不到兼容 executable、配置无效或
协议版本不支持时必须明确失败。具体编辑器的安装、进程发现、UI、图标、设置名和发布
方式不属于本提案。

本阶段不引入常驻 daemon、自定义 JSON-RPC 或 Language Server Protocol server。普通
进程协议先验证配置发现、未保存文档和诊断范围是否足够；只有启动延迟或跨文档导航在
真实插件中成为问题时，再用相同 normalized policy 和诊断模型增加常驻适配器。

## 兼容性

现有配置版本 1、仓库本地 JSON Schema、Python API、`check`、`index` 和诊断代码继续
工作。版本 2 是显式 opt-in；旧版 zendev 读取它时应报告不支持的配置版本，而不是把
profile 当作路径或跳过校验。

Zendev 和 Cue 的轻量 FP 仓库迁移后只删除各自重复的 schema 文件，frontmatter 接受与
拒绝集合、模板要求、关系、索引内容和 Git 历史行为必须保持不变。配置版本 1 不设置
弃用期限；复杂仓库无需迁移。本提案不改变 ZFP 治理、提案采纳语义或“仓库不维护单独
drafts 目录”的选择。

新增 CLI、配置格式、profile 和 IDE 协议都是公开契约。实现应随一个新的 minor 版本
发布，并在文档中分别记录配置版本、profile 版本和 IDE 协议版本，避免把 package semver
误当成任一数据格式版本。

## 验证

为 `feature-proposal/v1` 建立 ZFP 与通用 FP 两组等价 fixture：分别使用现有 JSON Schema
和 profile，验证有效文档、每个字段的无效边界、模板 type、关系 ID、附加字段和生成索引
完全一致。保留现有 VEP、SEP 与 draft fixture 验证配置版本 1 和自定义 schema 路径。

针对配置加载测试未知 profile、profile/schema 冲突、非法路径、profile 版本漂移和旧工具
读取版本 2。构建并安装 wheel 后重复 profile、静态配置 schema 和 `describe` 测试，证明
行为不依赖源码目录或网络。

以 golden JSON 测试 `describe` 和 `check-document` 的协议版本、POSIX 相对路径、编译
schema、未保存文本、正式文档/draft 选择和精确诊断范围。相同内容同时运行
`check-document` 与全仓 `check --json`，核对诊断代码和消息。增加一个不依赖具体 IDE
SDK 的最小客户端 fixture，证明外部进程可以完成初始化、schema 获取、文档校验、配置
失效和不支持协议版本的失败处理。

最后在 zendev 与 Cue 消费仓库中迁移 `proposal.toml`、删除重复 schema，运行 proposal
check/index、全仓 hooks、测试和 wheel 安装验证；确认离线环境下 IDE 查询与仓库 CI 得到
相同结果。
