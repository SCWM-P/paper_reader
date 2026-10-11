---
name: llm-wiki
description: 解释论文中的知识卡点，按用户需求系统讲解，并维护可溯源、可跨论文复用的概念与实际问答记录。用于论文伴读、知识归档、理解纠正和新会话接续；论文专属定义保留在该论文 Q & A。
---

# 文献卡点伴读与知识 Wiki 构建

目标是帮助用户读懂当前论文，并让实际问题、定义范围和理解证据在后续会话中可找回。接到“这句或这个公式是什么意思”“基础不够”“我缺少背景知识”“请你系统讲解一下”时使用。表达遵循项目 [CLS](../cls/SKILL.md)；本技能负责知识与记录，不另设语言规则。

## 接续与讲解

- 读取 `.runtime/llm_wiki/README.md` 的说明和用户备注。按当前论文、概念、领域与别名限定检索，再回读相关主记录、实际问答和证据。索引只是入口；缺索引或缺记录不表示用户已经掌握。
- 首次使用且没有旧学习目录时，执行下方 `init` 建空入口。若发现旧目录，按 [迁移与恢复流程](references/workflows.md) 备份、转换、验证后再切换，不建立两套活动档案。
- 定位原句、图、公式及 PDF 物理页。只有术语时，基于可见上下文解释，注明尚未定位的部分。用已知理解范围选择起点；没有相关证据时，暂按“聪明的本科生”解释，专业背景保持 unknown。
- 由当前卡点决定必要先修、粒度和展开程度。缺哪个前提就补哪个，再回到原句；不将一串陌生名词当作解释。系统讲解按用户需求组织，不固定概念数量、追溯深度或统一讲解顺序。
- 数值例子先实际计算，注明教学参数、定义范围和适用边界。类比之后给出准确表述。区分原文、背景、教学例子与推断；教学数字和自拟练习不充当论文实验或用户经历。
- 根据需要提供复述或应用问题。用户可以跳过自测、自述已知、说明遗忘或继续阅读。结束时将解释代回原文，给出返回位置和未解决内容。

## 唯一归属与理解证据

- 共识概念放在 `concepts/c_<UUID>.md`，注明领域、定义范围、来源和共识核实状态。领域基石即使来自论文，也可以登记为共识概念。同名不自动合并；复用前比较定义范围与来源。
- 论文专属公式、变量及作者定义放在该论文 `assets/reading-record.json` 的 `Q & A`。混合问题优先保留必要的论文语境，概念记录只引用该问答。没有论文上下文且无法归类时，放入 `unassigned.md`。
- 每次实际学习提问保留一个 `q_UUID4` 和逐字原问。追问独立保存，用关联 ID 归组。相同文字再次提问是新发生；重试同一次保存必须复用原 ID。历史记录标 `legacy_recorded`，不猜测原始措辞或发言时间。
- 原问和实际答复只有一处主记录。实际表现 `reader_evidence` 也随该问题主归属保存；其他概念用 `{record, evidence_id}` 引用。共识范围的当前判断放在概念 `reader.current`，论文语境判断放在对应问答 `reader_current`。
- 提问过、讲解过、自述懂了、真实复述或应用分别记录。`self_report` 和 `inference` 不能证明 `demonstrated_in_scope`。理解判断必须有范围与实际证据；一次表现不代表永久掌握或其他领域的理解。
- 用户说明遗忘、没懂或纠正时，保留旧证据，新增实际反馈与修订原因，再调整当前起点。共识依据的修订不自动改变读者理解状态。

## 保存与回读

用户已授权在伴读中自然更新本地记录，无需逐概念请求登记。首次写记录时读 [记录契约](references/record-contract.md)；更新、合并、转存或恢复时读 [操作流程](references/workflows.md)。[概念模板](assets/concept-record-template.md) 只供按实际资料填写，不代表用户历史。

先保存原问：`answer` 为 `""`、`answer_at` 为 null、`resolution` 为 `unanswered`。完成实际答复后按同一 ID 补答案与来源。缺论文记录时，先在 unassigned 保存问题与 `intended_record`；不为保存一问编造四个论文模块。

保存采用原件 hash、候选和备份。源文件变化时，重读并合并用户编辑。保存后按 ID 回读，核对完整原问；只有主记录成功才说明已记录。候选失败时保留候选位置，不能说已归档。最后重建派生索引。论文 Q & A 变化后用既有渲染器更新 `note.html`。

从工作区根目录、现有 Python 环境执行：

```bash
python -B .agents/skills/llm-wiki/scripts/wiki_store.py init
python -B .agents/skills/llm-wiki/scripts/wiki_store.py find --query '当前概念或原问题'
python -B .agents/skills/llm-wiki/scripts/wiki_store.py get --record 'store:unassigned.md'
python -B .agents/skills/llm-wiki/scripts/wiki_store.py reindex
```

`find --paper 'papers/<实际论文>/assets/reading-record.json'` 可以重复限定论文；学习目录始终参加检索。`get --id` 返回概念、实际问题或理解证据。工具只读规定的学习文件和确切 reading-record，不扫描凭据、PDF、临时资产或备份。完整参数见 `--help`。

`.runtime/` 不进入 Git；云端同步尚未配置。新克隆不会自动携带个人学习历史。论文四模块沿用 AGENTS：AI 草拟 summary 标记 degraded，尚未讨论的 `Q & A` 为 `[]`，`others` 保持普通扩展。实际 Zotero 操作另读 [Zotero SKILL](../zotero/SKILL.md)，本地保存不授予文库写入权限。

本技能承接 Paper Tutor 的卡点讲解、范围区分、理解证据与跨会话接续。教学设计参考 [university-skill](https://github.com/SCWM-P/university-skill) 的必要先修、小数值例子与来源核验思路；本地协议独立编写。
