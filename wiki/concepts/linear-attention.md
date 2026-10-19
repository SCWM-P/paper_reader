---
id: c_d7acaf7a-c529-4165-9f6e-f8b9292b6fe2
type: concept
title: 线性注意力
tags:
- 机器学习
- linear-attention
related:
- c_b677a187-1b09-4018-991e-a9cc0f588b24
- c_6c6f6b47-945b-4d77-aad6-07cbd5e5cec5
created: '2026-10-19T10:49:32.577119+00:00'
updated: '2026-10-19T10:49:32.577119+00:00'
domain: 机器学习
scope: 序列长度方向的计算或存储复杂度优化
definition: 通过重排注意力计算或递归状态更新，避免显式构造完整的序列两两注意力矩阵。
aliases:
- linear attention
sources:
- source_id: s1
  record: papers/DEMO/Kimi Linear- An Expressive, Efficient Attention Architecture/assets/reading-record.json
  locator: PDF 物理第 1 页
  url: https://arxiv.org/abs/2510.26692
consensus:
  status: verified
  source_refs:
  - s1
relations: []
question_refs: []
---
## 定义

通过重排注意力计算或递归状态更新，避免显式构造完整的序列两两注意力矩阵。

## 适用范围

序列长度方向的计算或存储复杂度优化。

## 来源

来源 s1：PDF 物理第 1 页。该来源用于定位本文讨论的术语；论文中的特定实验结论不自动成为概念定义。

## 相关知识

[[attention|注意力机制]] · [[recurrent-neural-network|循环神经网络]]
