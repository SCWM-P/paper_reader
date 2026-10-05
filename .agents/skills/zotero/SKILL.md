---
name: zotero
description: Use Zotero for literature reading and archiving on Windows, macOS, and Linux. Search papers and earlier conclusions, collect citation metadata, read PDFs and annotations, organize collections and tags, save reading summaries, and register portable HTML notes with replaceable templates. Use when the user wants to work with their Zotero library or continue a previous literature reading session.
---

# Zotero 文献伴读

用 Zotero 保存文献、引用元数据与阅读记录，通过本机索引快速接续历史阅读。
支持正在运行的 Zotero 10+ 本地 API；文库读写、索引与 HTML 渲染使用 Python 3.10+ 标准库。
PDF 插图提取按需使用独立环境中的 PyMuPDF。
本目录保留 SKILL.md、scripts/ 和运行所需的 assets/。

## 入口与连接

使用宿主或项目已有的 Python 环境，在 Zotero 所在电脑执行。脚本位于本 skill 的 scripts/，
下列 python 表示已选解释器；macOS/Linux 通常用 python3。路径含空格时加引号。

```powershell
# Windows PowerShell：定位实际 skill 路径并检查本地连接
$sk = (Resolve-Path '.agents/skills/zotero/scripts').Path
python "$sk/zotero_ops.py" doctor
```

```bash
# macOS/Linux：替换为实际 skill 路径，使用已有 Python 3.10+ 环境
sk="/path/to/zotero/scripts"
python3 "$sk/zotero_ops.py" doctor
```

首次使用检查 doctor。它自动发现本机 loopback API，默认端口 23119；
可用 ZOTERO_LOCAL_API 指定地址，ZOTERO_PROFILE_DIR / ZOTERO_DATA_DIR 覆盖路径发现。
用户配置位于 Windows %APPDATA%/zotero-agent、macOS ~/Library/Application Support/zotero-agent、
Linux ${XDG_CONFIG_HOME:-~/.config}/zotero-agent；ZOTERO_AGENT_HOME 可覆盖。
凭据和可重建索引存这里；附件实际路径通过 API 获取。

```bash
# 首次写入时申请本地授权；在 Zotero 弹窗选择 Always Allow，方便多步附件保存
python zotero_authorize.py
```

已有授权直接复用。遇到 401 时申请新授权；403 检查 API 设置或文库权限；
412 重新读取当前版本；连接失败检查应用、API 设置和脚本是否与 Zotero 同机。
密钥由工具保存到用户配置目录，执行时保持私密。

## 按用户意图执行

| 意图 | 操作 |
|---|---|
| 查找论文与历史结论 | recall → show 阅读命中的完整记录 |
| 阅读论文、图表、标注 | items 定位 → show → fulltext / path |
| 归档文献 | 查已有条目 → metadata collect → 核验补齐 → import → 按需 attach |
| 保存阅读笔记 | 组织阅读 record → reading-note，需要 HTML 时用 html-note |
| 整理文库 | 读取当前分类 → collection / organize / tag |

以下示例在 scripts/ 中运行；也可使用脚本绝对路径。
默认个人库 users/0。群组先运行 groups，再在子命令前指定 --library groups/ID。
--help 可查看全部参数。

```bash
# 找到目标条目，查看作者、版本、附件与已有笔记
python zotero_ops.py items --top --q 'Attention Is All You Need'
python zotero_ops.py show PAPER_KEY
# 读取已有 PDF 的全文；多份 PDF 根据 show 的结果选择附件 key
python zotero_ops.py fulltext PDF_KEY --all
python zotero_ops.py path PDF_KEY
# 查询历史结论；自动刷新元数据、摘要、笔记和标注索引
python zotero_ops.py recall 'multi-head attention' --limit 5
```

缓存全文适合定位，公式、图表和页码回到 PDF 核对。写明实际阅读章节、版本与证据位置。
索引按实例和文库区分，存储检索所需的元数据、摘要、笔记和标注。
命中后回读笔记；离线可用 index status 找到分区，再执行
recall QUERY --offline --server-id ID，报告缓存时间。换电脑后从同步到本机的文库重建索引。

## 归档与引用元数据

用户要求归档时，默认采集元数据。先复用 Connector 或人工登记的已有条目，保留作者顺序、刊物、卷期页和人工修订。
新条目优先使用以下采集管线：

```bash
# 根据 DOI、arXiv 标识符或网页地址自动采集，保存报告与可导入元数据
python zotero_metadata.py collect 'arXiv:1706.03762' --out /path/metadata.json --item-out /path/item.json
# 已配置官方 translation-server 时复用 Zotero translators
python zotero_metadata.py collect 'https://publisher.example/paper' --translator 'http://127.0.0.1:1969' --item-out /path/item.json
# 完成来源核对后去重并保存
python zotero_ops.py import --file /path/item.json --apply
# 按需保存本机 PDF 为文献的 stored attachment
python zotero_ops.py attach PAPER_KEY --file /path/paper.pdf --apply
```

基础采集支持 Crossref DOI、arXiv Atom、网页 citation_*/Dublin Core；可选官方
[translation-server](https://github.com/zotero/translation-server) 复用 Connector 的 translators。
服务由已有配置提供。登录资源可通过用户浏览器中的 Connector 保存，然后从 Local API 找到条目。
输入官方 BibTeX/RIS 时使用 Zotero 原生导入或可信转换工具。

采集报告记录来源、时间、缺项与字段通道。核验 title、完整 creators、date、url，以及按类型适用的字段：

- 期刊：publicationTitle、volume、issue、pages/文章编号、DOI。
- 会议：proceedingsTitle、conferenceName、pages、publisher/place。
- 图书/章节：bookTitle、publisher、place、edition、ISBN。
- 预印本：repository、archiveID、版本与首次提交日期。

个人作者核对 firstName/lastName，团体作者用 name；对中文姓名、多段姓按来源登记。
正式版、预印本和修订日期分别记录，按当前阅读版本引用。
采集不足时，推荐宿主支持的只读 sub-agent 收集官方来源的缺项，主 agent 合并并登记：

> 为指定 URL/DOI 采集 Zotero 元数据，按原顺序返回作者、年份、刊物/会议、卷期页、标识符。
> 每个字段附来源，列出缺项与版本冲突；将写入留给主 agent。

最终仍有缺项，保存来源 URL、实际取得的标题、accessDate，并标记 agent:metadata-incomplete，方便后续补全。
将关键出处与缺项说明写成原生子笔记。重复候选先读取并比较作者、年份与版本，再复用相应 key。
补齐已有条目时提交小范围字段补丁，并使用 show 返回的 version。

GB/T 7714 输出按用户或机构指定的版次、顺序编码/著者年份制与 CSL 样式处理。
BibTeX 同样依赖完整元数据；citation key 用于定位引文，最终排版由相应样式完成。

## 阅读笔记与 HTML

### 本地文献实例

项目有 `workAGENTS.md` 时读取其伴读约定。通常将每篇论文独立保存在
`papers/<文章标题>/`，用户分类时可位于更深子目录。基本结构为原始 PDF、
`note.html`、`assets/figures/` 与本论文的 `tmp/`；缺失原文或关键插图时说明原因与待补齐项。
翻译产物按需放 `translation/`，教学视频、绘制源码和字幕放 `assets/videos/`，
结构化记录放 `assets/reading-record.json`，元数据与 BibTeX 放 `assets/metadata/`。
额外 `others/` 目录在告知用户并取得同意后留存。各论文资产向实例内部索引，环境依赖由外部提供。

```bash
# 论文主入口使用相对资源路径，移动整个实例目录后可继续阅读。
python html_note.py --file 'papers/Attention Is All You Need/assets/reading-record.json' --out 'papers/Attention Is All You Need/note.html' --asset-mode relative --force
```

输入资源路径相对于 record 所在目录；输出自动换算为相对于 HTML 所在论文根目录的路径。
relative 模式要求所引用的本机资源位于输出目录内。record 的 `paper.file` 可填相对于 JSON
的原文路径，如 `../attention-is-all-you-need.pdf`，`paper.pdf_key` 对应主 PDF 的 Zotero key；
本地页面优先用原文相对链接和 `#page=N` 核对图表与证据。
KaTeX、字体、模板样式与交互脚本持续内联，阅读页面可离线打开。
`html-note` 登记时使用资源内嵌版，输出可放本论文 `tmp/zotero-note.html`，保留相同记录来源。

阅读 record 使用四个核心字段。metadata 对接采集管线，有哪些字段就保留哪些；
至少含 title 和 author。summary 简短表达结论与理解，highlights 写主要学术价值，
Q & A 记录用户与 AI 的实际讨论。others 按本次伴读需要自由拓展。

```json
{
  "metadata": {"title": "论文标题", "author": ["作者姓名"], "date": "2026", "url": "https://example.org/paper"},
  "summary": "核心结论与自己的理解，尽可能简短。",
  "highlights": [{"title": "主要贡献", "content": "它解决了什么问题，带来了什么学术价值。"}],
  "Q & A": [{"question": "用户在伴读中提出的问题", "answer": "讨论形成的解答", "origin": "用户讨论"}],
  "others": [{"title": "本次继续阅读", "content": "根据讨论选择的补充内容。"}]
}
```

metadata 可直接填 collect 的完整报告或 --item-out 内容，工具保留原字段和采集出处，
从 creators 派生有序 author 名单。来源未取得作者时明确标“作者待补全”，保留待补全信息。
论文作者位于 metadata.author；记录者用 note_author。额外可填 title（笔记标题）、
recorded_at、subtitle 和 paper 对象（key/library/title/url/select_uri）。
highlights 支持文字或贡献数组；Q & A 使用 question/answer 对象数组。尚未讨论时填 []，
未完成的解答可留空以便接续。AI 自拟练习题标为“AI 补充”，用户讨论保留实际内容和上下文。
旧记录的 read_scope/evidence/limitations/questions/next_steps 可继续读取；新记录按四个核心模块组织，
范围、出处和后续问题根据需要放在 others。
区分作者结论、原文证据与自己的推论；用自然、书面的正向陈述表达。直接写阅读范围、内容和用途，省去多余的否定与转折。

```bash
# 保存可检索的原生子笔记
python zotero_ops.py reading-note PAPER_KEY --file /path/reading.json --apply
# 导出单文件 HTML；默认 modern，另有 tufte / latex / github
python html_note.py --file /path/reading.json --out /path/reading.html --theme modern
# 导出并登记 HTML 附件及带打开链接的原生摘要
python zotero_ops.py html-note PAPER_KEY --file /path/reading.json --out /path/reading.html --apply
```

默认 reading-summary 表示每篇文献的主笔记位置，可用 --slot 划分 methods 等阶段。
修改已有笔记前合并人工编辑，传 --expected-version VERSION。相同内容可复用已有记录。
HTML 登记将完整页面存为该文献的 stored HTML attachment，摘要留在原生子笔记中供索引检索。
摘要通过 zotero://open/library/items/ATTACHMENT_KEY 打开 HTML；群组使用 open/groups/ID/items/KEY。
文件同步后，附件 key 可在对应设备找到当地文件。远端文件同步状态单独报告。
完整交互在系统浏览器中阅读；可在 Zotero 的 Settings → General → Open snapshots 选择 System Default。

模板选择：modern 适合中文伴读，Tufte 适合旁注精读，LaTeX 适合学术排版，GitHub 适合工程记录。
CSS 与许可证随 assets/ 分发，输出使用系统字体并内联资源，支持离线打开。
用户也可让 LLM 自编布局：

```bash
# 替换样式、正文片段或完整骨架；按需求提供对应参数
python html_note.py --file /path/reading.json --out /path/reading.html --css-file /path/style.css --body-file /path/body.html --template-file /path/template.html
```

html-note 同样支持这些替换参数。正文文件用 HTML fragment；整页模板至少含 {{TITLE}}、{{BODY_HTML}}。
常用可选 slot 为 STYLE_CSS、TOC_HTML、META_HTML、SOURCE_LINK_HTML、DATA_JSON、BEHAVIOR_JS、LICENSE_NOTICE。
正文或完整模板可用 METADATA_HTML、SUMMARY_HTML、HIGHLIGHTS_HTML、QA_HTML、OTHERS_HTML 复用核心模块。
BEHAVIOR_JS 已包含 KaTeX、公式初始化和交互模块；整页模板在正文后插入此脚本。
高级自编脚本可单独使用 MATH_JS；搭配 STYLE_CSS 并自行调用 renderMathInElement。
保留 UTF-8、移动端 viewport、嵌入 JSON、证据和文献跳转入口。
浏览器深色等偏好在当地保存；需要持久记录的阅读内容由 JSON 与 Zotero 笔记维护。
更大的专题知识库可选 [Quarto](https://quarto.org/docs/output-formats/html-basics) 或 [MyST](https://mystmd.org/guide)。

### others：按讨论需要拓展

others 可省略，推荐使用按阅读顺序排列的模块数组；也支持文字或“名称 → 内容”对象。
每个模块用 title 命名，可填 id 供目录跳转，content 写文字或条目列表。
常用前端资源按字段选择：code/language 为带复制按钮的代码；videos 为视频播放器；
figures 为可放大原图；equations 为公式卡片；visualizations 为交互教学图；
links 为代码仓库或资源链接；evidence 为带定位信息的出处。
证据条目包含 claim/locator，可填 url 或 attachment_key/page；page 是从 1 开始的 PDF 物理页序。
这些内容按本次研究对象和用户需求选择。预设条目提供可直接使用的布局，开放扩展可使用
html 或 html_file 嵌入由伴读 AI 编写的 HTML fragment；其他命名数据也会显示。
将提取到的网页/PDF 内容组织为自己的正文，显式编写需要执行的交互代码。
需要联网的嵌入可在自编模板中按实际来源配置 media-src/frame-src/connect-src；默认模板支持离线模块。

```json
{
  "others": [
    {"id":"minimal-code", "title":"最小复现", "language":"Python", "code":"print('hello')"},
    {"id":"teaching-video", "title":"概念讲解", "videos":[{"file":"lesson.mp4", "caption":"本次教学视频"}]},
    {"id":"further-reading", "title":"讨论延伸", "content":"用户与 AI 选定的补充内容。", "html_file":"extension.html"}
  ]
}
```

本机视频支持 MP4/WebM/OGV。默认内联进 Zotero HTML；本地实例用 --asset-mode relative 引用视频文件。
长视频会增加附件体积，可按用户选择改填 url 保留观看入口。
正文、图片、视频与 html_file 的相对路径均以 record 所在目录为准。
默认模板提供元数据卡片/完整字段、贡献卡片、可检索及展开/收起的问答、代码复制和扩展模块目录。
原生摘要同步结论、贡献、问答和扩展文字，供后续 recall 检索；图像和交互保存在完整 HTML。

### 公式、插图与交互阅读

默认模板内置 [KaTeX](https://katex.org/docs/autorender.html) 0.19.0：行内用 `\(...\)`，独立公式用 `\[...\]`；也支持 `$...$` / `$$...$$`。
普通美元金额转义为 `\$`。JSON 中反斜线写成 `\\`。脚本、CSS 与 WOFF2 字体随 skill 分发，
导出时全部内联，离线可显示公式；输出含 MathML。数学排版保留 KaTeX 的衬线字形与上下标度量，
独立公式适当放大，多行公式可用 `\\[0.45em]` 增加行间距。调整模板时保留数学字体与伸缩 SVG 的定位规则，
用正文衬线字体配合数学字体；长公式在移动端横向滚动。公式原文要回到 PDF 核对，特别是转置、下标、维度和 mask。

在 others 中选择原图、公式与交互模块：

```json
{
  "others": [{"title":"论文原图", "figures": [{
    "file": "figures/figure-1.png", "caption": "Figure 1 · 主架构",
    "alt": "编码器、解码器与交叉注意力连接", "explanation": "沿箭头阅读数据流。",
    "attachment_key": "PDF_KEY", "page": 3
  }]}, {"title":"公式与张量", "equations": [{
    "title": "缩放点积注意力",
    "latex": "\\operatorname{softmax}(QK^{\\mathsf T}/\\sqrt{d_k})V",
    "explanation": "softmax 沿键的位置逐行计算。"
  }]}, {"title":"交互计算与架构", "visualizations": ["attention", "transformer"]}]
}
```

file 相对于 record JSON 所在目录；支持 PNG/JPEG/WebP。Zotero 版图片作为 data URI 内嵌 HTML；
本地实例 relative 模式引用 assets/figures 中的实际文件。
figure 保留图号、原始页序、替代文本和解读；点击放大，PDF 链接提供核对入口。
优先插入关键架构图和支撑结论的图表。取图困难时保留出处，并记录待提取内容。

本机提取优先使用 [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/recipes-images.html)：

```bash
# 在已有 PyMuPDF 环境中执行；按图注和矢量/图片边界定位，输出 PNG 与 figures.json
python pdf_figures.py /path/paper.pdf --out /path/reading/figures --pages 3 4
# 裁剪需要修正时指定物理页序和 PDF 点坐标；也适用于扫描页的人工定位
python pdf_figures.py /path/paper.pdf --out /path/reading/figures --pages 3 --crop 'figure-1:3:180,60,430,405'
```

先查看输出图像，检查标签、箭头、图例、分图和边界。图注启发式适合布局清楚的电子 PDF；
矢量结构图采用页面裁剪渲染，以保留文字与线条。高密度双栏、多图、扫描件可选
[Docling 结构化解析](https://docling-project.github.io/docling/_generated/examples/export_figures/)：
在独立环境安装 docling，启用 generate_page_images / generate_picture_images，遍历 PictureItem，
用 get_image(document) 导出，关联 caption 和 page，再填入同一 figures 字段。
Docling 的模型与 OCR 按所用环境配置；本 skill 的基础读写保持轻量。
也可评估 [Marker](https://github.com/datalab-to/marker) 的图像/公式与 Markdown/JSON 导出，
或 [MinerU](https://github.com/opendatalab/MinerU) 的版面、OCR、公式和图表解析。
选择时先用目标论文查看裁剪质量、阅读顺序和公式还原，再按模型资源与当地平台决定。

交互教学图应表达研究对象与实际计算：可改变输入或参数，观察输出、维度和结构变化。
attention 模块提供 3×4 输入编辑、两头投影、查询切换、缩放、因果 mask、权重矩阵、加权输出及多头拼接；
transformer 模块提供可点击的编码器/解码器计算流。界面明确标注教学参数，原文结论保留页码。
阅读其他模型时，LLM 可通过 --body-file / --template-file 编写相应 SVG、Canvas 和交互脚本。
正文片段可用 {{FIGURES_HTML}}、{{EQUATIONS_HTML}}、{{VISUALS_HTML}} 安排位置。
自编样式和布局保留图注、来源、公式溢出滚动、键盘操作与移动端排布。

自然语言伴读时，按讨论需要将关键原图、公式解释与适合该论文的计算演示组织到 others。
保存前用一篇真实论文打开页面，检查公式、原图和主要交互，再运行 html-note 登记并回读。

## 整理与写入

```bash
# 查看集合，按 key 选择目标；追加成员与标签
python zotero_ops.py items --collections
python zotero_ops.py organize PAPER_KEY --collection COLLECTION_KEY --tag attention --apply
# 创建或复用同父级同名集合
python zotero_ops.py collection '本周阅读' --apply
# 小范围元数据修改，changes.json 只包含需更新字段
python zotero_ops.py update PAPER_KEY --file /path/changes.json --expected-version VERSION --apply
```

用户要求保存/整理即可完成对应写入；普通检索保持只读。--apply 表示执行已授权的保存。
读取与写入通过 Local API 完成。更新先整合当前内容；写后回读确认对象与文件。
上传中断保留已创建 key，检查后用 upload KEY --file FILE --apply 恢复到同一附件。
超时先查询实际结果，避免重复创建。元数据、文件、笔记与远端同步分别说明完成状态。
删除优先用 trash KEY --expected-version VERSION --apply；永久删除须有用户对目标的明确要求。
文献处于回收站时，用 html_note.py 继续本地导出；文库保存选择正常条目，恢复按用户的明确意图处理。

官方入口：[Local API](https://www.zotero.org/support/dev/web_api/v3/local_api)、
[添加文献](https://www.zotero.org/support/adding_items_to_zotero)、[Zotero 更新记录](https://www.zotero.org/support/changelog)。

## 分发与使用环境

压缩包包含 zotero/SKILL.md、scripts/ 和 assets/（模板、KaTeX/字体、第三方许可证）。
解压到宿主能发现的 skills 目录，保持该目录结构；已有 Python 3.10+ 可运行核心工作流。
PDF 提图按需选择 PyMuPDF 环境，结构化解析工具也按需配置。
依赖、Zotero 授权与索引使用当地环境及用户配置目录；换机后运行 doctor 并重新发现本机文库。
