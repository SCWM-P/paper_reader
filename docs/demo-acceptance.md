# Demo 实施与提交前验收

验收日期：2026-10-19。工作树：`/Users/pengbo/.codex/worktrees/paper-reader-demo/paper_reader`，分支 `demo`。项目版本保持 0.1.0，未暂存、提交或推送。

## 阶段与实际文件改动

| 阶段 | 改动范围 | 验收结果 |
| --- | --- | --- |
| D0 | 独立 worktree、独立 .venv、pyproject.toml 的 wiki 目录配置 | 基于原 HEAD 并带入已有开发改动；原分支不变，运行目录隔离 |
| D1 | llm-wiki/paper_reader_wiki 的 models、codecs、repository、links、service、search、graph、CLI、presentation；AGENTS、skill、契约与模板 | YAML 单一格式；list/query 分工；旧 get/find 和旧 helper 入口移除；实际记录查询及检查通过 |
| D2 | papers/DEMO 的 17 份 PDF、记录、元数据、HTML、16 张原图；catalog.json；wiki 的 65 个页面 | 官方版本与摘要可查；所有新 Q & A 为空，摘要均 degraded；两份原根 PDF 在归档核验后移除 |
| D3 | frontend/ 的 React 组件、主题、构建配置；API 适配与静态资源 | 分类浏览、查询、来源、编辑、双链、反向链接、公式、表格、Mermaid、原图、图谱正常流程通过 |
| D4 | 打包资源、许可清单、DEMO.md、本报告 | 独立 wheel 安装与命令通过；原工作区哈希核对通过；Git 与包排除项通过 |

核心包实际路径为 `.agents/skills/llm-wiki/paper_reader_wiki/`。原有 CLS 改动，以及此前 Zotero 检查器和渲染器改动，是从原工作区带入的开发状态，不应全部归因于本轮。

## 正式命令验收

以下命令均在 demo 根目录运行；独立安装另使用 `.runtime/package-env/bin/paper`。

| 命令或检查 | 结果 |
| --- | --- |
| `paper wiki list`、`list --json` | 列出 50 / 62 项，剩余 12；输出明确提示 --all |
| `paper wiki list --all --json` | 62 / 62 项，无遗漏 |
| `paper wiki query --tag kv-cache --domain 计算系统` | 唯一命中 KV cache；显示定义片段 |
| `paper wiki query '注意力机制怎样计算'` | 命中 EXAMPLE 主记录及实际原问 |
| `paper wiki query --id …`、`--record … --json` | 返回实际记录、稳定 ID、正文和保存基准 |
| 无条件 `paper wiki query` / 各级 --help | 显示用途和参数，不执行无条件全库查询 |
| `paper wiki check --json` | 83 条记录，0 错误，17 条警告 |
| `paper wiki reindex --json` | 成功；重建前后全部主记录 SHA256 一致 |
| `paper wiki graph --json` | 83 节点、214 条明确关系，0 引用错误 |
| `paper wiki graph --include-questions --json` | 88 节点、219 条关系，包含 EXAMPLE 的 5 个实际原问 |
| `paper check 'papers/EXAMPLE/Attention Is All You Need'` | metadata、summary、highlights、Q & A 均 OK |
| `paper wiki save` 保存现有 EXAMPLE 原内容 | source=unchanged、index=ok、html=ok；未改动原问、证据或身份 |
| 比较页 GUI 保存后 CLI 精确回读 | 稳定 ID 不变；scope 更新为真实比较范围 |
| 使用该比较页编辑前 SHA256 再保存 | conflict，退出码 3；新内容保留 |
| `paper wiki status`、`paper wiki stop --json` | 正常退出，listener=closed |
| `paper wiki serve --json` | 启动信息为 JSON；无手工 token 步骤 |
| `git diff --check` | 通过 |

17 条警告均为新采集论文的 AI 摘要降级及尚无实际问答。这是内容状态，不能将其消除为“已完成阅读”。

## 实际页面验收

使用本机浏览器访问 http://127.0.0.1:8766/ 。

- 直接访问成功，入口自动提供 API 访问配置。
- 分类树浏览、折叠恢复与拖动宽度通过；亮色和暗色主题可切换。
- 比较页的实际 scope 修订保存成功；主记录、索引、HTML 分别报告。
- KL 散度来源定位依据 DeepSeek-R1 PDF 第 15 页修正；表单及 Markdown 正文保存回读成功。
- 正文双链跳到 KV cache；反向链接可回到引用页；来源可打开实际论文。
- 搜索实际原问可展开 EXAMPLE 对应问答，并显示论文依据及原问锚点。
- 高斯分布公式、比较表格、综合页 Mermaid 均渲染。
- EXAMPLE 完整 note.html 的公式、原图和交互计算可用。因果 mask 切换改变现有教学计算输出。
- EXAMPLE 两张原图加载成功。已有 attention-from-scratch.mp4 实际播放，readyState=4，播放时间推进；没有新生成视频。
- 图谱使用实际节点与引用。类型筛选、放大、拖动 Cordis 节点、仅看邻居、打开实体页通过。不同语义边共享同一对节点时，GUI 合并为一条连线；API 保留各条明确关系。
- GUI「停止服务」后 status 显示 stopped；连接被拒绝，8766 可重新作为监听端口使用。
- 修复了验收发现的保存后误提示、Sigma 节点类型与记录类型混用、初始加载覆盖用户导航，以及隔离归档页面无法加载媒体的问题。

最终演示服务已重新启动于 8766。停止命令：在 demo 根目录运行 `.venv/bin/paper wiki stop`。

## 文献与数据核对

17 份 PDF 的 SHA256 均与采集清单一致。最新公开版本记录在每篇 `assets/metadata/source.json` 的版本历史及 `catalog.json`。获奖依据链接保留在 award 字段。

- 8 篇指定文献，加 CVPR 2026 的 1 篇、ICLR 2026 的 2 篇、ICML 2026 的 2 篇、NeurIPS 2025 的 4 篇。
- 50 个公共概念、12 个具名实体、2 个比较、1 个综合。没有填充无来源研究议题或个人理解状态。
- 16 张原图已查看；3 篇未选择原图。未选择不表示论文绝对没有图。
- 每篇归档体积均小于 30 MiB；最大约 19.54 MiB（不含忽略的处理过程目录）。
- 作者顺序来自官方元数据；Periodic Weak Spots 的一处作者切分按 PDF 署名校正，并保留原始采集值与修订说明。
- 部分会议论文的卷、期、页码尚未补齐；具体缺项列在 catalog.json，不推造出版信息。
- 新记录均明确说明只覆盖摘要、引言与方法概要，未声称复核全部实验。

EXAMPLE 阅读记录 SHA256 保持：
`937c494ec237cd2d4f549b0c74db51069844ee7e34ad4975de18320db8b78bea`。
原有 5 个原问、稳定 ID、元数据、依据及媒体文件保留；note.html 已重新生成。

## 打包与原工作区保护

执行 `npm run build`（含 TypeScript 检查）、`python -m pip wheel . --no-deps`，并在独立 venv 安装最终 wheel 的 GUI 依赖组。安装环境从 site-packages 加载核心包，正式 query/check 通过；独立安装启动 GUI 成功。

wheel 含 232 个文件，包括前端入口、JS、字体、KaTeX、上游及依赖许可。未包含 ref_repository、papers、wiki 数据、.runtime、node_modules 或 token。最终 wheel SHA256：
`41d7a67201fd0e2b72977fcd9faac30d85ec3b6501b9b9e39e4618034eb688f8`。

原工作区的 98 项文件基线中，只有授权删除的已跟踪根 PDF 缺失，其余文件哈希全部一致。另一份被忽略的根 PDF 也按授权移除。原分支仍为 `codex/prerequisite-companion`。两个工作区根目录均无 PDF。

demo 未跟踪参考仓库；新增 Git 候选文件没有 runtime、node_modules、论文 tmp 或缓存内容，没有新增测试脚本或测试目录。旧 helper 被新核心替代，静态构建原地覆盖，不保留平行旧版。

## 未验证与实际限制

- 没有真实个人理解表现数据，因此未验收 demonstrated_in_scope 等个人理解状态的完整展示与更新；未造数据补齐。
- query / overview 没有真实条目，本轮未验收这两类页面的创建保存流程。
- 未执行并发竞态、故障恢复、攻击、边界、合成性能或专项测试；单次旧基准冲突检查不等于并发验证。
- 未逐篇完整精读、逐项重跑论文实验，也未逐条完成公共概念来源的独立内容审查。
- 未全面覆盖全部 Markdown 组合、图谱规模、设备尺寸和浏览器；未完整播放两个既有视频。
- 未运行翻译、视频生成或 Zotero 写入流程。
- 前端构建有大于 500 kB 的 chunk 提示；构建成功，尚未做加载性能专项测量。
- 按计划保留原始源码编辑式 Markdown 编辑器，没有移植上游完整富文本、Chat、自动摄取或桌面容器。

上述限制不影响本轮已验收的实际主流程，但不能据此宣称全面测试通过。
