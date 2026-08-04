"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getProduct, Product, ProductField } from "@/lib/api";

function confidenceClass(c: number): string {
  if (c >= 0.8) return "conf-high";
  if (c >= 0.6) return "conf-medium";
  return "conf-low";
}

function confidenceLabel(c: number): string {
  return `${(c * 100).toFixed(0)}%`;
}

const SOURCE_ICONS: Record<string, string> = {
  doc: "📄",
  image: "📷",
  web: "🌐",
  kg: "🧠",
  human: "✋",
};

const UNCERTAINTY_LABELS: Record<string, { label: string; color: string }> = {
  source_contradiction:    { label: "⚡ Source Contradiction",     color: "text-red-400" },
  single_source:           { label: "⚠ Single Source",            color: "text-amber-400" },
  low_quality_extraction:  { label: "⚠ Low Quality Extraction",   color: "text-amber-400" },
  no_source_found:         { label: "✕ No Source Found",          color: "text-red-500" },
  none:                    { label: "",                             color: "" },
};

function FieldCard({ field }: { field: ProductField }) {
  const [open, setOpen] = useState(false);
  const confClass = confidenceClass(field.confidence);
  const isContradiction = field.verification_status === "contradiction";
  const uncertaintyMeta = UNCERTAINTY_LABELS[field.uncertainty_reason] ?? { label: "", color: "" };

  // Split sources into confirmed vs conflicting based on whether they agree with field.value
  const confirmingSources = field.sources.filter(
    (s) =>
      s.extracted_snippet &&
      field.value &&
      s.extracted_snippet.toLowerCase().includes(field.value.toLowerCase().split(" ")[0])
  );
  // Everything else goes to conflicting (heuristic — good enough for demo)
  const conflictingSources = field.sources.filter(
    (s) => !confirmingSources.includes(s)
  );

  return (
    <div
      className={`rounded-xl overflow-hidden border transition-all duration-200 ${
        isContradiction
          ? "border-red-500/40 bg-red-950/20"
          : "glass border-zinc-800/40"
      }`}
    >
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="text-xs text-zinc-500 font-mono uppercase tracking-wide mb-1">
              {field.field_name.replace(/_/g, " ")}
              {field.schema_field_id && (
                <span className="ml-2 text-zinc-600">· {field.schema_field_id}</span>
              )}
            </div>

            {/* Contradiction: show both values side by side */}
            {isContradiction && field.contradicting_value ? (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-zinc-100 bg-zinc-800/60 px-2 py-0.5 rounded">
                  {field.value}
                </span>
                <span className="text-xs text-red-400 font-mono">vs</span>
                <span className="text-sm font-medium text-red-300 bg-red-950/40 border border-red-500/30 px-2 py-0.5 rounded line-through opacity-70">
                  {field.contradicting_value}
                </span>
              </div>
            ) : (
              <div className="text-sm font-medium text-zinc-100 truncate">
                {field.value || <span className="text-zinc-600 italic">No value found</span>}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              id={`badge-${field.id}`}
              onClick={() => setOpen(!open)}
              className={`border rounded-md px-2 py-0.5 text-xs font-mono font-medium cursor-pointer hover:opacity-80 transition-opacity ${confClass}`}
            >
              {confidenceLabel(field.confidence)}
            </button>
          </div>
        </div>

        {/* Contradiction banner */}
        {isContradiction && (
          <div className="mt-2 flex items-center gap-1.5 text-xs text-red-400 bg-red-950/30 border border-red-500/20 rounded-md px-2 py-1">
            <span>⚡</span>
            <span className="font-mono">SOURCE CONTRADICTION — sources disagree on this value. Human review required.</span>
          </div>
        )}

        {/* Other uncertainty reasons */}
        {!isContradiction && uncertaintyMeta.label && (
          <div className={`mt-2 text-xs font-mono ${uncertaintyMeta.color}`}>
            {uncertaintyMeta.label}
          </div>
        )}
      </div>

      {/* Citation drawer */}
      {open && (
        <div className="citation-drawer border-t border-zinc-800/40 bg-zinc-900/60 p-4">
          {field.sources.length === 0 ? (
            <p className="text-xs text-zinc-600">No sources recorded.</p>
          ) : (
            <div className="space-y-4">
              {/* Confirmed sources */}
              {field.sources.length > 0 && (
                <div>
                  <div className="text-xs font-mono text-zinc-500 uppercase tracking-wider mb-2">
                    {isContradiction ? `Supporting "${field.value}"` : `Sources (${field.sources.length})`}
                  </div>
                  <div className="space-y-2">
                    {(isContradiction ? confirmingSources : field.sources).map((src) => (
                      <div key={src.id} className="flex gap-3">
                        <span className="text-base flex-shrink-0">{SOURCE_ICONS[src.source_type] || "?"}</span>
                        <div>
                          <div className="text-xs font-mono text-zinc-400 mb-0.5">{src.source_ref}</div>
                          {src.extracted_snippet && (
                            <div className="text-xs text-zinc-600 italic">"{src.extracted_snippet}"</div>
                          )}
                          <div className="text-xs text-zinc-700 mt-0.5">via {src.extraction_agent}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Conflicting sources — only shown during contradictions */}
              {isContradiction && field.contradicting_value && (
                <div>
                  <div className="text-xs font-mono text-red-500/70 uppercase tracking-wider mb-2">
                    Conflicting — "{field.contradicting_value}"
                  </div>
                  <div className="space-y-2">
                    {conflictingSources.map((src) => (
                      <div key={src.id} className="flex gap-3 opacity-70">
                        <span className="text-base flex-shrink-0">{SOURCE_ICONS[src.source_type] || "?"}</span>
                        <div>
                          <div className="text-xs font-mono text-red-400/80 mb-0.5">{src.source_ref}</div>
                          {src.extracted_snippet && (
                            <div className="text-xs text-red-600/60 italic">"{src.extracted_snippet}"</div>
                          )}
                          <div className="text-xs text-zinc-700 mt-0.5">via {src.extraction_agent}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


export default function ProductPage() {
  const { productId } = useParams<{ productId: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!productId) return;
    const load = async () => {
      try {
        const p = await getProduct(productId);
        setProduct(p);
      } finally {
        setLoading(false);
      }
    };
    load();
    // Poll every 3s while processing
    const interval = setInterval(async () => {
      const p = await getProduct(productId).catch(() => null);
      if (p) {
        setProduct(p);
        if (p.status !== "processing") clearInterval(interval);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [productId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span key={i} className="w-2 h-2 rounded-full bg-zinc-600 stream-dot" style={{ animationDelay: `${i * 0.2}s` }} />
          ))}
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-zinc-500">
        Product not found.
      </div>
    );
  }

  const verified = product.fields.filter((f) => f.verification_status === "verified");
  const review = product.fields.filter((f) => f.confidence < 0.7);
  const avgConf = product.fields.length > 0
    ? product.fields.reduce((s, f) => s + f.confidence, 0) / product.fields.length
    : 0;

  return (
    <div className="max-w-5xl mx-auto px-6 py-12">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <span className={`text-xs font-mono px-2 py-0.5 rounded-full border ${
            product.status === "complete" ? "conf-high" :
            product.status === "pending_review" ? "border-amber-500/30 text-amber-400 bg-amber-500/10" :
            "border-zinc-700 text-zinc-400"
          }`}>
            {product.status.replace("_", " ")}
          </span>
          {product.category && (
            <span className="text-xs text-zinc-500 font-mono">{product.category}</span>
          )}
        </div>
        <h1 className="text-3xl font-bold text-zinc-100 mb-1">{product.name}</h1>
        <p className="text-xs text-zinc-600 font-mono">{product.id}</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4 mb-10">
        {[
          { label: "Total Fields", value: product.fields.length },
          { label: "Verified (≥2 sources)", value: verified.length },
          { label: "Avg Confidence", value: `${(avgConf * 100).toFixed(0)}%` },
        ].map((stat) => (
          <div key={stat.label} className="glass rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-zinc-100 font-mono">{stat.value}</div>
            <div className="text-xs text-zinc-500 mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Fields grid */}
      {product.fields.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center text-zinc-600">
          {product.status === "processing" ? (
            <span className="flex flex-col items-center gap-3">
              <span className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <span key={i} className="w-2 h-2 rounded-full bg-zinc-600 stream-dot" />
                ))}
              </span>
              Pipeline still running — fields will appear here shortly.
            </span>
          ) : (
            "No fields extracted."
          )}
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-zinc-300">
              Extracted Fields
            </h2>
            <p className="text-xs text-zinc-600">
              Click a confidence badge to see sources
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {product.fields.map((f) => (
              <FieldCard key={f.id} field={f} />
            ))}
          </div>
        </div>
      )}

      {/* HITL prompt */}
      {review.length > 0 && (
        <div className="mt-8 glass rounded-xl p-5 border border-amber-500/20">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold text-amber-400 mb-0.5">
                {review.length} field{review.length !== 1 ? "s" : ""} need human review
              </div>
              <div className="text-xs text-zinc-500">
                Low-confidence fields are in the review queue — accept, edit, or reject with context.
              </div>
            </div>
            <a
              href="/review"
              className="text-sm font-medium bg-amber-500/15 border border-amber-500/30 text-amber-400 hover:bg-amber-500/25 rounded-lg px-4 py-2 transition-colors flex-shrink-0"
            >
              Go to Review →
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
