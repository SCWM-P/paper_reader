# CLS · 受控语言风格

CLS（Controlled Language Style）是 Paper Reader 的内置 skill，用于统一 AI 面向用户的表达：关键信息先行、术语一致、动作明确、证据可查。

适用于日常交流、论文解释、归档资料、进度与结果汇报。创意写作、代码与注释、来源原文、日志和 Agent 间通信不受本规范约束。具体边界以 [SKILL.md](SKILL.md) 为准。

## 使用

项目通过 [AGENTS.md](../../../AGENTS.md) 引用本 skill。让 Agent 读取本目录的 `SKILL.md` 即可使用；不需要单独安装上游项目或运行服务。规范依靠 Agent 执行，不提供程序化校验器。

规则分为词、句、段落、汇报、字符和格式六组。引用具体规则时使用 `R1-1` 形式，并以 `SKILL.md` 中的当前定义为准。

## 文件

| 文件 | 内容 |
| --- | --- |
| [SKILL.md](SKILL.md) | 适用范围、规则、模板入口与自检清单 |
| [references/terminology.md](references/terminology.md) | 术语、情态词、动词替换和状态词 |
| [references/templates.md](references/templates.md) | 进度、结果、排查和多项总结模板 |
| [examples/](examples/) | 原有表达改写示例 |
| [LICENSE](LICENSE) | 上游版权及 MIT 许可全文 |

## 来源与许可

本目录改编自 [dualface/ste-zh](https://github.com/dualface/ste-zh)，作为 Paper Reader 的 `cls` skill 维护。改编包括适用范围、分组规则、模板组织和项目术语。

保留 `Copyright (c) 2026 dualface` 及完整 [MIT 许可证](LICENSE)。本目录的改编内容继续按 MIT 分发；该许可不覆盖项目其他组件。

CLS 借鉴 ASD-STE100 的写作原则，规则编号和中文内容由本项目维护。CLS 不代表 ASD-STE100 官方标准或认证。
