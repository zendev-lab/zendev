---
zfp: 1
title: "将 Zendev 拆分为 PEP 420 发行包"
status: Accepted
type: Feature
authors:
  - "zrr1999"
created: 2026-08-26
supersedes: []
---

# ZFP-0001: 将 Zendev 拆分为 PEP 420 发行包

## 摘要

把 `zendev`、`zendev-commit`、`zendev-review`、`zendev-proposal` 和
`zendev-log` 发布为共同组成隐式 `zendev` namespace 的五个发行包。根
`zendev` 发行包直接依赖其余四个组件，提供统一的 `zendev` 命令和
`python -m zendev` 入口。0.2.0 移除根 namespace 的日志重导出，用户从
`zendev.log` 导入 `setup_log`。

## 动机

当前发行包混合了提交规范、PR 检查、提案管理和日志配置，而这些能力的使用者、
依赖和集成入口不同。提案 CLI 的用户不应被迫安装提交交互或 Loguru；日志用户不应
需要 JSON Schema 或 YAML；只使用提交 hook 的仓库也不需要 PR body 校验机制。

独立发行包让这些 owner 和依赖边界可见，并允许按组件安装。根 `zendev` 仍是
默认的完整工具集，个人项目无需在组件之间做选择。

## 设计

仓库继续使用一个 uv workspace、一个 lockfile、一个版本和一个发布标签。五个
发行包的职责如下：

| Distribution | Namespace 内容 | 运行时依赖 | 命令 |
| --- | --- | --- | --- |
| `zendev` | `zendev.cli`、`zendev.__main__` | Typer 及其余四个组件 | `zendev` |
| `zendev-commit` | `zendev.commit`、`zendev.conventional`、`zendev.gitmoji` 和离线数据 | Questionary、Typer | `zendev-commit`、`zendev-commit-msg` |
| `zendev-review` | `zendev.title`、`zendev.body`、`zendev.checklist`、`zendev.markdown_scan` | Typer、`zendev-commit` | `zendev-validate-title`、`zendev-validate-body` |
| `zendev-proposal` | `zendev.proposal` | JSON Schema、PyYAML、Typer | `zendev-proposal` |
| `zendev-log` | `zendev.log` | Loguru | 无 |

`zendev-review` 统一拥有 PR title 和 body 校验，并依赖 `zendev-commit` 复用提交
profile；它不复制提交语义。根 `zendev` 直接依赖全部四个组件，并直接组合它们的
Typer command，不为缺失组件定义降级行为。

所有发行包使用 PEP 420 隐式 namespace：任何 wheel 都不得安装
`zendev/__init__.py`，不同 wheel 不得拥有同一路径。为满足 PEP 561，原有的单文件
公开模块改为同名常规子包，并在各子包中放置 `py.typed`。这保持
`zendev.commit`、`zendev.title`、`zendev.body` 等导入路径不变，同时避免多个
发行包争用根 `zendev/py.typed`。

根发行包以 typed `zendev.cli` 作为统一 CLI owner。`zendev.__main__` 是委托层，
继续导出 `app` 和 `main` 并支持 `python -m zendev`。统一命令包括：

- `zendev commit`
- `zendev commit-msg`
- `zendev validate-title`
- `zendev validate-body`
- `zendev proposal`

现有五个独立 console script 继续存在。复合 GitHub Actions 和远程 proposal hook
继续从仓库根发行包安装，以保持按 revision 使用的行为不变；组件包同时允许直接
安装和调用。所有公开 CLI 继续使用 Typer。

发布工作流从同一个 `v0.2.0` tag 构建并发布全部五个 workspace 发行包。每个包有
自己的 README 和 wheel metadata，但共享版本与变更历史。

## 兼容性

这是随 0.2.0 发布的破坏性变更。日志用户从：

```python
from zendev import setup_log
```

迁移为显式安装和导入：

```console
uv add zendev-log
```

```python
from zendev.log import setup_log
```

旧的根导入必须失败。安装 `zendev` 会通过必需依赖提供全部 namespace portions；
只需要单项能力的用户可以独立安装对应组件。现有 Python 模块路径、五个兼容命令、
统一命令和 `python -m zendev` 保持可用。不添加兼容发行包、模块别名或可选组件
模式。

## 验证

构建五个 wheel，检查文件列表没有重叠、没有根 `zendev/__init__.py`，并确认 typed
marker 位于各常规子包。分别安装 commit、review、proposal 和 log wheel；确认
review 自动解析 commit 依赖。只安装根 wheel 时，确认安装器从同一 wheel 目录解析
全部四个组件。

运行全部既有 Python 导入、五个兼容 console script、`zendev` 和
`python -m zendev`，包括统一 proposal command。针对安装后的 wheel 运行类型检查
smoke test，并确认卸载一个组件后其余 namespace portions 仍可导入。确认
`from zendev import setup_log` 失败，而安装 `zendev-log` 后
`from zendev.log import setup_log` 成功。最后运行仓库测试、静态检查、hooks、依赖
一致性检查和发布构建 dry run。
