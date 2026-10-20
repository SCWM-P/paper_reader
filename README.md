# Paper Reader

Paper Reader 是一个面向 AI 伴读的本地文献工作区。它将论文、阅读记录、问答、HTML 笔记和公共知识库保存在可检查、可迁移的文件中。

- **论文阅读**：采集元数据、提取原图、记录实际问答，生成可独立打开的 `note.html`。
- **公共知识库**：维护可跨论文复用的概念与实体，提供检索、来源定位、比较、综合和关系图谱。
- **浏览器界面**：浏览、搜索和编辑知识记录；GUI 与 CLI 使用同一套 Python 服务。
- **按需扩展**：连接 Zotero，生成 PDF 译文或教学视频。

问答与理解证据保留在对应论文中。知识库条目数量不用于判断用户掌握程度。AI 草拟摘要标记为降级，尚未讨论的论文保留空问答列表。

## 开始使用

推荐 Python 3.11 和 conda。在仓库根目录执行：

```bash
conda create -n paper_reader python=3.11
conda activate paper_reader
python -m pip install -e ".[gui,pdf,translation]"
paper --help
paper check "papers/EXAMPLE/Attention Is All You Need"
```

基础安装 `python -m pip install -e .` 提供核心 CLI。可选依赖按任务启用：

| 依赖组 | 用途 |
| --- | --- |
| `gui` | 本地 API 与浏览器界面 |
| `pdf` | PDF 读取与原图提取 |
| `translation` | PDFMathTranslate 翻译；翻译服务凭据另行配置 |
| `video` | Manim 视频制作；FFmpeg、TeX 和字体按素材要求安装 |

AI 伴读入口为 [AGENTS.md](AGENTS.md)。项目技能位于 [.agents/skills/](.agents/skills/)，其中 CLS 规定交流风格，Zotero skill 提供文献工具，llm-wiki skill 维护公共知识。

## 知识库与页面

```bash
paper wiki init
paper wiki list
paper wiki list --all
paper wiki query 'attention'
paper wiki query --type source
paper wiki check
paper wiki serve --port 8765
```

浏览器访问终端输出的地址，默认是 `http://127.0.0.1:8765/`。在另一个终端执行 `paper wiki status` 查看状态，执行 `paper wiki stop` 停止服务；前台服务也支持 `Ctrl+C`。

`list` 用于浏览标题，默认限制输出长度；`query` 用于定向查询。默认输出可读文本，`--json` 提供机器可处理的结果。各命令的完整参数见 `--help`。

论文主记录为 `assets/reading-record.json`。编辑记录后可重新生成页面：

```bash
paper render --file "papers/EXAMPLE/Attention Is All You Need/assets/reading-record.json" --out "papers/EXAMPLE/Attention Is All You Need/note.html" --asset-mode relative --force
```

保存协议、字段和来源引用要求见 [llm-wiki skill](.agents/skills/llm-wiki/SKILL.md)；文献采集与翻译流程见 [Zotero skill](.agents/skills/zotero/SKILL.md)。

## 目录与分支

```text
AGENTS.md                              AI 伴读入口
pyproject.toml                         依赖、CLI 与工作区配置
MANIFEST.in                            Python 源码分发清单
.agents/skills/cls/                     受控语言规则与模板
.agents/skills/zotero/                  文献工具、HTML 模板与第三方资源
.agents/skills/llm-wiki/scripts/         Python 核心、API 与 static/ 构建产物
.agents/skills/llm-wiki/frontend/        React/TypeScript 前端源码
.agents/skills/llm-wiki/wiki/            知识条目与可重建索引
papers/EXAMPLE/                         完整文献实例
papers/DEMO/                            demo 分支的展示文献
.runtime/                              本地凭据、锁、服务登记与缓存
```

`main` 包含通用功能与 EXAMPLE。`demo` 额外包含展示文献及对应知识条目。两条分支共用功能代码和协议。

每篇文献的 PDF、`note.html`、`assets/` 与可选 `translation/` 保存在同一个实例目录。阅读代码放在 `assets/code/`；视频源码放在 `assets/code/video/`；视频成片及播放资源放在 `assets/videos/`。

个人资料可通过自己的 Git 仓库同步。启用前请将远端配置为自己的仓库，并检查准备提交的文献与知识内容。`.runtime/`、开发参考目录和审查资料留在本地。

## 构建与分发

日常运行使用随包分发的静态资源，无需 Node 或 Rust。修改前端时，需要满足前端依赖要求的 Node.js 和 npm。进入前端目录构建：

```bash
cd .agents/skills/llm-wiki/frontend
npm ci
npm run build
```

构建包含 TypeScript 检查，并将资源写入同一 skill 下的 `scripts/static/`。返回仓库根目录后，可生成 Python 分发包：

```bash
python -m pip install build
python -m build
```

`MANIFEST.in` 将前端源码、锁文件、构建配置、静态资源和许可文件纳入 sdist。sdist 解压后可按上述命令重新构建前端，再构建 wheel。首次安装 npm 依赖需要访问包源；浏览器运行时使用本地资源。

分发包不包含论文、个人知识条目、运行目录、参考仓库或开发审查资料。完整文献工作区请使用 Git 仓库；wheel 提供运行工具与构建后的界面。

## 来源与许可

- CLS 改编自 `dualface/ste-zh`，保留 [MIT 许可证](.agents/skills/cls/LICENSE) 与上游版权。
- llm-wiki 前端改编来源、GPL-3.0 许可及依赖声明见 [前端来源与许可](.agents/skills/llm-wiki/frontend/THIRD_PARTY_NOTICES.md) 和 [LICENSE](.agents/skills/llm-wiki/frontend/LICENSE)。
- HTML 模板及浏览器依赖的许可保存在 [Zotero vendor 目录](.agents/skills/zotero/assets/vendor/)。论文及其他引用资料的权利归相应权利人。

各组件按自身许可分发；本 README 不将某一组件的许可扩展为整个仓库的统一许可。
