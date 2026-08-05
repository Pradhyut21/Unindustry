"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  listReviewQueue,
  submitReviewAction,
  ReviewQueueItem,
} from "@/lib/api";

const SOURCE_ICONS: Record<string, string> = {
  doc: "📄",
  image: "📷",
  web: "🌐",
  kg: "🧠",
  human: "✋",
};

export default function ReviewPage() {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewer, setReviewer] = useState("Reviewer 1");
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [actioning, setActioning] = useState<string | null>(null);

  useEffect(() => {
    listReviewQueue().then(setItems).finally(() => setLoading(false));
  }, []);

  const handleAction = async (
    itemId: string,
    action: "accepted" | "edited" | "rejected"
  ) => {
    setActioning(itemId);
    try {
      await submitReviewAction(
        itemId,
        action,
        reviewer,
        action === "edited" ? editValues[itemId] : undefined
      );
      setItems((prev) => prev.filter((i) => i.id !== itemId));
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setActioning(null);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--neutral-50)", padding: "3rem 1.5rem 5rem" }}>
      <div style={{ maxWidth: "64rem", margin: "0 auto" }}>

        {/* Back link */}
        <div style={{ marginBottom: "1.5rem" }}>
          <Link href="/" style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--neutral-500)", textDecoration: "none" }}>
            ← Back to Main Dashboard
          </Link>
        </div>

        {/* Page Header */}
        <div style={{ background: "var(--white)", border: "1px solid var(--neutral-200)", borderTop: "4px solid var(--red)", borderRadius: "1rem", padding: "1.75rem", boxShadow: "var(--shadow-sm)", marginBottom: "2rem", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--red)", marginBottom: "0.25rem" }}>
              Human-in-the-Loop Audit Queue
            </div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 900, color: "var(--neutral-900)", letterSpacing: "-0.025em" }}>
              Review Queue ({items.length})
            </h1>
            <p style={{ fontSize: "0.8125rem", color: "var(--neutral-500)", marginTop: "0.25rem" }}>
              Low-confidence & contradicted fields flagged by VerifierAgent before going live.
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", background: "var(--neutral-50)", border: "1px solid var(--neutral-200)", padding: "0.5rem 0.875rem", borderRadius: "0.625rem" }}>
            <label style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--neutral-600)" }}>Reviewer:</label>
            <input
              id="reviewer-name"
              type="text"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              style={{ background: "var(--white)", border: "1px solid var(--neutral-300)", borderRadius: "0.375rem", padding: "0.25rem 0.625rem", fontSize: "0.8125rem", fontWeight: 600, color: "var(--neutral-900)", width: "120px", outline: "none" }}
            />
          </div>
        </div>

        {/* Queue Items */}
        {loading ? (
          <div style={{ padding: "4rem", textAlign: "center", color: "var(--neutral-400)", fontSize: "0.875rem" }}>
            Loading review items from database...
          </div>
        ) : items.length === 0 ? (
          <div style={{ background: "var(--white)", border: "1px solid var(--neutral-200)", borderRadius: "1rem", padding: "4rem 1.5rem", textAlign: "center" }}>
            <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>🛡️</div>
            <div style={{ fontSize: "1.125rem", fontWeight: 800, color: "#15803D", marginBottom: "0.25rem" }}>
              Review Queue Clear!
            </div>
            <p style={{ fontSize: "0.8125rem", color: "var(--neutral-500)", maxWidth: "24rem", margin: "0 auto" }}>
              All fields have passed automatic 2-source verification or have already been reviewed.
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {items.map((item) => {
              const f = item.field;
              return (
                <div
                  key={item.id}
                  style={{
                    background: "var(--white)",
                    border: "1px solid var(--neutral-200)",
                    borderLeft: "4px solid var(--red)",
                    borderRadius: "0.875rem",
                    overflow: "hidden",
                    boxShadow: "var(--shadow-sm)",
                  }}
                >
                  {/* Card Header */}
                  <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid var(--neutral-100)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.375rem" }}>
                          <span style={{ fontSize: "0.6875rem", fontWeight: 700, fontFamily: "var(--font-mono)", textTransform: "uppercase", color: "var(--neutral-400)" }}>
                            {f.field_name.replace(/_/g, " ")}
                          </span>
                          <span className={`conf-badge ${f.confidence >= 0.8 ? "high" : f.confidence >= 0.6 ? "medium" : "low"}`}>
                            {(f.confidence * 100).toFixed(0)}% Confidence
                          </span>
                          {f.uncertainty_reason !== "none" && (
                            <span style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--red)", background: "var(--red-light)", padding: "0.125rem 0.375rem", borderRadius: "0.25rem", fontFamily: "var(--font-mono)" }}>
                              {f.uncertainty_reason.replace(/_/g, " ")}
                            </span>
                          )}
                        </div>

                        <div style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--neutral-900)" }}>
                          {f.value || <span style={{ color: "var(--neutral-400)", fontStyle: "italic", fontWeight: 400 }}>No value extracted</span>}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Source Evidence */}
                  <div style={{ background: "var(--neutral-50)", padding: "1rem 1.5rem", borderBottom: "1px solid var(--neutral-100)" }}>
                    <div style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", color: "var(--neutral-400)", fontFamily: "var(--font-mono)", marginBottom: "0.5rem" }}>
                      Extracted Evidence & Citations
                    </div>
                    {f.sources.length === 0 ? (
                      <p style={{ fontSize: "0.75rem", color: "var(--neutral-400)" }}>No source citations logged.</p>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem" }}>
                        {f.sources.map((src) => (
                          <div key={src.id} style={{ display: "flex", gap: "0.5rem", fontSize: "0.75rem", alignItems: "center" }}>
                            <span>{SOURCE_ICONS[src.source_type] || "📄"}</span>
                            <span style={{ fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--neutral-800)" }}>{src.source_ref}</span>
                            {src.extracted_snippet && (
                              <span style={{ color: "var(--neutral-500)", fontStyle: "italic" }}>
                                {`"${src.extracted_snippet.slice(0, 120)}"`}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div style={{ padding: "1.25rem 1.5rem", display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                    <input
                      id={`edit-${item.id}`}
                      type="text"
                      placeholder="Enter corrected value to edit..."
                      value={editValues[item.id] || ""}
                      onChange={(e) =>
                        setEditValues((prev) => ({ ...prev, [item.id]: e.target.value }))
                      }
                      style={{
                        flex: "1 1 200px",
                        padding: "0.5rem 0.875rem",
                        fontSize: "0.8125rem",
                        border: "1px solid var(--neutral-300)",
                        borderRadius: "0.5rem",
                        outline: "none",
                      }}
                    />

                    <button
                      id={`accept-${item.id}`}
                      onClick={() => handleAction(item.id, "accepted")}
                      disabled={actioning === item.id}
                      style={{
                        background: "#DCFCE7",
                        color: "#15803D",
                        border: "1px solid #BBF7D0",
                        borderRadius: "0.5rem",
                        padding: "0.5rem 1rem",
                        fontSize: "0.8125rem",
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      ✓ Accept
                    </button>

                    <button
                      id={`edit-btn-${item.id}`}
                      onClick={() => handleAction(item.id, "edited")}
                      disabled={actioning === item.id || !editValues[item.id]}
                      style={{
                        background: "var(--neutral-900)",
                        color: "white",
                        border: "none",
                        borderRadius: "0.5rem",
                        padding: "0.5rem 1rem",
                        fontSize: "0.8125rem",
                        fontWeight: 700,
                        cursor: actioning === item.id || !editValues[item.id] ? "not-allowed" : "pointer",
                        opacity: actioning === item.id || !editValues[item.id] ? 0.5 : 1,
                      }}
                    >
                      ✏ Edit & Accept
                    </button>

                    <button
                      id={`reject-${item.id}`}
                      onClick={() => handleAction(item.id, "rejected")}
                      disabled={actioning === item.id}
                      style={{
                        background: "var(--red-light)",
                        color: "var(--red)",
                        border: "1px solid rgba(200,16,46,0.3)",
                        borderRadius: "0.5rem",
                        padding: "0.5rem 1rem",
                        fontSize: "0.8125rem",
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      ✕ Reject
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

      </div>
    </div>
  );
}
