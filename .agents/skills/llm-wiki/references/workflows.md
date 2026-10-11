# 保存、接续与恢复

本版按用户确认的 `.runtime/llm_wiki/` 和单一 helper 实施。用户后续收窄要求优先：保留直接服务保存、检索和恢复的功能，不建立锁服务、跨文件事务或全量语义检查框架。

## 日常问答

1. 读取相关主记录。用 `get --record ...` 取得内容与 SHA256；新文件基线为 `missing`。
2. 分配并保留 q_UUID4。选择唯一归属；无论文记录时暂存 unassigned，不伪造四模块。
3. 在当前 store 的 `.pending/op_UUID4/candidate.md` 或 `candidate.json` 写候选。现有 Markdown 用 helper 的 `encode_record(data, original)` 只替换数据区；保留未知字段和自由笔记。
4. 调用 save。它保留原件、核对读时 hash、完整替换单个目标。源文件变化时返回 conflict，保留候选；重读后合并用户改动，用新的 op_ID 保存。
5. get 同一 q_ID，核对原问。实际答复完成后补 answer、来源和未解决项，再保存回读。
6. 添加相关概念引用或理解证据引用。最后 reindex；论文 Q & A 变更后，用项目现有 render 更新页面。

```bash
python -B .agents/skills/llm-wiki/scripts/wiki_store.py get \
  --record 'store:unassigned.md'
python -B .agents/skills/llm-wiki/scripts/wiki_store.py save \
  --target 'store:unassigned.md' \
  --candidate '.runtime/llm_wiki/.pending/op_<实际UUID4>/candidate.md' \
  --expect '<读取时SHA256>' --op-id 'op_<实际UUID4>'
python -B .agents/skills/llm-wiki/scripts/wiki_store.py get \
  --record 'store:unassigned.md' --id 'q_<实际UUID4>'
python -B .agents/skills/llm-wiki/scripts/wiki_store.py reindex
```

所有命令可用 `--workspace` 指定包含 AGENTS.md 和 papers 的根目录。`--store` 只接受正式根或 `.runtime/llm_wiki-migrations/m_UUID4/candidate`。参数可放在子命令前后。

准备现有 Markdown 候选时，可以在 Python 中通过 `importlib.util` 加载 helper，调用 `load_record(path)`，只修改其 data，再用 `encode_record(data, original)` 输出候选。`new_id('q')`、`new_id('e')`、`new_id('op')` 生成 UUID4；同一次问题或保存重试不重新生成身份。

helper 不创建语义内容。先写真实原问，answer 使用空字符串；不把新建概念、讲解、模板或练习当作用户理解证据。用户正在编辑同一源文件时先保留候选，待编辑结束后读取新基线。

## 恢复与范围

`.pending/op_ID/operation.json` 保存逻辑目标、原 hash、候选 hash 和阶段；`.backups/op_ID/base.md` 或 base.json 保存被替换前原件。备份与候选不参加现行检索，不自动清理。

- 相同 op_ID、相同候选，目标已等于候选 hash：返回 unchanged，补记 committed。
- 目标仍等于原 hash：复用候选和原 ID 重试。
- 目标与两种 hash 均不同：保留用户当前文件，合并后建立新候选，不用备份覆盖后来编辑。
- 候选尚未成功写入：不得声称已保存。CLI 只有在候选实际可回读时返回 recoverable_path。
- 索引失败：主记录仍可 get/find。修复具体断链后重建；不删除原问来消除错误。

完整文件替换和 hash 比较不等于任意并发事务。此版本不加锁；不要让多个写入者同时更新同一记录。它不自动回放未提交候选、不做多文件原子提交、不自动合并语义冲突。科学真实性、理解范围与未知字段保留由伴读 AI 依据原文负责。

`check` 只检查可读结构、稳定身份重复、显式问题/证据引用和入口缺项，不证明科学定义或理解判断正确。退出码为 0 成功、1 内容或引用错误、2 参数或路径错误、3 基线冲突、4 I/O 错误。命令结果用 JSON，面向用户的回复遵循 CLS。

## 新会话与索引

读取 README 区外备注，再用 find/get 回源。find 对 JSON 解码后的原问、别名和实际表现查询，支持换行与引号；不依赖上次聊天缓存。`--paper` 指定确切论文记录，未指定时只枚举 `papers/**/assets/reading-record.json`，不读取其他论文资产或 Zotero 运行数据。

reindex 从源文件重建派生区，并保存源 hash；它保留区外备注。失败时旧索引保留，不声称完整。无索引时直接检索，不把缺索引解释为用户没有知识。需要人工搜索时，列出确切学习目录和论文记录，并使用 `rg --hidden --no-ignore`；不得对整个 `.runtime/` 全文扫描。

## 转存、合并与修订

unassigned 转存按两步完成：先以相同 q_ID 和 e_ID 保存目标、回读原问与实际表现；再把原问题改为 moved_to，删除原位置已转存的表现正文。保留两次保存的 op_ID，并在本次操作记录中写 source、destination、question_id、evidence_ids 和阶段。目标中的 evidence.question_ref 改为新主记录。中断时以原件、候选与回读结果继续；重复正文消除后才重建索引。旧 current 的 evidence 引用可经 moved_to 找回。

概念合并只在定义、领域、范围与依据一致时执行。旧文件保留 merged/redirect_to 与原问题；目标用引用接续。来源冲突、版本变更或用户纠正必须保留旧事实与 revision；不因为来源更新就修改读者理解状态。

## 旧目录迁移

1. 只盘点旧学习目录的 README 和 concepts。遇未知文件、符号链接或活动编辑，先确认其用途，不扫描其他 runtime。
2. 在 `.runtime/llm_wiki-migrations/m_UUID4/` 保存 manifest、原字节 hash、属性及 original 副本。旧正式技能的实际工作区版本一并留在 `skill-original/`，避免遗漏用户未提交内容。
3. 初始化 candidate，按契约转换真实内容。旧原问无法证明逐字时标 legacy_recorded；历史时间未知为 null。空旧索引只保留说明与备注，不生成概念或学习经历。
4. 在 candidate 下 get/find 相关记录，核对原问、表现和逻辑引用。`store:` 始终相对本次根，论文引用始终相对 workspace。
5. 源 hash 保持一致且正式根不存在时，将 candidate 改名提升到 `.runtime/llm_wiki/`。目标有其他内容时停止，不覆盖。
6. 在正式根完成基础读取与索引重建，再切 AGENTS/Zotero 入口，将旧学习目录移至 manifest 同级的 retired。新技能入口接续成功后移除旧正式技能。

备份保留到用户决定清理。正式根尚无新写入时，可恢复 retired 与 skill-original；正式根已有新记录时先合并新记录，不直接回滚。云端同步对象与远端存储尚未配置，本版只维护本地资料。

本版承接的原工作区 Paper Tutor SKILL SHA256 为 `a628bd2c4086b3c38b875525bc419c88eea2d2ad74acc981ce7aca4e27d156eb`。卡点解释、来源区分、实际证据、原问保存和接续分别进入新 SKILL 对应章节；表达职责交给 CLS；不固定旧版 5 个先修、深度 2 或统一讲解顺序。用户已删除的草稿不恢复。
