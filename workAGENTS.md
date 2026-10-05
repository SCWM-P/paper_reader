# Paper Reader 伴读工作要求

## 工作空间与接续

本工作空间用于文献伴读、翻译、讨论与归档。用户主要用简体中文交流；论文标题、作者、模型名与关键术语保留原文，解释采用清晰的中文。

会话开始时读取本文，按用户指定论文定位 `papers/` 中的实例，再读 `assets/reading-record.json` 与 `note.html` 接续讨论。本文暂名 `workAGENTS.md`，宿主可能需要显式加载；将其作为伴读入口。根目录 `AGENTS.md` 与 `docs/` 保存本地开发指导和开发记录。

多个 Agents 工作时按论文或明确模块分工，指定一个写入负责人合并记录与 Zotero 操作。编辑前回读当前文件和条目版本，保留用户手工修改。

## 项目结构

```text
paper_reader/
├── workAGENTS.md                     伴读 AI 工作入口
├── pyproject.toml                    Python 依赖与翻译默认参数
├── .agents/skills/zotero/             伴读运行工具、模板和第三方许可证
└── papers/
    └── Attention Is All You Need/    完整独立的文献实例
        ├── attention-is-all-you-need.pdf
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
- `translation/` 与 `assets/videos/` 在产生相应资产时创建。`others/` 用于需要额外留存的材料，创建和留存前告知用户并取得同意。笔记 JSON 的 `others` 是讨论扩展字段，可按伴读需要使用。
- 记录与引用元数据放在 `assets/`；临时翻译脚本、Zotero 操作探针、截图和日志放在本论文 `tmp/`。代码复现作为阅读产物时放在 `assets/code/`，外部执行环境留在 conda 或用户环境目录。
- `note.html` 的本地资源使用相对于论文根目录的路径，例如 `assets/figures/figure-1.png`。子目录中的页面按所在位置引用实例内部文件。整份论文目录可移动、复制和独立打开。
- `assets/reading-record.json` 中的资源路径相对于该 JSON 所在目录，例如 `figures/figure-1.png`、`videos/attention-explained.mp4`；渲染器会换算为输出 HTML 的相对路径。记录中的 `paper.file` 可用 `../attention-is-all-you-need.pdf`。
- PDF 译文保留在 translation，原文持续保留；记录来源、版本、采集时间与 PDF 物理页序。目录迁移后更新引用并打开页面确认资源加载。

## Python 环境

使用独立 conda 环境 `paper_reader`。在工作空间根目录执行：

```bash
# 首次创建环境，Python 3.11 兼容当前 pdf2zh 和可选视频工具。
conda create -n paper_reader python=3.11 pip
# 每次工作先激活，再按 pyproject.toml 安装运行依赖。
conda activate paper_reader
python -m pip install -e .
# 检查 CLI 和依赖是否可用。
pdf2zh --help
python -m pip check
```

环境通过 `pyproject.toml` 安装原版 PDFMathTranslate 的 `pdf2zh==1.9.11`、PyMuPDF 1.25.2，以及 `tencentcloud-sdk-python-tmt==3.1.70`。腾讯云新 SDK 移除旧翻译 API 导致导入失败，详见 [上游 issue #1167](https://github.com/PDFMathTranslate/PDFMathTranslate/issues/1167)；固定版本与[上游当前依赖配置](https://github.com/PDFMathTranslate/PDFMathTranslate/blob/main/pyproject.toml)一致。升级时先查官方发布与兼容约束，在独立环境用目标论文验证。

视频源码需要时使用 `python -m pip install -e ".[video]"`；FFmpeg、TeX 和中文字体属于额外系统依赖。视频字体可通过 ATTENTION_FONT 指定；默认探测 Windows Microsoft YaHei、macOS PingFang SC 和 Linux Noto Sans CJK SC。Windows 用本篇 voice.ps1 生成旁白，其他平台可提供同名的 00.wav–08.wav。`pdf2zh-next` 是另一套 CLI 与依赖体系，选用时单独建环境并参考其文档。`pyproject.toml` 的 `tool.paper-reader` 段记录伴读默认参数，由 AI 读取并传给 CLI。

## 工作流工具

### Zotero SKILL

先读 [.agents/skills/zotero/SKILL.md](.agents/skills/zotero/SKILL.md)。核心读写、索引和 HTML 渲染使用 Python 标准库；本机 Zotero 10+ 的 Local API 承接文库操作。优先支持当前稳定版，并通过 doctor 探测实际能力。

```bash
# 从工作空间根目录检查正在运行的本机 Zotero。
python -B .agents/skills/zotero/scripts/zotero_ops.py doctor
# 查文献和历史结论，再回读完整条目或笔记。
python -B .agents/skills/zotero/scripts/zotero_ops.py recall "multi-head attention" --limit 5
```

用户提出保存、归档或整理时完成相应写入。归档先检索重复条目，优先保留 Connector 采集的完整元数据；新文献采集官方 DOI、arXiv 或出版网页信息，核对作者顺序、版本、期刊/会议、卷期页和标识符。需要补齐时可按宿主能力派出只读采集 sub-agent，主 Agent 合并登记；缺项至少留资源 URL 和待补全说明。

GB/T 7714 与 BibTeX 均依赖准确引用元数据，按用户/机构要求选择样式与版本。凭据、本机索引和 Zotero 数据库留在用户配置或 Zotero 目录。读写通过 API，写后回查；未知写入结果先查询实际状态。保存前检查回收站状态，恢复条目按用户明确意图处理。

### pdf2zh 翻译

英文文献按用户阅读偏好提供简体中文翻译，工具来自 [PDFMathTranslate](https://github.com/PDFMathTranslate/PDFMathTranslate)，使用原版 `pdf2zh` CLI，参考[官方使用文档](https://github.com/PDFMathTranslate/PDFMathTranslate/blob/main/docs/README_zh-CN.md)。

默认源为 **deepseek-flash**，密钥由环境变量 **DEEPSEEK_API_KEY** 提供。用户指定新的长期翻译源时同步更新本文及 pyproject 中的默认参数。先检查密钥是否存在和提供方是否接受模型名；凭据缺失、模型不可用或服务报错时提醒用户并说明实际状态。当前原版 DeepSeek adapter 指向 `https://api.deepseek.com/v1`；若用户的模型由其他兼容服务提供，使用 `openailiked` 及对应环境变量配置。保留用户选定模型，确认实际服务配置后开始翻译。

```bash
# 激活伴读环境；先用一页确认源、模型与版面质量。
conda activate paper_reader
pdf2zh "papers/Attention Is All You Need/attention-is-all-you-need.pdf" -s deepseek:deepseek-flash -li en -lo zh -p 1 -o "papers/Attention Is All You Need/tmp/translation-preview"
# 预览通过后翻译全文，保存单语和双语 PDF。
pdf2zh "papers/Attention Is All You Need/attention-is-all-you-need.pdf" -s deepseek:deepseek-flash -li en -lo zh -o "papers/Attention Is All You Need/translation"
# 用户接受备选源时，可用免费 Google Translate。
pdf2zh "papers/Attention Is All You Need/attention-is-all-you-need.pdf" -s google -li en -lo zh -o "papers/Attention Is All You Need/translation"
```

首次运行可能下载版面模型和字体，按系统代理或官方镜像配置网络。原文用于核对公式、术语和结论；译文辅助理解。完成后检查标题、正文、公式、图注与双语排布。记录实际服务、模型、时间、翻译范围和输出文件，服务失败时保留本论文 tmp 中的排查信息。GUI 可用 `pdf2zh -i` 按需启动。

### PDF 插图与结构化解析

用 PyMuPDF 读取页文本、定位图注并裁剪原图。矢量图采用页面区域渲染，保留箭头和文字。图号、物理页序与裁剪坐标保存在 `assets/figures/figures.json`。

```bash
# 在 paper_reader 环境执行，输出本篇论文的原图与位置记录。
python -B .agents/skills/zotero/scripts/pdf_figures.py "papers/Attention Is All You Need/attention-is-all-you-need.pdf" --out "papers/Attention Is All You Need/assets/figures" --pages 3 4
```

打开图片确认分图、标签和边界；关键原图直接插入笔记。复杂多栏或扫描件可在独立环境按需选用 Docling、Marker 或 MinerU，先用该论文检查质量和资源需求。

## 阅读记录与页面

核心内容为 `metadata`、`summary`、`highlights`、`Q & A`。metadata 尽量保留采集管线产出的字段，至少包含 title 和 author；note_author 表示记录者。summary 简短表达核心结论和自己的理解；highlights 说明主要价值和贡献；Q & A 持续记录实际用户讨论。尚未讨论的问答填空数组，AI 补充问题标明来源。

JSON 的 `others` 根据交流扩展代码、视频、原图、交互图、证据和阅读计划。区分原文结论与自己的推论，写明阅读范围和证据位置。默认 modern 模板提供元数据卡片、贡献卡片、问答检索与折叠、KaTeX 公式、图像放大和交互模块；也支持替换 HTML/CSS 与 AI 编写的新模块。数学字体使用随模板分发的 KaTeX 衬线字体；保持字形度量、上下标与根号定位，独立公式放大显示，多行公式适当增加行间距，长公式在手机端横向滚动。

```bash
# 导出论文主入口；图片和视频按实例内部相对路径加载。
python -B .agents/skills/zotero/scripts/html_note.py --file "papers/Attention Is All You Need/assets/reading-record.json" --out "papers/Attention Is All You Need/note.html" --asset-mode relative --force
# 用户要求登记到正常 Zotero 条目时，生成资源内嵌版并保存附件与原生摘要。
python -B .agents/skills/zotero/scripts/zotero_ops.py html-note PAPER_KEY --file "papers/Attention Is All You Need/assets/reading-record.json" --out "papers/Attention Is All You Need/tmp/zotero-note.html" --apply
```

两种页面共享记录与模板。本地入口引用本篇资产；Zotero 附件内嵌公式字体、图片和视频，原生摘要提供一键打开链接并支持跨会话 recall。更大视频按用户选择保留观看入口。保存后用真实页面检查公式、原图、问答、交互和视频；移动论文目录后资源继续加载。

Attention 样例包含原文、两张原图、四个核心模块、注意力交互与约五分钟教学视频，视频源码和章节字幕与成片共同留在 `assets/videos/`。原文及出版元数据的版权归原作者/出版方；展示与分享遵循来源许可。

## 使用资产与 Git

版本库跟踪 `workAGENTS.md`、`pyproject.toml`、运行用 Zotero skill 和 `papers/` 中的阅读产物及必要源码。`docs/`、根 AGENTS.md、dist、根 tmp、论文 tmp、虚拟环境、缓存、凭据与 `.gitignore` 保留在本机并忽略。新增阅读产物可检查后暂存；提交、推送和对外分享按用户本次授权执行。

本机忽略规则由 `.gitignore` 维护，按用户要求该文件自身也不提交。新克隆工作空间时先在 `.git/info/exclude` 或本机 `.gitignore` 重建上述排除规则；Git 会自动忽略空目录，在新论文工作时按协议创建 figures 与 tmp。
