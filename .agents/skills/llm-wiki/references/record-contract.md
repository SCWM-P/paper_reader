# 记录契约

Python 服务、CLI、GUI 和模板使用同一契约。主记录是文件；索引与图谱可重建。

## 存储边界

普通工作区默认使用 `.runtime/llm_wiki/`。在 pyproject.toml 的 `tool.paper-reader.wiki.root` 设为 `wiki` 后，公共知识使用可跟踪的 `wiki/`。demo 使用这一设置。锁、服务登记、token 与缓存仍只在 `.runtime/`。

| 类型 | 主记录位置 | 用途 |
| --- | --- | --- |
| concept | concepts/*.md | 跨语境公共概念 |
| entity | entities/*.md | 有身份的模型、工具、数据集或组织 |
| query | queries/*.md | 有来源的研究议题；不是实际用户问题 |
| comparison | comparisons/*.md | 有依据的比较 |
| synthesis | synthesis/*.md | 有依据的综合 |
| overview | overview.md | 知识概览 |
| source | papers/**/assets/reading-record.json | 论文唯一主记录，经适配供 GUI 展示 |

README.md 是入口说明，index.md 是派生索引；两者不作为知识节点。扫描排除 ref_repository、隐藏目录、tmp、node_modules 与符号链接。

## YAML 与身份

知识 Markdown 必须以 YAML frontmatter 开始。只读取当前格式，不保留旧格式入口。正文允许表格、公式、代码、Mermaid 和双链。

公共必含字段：`id`、`type`、`title`、`tags`、`related`、`created`、`updated`。tags 与 related 是字符串数组。时间是实际记录时间字符串；历史未知为 null。标题修改不改变身份或文件名。

concept 使用 c_UUID4；其他知识页面使用 p_UUID4。文件名可以是稳定 ID 或稳定 slug，不随标题重命名。论文的历史 ID 原样保留。

`[[稳定ID]]`、`[[文件名]]`、`[[目录/文件名|显示标题]]` 通过同一解析器定位记录。重复文件名导致歧义时必须改用稳定 ID。related 也使用该解析器。完整逻辑路径如 `store:concepts/attention.md` 或 `papers/DEMO/.../assets/reading-record.json` 可以直接引用。代码块中的双链不构成关系。

## 扩展字段与来源

- domain：领域；scope：定义或结论的适用范围。
- definition：概念定义；aliases：别名数组。
- sources：来源对象数组。每项含本记录唯一 source_id，以及 record 或 url；locator 指明章节、公式、图号或 PDF 物理页。
- source_refs：只引用本记录的 source_id。
- consensus：concept 必含，status 为 verified 或 unverified；verified 必须有 source_refs。结构检查只确认依据存在，不能替代公共共识的内容审查。
- relations：对象数组，每项含 type（requires / uses / contrasts_with）、target_id、scope、source_refs。关系必须有适用范围和来源依据。
- question_refs：可选，只引用论文的 record 与 q_UUID4，不复制实际问题。
- entity 表示具名对象，不因发表于论文而被标为公共共识。

上游字段 type/title/tags/related/created/updated 保持原义。本项目增补稳定身份、领域、范围、来源定位与关系依据。旧 name 更新为 title；旧时间字段更新为 created/updated；关联项使用稳定引用。论文作者、年份、出版信息从论文 JSON 读取，不另存 source 摘要。

## 实际问答与理解依据

实际问答只保存在论文 JSON 的 `Q & A`。每问含稳定 q_UUID4、逐字 question、answer、question_form（exact / legacy_recorded）。resolution 为 unanswered / partial / answered。新问未答时 answer 为空字符串；未知历史时间保持 null，不补造。

reader_evidence 随所属论文问题保存，含 e_UUID4、kind、actual、scope、question_ref。kind 为 self_report、demonstration、inference、forgotten 或 correction。question_ref 必须回指同一论文中存在的问题。reader_current 的判断必须引用实际 evidence_refs；demonstrated_in_scope 需要同范围 demonstration。原问、稳定身份和既有证据必须保留。知识页面不保存个人问答或理解状态。

论文继续沿用四个必要模块：metadata、summary、highlights、Q & A。AI 整理的摘要标 degraded，未讨论论文的 Q & A 为 []。EXAMPLE 每次随最新协议验收，保留全部历史内容、元数据与资源。

## 保存

先读取 SHA256，再提交候选内容和基准。新记录基准为 missing。保存使用跨进程锁、核对基准、原子替换；冲突返回明确错误。外部不遵守锁的编辑器不具备事务保证。

响应分别报告 source（主记录）、index、html。HTML 或索引失败不撤销已成功的主记录，也不伪报主记录失败。记录身份不可改；论文编辑只更新实际 Q & A。内容编辑不建立备份、回滚副本或并行协议。
