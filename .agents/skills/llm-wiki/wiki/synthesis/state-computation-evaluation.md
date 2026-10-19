---
id: p_2652e3bb-22d7-456b-bd6a-c058c83188b0
type: synthesis
title: 从状态表示到可靠评估：阅读这些架构论文的共同路径
tags:
- 跨论文整理
related:
- c_92b75394-f417-46ce-978e-2a7ce4f24c76
- c_4e39d13d-2203-401d-ab3c-4b9264907b40
- c_2ac6262e-988f-4963-93e4-1628fc5dd2a9
- p_2fdb3776-96ac-4c01-a9cd-fbb8671b75f6
created: '2026-10-19T10:50:57.748785+00:00'
updated: '2026-10-19T10:50:57.748785+00:00'
domain: 机器学习
scope: 所列来源的公开方法与评估条件；AI 综合
sources:
- source_id: s1
  record: papers/DEMO/Kimi Linear- An Expressive, Efficient Attention Architecture/assets/reading-record.json
  url: https://arxiv.org/abs/2510.26692
  locator: PDF 物理第 4–6 页：§3 Kimi Delta Attention、§3.1 Hardware-Efficient Chunkwise Algorithm、§4 The Kimi Linear Model Architecture
- source_id: s2
  record: papers/DEMO/The Recurrent Transformer- Greater Effective Depth and Efficient Decoding/assets/reading-record.json
  url: https://arxiv.org/abs/2604.21215
  locator: PDF 物理第 3–5 页：§2 Architectural overview and notation，尤其 §2.2 The Recurrent Transformer layer
- source_id: s3
  record: papers/DEMO/Conditional Memory via Scalable Lookup- A New Axis of Sparsity for Large Language Models/assets/reading-record.json
  url: https://arxiv.org/abs/2601.07372
  locator: PDF 物理第 3–4 页：§2.1 Overview、§2.2 Sparse Retrieval via Hashed N-grams、§2.3 Context-aware Gating
- source_id: s4
  record: papers/DEMO/Periodic Weak Spots- Phase Sensitivity from Chunked KV-Cache Compression/assets/reading-record.json
  url: https://arxiv.org/abs/2609.36322
  locator: PDF 物理第 1–4 页：Abstract、§2 Stride-Periodic Behavior、§2.2 Measuring Phase Sensitivity in Retrieval、§3.1 A Family of KV Compression Kernels
- source_id: s5
  record: papers/DEMO/LLMs Get Lost In Multi-Turn Conversation/assets/reading-record.json
  url: https://arxiv.org/abs/2505.06120
  locator: PDF 物理第 1 页 Abstract 与 Figure 1，第 3–5 页 §3 Simulating Underspecified, Multi-Turn Conversation
question_refs: []
---
## 综合观点

阅读效率架构时，可以依次核对状态、计算依赖、数据移动和评估条件。这个组织方式是 AI 对所列来源的综合，不是任一论文提出的通用定理。

```mermaid
flowchart LR
  A["状态保存什么"] --> B["依赖如何传播"]
  B --> C["数据如何搬运"]
  C --> D["在哪些条件下评估"]
  D --> E["结论适用范围"]
```

## 四个检查点

1. 状态是逐 token 的 [[kv-cache|KV cache]]、递归状态，还是由参数表保存的知识表示。
2. 依赖是否改变了 [[computation-graph|计算图]] 的深度与并行性。
3. 减少运算是否同时减少访存；用 [[arithmetic-intensity|算术强度]] 区分两个问题。
4. 平均指标是否掩盖位置、对话轮数或任务条件的差异。

Engram 的参数查询、KDA 的状态更新与 Recurrent Transformer 的层内循环解决不同问题。Periodic Weak Spots 与多轮对话研究提醒读者：改变输入组织方式也可能改变可靠性。

## 使用边界

这里只整理研究阅读顺序，没有生成用户提问、理解判断或新实验结果。每项结论应回到来源中的模型、版本、数据和测量条件。

## 来源定位

s1–s3：对应论文摘要与方法概要。s4：第1–2页的相位分析动机。s5：摘要与多轮评估方法。
