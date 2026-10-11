# llm-wiki 记录契约 v1

本契约约束伴读 AI 填写的内容。helper 只做文件定位、基本结构与引用检查，不判断科学定义或用户理解为真。

## 记录与定位

概念和待归属问题使用 UTF-8 Markdown。唯一机器数据区如下；区外是用户自由笔记，字段更新和索引重建必须保留原文。

````markdown
<!-- llm-wiki:data:v1 -->
```json
{"schema_version": 1, "questions": [], "reader_evidence": [], "revisions": []}
```
<!-- /llm-wiki:data -->
````

上例是空 unassigned 数据，不是已发生的学习。概念完整字段见 [静态模板](../assets/concept-record-template.md)。不支持的 schema_version 不自动改写；未知附加字段随原记录保留。

- 概念 ID：`c_UUID4`，与 `concepts/c_UUID4.md` 文件名一致。
- 每次实际问题 ID：`q_UUID4`。名称、数组位置、HTML 的 Q1/Q2 不作为身份。
- 实际表现 ID：`e_UUID4`。修订用 `r_UUID4`，保存操作用 `op_UUID4`。
- 学习记录引用：`store:concepts/c_UUID4.md` 或 `store:unassigned.md`，相对本次 `--store` 解析。
- 论文记录引用：`papers/<分类或论文>/assets/reading-record.json`，相对 workspace 解析。
- 不在数据引用中保存 `.runtime/llm_wiki` 或迁移 candidate 的物理路径；不允许绝对路径、`..`、其他前缀或符号链接。
- HTML 问答入口：论文 `note.html#qa-q_UUID4`。它是展示链接；持久记录引用仍使用 record 与 question_id。

## 唯一事实源

| 内容 | 主记录 | 其他记录 |
| --- | --- | --- |
| 论文采集元数据 | 论文 metadata 及已有 metadata 资产 | 只保留来源标识、记录路径与锚点 |
| 共识定义、领域、别名、关系 | 一个概念文件 | 引用 c_ID |
| 论文专属定义与问题 | 该论文 Q & A | 概念 question_refs |
| 共识实际问题 | 一个主归属概念的 questions | 其他概念 question_refs |
| 暂无归属的实际问题 | unassigned.questions | 转存后保留 moved_to |
| 用户实际表现正文 | 实际问题所属记录的 reader_evidence；论文侧位于该问答内 | current 仅引用 evidence_id |
| 当前理解判断 | 概念 reader.current 或论文语境 reader_current | 索引为可重建摘要 |

README 的 `<!-- llm-wiki:index:start -->` 与 `<!-- llm-wiki:index:end -->` 之间是派生索引。区外说明和备注保留；原问、证据和定义不以索引为唯一来源。缺索引时直接 find/get 源记录。

## 概念字段

| 字段 | 内容 |
| --- | --- |
| schema_version、id | 1；稳定 c_UUID4 |
| name、aliases | 规范名、别名数组；同名不代表同义 |
| domain、definition、scope | 领域、定义、适用边界；未知内容留空并说明 |
| consensus | status 为 verified/unverified；source_refs 引用本记录 sources 的 source_id |
| sources | source_id、kind、record 或 url、locator、version_note、verification |
| relations | type 为 requires/uses/contrasts_with，另存 target_id、scope、source_refs |
| questions、question_refs | 自己拥有的实际问答；他处引用为 `{record, question_id}` |
| reader_evidence | 本概念拥有的问题对应的实际表现 |
| reader.current | state、scope、evidence_refs、reason、updated_at |
| revisions | revision_id、at、reason、previous、replacement、source_refs |
| record_status、redirect_to | active + null；或 merged + 目标 c_ID，保留旧 ID 入口 |
| created_at、updated_at | 实际记录时间；历史未知用 null 并注明原因 |

source.kind 区分 paper、background、teaching、inference、user。locator 记录已知的章节、式号、图号或 PDF 物理页；version_note 记录版本或缺项。来源路径可解析不代表来源真实，外部页面核验由伴读 AI 完成。

## 每条实际问题

| 字段 | 内容 |
| --- | --- |
| id、question | 一次发言的 q_UUID4；逐字原问题，保留换行、引号和符号 |
| question_form | exact；旧记录无法证明逐字时为 legacy_recorded |
| question_at、time_note | 已知发言时间；未知为 null 并说明原因，不以 mtime 推断 |
| recorded_at | 实际登记时间；未知历史登记时间可为 null 并说明 |
| answer、answer_at、resolution | answer 是字符串；未答为 `""`、null、unanswered；答后为 partial/answered |
| keywords、related_question_ids、topic_id | 可选检索与归组，不代替原问 |
| source_refs、concept_refs | 已知来源锚点与概念 ID；缺项注明待核实 |
| intended_record | 论文记录尚未建立时，暂存预期论文逻辑路径 |

论文问答保留原有 question、answer、origin、evidence。以上字段均为可选附加字段；普通旧记录无需补全才可 check/render。首次建立长期引用时补 ID。仅追加 ID 的历史 EXAMPLE 保持 `legacy_recorded`，不伪造历史时间。

## 理解证据与修订

每条 reader_evidence 包含 evidence_id、kind、observed_at、recorded_at、scope、actual、question_ref。`actual` 是真实表现或原自述；`question_ref` 指向同一主归属的实际问题。

kind 为 self_report、demonstration、inference、forgotten、correction。current.state 为 unknown、uncertain、demonstrated_in_scope、forgotten。`demonstrated_in_scope` 必须由对应范围的实际 demonstration 支持；自述、AI 讲解或推测不能代替它。evidence_refs 使用 `{record, evidence_id}`，可以跨记录引用表现，但不得复制 actual 正文。

只限论文语境的表现不自动推广为共识理解。用户遗忘或纠正时新增实际证据，调整 current，保留旧证据。定义或理解修订写 previous、replacement、reason 和依据；新来源不自动覆盖旧定义或用户状态。

## 转存与合并

unassigned 转存保留 q_ID 和关联 e_ID。目标保存并回读后，原条目改为：

```json
{"id": "q_<原UUID4>", "moved_to": {"record": "store:concepts/c_<目标UUID4>.md", "question_id": "q_<原UUID4>", "evidence_ids": []}}
```

这是形状示意，占位符必须替换。原条目不再保存 question、answer 或已转存的实际表现；旧问题与证据引用经 moved_to 解析。两步间有重复正文时，先完成转存，再重建索引。

概念合并时，旧概念设 merged/redirect_to，历史问题与证据仍留原文件；目标仅引用它们。禁止重定向环。两份原问不能同时被当作主记录。
