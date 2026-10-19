# Paper Reader 伴读

## 工作空间简介

- 本工作空间用于AI伴读的文献阅读、翻译、讨论与归档
- 用户主要用简体中文交流，论文标题、作者、模型名与关键术语保留原文，仅`<think></think>`（及其等价物）内的思考内容允许使用英文
- 本项目原始仓库链接为 [Github Paper Reader](https://github.com/SCWM-P/paper_reader)，项目支持通过托管代码仓库实现个人文献与知识库的跨设备云同步

## 初始化

如果是一段新的会话，请依次完成以下初始化：

### [1] 初始化 skills
本项目的技能位于`.agents/skills/`。
检查 harness 是否能发现该目录；可以则直接加载并阅读相关 `SKILL.md`。否则将需要的技能复制到 harness 支持的配置目录，保留项目内的原始技能，已有配置先合并而不覆盖，然后加载新添加的 skills 并阅读`SKILL.md`，并将该 harness 配置目录添加到`.gitignore`中。
完成后打印一条告知 `[INFO] 初始化skills | 完成...`

### [2] 学习 `papers/` 下的最佳实践
定位`papers/EXAMPLE/Attention is all you need/`为伴读文献实例的最佳实践，读 `assets/reading-record.json` 了解伴读文献实例的期望交付物形式与内容
完成后打印一条告知 `[INFO] 最佳实践学习 | 完成...`

### [3] 检查并配置环境依赖
检查本机虚拟环境工具，检查虚拟环境 `paper_reader` 可用性，依据 `pyproject.toml` 检查 `paper_reader` 的依赖项是否齐全版本正确，若缺失请提醒用户。
完成后打印一条告知 `[INFO] 环境检查 | 完成...`

### [4] 检查 git 远端仓库和分支

如果用户需要启用借助代码托管仓库的跨设备文献与知识库同步功能，请检查 git 当前的代码仓库指向，**禁止指向**原始仓库 `https://github.com/SCWM-P/paper_reader`。
请在用户授权下 fork 一份到用户的个人代码仓库，然后指向该个人代码仓库用于同步个人资料，必要时可在用户同意下将仓库可见性设置为`Private`。

### [5] 同步仓库的云端`papers/`路径

如果 [4] 已就绪，可继续进行以下配置：
请从中采用合并方式拉取最新 `papers/` 路径下，用户在其他设备处阅读完成的文献实例/正在阅读的实例，不要影响在本地其他暂未上传同步的文献实例。
完成后打印一条告知 

```markdown
[INFO] 文献云端同步 | 完成，无同步新增的文献...
```

或者

```markdown
[INFO] 文献云端同步 | 完成，新增同步的文献：
paper 1 metadata
paper 2 metadata
...
```

如果 [4] 的配置不可用，请跳过本初始化，然后打印：
```markdown
[WARNING] 文献同步 ｜ 未就绪
```

### [6] 检查 llm-wiki 完整性并同步 wiki 资料

如果 [4] 已就绪，可继续进行以下配置：
读取 [llm-wiki SKILL](.agents/skills/llm-wiki/SKILL.md)。知识目录由 pyproject.toml 选择：普通工作区默认 `.runtime/llm_wiki/`，demo 使用可跟踪的 `wiki/`。先执行 `paper wiki list` 浏览概念与实体，再用 query 定向读取。实际问答及理解证据只保存在论文 Q & A。

首次使用且运行目录不存在时，用现有 Python 环境执行：

```bash
paper wiki init
```

记录统一使用当前无版本号契约，不保留并行格式。技能或 Python 包缺失时，列明缺项并跳过，不声称初始化成功。

已有入口时执行基本文件与引用检查：

```bash
paper wiki check
```

发现错误时保留原记录，报告具体路径。检查通过后按当前论文、领域与问题检索并回读相关记录。

如果 [4] 的配置不可用，请跳过本初始化，然后打印：
```markdown
[WARNING] 知识库同步 ｜ 未启用
```

## 受控语言风格

有经验表明，在专业性强的语境中，采用 ASD-STE100 风格的输出可以提高可读性与准确性，进而提高人机交互的效率。ASD-STE100 是航空航天与国防行业制定的一项受控语言标准，考虑到其要求专为英文语境下优化设计，且包含大量飞行器专业相关的要求，在这里我们主要采纳其语言风格和严谨表述，以 **受控语言风格(Contoled Language Style)** 提供输出，力求做到 70%～80% 的 ASD-STE100 。

### 适用范围

适用于所有面向用户阅读的文字，包括但不限于：

- 用户的直接交流
- 向用户做概念解释
- 归档供用户审查的资料
- 任务结果汇报与进度说明
- 请用户决定或确认的问题
- 多项工作的总结，例如任务清单、issue、变更
- 提交的 PR，commit message

**不适合**的情况：

- 创意输出，风格写作
- 代码风格与代码注释
- 有明确来源的文本
- 日志、命令、报错
- 面向 LLM 的机器对话，例如与 Sub-Agent 的对话；多 Agent 协作下的 Agent 之间的交流

### 执行细则

请参考[CLS SKILL](.agents/skills/cls/SKILL.md)（Controled Language Style Skill）中的相关说明和参考资料。

## 项目结构

```text
paper_reader/
├── AGENTS.md                         伴读 AI 通用上下文注入口
├── pyproject.toml                    Python 依赖与翻译默认参数
├── .agents/skills/zotero/            伴读运行工具、模板和第三方许可证
├── .agents/skills/llm-wiki/          知识维护协议、Python 核心与浏览器 GUI
├── frontend/                       React/TypeScript 前端源码与构建配置
├── wiki/                           demo 公共知识（由项目配置选择，可入 Git）
├── .runtime/                        本地运行数据（整体不入 Git）
│   ├── zotero_agent/                授权凭据和可重建索引
│   └── llm_wiki/                    锁与服务登记；普通配置也在此保存知识库
└── papers/                           储存文献实例
       └──EXAMPLE    文献实例的最佳实践样例，请勿删除
            └── Attention Is All You Need/             完整独立的文献实例
                ├── attention-is-all-you-need.pdf      文献本体
                ├── note.html                阅读主入口
                ├── assets/
                │   ├── reading-record.json  可持续编辑的结构化阅读记录
                │   ├── metadata/            采集元数据与出版方 BibTeX
                │   ├── figures/             原文插图、图号、页序和裁剪信息
                │   └── videos/              按需保存视频、绘制源码、旁白和字幕
                ├── translation/             按需保存译文和双语 PDF
                └── tmp/                     本论文的探针、日志和处理过程文件
```

### 文献实例目录协议

- 未分类论文直接放在 `papers/<文章标题>/`；按用户需求分类时可位于 `papers/` 的更深层目录。目录名保留标题，跨平台时替换 Windows 禁用字符和结尾点/空格；必要时用年份或版本区分同名论文。
- 原始 PDF、`note.html`、`assets/figures/` 和论文专用 `tmp/` 为基本结构。没有图的论文保留 figures 目录；受访问限制无法取得 PDF 或关键图时，说明缺项与来源，继续可完成的阅读。
- `translation/` 与 `assets/videos/` 在产生相应资产时创建。
- 如需要额外留存资料，创建和留存前告知用户并取得同意。笔记 JSON 的 `others` 是讨论扩展字段，可按伴读需要使用。
- 记录与引用元数据放在 `assets/`。
- 临时翻译脚本、操作探针、截图和日志放在本论文 `tmp/`。
- 如有代码复现，作为阅读产物时放在 `assets/code/`。
- `note.html` 的本地资源使用相对于论文根目录的路径，例如 `assets/figures/figure-1.png`。子目录中的页面按所在位置引用实例内部文件。整份论文目录可移动、复制和独立打开。
- `assets/reading-record.json` 中的资源路径相对于该 JSON 所在目录，例如 `figures/figure-1.png`、`videos/attention-explained.mp4`；渲染器会换算为输出 HTML 的相对路径。记录中的 `paper.file` 可用 `../attention-is-all-you-need.pdf`。
- PDF 译文保留在 translation，原文持续保留；记录来源、版本、采集时间与 PDF 物理页序。目录迁移后更新引用并打开页面确认资源加载。
- 推荐的单个文献实例文件夹大小不超过 30MB，如果有超过请经过用户授权。

## Python 环境

推荐使用 conda 管理虚拟环境 `paper_reader`。`pyproject.toml` 的 `tool.paper-reader` 段记录伴读默认参数，由 AI 读取并传给 CLI

### 基础环境
在工作空间根目录执行：

```bash
# 首次创建环境，Python 3.11 兼容当前 pdf2zh 和可选视频工具。
conda create -n paper_reader python=3.11
# 每次工作先激活，再按 pyproject.toml 安装运行依赖。
conda activate paper_reader
python -m pip install -e ".[gui,pdf,translation]"
# 安装后可直接使用统一入口；保持在工作空间根目录运行。
paper --help
paper check "papers/EXAMPLE/Attention Is All You Need"
pdf2zh --help
```

基础安装 `python -m pip install -e .` 仅安装核心 CLI。`gui`、`pdf`、`translation`、`video` 按需启用。

浏览器知识工作台：

```bash
paper wiki init
paper wiki serve --port 8765  # 直接访问 http://127.0.0.1:8765/
paper wiki status
paper wiki stop  # 或在启动终端按 Ctrl+C
```

服务默认只监听 127.0.0.1。打开终端输出的完整链接。GUI 和 CLI 共享保存服务；知识记录使用无版本号的当前契约，不建立历史副本。

### 教学视频拓展
视频源码需要时执行：

```bash
python -m pip install -e ".[video]"
```

注意事项：
- FFmpeg、TeX 和中文字体属于额外系统依赖。
- 视频字体可通过 ATTENTION_FONT 指定；默认探测 Windows Microsoft YaHei、macOS PingFang SC 和 Linux Noto Sans CJK SC。

## 工作流工具

### 论文伴读与知识维护

论文卡点解释、系统讲解、跨论文知识库构建使用 [llm-wiki SKILL](.agents/skills/llm-wiki/SKILL.md)。新会话用 `paper wiki list` 浏览，再用 `paper wiki query` 按当前论文、领域和原问题查询，回读主记录与实际证据。AI 根据真实理解证据选择讲解起点；知识条目数量不代表用户掌握程度。

公共共识概念保存在 `concepts/c_<UUID>.md`，例如高斯分布、注意力机制、多组学、麦克斯韦方程组。定义必须可跨语境复用；比较和综合页面也遵守此边界。所有实际提问、答复、论文专属定义和理解证据保留在该论文 `Q & A`。每次提问保留稳定 q_ID 和原问，追问按 ID 关联。概念只能引用论文问答，不承接个人讨论。理解判断及其依据保存在论文问答；提问过、讲解过和用户自述不等于真实理解表现。

在伴读中自然更新本地记录，无需逐概念请求登记。缺少论文主记录时说明尚未归档，不建立暂存问题库；保存后按 ID 回读。用户可以纠正记录、说明遗忘或跳过自测。表达遵循 CLS，文件契约与保存方法见 llm-wiki 的 references。

### Zotero SKILL

先读 [Zotero SKILL](.agents/skills/zotero/SKILL.md)。核心读写、索引和 HTML 渲染使用 Python 标准库；本机 Zotero 10+ 的 Local API 承接文库操作。优先支持当前稳定版，并通过 doctor 探测实际能力。

```bash
# 从工作空间根目录检查正在运行的本机 Zotero。
paper zotero doctor
# 查文献和历史结论，再回读完整条目或笔记。
paper zotero recall "multi-head attention" --limit 5
```

用户提出保存、归档或整理时完成相应写入。归档先检索重复条目，优先保留 Zotero Connector 采集的完整元数据；新文献采集官方 DOI、arXiv 或出版网页信息，核对作者顺序、版本、期刊/会议、卷期页和标识符。需要补齐时可按宿主能力派出只读采集 sub-agent，主 Agent 合并登记；缺项至少留资源 URL 和待补全说明。

### pdf2zh 翻译

英文文献按用户阅读偏好提供简体中文翻译，工具来自 [PDFMathTranslate](https://github.com/PDFMathTranslate/PDFMathTranslate)，使用原版 `pdf2zh` CLI。

`pyproject.toml` 的 `tool.paper-reader` 记录了默认翻译源，若用户指定新的长期翻译源时同步更新本文及 pyproject 中的默认参数。

先检查密钥是否存在和提供方是否接受模型名；凭据缺失、模型不可用或服务报错时提醒用户并说明实际状态，保留用户选定的新模型，确认实际服务配置后开始翻译。

```bash
# 激活伴读环境；先用一页确认源、模型与版面质量。
conda activate paper_reader
pdf2zh "path/to/your/paper.pdf" -s deepseek:deepseek-flash -li en -lo zh -p 1 -o "path/to/your/preview"
# 预览通过后翻译全文，保存单语和双语 PDF。
pdf2zh "path/to/your/paper.pdf" -s deepseek:deepseek-flash -li en -lo zh -o "path/to/your/translation"
# 用户接受备选源时，可用免费 Google Translate。
pdf2zh "path/to/your/paper.pdf" -s google -li en -lo zh -o "path/to/your/translation"
```

### PDF 插图与结构化解析

用 PyMuPDF 读取页文本、定位图注并裁剪原图。矢量图采用页面区域渲染，保留箭头和文字。图号、物理页序与裁剪坐标保存在 `assets/figures/figures.json`。

```bash
# 在 paper_reader 环境执行，输出本篇论文的原图与位置记录。
paper figures "path/to/your/paper.pdf" --out "path/to/your/<paper>/assets/figures" --pages 3 4
```

打开图片确认分图、标签和边界；关键原图直接插入笔记。复杂多栏或扫描件可在独立环境按需选用 Docling、Marker 或 MinerU，先用该论文检查质量和资源需求。

## 阅读记录与页面

核心内容为 `metadata`、`summary`、`highlights`、`Q & A`，为 **必含项**，若文献实例存在缺失/降级意味着文献没有阅读完，需要**提醒用户** 。

- `metadata` 尽量保留采集管线产出的字段，至少包含 title 和 author；note_author 表示记录者。
- `summary` 简短表达核心结论和文献的理解，必须由伴读AI与用户交流后得出，伴读AI仅可草拟内容并标注为**降级**；
- `highlights` 说明主要价值和贡献，可由用户/伴读AI形成；
- `Q & A` 保留每条实际原问，answer 精简整合实际答复。相关话题与追问通过稳定 ID 关联，不用摘要替换原问；尚未讨论时填空数组。旧记录无法确认逐字原问时标记 `question_form: legacy_recorded`；

阅读记录必须包含 `type: source`。每条实际问答必须有稳定 `id: q_<UUID4>` 和 question_form。HTML 对应 `note.html#qa-q_<UUID4>`，重排问答不改变该入口。

完整性由四个必要模块分别检查，`others` 不参与检查：

| 模块 | 必要性与检查 |
| --- | --- |
| `metadata` | 必要，非空 |
| `summary` | 必要，非空；标记降级时输出 WARNING |
| `highlights` | 必要，非空 |
| `Q & A` | 必要，空数组输出 WARNING；非空通过 |
| `others` | 非必要，不检查 |

降级使用独立的 `completeness` 状态表，保留模块现有内容格式。例如：

```json
"completeness": {"summary": {"status": "degraded"}}
```

状态表中每个模块仅有 `status`，值为 `complete` 或 `degraded`；模块名与记录一致，包括 `Q & A`。
省略状态时按内容检查。任何必要模块显式标记 `degraded` 都会输出 WARNING。
缺少必要模块或必要内容为空输出 ERROR；`Q & A` 字段存在但为空时只输出 WARNING。
检查结果由各模块汇总，优先级为 ERROR、WARNING、OK。

```bash
paper check "papers/EXAMPLE/Attention Is All You Need"
paper check "papers/EXAMPLE/Attention Is All You Need/assets/reading-record.json" --json
```

报告只列四个模块。退出码 0 表示无错误（可有 WARNING），1 表示必要模块错误，2 表示文件、JSON 或命令错误。
WARNING 会在阅读页面和 Zotero 摘要中提示。`check` 不检查 PDF、图片或 `others` 中的扩展内容。

JSON 的 `others` 根据交流扩展代码、视频、原图、交互图、证据和阅读计划。区分原文结论与自己的推论，写明阅读范围和证据位置。默认 modern 模板提供元数据卡片、贡献卡片、问答检索与折叠、KaTeX 公式、图像放大和交互模块；也支持替换 HTML/CSS 与 AI 编写的新模块。

```bash
# 以EXAMPLE最佳实践为例
# 导出论文主入口；图片和 视频按实例内部相对路径加载。
paper render --file "papers/EXAMPLE/Attention Is All You Need/assets/reading-record.json" --out "papers/EXAMPLE/Attention Is All You Need/note.html" --asset-mode relative --force
# 用户要求登记到正常 Zotero 条目时，生成资源内嵌版并保存附件与原生摘要。
paper zotero html-note PAPER_KEY --file "papers/EXAMPLE/Attention Is All You Need/assets/reading-record.json" --out "papers/EXAMPLE/Attention Is All You Need/tmp/zotero-note.html" --apply
```

保存后用真实页面检查公式、原图、问答、交互和视频。

## Git 跟踪规范

- 版本库跟踪 `AGENTS.md`、`pyproject.toml`、运行用 Zotero skill 和 `papers/` 中的阅读产物及必要源码。
- `.gitignore`维护工作目录的忽略规则，如果不存在请重建。`.gitignore`应该包含自身，包含所有(各级)缓存文件如`__pycache__`, `.vscode`, `.DS_Store`等, 包含 harness 配置目录如 `.codex`, `.claude`, `.dsh`等，以及工作目录运行数据 `.runtime/`。
- 新增阅读产物可检查后暂存；提交、推送同步到远端仓库按用户本次授权执行。
- 协议、模板或读写器变更时，必须按最新 schema 更新 EXAMPLE 的记录与页面，并在提交前完成正式命令和真实页面验收。
- 文件资产只保留当前格式，不添加独立版本号或兼容副本；项目版本未经授权不得递增。开发参考目录 ref_repository 不进入 Git 跟踪或提交。
