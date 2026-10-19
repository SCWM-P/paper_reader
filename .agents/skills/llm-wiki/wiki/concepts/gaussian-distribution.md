---
id: c_59c8d0f9-72f1-4a34-97ef-53c0951afc53
type: concept
title: 高斯分布
tags:
- 数学与统计
- gaussian-distribution
related: []
created: '2026-10-19T10:49:32.577119+00:00'
updated: '2026-10-19T10:49:32.577119+00:00'
domain: 数学与统计
scope: 实数向量上的正态分布
definition: 由均值与协方差确定的连续概率分布，常用于生成模型的潜变量先验。
aliases:
- Gaussian
sources:
- source_id: s1
  record: papers/DEMO/Toward Multimodal Image-to-Image Translation/assets/reading-record.json
  locator: PDF 物理第 3 页
  url: https://arxiv.org/abs/1711.11586
consensus:
  status: verified
  source_refs:
  - s1
relations: []
question_refs: []
---
## 来源

来源 s1：PDF 物理第 3 页。该来源用于定位本文讨论的术语；论文中的特定实验结论不自动成为概念定义。

一维情形：

$$p(x)=\frac{1}{\sqrt{2\pi\sigma^2}}\exp\left(-\frac{(x-\mu)^2}{2\sigma^2}\right),\quad \sigma^2>0.$$
