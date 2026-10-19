---
id: c_b2ea3f97-e22f-4cc7-85e5-4e6cfeaeb5b6
type: concept
title: 变分自编码器
tags:
- 机器学习
- variational-autoencoder
related:
- c_016849a8-6205-4573-8be3-b1d576203015
- c_59c8d0f9-72f1-4a34-97ef-53c0951afc53
created: '2026-10-19T10:49:32.577119+00:00'
updated: '2026-10-19T10:49:32.577119+00:00'
domain: 机器学习
scope: 潜变量概率生成模型
definition: 通过近似后验与解码器联合学习潜变量生成模型，使用变分目标进行训练。
aliases:
- variational
sources:
- source_id: s1
  record: papers/DEMO/Toward Multimodal Image-to-Image Translation/assets/reading-record.json
  locator: PDF 物理第 2 页
  url: https://arxiv.org/abs/1711.11586
consensus:
  status: verified
  source_refs:
  - s1
relations:
- type: uses
  target_id: c_016849a8-6205-4573-8be3-b1d576203015
  scope: 潜变量生成模型的概率建模
  source_refs:
  - s1
question_refs: []
---
## 定义

通过近似后验与解码器联合学习潜变量生成模型，使用变分目标进行训练。

## 适用范围

潜变量概率生成模型。

## 来源

来源 s1：PDF 物理第 2 页。该来源用于定位本文讨论的术语；论文中的特定实验结论不自动成为概念定义。

## 相关知识

[[latent-variable|潜变量]] · [[gaussian-distribution|高斯分布]]
