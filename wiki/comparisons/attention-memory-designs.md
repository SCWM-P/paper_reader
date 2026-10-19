---
id: p_1c033c0a-99e4-40ca-a180-ef2fcc3a278c
type: comparison
title: 注意力、循环状态与条件记忆的区别
tags:
- 跨论文整理
related:
- p_7747dcb5-4f2e-40e9-bc1c-c21eba576f22
- p_c2891325-eb87-4fb2-81ea-8dfcbf36ac4e
- p_2fdb3776-96ac-4c01-a9cd-fbb8671b75f6
- c_92b75394-f417-46ce-978e-2a7ce4f24c76
created: '2026-10-19T10:50:57.748785+00:00'
updated: '2026-10-19T11:06:07.938Z'
domain: 机器学习
scope: 四篇来源的状态存储、计算依赖与数据搬运；不作跨论文性能排名，性能结论需回到各自实验设置。
sources:
- source_id: s1
  record: papers/DEMO/Kimi Linear- An Expressive, Efficient Attention Architecture/assets/reading-record.json
  url: https://arxiv.org/abs/2510.26692
  locator: 摘要、引言及正文中指明的方法位置
- source_id: s2
  record: papers/DEMO/The Recurrent Transformer- Greater Effective Depth and Efficient Decoding/assets/reading-record.json
  url: https://arxiv.org/abs/2604.21215
  locator: 摘要、引言及正文中指明的方法位置
- source_id: s3
  record: papers/DEMO/Conditional Memory via Scalable Lookup- A New Axis of Sparsity for Large Language Models/assets/reading-record.json
  url: https://arxiv.org/abs/2601.07372
  locator: 摘要、引言及正文中指明的方法位置
- source_id: s4
  record: papers/DEMO/Periodic Weak Spots- Phase Sensitivity from Chunked KV-Cache Compression/assets/reading-record.json
  url: https://arxiv.org/abs/2609.36322
  locator: 摘要、引言及正文中指明的方法位置
question_refs: []
---
## 比较范围

这些工作改变了不同的系统部分，不能用同一个“压缩比”衡量。下表依据关联论文的方法描述整理，属于 AI 综合；没有重跑实验。

| 设计 | 主要存储内容 | 更新或读取方式 | 主要约束 |
| --- | --- | --- | --- |
| Kimi Linear | KDA 递归状态与部分 MLA 缓存 | 混合层计算 | 有限状态表达能力与混合层配置 |
| Recurrent Transformer | 每层输出产生的逐 token KV | 读取已经完成本层计算的历史表示 | 训练时的依赖调度与显存流量 |
| Engram | 由局部 N-gram 索引的参数表 | 确定性查表与上下文门控 | 容量分配、哈希与数据搬运 |
| 分块 KV 压缩 | 连续窗口的压缩表示 | 按固定步长聚合 | 信息保留与相位敏感性 |

## 阅读建议

先区分 [[kv-cache|历史上下文缓存]] 与 [[embedding|参数表中的嵌入]]。Engram 的查表不是外部文献检索。Recurrent Transformer 增加层内时间深度，仍保留逐 token KV；不能把它归为固定状态线性注意力。

[[kimi-linear|Kimi Linear]] 和 [[recurrent-transformer|Recurrent Transformer]] 的性能数字来自不同训练与硬件条件，本页不据此给出跨论文名次。

## 来源定位

s1：Kimi Linear 摘要与架构章节。s2：Recurrent Transformer 第1–2页。s3：Engram 第1–3页。s4：Periodic Weak Spots 第1–2页。
