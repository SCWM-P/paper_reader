---
id: p_f5644482-dc02-4732-afcb-ea16fe676503
type: comparison
title: 图像生成与开放式语言生成中的多样性
tags:
- 跨论文整理
related:
- c_76dc8960-64de-4ae9-bdda-312f824b9381
- p_72ce7c30-1803-4c4d-91b3-481612a895bb
- p_48f76a8e-3c3c-42ea-9116-f60942978b61
- p_c4ad2419-45a1-499a-a374-a3292bcdd1e3
created: '2026-10-19T10:50:57.748785+00:00'
updated: '2026-10-19T10:50:57.748785+00:00'
domain: 机器学习
scope: 所列来源的公开方法与评估条件；AI 综合
sources:
- source_id: s1
  record: papers/DEMO/Toward Multimodal Image-to-Image Translation/assets/reading-record.json
  url: https://arxiv.org/abs/1711.11586
  locator: 摘要、引言及正文中指明的方法位置
- source_id: s2
  record: papers/DEMO/Artificial Hivemind- The Open-Ended Homogeneity of Language Models (and Beyond)/assets/reading-record.json
  url: https://arxiv.org/abs/2510.22954
  locator: 摘要、引言及正文中指明的方法位置
- source_id: s3
  record: papers/DEMO/The Flexibility Trap- Rethinking the Value of Arbitrary Order in Diffusion Language Models/assets/reading-record.json
  url: https://arxiv.org/abs/2601.15165
  locator: 摘要、引言及正文中指明的方法位置
question_refs: []
---
## 共同问题与不同测量

三个来源都讨论生成结果覆盖不足，但任务、样本空间与指标不同。本页的共同视角是 AI 综合，不能当作三篇论文采用了相同的模式坍塌定义。

| 来源 | 观察对象 | 关键区分 |
| --- | --- | --- |
| BicycleGAN | 同一输入下的图像输出 | 感知真实性与多样性 |
| Artificial Hivemind | 开放式问题的语言输出 | 模型内重复与模型间同质化 |
| The Flexibility Trap | 推理任务的候选解 | 生成顺序自由度与实际探索覆盖 |

## 机制

[[bicyclegan|BicycleGAN]] 通过潜变量往返约束减少生成器忽略噪声的情况。[[infinity-chat|Infinity-Chat]] 支持对开放式输出进行数据层面的评估，不能据此推定语言模型与 GAN 共享同一训练机制。

[[justgrpo|JustGRPO]] 区分训练 rollout 的顺序与推理并行性。更多合法生成顺序不必然带来更大的实际解空间覆盖。

## 来源定位

s1：第3–5页，模型与训练目标。s2：摘要、任务分类与多样性评估。s3：第1–3页，生成顺序与探索分析。
