# 保存、查询与本地服务

先执行 `paper wiki list` 浏览已有概念与实体，再使用 `paper wiki query` 定向读取。知识数量不代表用户理解程度；讲解深度应依据论文中的真实问答与证据。

## 命令

```bash
paper wiki init
paper wiki list
paper wiki list --all
paper wiki query 'attention'
paper wiki query --tag attention --domain '机器学习'
paper wiki query --type source
paper wiki query --id q_UUID4
paper wiki query --record 'papers/EXAMPLE/Attention Is All You Need/assets/reading-record.json'
paper wiki check
paper wiki reindex
paper wiki graph
paper wiki serve --port 8765
paper wiki status
paper wiki stop
```

list 不接受筛选，按类型和领域分组，默认最多50个标题、约8000字符，明确报告剩余数量；--all 不截断标题或数量。query 接受关键词、--tag、--domain、--type、--id、--record，条件取交集；普通查询默认20项，--limit 调整上限。无条件 query 显示用法。精确读取返回正文、来源、身份及 SHA256。

默认输出适合终端阅读；--json 获取完整结构化结果。所有命令支持 --workspace。NO_COLOR 关闭颜色。退出码：0成功；1内容、引用或服务状态错误；2参数或路径错误；3保存基准冲突；4 I/O错误。

## 写入

1. query --record 或 --id 读取完整主记录与 SHA256（需要机器内容时加 --json）。
2. 按记录契约准备候选文件；新记录使用 missing。
3. 执行 `paper wiki save --target '引用' --candidate '候选文件' --expect '基准'`。
4. 回读同一身份，核对原问、证据、来源和正文。
5. 冲突时重读、合并；不强制覆盖。

--candidate - 可以读取标准输入。GUI 与 CLI 共用保存服务。响应分别报告主记录、索引与 HTML；派生更新失败可重新读取后保存相同内容重试。

## 引用、图谱与索引

正文双链、related、sources、relations 与 question_refs 共用引用解析。反向链接与图谱从这些明确引用构建，不推测语义关系。图谱分概念关系、来源引用、论文问答引用。默认不把实际问题作为知识实体；--include-questions 可以临时附带问答节点。focus 定位当前节点及邻居。

index.md 完全由 reindex 生成；README.md 和主记录正文不被重建覆盖。服务不会扫描参考仓库、PDF、凭据和临时目录。

## 服务

安装 `python -m pip install -e ".[gui]"`。启动后直接访问 http://127.0.0.1:8765/，不需要复制 token。只有开发前端时需要 Node；运行内置界面不需要 Node 或 Rust。

关闭方式：启动终端 Ctrl+C、同一工作区的 paper wiki stop、GUI「停止服务」。status 显示状态、PID与访问地址。另一个终端可用 --workspace 指明目录。

服务仅监听127.0.0.1。首页提供同源 API token；API核验 token 与 Origin。server.json 位于忽略的运行目录，权限0600，关闭后移除。stop 请求正常退出并等待监听器关闭，不按端口杀进程。

## API

| 接口 | 输入与输出 |
| --- | --- |
| GET /api/records | 记录目录与逐项错误 |
| GET /api/record | record、可选id；正文、元数据、SHA256、双链和反向链接 |
| GET /api/query | q、tag、domain、type、id、record、limit；与CLI共用查询 |
| GET /api/graph | focus、kind、limit、include_questions |
| GET /api/draft | kind；生成未保存的知识草稿 |
| POST /api/save | record、data、expected、可选body |
| POST /api/reindex | 重建派生索引 |
| GET /api/server/status | 本服务身份与状态 |
| POST /api/server/stop | 正常退出 |

HTTP409 表示冲突；GUI 保留未保存表单。知识正文不执行原始HTML。论文 note.html 在受限独立页面打开。
