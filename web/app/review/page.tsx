"use client";

import { useEffect, useState } from "react";
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

function confidenceClass(c: number): string {
  if (c >= 0.8) return "conf-high";
  if (c >= 0.6) return "conf-medium";
  return "conf-low";
}

export default function ReviewPage() {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewer, setReviewer] = useState("reviewer");
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
    <div className="max-w-5xl mx-auto px-6 py-12">
      <div className="mb-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-zinc-100 mb-1">Human Review Queue</h1>
            <p className="text-sm text-zinc-500">
              Low-confidence fields that need a reviewer before going live.
              All corrections are logged as knowledge graph sources.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-zinc-500 font-mono">Reviewer:</label>
            <input
              id="reviewer-name"
              type="text"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-violet-500/60 w-36"
            />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <span key={i} className="w-2 h-2 rounded-full bg-zinc-600 stream-dot" />
            ))}
          </div>
        </div>
      ) : items.length === 0 ? (
        <div className="glass rounded-xl p-16 text-center">
          <div className="text-4xl mb-4">✓</div>
          <div className="text-lg font-semibold text-emerald-400 mb-2">Queue is clear</div>
          <div className="text-sm text-zinc-500">
            All fields have been reviewed or passed automatic verification.
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="text-xs text-zinc-500 font-mono mb-2">
            {items.length} item{items.length !== 1 ? "s" : ""} pending review
          </div>
          {items.map((item) => {
            const f = item.field;
            return (
              <div key={item.id} className="glass rounded-xl overflow-hidden border border-amber-500/10">
                {/* Field header */}
                <div className="p-5 border-b border-zinc-800/40">
                  <div className="flex items-start gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-mono text-zinc-500 uppercase tracking-wide">
                          {f.field_name.replace(/_/g, " ")}
                        </span>
                        <span className={`border rounded px-1.5 py-0.5 text-xs font-mono ${confidenceClass(f.confidence)}`}>
                          {(f.confidence * 100).toFixed(0)}% confidence
                        </span>
                        {f.uncertainty_reason !== "none" && (
                          <span className="text-xs text-amber-400/70 font-mono">
                            · {f.uncertainty_reason.replace(/_/g, " ")}
                          </span>
                        )}
                      </div>
                      <div className="text-lg font-semibold text-zinc-100">
                        {f.value || <span className="text-zinc-600 italic text-base">No value extracted</span>}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Sources */}
                <div className="px-5 py-4 bg-zinc-900/40 border-b border-zinc-800/40">
                  <div className="text-xs font-mono text-zinc-500 mb-2">Evidence</div>
                  {f.sources.length === 0 ? (
                    <p className="text-xs text-zinc-600">No sources available.</p>
                  ) : (
                    <div className="space-y-2">
                      {f.sources.map((src) => (
                        <div key={src.id} className="flex gap-3 text-xs">
                          <span>{SOURCE_ICONS[src.source_type] || "?"}</span>
                          <div>
                            <span className="text-zinc-400 font-mono">{src.source_ref}</span>
                            {src.extracted_snippet && (
                              <span className="text-zinc-600 ml-2 italic">
                                "{src.extracted_snippet.slice(0, 100)}"
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="p-5">
                  <div className="flex items-center gap-3 flex-wrap">
                    <input
                      id={`edit-${item.id}`}
                      type="text"
                      placeholder="Corrected value (for Edit)..."
                      value={editValues[item.id] || ""}
                      onChange={(e) =>
                        setEditValues((prev) => ({ ...prev, [item.id]: e.target.value }))
                      }
                      className="flex-1 min-w-48 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-violet-500/60"
                    />
                    <button
                      id={`accept-${item.id}`}
                      onClick={() => handleAction(item.id, "accepted")}
                      disabled={actioning === item.id}
                      className="text-sm font-medium bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/25 rounded-lg px-4 py-2 transition-colors disabled:opacity-50"
                    >
                      Accept
                    </button>
                    <button
                      id={`edit-btn-${item.id}`}
                      onClick={() => handleAction(item.id, "edited")}
                      disabled={actioning === item.id || !editValues[item.id]}
                      className="text-sm font-medium bg-violet-500/15 border border-violet-500/30 text-violet-400 hover:bg-violet-500/25 rounded-lg px-4 py-2 transition-colors disabled:opacity-50"
                    >
                      Edit & Accept
                    </button>
                    <button
                      id={`reject-${item.id}`}
                      onClick={() => handleAction(item.id, "rejected")}
                      disabled={actioning === item.id}
                      className="text-sm font-medium bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 rounded-lg px-4 py-2 transition-colors disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
