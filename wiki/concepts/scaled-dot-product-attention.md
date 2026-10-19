---
id: c_41af3ce1-a069-41d0-bfd1-321b0dd36737
type: concept
title: 缩放点积注意力
tags:
- 机器学习
- scaled-dot-product-attention
related:
- c_f61fc709-5dad-4843-8f88-e915ced93d02
- c_c268381c-6d1c-464c-ae6a-04b135aafd1c
created: '2026-10-19T10:49:32.577119+00:00'
updated: '2026-10-19T10:49:32.577119+00:00'
domain: 机器学习
scope: Transformer 的 softmax 注意力
definition: 以查询和键的点积构造分数，按键维度平方根缩放，经 softmax 后加权求和值。
aliases:
- scaled dot
sources:
- source_id: s1
  record: papers/EXAMPLE/Attention Is All You Need/assets/reading-record.json
  locator: PDF 物理第 4 页
  url: https://arxiv.org/abs/1706.03762
consensus:
  status: verified
  source_refs:
  - s1
relations:
- type: uses
  target_id: c_f61fc709-5dad-4843-8f88-e915ced93d02
  scope: 标准缩放点积注意力的权重归一化
  source_refs:
  - s1
question_refs: []
---
## 定义

以查询和键的点积构造分数，按键维度平方根缩放，经 softmax 后加权求和值。

## 适用范围

Transformer 的 softmax 注意力。

## 来源

来源 s1：PDF 物理第 4 页。该来源用于定位本文讨论的术语；论文中的特定实验结论不自动成为概念定义。

$$
\operatorname{Attention}(Q,K,V)=\operatorname{softmax}(QK^\top/\sqrt{d_k})V
$$

## 相关知识

[[softmax|Softmax]] · [[multi-head-attention|多头注意力]]
