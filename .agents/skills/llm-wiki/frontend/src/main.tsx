import { useEffect, useRef, useState, lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import {
  BookOpen,
  Library,
  Search,
  Network,
  Sun,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  ChevronDown,
  FileText,
  ArrowUpRight,
  Pencil,
  CheckCircle2,
  Power,
  RefreshCw,
  ChevronRight,
  ArrowLeft,
} from "lucide-react";
import { api, labels } from "./types";
import type { Row, Document, Data } from "./types";
import Markdown from "./Markdown";
import Editor from "./Editor";
import "@fontsource-variable/geist";
import "./theme.css";
import "./style.css";
const GraphView = lazy(() => import("./GraphView"));
type Mode = "wiki" | "sources" | "search" | "graph" | "status";

function App() {
  const [rows, setRows] = useState<Row[]>([]),
    [doc, setDoc] = useState<Document>(),
    [mode, setMode] = useState<Mode>("wiki");
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [editing, setEditing] = useState(false),
    [busy, setBusy] = useState(false);
  const [left, setLeft] = useState(true),
    [right, setRight] = useState(true),
    [width, setWidth] = useState(
      Number(localStorage.getItem("tree-width")) || 255,
    );
  const [dark, setDark] = useState(localStorage.getItem("theme") === "dark"),
    [query, setQuery] = useState(""),
    [tag, setTag] = useState(""),
    [domain, setDomain] = useState(""),
    [kind, setKind] = useState(""),
    [matches, setMatches] = useState<Data>();
  const [status, setStatus] = useState<Data>(),
    [check, setCheck] = useState<Data>(),
    [activeQuestion, setActiveQuestion] = useState<string>(),
    [zoom, setZoom] = useState<string>();
  const request = useRef(0),
    routeHash = useRef(location.hash),
    routeIndex = useRef<number>(window.history.state?.wikiIndex || 0);
  const [backIndex, setBackIndex] = useState(routeIndex.current);
  const restoreRoute = useRef<() => void>(() => {});
  function writeRoute(hash: string, replace = false) {
    if (hash === routeHash.current) return;
    if (!replace) routeIndex.current += 1;
    window.history[replace ? "replaceState" : "pushState"](
      { wikiIndex: routeIndex.current },
      "",
      hash,
    );
    routeHash.current = hash;
    setBackIndex(routeIndex.current);
  }
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);
  const refresh = async () => {
    const result = await api("records");
    setRows(result.records);
    if (result.errors.length)
      setError(
        result.errors.map((e: Data) => e.record + ": " + e.reason).join("\n"),
      );
    return result.records as Row[];
  };
  useEffect(() => {
    refresh()
      .then((list) => {
        if (request.current) return;
        const hash = new URLSearchParams(location.hash.slice(1)),
          ref = hash.get("record");
        if (ref) open(ref, hash.get("id") || undefined, false);
        else if (hash.has("view")) restoreRoute.current();
        else {
          const first =
            list.find((x) => x.type === "synthesis") ||
            list.find((x) => x.type === "concept");
          if (first) open(first.record, undefined, false);
        }
      })
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    const restore = () => {
      if (location.hash !== routeHash.current) restoreRoute.current();
    };
    window.addEventListener("hashchange", restore);
    return () => {
      window.removeEventListener("hashchange", restore);
    };
  }, []);
  restoreRoute.current = () => {
    const nextIndex = window.history.state?.wikiIndex || 0;
    if (editing && !window.confirm("离开编辑页将丢弃未保存内容。继续？")) {
      const delta = routeIndex.current - nextIndex;
      if (delta) window.history.go(delta);
      else
        window.history.replaceState(
          { wikiIndex: routeIndex.current },
          "",
          routeHash.current || location.pathname,
        );
      return;
    }
    routeHash.current = location.hash;
    routeIndex.current = nextIndex;
    setBackIndex(nextIndex);
    const hash = new URLSearchParams(location.hash.slice(1)),
      ref = hash.get("record");
    if (ref) void open(ref, hash.get("id") || undefined, false, false, true);
    else {
      const view = hash.get("view");
      navigate(
        ["wiki", "sources", "search", "graph", "status"].includes(view || "")
          ? (view as Mode)
          : "wiki",
        true,
      );
    }
  };
  useEffect(() => {
    if (activeQuestion && doc)
      setTimeout(
        () =>
          document
            .getElementById("qa-" + activeQuestion)
            ?.scrollIntoView({ block: "center" }),
        80,
      );
  }, [activeQuestion, doc]);
  async function open(
    ref: string,
    id?: string,
    remember = true,
    afterSave = false,
    fromHistory = false,
  ) {
    if (
      editing &&
      !afterSave &&
      !fromHistory &&
      !window.confirm("离开编辑页将丢弃未保存内容。继续打开另一页？")
    )
      return;
    const current = ++request.current;
    setBusy(true);
    setError("");
    setDoc(undefined);
    setEditing(false);
    if (!afterSave) setNotice("");
    try {
      const result = await api<Document>(
        "record?record=" +
          encodeURIComponent(ref) +
          (id ? "&id=" + encodeURIComponent(id) : ""),
      );
      if (current !== request.current) return;
      setDoc(result);
      setActiveQuestion(id);
      setMode(result.data.type === "source" ? "sources" : "wiki");
      const hash =
        "#" +
        new URLSearchParams({
          record: result.record,
          ...(id ? { id } : {}),
        }).toString();
      writeRoute(hash, fromHistory || !remember);
    } catch (e) {
      if (current === request.current) setError(String(e));
    } finally {
      if (current === request.current) setBusy(false);
    }
  }
  function navigate(next: Mode, fromHistory = false) {
    if (
      editing &&
      !fromHistory &&
      !window.confirm("离开编辑页将丢弃未保存内容。继续？")
    )
      return;
    ++request.current;
    setBusy(false);
    setEditing(false);
    setDoc(undefined);
    setActiveQuestion(undefined);
    setMode(next);
    setNotice("");
    setError("");
    if (!fromHistory) writeRoute("#view=" + next);
    if (next === "status")
      api("server/status")
        .then(setStatus)
        .catch((e) => setError(e.message));
  }
  async function search(event?: React.FormEvent) {
    event?.preventDefault();
    setError("");
    setBusy(true);
    try {
      const p = new URLSearchParams({ limit: "40" });
      if (query) p.set("q", query);
      if (tag) p.set("tag", tag);
      if (domain) p.set("domain", domain);
      if (kind) p.set("type", kind);
      setMatches(await api("query?" + p));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function draft(type: string) {
    if (editing && !window.confirm("新建页面将丢弃未保存内容。继续？")) return;
    try {
      const next = await api<Document>("draft?kind=" + type);
      setDoc(next);
      setMode("wiki");
      setEditing(true);
    } catch (e) {
      setError(String(e));
    }
  }
  async function saved(result: Data) {
    setEditing(false);
    const parts = [
      "主记录：" + result.source.status,
      "索引：" + result.index.status,
      "HTML：" + result.html.status,
    ];
    if (result.index.reason) parts.push(result.index.reason);
    if (result.html.reason) parts.push(result.html.reason);
    setNotice(parts.join(" · "));
    await refresh();
    await open(result.record, undefined, false, true);
  }
  function resize(e: React.PointerEvent) {
    const start = e.clientX,
      initial = width;
    const target = e.currentTarget;
    target.setPointerCapture(e.pointerId);
    const move = (x: PointerEvent) =>
      setWidth(Math.min(400, Math.max(180, initial + x.clientX - start)));
    const stop = () => {
      target.removeEventListener("pointermove", move as EventListener);
      target.removeEventListener("pointerup", stop);
      localStorage.setItem(
        "tree-width",
        String(
          document.querySelector(".tree")?.getBoundingClientRect().width ||
            width,
        ),
      );
    };
    target.addEventListener("pointermove", move as EventListener);
    target.addEventListener("pointerup", stop, { once: true });
  }
  const known = rows.filter((r) => r.type !== "source"),
    sources = rows.filter((r) => r.type === "source");
  const orderedTypes = [
    "concept",
    "entity",
    "comparison",
    "synthesis",
    "query",
    "overview",
  ];
  const titleByRef = (ref: string) =>
    rows.find((r) => r.record === ref)?.title || ref;
  return (
    <div className="app-shell">
      <nav className="iconbar" aria-label="主导航">
        <div className="brand" title="Paper Reader">
          <BookOpen size={22} />
        </div>
        {(
          [
            ["wiki", BookOpen, "知识库"],
            ["sources", Library, "论文来源"],
            ["search", Search, "搜索"],
            ["graph", Network, "图谱"],
          ] as const
        ).map(([key, Icon, label]) => (
          <button
            key={key}
            title={label}
            aria-label={label}
            className={mode === key ? "active" : ""}
            onClick={() => navigate(key)}
          >
            <Icon size={20} />
          </button>
        ))}
        <div className="nav-spacer" />
        <button
          aria-label={dark ? "切换亮色" : "切换暗色"}
          title="切换主题"
          onClick={() => setDark(!dark)}
        >
          {dark ? <Sun size={19} /> : <Moon size={19} />}
        </button>
        <button
          aria-label="服务状态"
          title="服务状态"
          className={mode === "status" ? "active" : ""}
          onClick={() => navigate("status")}
        >
          <span
            className={
              "status-dot " + (status?.status === "stopped" ? "off" : "")
            }
          />
        </button>
      </nav>
      {left && (
        <aside className="tree" style={{ width }}>
          <div className="tree-heading">
            <div>
              <b>Paper Reader</b>
              <span className="workspace-label">本地知识空间</span>
            </div>
            <button aria-label="收起知识树" onClick={() => setLeft(false)}>
              <PanelLeftClose size={17} />
            </button>
          </div>
          <button className="search-trigger" onClick={() => navigate("search")}>
            <Search size={15} />
            <span>搜索知识与论文</span>
            <span className="keycap">⌕</span>
          </button>
          <div className="tree-section-title">
            <span>
              {mode === "sources" ? "论文来源" : "知识库"}{" "}
              <span className="count">
                {mode === "sources" ? sources.length : known.length}
              </span>
            </span>
            <details className="new-menu">
              <summary aria-label="新建页面">
                <Plus size={16} />
              </summary>
              <div>
                {orderedTypes.map((k) => (
                  <button key={k} onClick={() => draft(k)}>
                    {labels[k]}
                  </button>
                ))}
              </div>
            </details>
          </div>
          <div className="tree-scroll">
            {mode === "sources" ? (
              <div className="tree-children">
                {sources.map((r) => (
                  <button
                    key={r.record}
                    className={
                      "tree-item " +
                      (doc?.record === r.record ? "selected" : "")
                    }
                    onClick={() => open(r.record)}
                    title={r.title}
                  >
                    <FileText size={14} />
                    <span>{r.title}</span>
                  </button>
                ))}
              </div>
            ) : (
              orderedTypes.map((k) => (
                <details className="tree-group" open={true} key={k}>
                  <summary>
                    <ChevronRight size={13} />
                    <span>{labels[k]}</span>
                    <span className="count">
                      {known.filter((r) => r.type === k).length}
                    </span>
                  </summary>
                  <div className="tree-children">
                    {known
                      .filter((r) => r.type === k)
                      .map((r) => (
                        <button
                          key={r.record}
                          className={
                            "tree-item " +
                            (doc?.record === r.record ? "selected" : "")
                          }
                          onClick={() => open(r.record)}
                          title={r.title}
                        >
                          <FileText size={13} />
                          <span>{r.title}</span>
                        </button>
                      ))}
                    {!known.some((r) => r.type === k) && (
                      <p className="tree-empty">暂无页面</p>
                    )}
                  </div>
                </details>
              ))
            )}
          </div>
          <div className="tree-footer">
            <span className="status-dot" /> 文件存储 · {known.length} 个知识页面
          </div>
        </aside>
      )}
      {left && (
        <div
          className="resize-handle"
          role="separator"
          aria-label="调整知识树宽度"
          onPointerDown={resize}
        />
      )}
      <main className="main">
        <header className="topbar">
          <div className="row">
            {!left && (
              <button aria-label="展开知识树" onClick={() => setLeft(true)}>
                <PanelLeftOpen size={17} />
              </button>
            )}
            <button
              aria-label="返回上一页"
              disabled={!backIndex}
              onClick={() => window.history.back()}
            >
              <ArrowLeft size={16} />
            </button>
            <span className="breadcrumb">
              {mode === "wiki"
                ? "知识库"
                : mode === "sources"
                  ? "论文来源"
                  : mode === "search"
                    ? "搜索"
                    : mode === "graph"
                      ? "图谱"
                      : "服务"}
              <ChevronRight size={13} />
              <span>
                {mode === "wiki" || mode === "sources"
                  ? doc?.data.title || "选择页面"
                  : "Paper Reader"}
              </span>
            </span>
          </div>
          <div className="row">
            {(mode === "wiki" || mode === "sources") && doc && !editing && (
              <button
                onClick={() => setEditing(true)}
                disabled={
                  doc.data.type === "source" && !doc.data["Q & A"]?.length
                }
              >
                <Pencil size={14} />
                编辑
              </button>
            )}
            <button
              aria-label={right ? "收起引用栏" : "展开引用栏"}
              onClick={() => setRight(!right)}
            >
              {right ? (
                <PanelRightClose size={17} />
              ) : (
                <PanelRightOpen size={17} />
              )}
            </button>
          </div>
        </header>
        {error && (
          <div role="alert" className="banner error">
            {error}
            <button aria-label="关闭错误提示" onClick={() => setError("")}>
              ×
            </button>
          </div>
        )}
        {notice && (
          <div role="status" className="banner">
            <CheckCircle2 size={16} />
            {notice}
          </div>
        )}
        {busy && <div className="loading-line" />}
        <div className="main-scroll">
          {mode === "search" ? (
            <section className="search-page">
              <span className="eyebrow">SEARCH YOUR KNOWLEDGE</span>
              <h1>找到已有的知识与依据</h1>
              <p className="muted">
                关键词与筛选条件取交集。原问可直接定位到论文记录。
              </p>
              <form onSubmit={search}>
                <div className="search-box">
                  <Search size={20} />
                  <input
                    aria-label="全文关键词"
                    placeholder="搜索概念、实体、论文或实际原问…"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                  <button className="primary">搜索</button>
                </div>
                <div className="filters">
                  <select
                    aria-label="筛选类型"
                    value={kind}
                    onChange={(e) => setKind(e.target.value)}
                  >
                    <option value="">全部类型</option>
                    {Object.entries(labels)
                      .filter(([k]) => k !== "question")
                      .map(([k, v]) => (
                        <option key={k} value={k}>
                          {v}
                        </option>
                      ))}
                  </select>
                  <input
                    aria-label="筛选标签"
                    placeholder="标签"
                    value={tag}
                    onChange={(e) => setTag(e.target.value)}
                  />
                  <select
                    aria-label="筛选领域"
                    value={domain}
                    onChange={(e) => setDomain(e.target.value)}
                  >
                    <option value="">全部领域</option>
                    {[
                      ...new Set(rows.map((r) => r.domain).filter(Boolean)),
                    ].map((d) => (
                      <option key={d}>{d}</option>
                    ))}
                  </select>
                </div>
              </form>
              {matches && (
                <>
                  <p className="muted">
                    {matches.total} 项匹配 · 显示 {matches.matches.length} 项
                  </p>
                  {matches.matches.map((m: Data, i: number) => (
                    <button
                      className="search-result"
                      key={i}
                      onClick={() =>
                        open(
                          m.record,
                          ["question", "evidence"].includes(m.kind)
                            ? m.id
                            : undefined,
                        )
                      }
                    >
                      <span className="type-badge">
                        {labels[m.kind] || m.kind}
                      </span>
                      <h3>{m.title}</h3>
                      <p>{m.snippet}</p>
                      <span className="muted small">{m.record}</span>
                      <ArrowUpRight size={17} />
                    </button>
                  ))}
                </>
              )}
            </section>
          ) : mode === "graph" ? (
            <Suspense fallback={<p className="empty">图谱加载中…</p>}>
              <GraphView key={String(dark)} onOpen={open} />
            </Suspense>
          ) : mode === "status" ? (
            <section className="service-page">
              <span className="eyebrow">LOCAL WORKSPACE</span>
              <h1>本地服务</h1>
              <div className="service-card">
                <span className="status-dot" /> {status?.status || "读取中"}
                <p>{status?.workspace}</p>
                <p className="muted">
                  PID {status?.pid} · {location.origin}
                </p>
              </div>
              <div className="row">
                <button
                  onClick={async () => {
                    try {
                      setCheck(await api("reindex", {}));
                      setNotice("索引重建完成");
                    } catch (e) {
                      setError(String(e));
                    }
                  }}
                >
                  <RefreshCw size={15} />
                  重建索引
                </button>
                <button
                  className="danger"
                  disabled={status?.status === "stopped"}
                  onClick={async () => {
                    try {
                      await api("server/stop", {});
                      setStatus({ ...status, status: "stopped" });
                      setNotice(
                        "服务正在正常退出。重新启动请执行 paper wiki serve。",
                      );
                    } catch (e) {
                      setError(String(e));
                    }
                  }}
                >
                  <Power size={15} />
                  停止服务
                </button>
              </div>
              {check && <p>索引记录数：{check.sources}</p>}
              <p className="muted">
                可在另一终端运行 paper wiki status 或 paper wiki
                stop。服务停止后会释放监听端口。
              </p>
            </section>
          ) : editing && doc ? (
            <Editor
              key={doc.record}
              doc={doc}
              rows={rows}
              onSaved={saved}
              onCancel={() => setEditing(false)}
            />
          ) : doc &&
            ((mode === "sources" && doc.data.type === "source") ||
              (mode === "wiki" && doc.data.type !== "source")) ? (
            <article className="document">
              <div className="document-meta">
                <span className={"type-badge " + doc.data.type}>
                  {labels[doc.data.type]}
                </span>
                <span>{doc.data.domain || "来源记录"}</span>
                <span className="meta-date">
                  {doc.data.updated?.slice(0, 10) || ""}
                </span>
              </div>
              <h1>{doc.data.title || doc.view?.metadata?.title}</h1>
              {!!doc.data.tags?.length && (
                <div className="tags">
                  {doc.data.tags.map((t: string) => (
                    <button
                      key={t}
                      onClick={() => {
                        navigate("search");
                        setTag(t);
                        setQuery("");
                      }}
                    >
                      #{t}
                    </button>
                  ))}
                </div>
              )}
              {doc.data.type === "source" ? (
                <Source
                  doc={doc}
                  activeQuestion={activeQuestion}
                  onZoom={setZoom}
                  onOpen={open}
                />
              ) : (
                <>
                  <div className="record-scope">{doc.data.scope}</div>
                  {doc.data.type === "concept" && (
                    <div className="source-status">
                      <CheckCircle2 size={14} />
                      {doc.data.consensus?.status === "verified"
                        ? "有来源依据的公共概念"
                        : "共识状态未核实"}
                      <span>不表示用户已掌握</span>
                    </div>
                  )}
                  {doc.data.type === "concept" && (
                    <section aria-label="概念定义">
                      <h2>定义</h2>
                      <Markdown
                        body={doc.data.definition}
                        targets={doc.link_targets}
                        onOpen={open}
                      />
                    </section>
                  )}
                  <Markdown
                    body={doc.body}
                    targets={doc.link_targets}
                    onOpen={open}
                  />
                  <footer className="document-footer">
                    <span>{doc.data.id}</span>
                    <span>更新于 {doc.data.updated || "未知"}</span>
                  </footer>
                </>
              )}
            </article>
          ) : (
            <section className="catalog-page">
              <span className="eyebrow">
                {mode === "sources" ? "PAPER LIBRARY" : "KNOWLEDGE LIBRARY"}
              </span>
              <h1>{mode === "sources" ? "论文来源" : "知识库"}</h1>
              <p className="muted">选择一个页面开始阅读。</p>
              <div className="catalog-grid">
                {(mode === "sources" ? sources : known).map((r) => (
                  <button key={r.record} onClick={() => open(r.record)}>
                    <span className="type-badge">{labels[r.type]}</span>
                    <h3>{r.title}</h3>
                    <span className="muted">{r.domain}</span>
                  </button>
                ))}
              </div>
            </section>
          )}
        </div>
      </main>
      {right && doc && (mode === "wiki" || mode === "sources") && (
        <aside className="inspector">
          <div className="inspector-heading">页面关系</div>
          <section>
            <h4>
              来源{" "}
              <span className="count">{doc.data.sources?.length || 0}</span>
            </h4>
            {(doc.data.sources || []).map((s: Data) => (
              <div className="citation" key={s.source_id}>
                <span className="small muted">{s.source_id}</span>
                {s.record ? (
                  <button className="text-link" onClick={() => open(s.record)}>
                    {titleByRef(s.record)}
                  </button>
                ) : (
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {s.url}
                  </a>
                )}
                <p>{s.locator}</p>
              </div>
            ))}
            {!doc.data.sources?.length && (
              <p className="muted small">
                {doc.data.type === "source"
                  ? "当前页本身为论文主记录。"
                  : "尚未登记来源。"}
              </p>
            )}
          </section>
          <section>
            <h4>
              反向链接{" "}
              <span className="count">{doc.backlinks?.length || 0}</span>
            </h4>
            {doc.backlinks?.map((b) => (
              <button
                key={b.record}
                className="text-link backlink"
                onClick={() => open(b.record)}
              >
                <FileText size={13} />
                {b.title}
              </button>
            ))}
            {!doc.backlinks?.length && (
              <p className="muted small">暂无页面引用</p>
            )}
          </section>
          <section>
            <h4>相关页面</h4>
            {[...new Set((doc.links || []).map((l) => l.record))]
              .filter((ref) => ref !== doc.record)
              .map((ref) => (
                <button
                  className="text-link"
                  key={ref}
                  onClick={() => open(ref)}
                >
                  {titleByRef(ref)}
                </button>
              ))}
          </section>
          <section className="identity">
            <h4>记录身份</h4>
            <p>{doc.data.id || doc.record}</p>
            <p className="muted">{doc.record}</p>
          </section>
        </aside>
      )}
      {zoom && (
        <div
          className="image-modal"
          role="dialog"
          aria-label="原图预览"
          onClick={() => setZoom(undefined)}
        >
          <button aria-label="关闭原图">×</button>
          <img src={zoom} />
        </div>
      )}
    </div>
  );
}
function Source({
  doc,
  activeQuestion,
  onZoom,
  onOpen,
}: {
  doc: Document;
  activeQuestion?: string;
  onZoom: (src: string) => void;
  onOpen: (ref: string) => void;
}) {
  const data = doc.view || doc.data,
    metadata = data.metadata;
  const figures = (data.others || []).flatMap((s: Data) => s.figures || []);
  const prefix = doc.note_url?.replace(/note.html$/, "") || "";
  return (
    <>
      {doc.completeness?.status !== "ok" && (
        <div className="warning">
          阅读未完成：
          {Object.entries(doc.completeness?.modules || {})
            .filter(([, v]: any) => v.status !== "ok")
            .map(([k, v]: any) => k + " · " + v.message)
            .join("；")}
        </div>
      )}
      <div className="paper-metadata">
        <p>
          {Array.isArray(metadata.author)
            ? metadata.author.join(" · ")
            : metadata.author}
        </p>
        <div className="row">
          <b>{metadata.publicationTitle || metadata.conferenceName || ""}</b>
          <span>{metadata.date}</span>
          <span>{metadata.version || metadata.provenance?.version || ""}</span>
        </div>
        <div className="row links">
          {doc.pdf_url && (
            <a href={doc.pdf_url} target="_blank" rel="noreferrer">
              <FileText size={14} />
              PDF <ArrowUpRight size={13} />
            </a>
          )}
          <a href={doc.note_url} target="_blank" rel="noreferrer">
            完整 note.html <ArrowUpRight size={13} />
          </a>
          {metadata.url && (
            <a href={metadata.url} target="_blank" rel="noreferrer">
              官方来源 <ArrowUpRight size={13} />
            </a>
          )}
        </div>
      </div>
      <h2>摘要</h2>
      <Markdown body={data.summary} onOpen={onOpen} />
      <h2>主要贡献</h2>
      <ul>
        {(Array.isArray(data.highlights)
          ? data.highlights
          : [data.highlights]
        ).map((h: any, i: number) => (
          <li key={i}>
            {typeof h === "string" ? h : h.title || h.text || JSON.stringify(h)}
          </li>
        ))}
      </ul>
      {!!figures.length && (
        <>
          <h2>原文插图</h2>
          <div className="paper-figures">
            {figures.map((f: Data, i: number) => {
              const src = prefix + "assets/" + f.file;
              return (
                <figure key={i}>
                  <button onClick={() => onZoom(src)}>
                    <img src={src} alt={f.caption || f.id} loading="lazy" />
                  </button>
                  <figcaption>
                    {f.caption || f.id} · PDF p.{f.page}
                  </figcaption>
                </figure>
              );
            })}
          </div>
        </>
      )}
      <h2>
        Q & A <span className="count">{data["Q & A"].length}</span>
      </h2>
      {!data["Q & A"].length && (
        <div className="empty-qa">
          尚无实际问答。这里不使用预设问题代替用户讨论。
        </div>
      )}
      {data["Q & A"].map((q: Data) => (
        <details
          id={"qa-" + q.id}
          className={"question " + (q.id === activeQuestion ? "focused" : "")}
          key={q.id}
          open={q.id === activeQuestion}
        >
          <summary>{q.question}</summary>
          <Markdown body={q.answer || "尚未答复"} onOpen={onOpen} />
          <p className="small muted">
            {q.question_form === "legacy_recorded"
              ? "历史记录原问"
              : "逐字原问"}{" "}
            · {q.id}
          </p>
          {q.evidence && (
            <div className="evidence">
              <b>论文依据</b>
              {(Array.isArray(q.evidence) ? q.evidence : [q.evidence]).map(
                (e: Data, i: number) => (
                  <div key={i}>
                    <p>{e.claim}</p>
                    <p>{e.locator}</p>
                  </div>
                ),
              )}
            </div>
          )}
          {!!q.reader_evidence?.length && (
            <div className="evidence">
              <b>实际理解证据</b>
              {q.reader_evidence.map((e: Data) => (
                <div key={e.evidence_id}>
                  <p>{e.actual}</p>
                  <span>
                    {e.kind} · {e.scope}
                  </span>
                </div>
              ))}
            </div>
          )}
          {q.reader_current && (
            <p>
              当前判断：{q.reader_current.state} · {q.reader_current.scope}
            </p>
          )}
          <a
            className="small"
            href={doc.note_url + "#qa-" + q.id}
            target="_blank"
            rel="noreferrer"
          >
            在完整笔记中定位原问 ↗
          </a>
        </details>
      ))}
      <p className="small muted">
        采集：{metadata.retrieved_at || "历史记录未保存"}
        <br />
        PDF SHA256：{metadata.pdf_sha256 || "见原始元数据"}
      </p>
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
