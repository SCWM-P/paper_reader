---
id: c_92b75394-f417-46ce-978e-2a7ce4f24c76
type: concept
title: KV cache
tags:
- 计算系统
- kv-cache
related: []
created: '2026-10-19T10:49:32.577119+00:00'
updated: '2026-10-19T10:49:32.577119+00:00'
domain: 计算系统
scope: 采用键值注意力的增量解码
definition: 保存历史 token 的键和值，使自回归解码能够复用既有计算结果。
aliases:
- cache
sources:
- source_id: s1
  record: papers/DEMO/Periodic Weak Spots- Phase Sensitivity from Chunked KV-Cache Compression/assets/reading-record.json
  locator: PDF 物理第 1 页
  url: https://arxiv.org/abs/2609.36322
consensus:
  status: verified
  source_refs:
  - s1
relations: []
question_refs: []
---
## 定义

保存历史 token 的键和值，使自回归解码能够复用既有计算结果。

## 适用范围

采用键值注意力的增量解码。

## 来源

来源 s1：PDF 物理第 1 页。该来源用于定位本文讨论的术语；论文中的特定实验结论不自动成为概念定义。
