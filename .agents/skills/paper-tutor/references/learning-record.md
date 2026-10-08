# 单卡点记录格式（version 1）

在阅读 record 的 `others` 模块添加 `learning` 对象。原有记录不用迁移。一次记录对应一个原文锚点，概念及先修只服务这个锚点。

| 字段 | 用途 |
| --- | --- |
| `version` | 固定 1，可省略 |
| `anchor` | 必须含 `locator`（章节/式号）和 `excerpt`（原句/公式）；可含 `page`（从 1 开始的 PDF 物理页）、`url` |
| `reader` | `starting_point` 写当前已知基础；`basis` 为 `assumed`（暂定）或 `user_report`（用户自述） |
| `goal` | 本次要读懂什么 |
| `budget` | 默认 `max_depth: 2, max_nodes: 5`；合法范围分别为 1–3、1–8 |
| `concepts` | 小范围概念列表，推荐按先修到原文概念的顺序保存；允许 `[]` 表示暂未展开 |
| `unresolved` | 可选，人工保留的未解决项文本列表 |
| `next` | `action` 为 `check` / `continue_prerequisite` / `return_to_paper`；`reason` 说明下一步 |

概念含唯一 `id`（小写字母开头，最多 64 个字母/数字/连字符）、`term`、`state`；可含 `depends_on`（本条卡点内的 id 列表）、`lesson`、`check`、`revision`（状态纠正原因）。

- `state` 仅为 `unknown`、`uncertain`、`explained`、`confirmed`、`skipped`。
- `lesson` 是带来源类型的内容块列表。每块含 `kind`（`paper/background/teaching/inference`）、`title`、`text`。`paper/background` 还须含 `locator`；`url` 可选。`explained` 必须有讲解内容。
- `check` 含 `question`、`reference_answer`，`assessment` 默认为 `pending`。有真实作答后可补 `user_answer`、`feedback`，评价为 `retry` 或 `pass`。这两种评价必须有用户回答与反馈；`confirmed` 必须对应 `pass`。旧评价可保留，但当前状态可以撤回。
- 原文、起点、目标、下一步以及必需文本均不能为空。页数和预算不接受布尔值。URL 为无凭据的 HTTP(S)/Zotero 地址。缺失锚点等格式错误会阻止导出。
- 缺先修、循环、超节点/深度预算属于未解决的教学路线，仍可导出并返回原文。渲染只展开前 `max_nodes` 个概念。解释中不能继续递归这些卡点。
- `issues` 是校验器重算的展示字段，不手工维护。纠正状态后重新渲染会刷新它；`unresolved` 中的人工记录应按实际讨论更新。页面不会写学习状态到 localStorage，也不会因自测折叠/展开更改记录。

无需作答也可把 `next.action` 设为 `return_to_paper`。如用户跳过某概念，将它标为 `skipped`；返回不代表它已经理解。记录需要补课的概念时可以先不写 lesson/check，避免把每个先修都展开成长讲义。

从工作区根目录生成可审阅的 Attention 示范页（不改原样例）：

```bash
python -B .agents/skills/zotero/scripts/html_note.py \
  --file .agents/skills/paper-tutor/assets/attention-prerequisites.json \
  --out "papers/EXAMPLE/Attention Is All You Need/prerequisite-demo.html" \
  --asset-mode relative
```

示范 JSON 的 `paper.file` 指向本仓库现有 Attention 原文，路径相对于示范 JSON；独立使用示范时改成对应论文实例路径，或删去该字段保留官方来源 URL。实际用户记录继续放在论文 `assets/`，例如 `paper.file: "../paper.pdf"`。

本地检查（标准库，无 Zotero/LLM 调用）：

```bash
python -B -m unittest discover -s tests -v
```
