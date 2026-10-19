import { useState } from "react";
import { Plus, X, Save } from "lucide-react";
import { api, labels } from "./types";
import type { Document, Row, Data } from "./types";

export default function Editor({
  doc,
  rows,
  onSaved,
  onCancel,
}: {
  doc: Document;
  rows: Row[];
  onSaved: (result: Data) => void;
  onCancel: () => void;
}) {
  const [data, setData] = useState<Data>(() => structuredClone(doc.data)),
    [body, setBody] = useState(doc.body),
    [error, setError] = useState(""),
    [saving, setSaving] = useState(false);
  const set = (k: string, v: any) => setData((d) => ({ ...d, [k]: v }));
  async function save() {
    setSaving(true);
    setError("");
    try {
      const next = { ...data };
      if (next.type !== "source") {
        next.updated = new Date().toISOString();
        next.sources = (next.sources || []).map((source: Data) =>
          Object.fromEntries(
            Object.entries(source).filter(
              ([key, value]) =>
                !["record", "url"].includes(key) || value !== "",
            ),
          ),
        );
      }
      const result = await api("save", {
        record: doc.record,
        data: next,
        body,
        expected: doc.sha256,
      });
      onSaved(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="editor">
      <div className="editor-toolbar">
        <span>编辑 · {labels[data.type]}</span>
        <div>
          <button onClick={onCancel}>取消</button>
          <button className="primary" disabled={saving} onClick={save}>
            <Save size={15} />
            {saving ? "保存中" : "保存"}
          </button>
        </div>
      </div>
      {error && (
        <div role="alert" className="warning">
          {error}。本地编辑内容仍保留；请在另一个页面读取最新记录并合并。
        </div>
      )}
      {data.type === "source" ? (
        <>
          <p className="muted">原问、身份与证据保持原样；此处整理已有答复。</p>
          {data["Q & A"].map((q: Data, i: number) => (
            <label key={q.id}>
              {q.question}
              <textarea
                value={q.answer}
                onChange={(e) =>
                  set(
                    "Q & A",
                    data["Q & A"].map((x: Data, j: number) =>
                      j === i ? { ...x, answer: e.target.value } : x,
                    ),
                  )
                }
              />
            </label>
          ))}
        </>
      ) : (
        <>
          <div className="form-grid">
            <label className="wide">
              标题
              <input
                value={data.title}
                onChange={(e) => set("title", e.target.value)}
              />
            </label>
            <label>
              领域
              <input
                value={data.domain || ""}
                onChange={(e) => set("domain", e.target.value)}
              />
            </label>
            <label>
              标签（逗号分隔）
              <input
                value={(data.tags || []).join(", ")}
                onChange={(e) =>
                  set(
                    "tags",
                    e.target.value
                      .split(/[,，]/)
                      .map((s) => s.trim())
                      .filter(Boolean),
                  )
                }
              />
            </label>
            <label className="wide">
              适用范围
              <input
                value={data.scope || ""}
                onChange={(e) => set("scope", e.target.value)}
              />
            </label>
            {data.type === "concept" && (
              <>
                <label className="wide">
                  定义
                  <textarea
                    aria-label="定义"
                    value={data.definition}
                    onChange={(e) => set("definition", e.target.value)}
                  />
                </label>
                <label>
                  共识核实状态
                  <select
                    value={data.consensus.status}
                    onChange={(e) =>
                      set("consensus", {
                        ...data.consensus,
                        status: e.target.value,
                      })
                    }
                  >
                    <option value="unverified">未核实</option>
                    <option value="verified">有来源依据</option>
                  </select>
                </label>
                <label>
                  依据来源
                  <select
                    multiple
                    value={data.consensus.source_refs}
                    onChange={(e) =>
                      set("consensus", {
                        ...data.consensus,
                        source_refs: Array.from(
                          e.target.selectedOptions,
                          (x) => x.value,
                        ),
                      })
                    }
                  >
                    {(data.sources || []).map((s: Data) => (
                      <option key={s.source_id} value={s.source_id}>
                        {s.source_id} · {s.locator || s.url || s.record}
                      </option>
                    ))}
                  </select>
                </label>
              </>
            )}
          </div>
          <label>
            相关页面
            <select
              multiple
              value={data.related || []}
              onChange={(e) =>
                set(
                  "related",
                  Array.from(e.target.selectedOptions, (x) => x.value),
                )
              }
            >
              {rows
                .filter((r) => r.record !== doc.record)
                .map((r) => (
                  <option key={r.record} value={r.id}>
                    {r.title}
                  </option>
                ))}
            </select>
          </label>
          <details>
            <summary>来源 · {(data.sources || []).length}</summary>
            {(data.sources || []).map((s: Data, i: number) => (
              <div className="source-form" key={i}>
                <div className="row">
                  <b>{s.source_id}</b>
                  <button
                    aria-label="移除来源"
                    onClick={() =>
                      set(
                        "sources",
                        data.sources.filter((_: Data, j: number) => i !== j),
                      )
                    }
                  >
                    <X size={14} />
                  </button>
                </div>
                <label>
                  本地来源
                  <select
                    value={s.record || ""}
                    onChange={(e) =>
                      set(
                        "sources",
                        data.sources.map((x: Data, j: number) =>
                          i === j ? { ...x, record: e.target.value } : x,
                        ),
                      )
                    }
                  >
                    <option value="">外部来源</option>
                    {rows.map((r) => (
                      <option key={r.record} value={r.record}>
                        {r.title}
                      </option>
                    ))}
                  </select>
                </label>
                {["url", "locator"].map((k) => (
                  <label key={k}>
                    {k === "url" ? "来源网址" : "章节 / 页码"}
                    <input
                      value={s[k] || ""}
                      onChange={(e) =>
                        set(
                          "sources",
                          data.sources.map((x: Data, j: number) =>
                            i === j ? { ...x, [k]: e.target.value } : x,
                          ),
                        )
                      }
                    />
                  </label>
                ))}
              </div>
            ))}
            <button
              onClick={() =>
                set("sources", [
                  ...(data.sources || []),
                  {
                    source_id: "s_" + crypto.randomUUID(),
                    url: "",
                    locator: "",
                  },
                ])
              }
            >
              <Plus size={14} />
              添加来源
            </button>
          </details>
          {data.type === "concept" && (
            <p className="muted">
              定义与适用范围使用上方字段。正文补充说明、公式与来源，不重复保存定义。
            </p>
          )}
          <label>
            Markdown 正文
            <textarea
              aria-label="Markdown 正文"
              className="markdown-input"
              spellCheck={false}
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
          </label>
        </>
      )}
      <p className="muted small">
        保存后分别报告主记录、索引和 HTML 的结果。基准：
        {doc.sha256 === "missing" ? "新记录" : doc.sha256.slice(0, 16) + "…"}
      </p>
    </div>
  );
}
