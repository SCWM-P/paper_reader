---
name: paper-tutor
description: Explain a difficult paper passage to a research beginner or cross-domain reader, filling only the prerequisites needed for that passage with short worked examples and optional checks. Preserve the original passage, uncertainty and actual reader responses in portable reading records.
---

# 原文卡点伴读

目标是让用户继续读懂当前论文。接到“这句/这个公式不懂”“基础不够”“越解释越不懂”时使用；长篇课程按用户明确需求另行安排。

## 直接讲清一个卡点

- 定位原句、公式或图，保留章节/式号和 PDF 物理页。只有术语而缺原文时，先用已知上下文解释，明确尚未定位的部分；不要编造出处。
- 复用本次会话已有的读者起点与自述。没有信息时先按基础算术、常识解释，并把起点标为暂定；只在歧义会改变解答时提出一个短问题。不要每次重新做背景调查。
- 从当前卡点挑最必要的先修。解释 A 时若需要未知 B，先用一句话或一个小例子补 B，再回到 A；不要用一串新名词替换原名词。
- 按“要解决什么 → 小例子 → 必要定义/符号 → 回到原句”组织讲解。数值例子先实际计算，标清教学参数与适用边界。类比只用于真正的难点，随后给出能回到论文的准确表述。
- 默认单次处理一个卡点，主讲一个阻塞概念。先修展开默认最多 5 个概念、深度 2（从当前概念向前追溯的边数）。缩短优先于扩展；单份记录硬上限为 8 个概念、3 层，更多内容拆为下一次卡点。出现循环、缺先修或预算用尽时停止展开，写明未解决内容，仍允许返回原文。
- 关键处可给一个短算题或复述问题，参考解答可折叠。用户可以跳过、自述已知或直接继续；自测不是继续阅读的门槛。
- 结尾把解释代回原句，给出明确返回位置与接下来可读的内容。一次讲清后就回到阅读，不自动扩成整本教材。

## 状态与证据

`unknown` 需要补习；`uncertain` 不确定；`explained` 已讲解、理解待确认；`confirmed` 有用户实际作答及通过反馈；`skipped` 已跳过、未检验。

生成解释、展示参考答案、用户打开页面，都不能产生 `confirmed`。用户说“懂了”可以记录自述并继续；这本身不是作答证据。只记录真实发生的回答与评价，不代写用户回答。确认仅表示本次小检查通过，不保证完整掌握或长期记忆。

用户可随时纠正起点、将任何状态改回 `uncertain`/`unknown`，或撤回确认。在 `revision` 写明原因；保留旧回答时明确它是上次自测记录。跳过与确认分开。用户不答题也可返回原文；如需扩大补习范围，拆成下一条卡点而不是提高到无限预算。

来源按内容块区分：`paper` 原文引文/概述（写定位）；`background` 外部背景（写可核验书目或网址与定位）；`teaching` 人工构造的教学例子；`inference` 教学推断与边界。教学数字、类比和自拟练习不得成为论文实验证据。无法核验时保留不确定说明。

## 保存与接续

普通讲解直接在会话中完成。用户要求保存或已有归档授权时，在原来的 `assets/reading-record.json` 的 `others` 增加一个带 `learning` 的模块，保留原有字段及用户编辑。下一次先读这条卡点、起点和未解决项，再接续解释。

保存前读 [记录格式](references/learning-record.md)。四个核心字段继续遵循项目约定：AI 草拟 summary 设置 `completeness.summary.status: degraded`；`Q & A` 只收实际讨论，未发生时为 `[]`。自拟练习放在 `learning`，不伪装成用户问答。

使用 `paper render` 渲染学习模块并保留离线公式；摘要渲染共享同一内容。没有保存授权时不写 Zotero。首次实际文库操作另读 `../zotero/SKILL.md`。

[Attention 短示例](assets/attention-prerequisites.json) 是人工编写的结构演示，所有概念均为 `explained`、所有自测待回答；它不是实际用户讨论，也不是 AI 教学效果测评。运行方法见记录格式。

教学设计参考 [university-skill](https://github.com/SCWM-P/university-skill)：采用必要先修、小数值例子与来源核验的思路；具体内容与本地协议自行编写，篇幅按当前卡点决定。
