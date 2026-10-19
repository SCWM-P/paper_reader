# Demo 工作区

本分支用于真实文献与公共知识的功能演示。项目版本仍为 **0.1.0**。文献摘要为 AI 整理，尚未完成用户讨论；知识条目不表示用户已掌握。

## 启动与停止

在本工作树根目录使用独立环境：

```bash
.venv/bin/paper wiki serve --port 8766
.venv/bin/paper wiki status
.venv/bin/paper wiki stop
```

浏览器直接访问 http://127.0.0.1:8766/ 。入口自动建立本地 API 访问，无需手工复制 token。停止也可以使用 GUI「服务状态 → 停止服务」或前台终端 Ctrl+C。

在新设备安装：

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e ".[gui,pdf]"
.venv/bin/paper wiki init
.venv/bin/paper wiki check
.venv/bin/paper wiki serve --port 8766
```

基础安装包含 YAML 和终端显示依赖。GUI、PDF、translation、video 为独立依赖组；演示阅读无需安装翻译或视频生成工具。预构建 GUI 已随 Python 包分发。修改前端才需要 Node；在 `frontend/` 执行 `npm ci && npm run build`。

## 数据与工作区

- `papers/DEMO/`：17 篇文献，含 PDF、阅读记录、来源元数据、选取的原图与 note.html。采集清单为 `papers/DEMO/catalog.json`。
- `papers/EXAMPLE/`：保留原有阅读实例、真实原问、稳定 ID 与证据。
- `wiki/`：50 个 concept、12 个 entity、2 个 comparison、1 个 synthesis，共 65 个知识页面。未填充 query 或 overview。
- `pyproject.toml` 的 `tool.paper-reader.wiki.root = "wiki"` 选择可跟踪知识目录。没有此配置的普通工作区默认使用 `.runtime/llm_wiki/`。
- token、进程登记、锁、环境、构建缓存与检查过程文件保留在忽略目录。论文 `tmp/` 不纳入 Git。
- `ref_repository` 只在原工作区供只读参考，不进入 demo、索引或安装包。

两份原根目录 PDF 已在 demo 归档，核对官方版本并打开检查后，从原工作区移除。两个工作区根目录均不留 PDF。没有复制原工作区凭据或运行历史，也没有提交或推送。

## CLI 分工

```bash
paper wiki list
paper wiki list --all
paper wiki query 'attention'
paper wiki query --tag kv-cache --domain 计算系统
paper wiki query --type source
paper wiki query --id c_a3da01f3-eea9-40fa-b620-ec0318f438d4
paper wiki query --record store:concepts/attention.md --json
paper wiki check
paper wiki reindex
paper wiki graph
```

精确 ID 请以当前 list/query 结果为准。list 只浏览 concept/entity 标题，按类型与领域分组；默认最多 50 项、约 8,000 字符，显示剩余数量。--all 取消截断。query 处理有目标的检索，条件取交集；无条件只显示帮助。没有 get/find 别名或额外 entries/view 层级。

默认显示人类可读文本；--json 返回完整结构化结果。精确读取提供稳定身份、完整内容与 SHA256。save 使用目标路径、候选内容、--expect；新记录使用 missing。旧基准冲突退出码为 3，不覆盖记录。

## 最新存储协议

知识页面使用 YAML frontmatter 和 Markdown 正文。基础类型与上游一致：entity、concept、source、query、comparison、synthesis、overview。

| 旧字段 | 当前字段 / 处理 |
| --- | --- |
| name | title |
| created_at / updated_at | created / updated；未知历史时间保持未知 |
| related_refs | related；通过稳定 ID 或固定文件名解析 |
| JSON 机器数据区 | YAML frontmatter；不保留旧读取分支 |
| schema_version / 协议版本后缀 | 删除；只保留项目整体版本 |
| 论文摘要副本 | 不创建；source 直接适配论文 reading-record.json |

公共字段为 id、type、title、tags、related、created、updated；按需保留 domain、scope、sources、relations。concept 额外保存 definition 与有来源的 consensus。entity 表示具名对象，不能因为新论文提出就登记为领域共识。

正文使用 `[[固定文件名|显示标题]]` 或稳定 ID。标题改动不改变文件名或身份。列表、检索、反向链接、检查和图谱共享引用解析。实际原问及理解证据只保存在论文主记录；query 表示研究议题，不是用户提问的副本。

## 架构与上游对齐范围

Python 的 models/codecs 负责契约与 YAML，repository/locking 负责原子文件写入，service 负责正式保存与派生产物，links/search/graph 负责统一引用、查询与图谱；CLI 和 FastAPI 共用这些服务。论文适配继续调用原检查器及 HTML 渲染器。

React/TypeScript 前端采用窄图标导航、可调整知识树、中央阅读区和引用侧栏。阅读支持表格、KaTeX、Mermaid、代码与双链；编辑采用字段表单加 Markdown 源码编辑。图谱使用 Sigma、Graphology 和 ForceAtlas2。

本轮没有移植上游桌面容器、Chat、Deep Research、模型设置、自动摄取或向量检索；编辑器也未复刻其完整富文本编辑体验。界面按上游布局与主题体系重写，不宣称逐像素一致。来源及许可见 `frontend/THIRD_PARTY_NOTICES.md`。

完整验收结果见 [docs/demo-acceptance.md](docs/demo-acceptance.md)。
