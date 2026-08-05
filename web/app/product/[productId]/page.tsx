"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
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
  source_contradiction:   { label: "⚡ Source Contradiction", color: "var(--red)" },
  single_source:          { label: "⚠ Single Source", color: "#D97706" },
  low_quality_extraction: { label: "⚠ Low Quality Extraction", color: "#D97706" },
  no_source_found:        { label: "✕ No Source Found", color: "var(--red)" },
  none:                   { label: "", color: "" },
};

function FieldCard({ field }: { field: ProductField }) {
  const [open, setOpen] = useState(false);
  const confClass = confidenceClass(field.confidence);
  const isContradiction = field.verification_status === "contradiction";
  const uncertaintyMeta = UNCERTAINTY_LABELS[field.uncertainty_reason] ?? { label: "", color: "" };

  const confirmingSources = field.sources.filter(
    (s) =>
      s.extracted_snippet &&
      field.value &&
      s.extracted_snippet.toLowerCase().includes(field.value.toLowerCase().split(" ")[0])
  );
  const conflictingSources = field.sources.filter(
    (s) => !confirmingSources.includes(s)
  );

  return (
    <div
      style={{
        background: "var(--white)",
        border: isContradiction ? "1.5px solid var(--red)" : "1px solid var(--neutral-200)",
        borderRadius: "0.75rem",
        overflow: "hidden",
        boxShadow: "var(--shadow-sm)",
        transition: "all 0.15s ease",
      }}
    >
      <div style={{ padding: "1rem 1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.75rem" }}>
          <div style={{ flex: "1 1 0%", minWidth: 0 }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--neutral-400)", marginBottom: "0.25rem", fontFamily: "var(--font-mono)" }}>
              {field.field_name.replace(/_/g, " ")}
              {field.schema_field_id && (
                <span style={{ color: "var(--neutral-400)", marginLeft: "0.5rem" }}>· {field.schema_field_id}</span>
              )}
            </div>

            {isContradiction && field.contradicting_value ? (
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                <span style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--neutral-900)", background: "var(--neutral-100)", padding: "0.125rem 0.5rem", borderRadius: "0.25rem" }}>
                  {field.value}
                </span>
                <span style={{ fontSize: "0.75rem", color: "var(--red)", fontWeight: 700, fontFamily: "var(--font-mono)" }}>vs</span>
                <span style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--red)", background: "var(--red-light)", padding: "0.125rem 0.5rem", borderRadius: "0.25rem", textDecoration: "line-through", opacity: 0.8 }}>
                  {field.contradicting_value}
                </span>
              </div>
            ) : (
              <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--neutral-900)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {field.value || <span style={{ color: "var(--neutral-400)", fontStyle: "italic", fontWeight: 400 }}>No value found</span>}
              </div>
            )}
          </div>

          <button
            id={`badge-${field.id}`}
            onClick={() => setOpen(!open)}
            className={`conf-badge ${field.confidence >= 0.8 ? "high" : field.confidence >= 0.6 ? "medium" : "low"}`}
            style={{ cursor: "pointer" }}
          >
            {confidenceLabel(field.confidence)}
          </button>
        </div>

        {isContradiction && (
          <div style={{ marginTop: "0.625rem", fontSize: "0.75rem", color: "var(--red)", background: "var(--red-light)", border: "1px solid rgba(200,16,46,0.25)", borderRadius: "0.375rem", padding: "0.375rem 0.625rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "0.375rem" }}>
            <span>⚡</span>
            <span>SOURCE CONTRADICTION — sources disagree on this value. Human review required.</span>
          </div>
        )}

        {!isContradiction && uncertaintyMeta.label && (
          <div style={{ marginTop: "0.5rem", fontSize: "0.75rem", fontFamily: "var(--font-mono)", color: uncertaintyMeta.color, fontWeight: 600 }}>
            {uncertaintyMeta.label}
          </div>
        )}
      </div>

      {/* Citation drawer */}
      {open && (
        <div style={{ borderTop: "1px solid var(--neutral-200)", background: "var(--neutral-50)", padding: "1rem 1.25rem" }}>
          {field.sources.length === 0 ? (
            <p style={{ fontSize: "0.75rem", color: "var(--neutral-400)" }}>No sources recorded.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div>
                <div style={{ fontSize: "0.6875rem", fontFamily: "var(--font-mono)", color: "var(--neutral-500)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 700, marginBottom: "0.5rem" }}>
                  {isContradiction ? `Supporting "${field.value}"` : `Sources (${field.sources.length})`}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {(isContradiction ? confirmingSources : field.sources).map((src) => (
                    <div key={src.id} style={{ display: "flex", gap: "0.625rem", fontSize: "0.75rem" }}>
                      <span style={{ fontSize: "1rem", flexShrink: 0 }}>{SOURCE_ICONS[src.source_type] || "📄"}</span>
                      <div>
                        <div style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: "var(--neutral-800)" }}>{src.source_ref}</div>
                        {src.extracted_snippet && (
                          <div style={{ color: "var(--neutral-600)", fontStyle: "italic", marginTop: "0.125rem" }}>{`"${src.extracted_snippet}"`}</div>
                        )}
                        <div style={{ color: "var(--neutral-400)", fontSize: "0.6875rem", marginTop: "0.125rem" }}>via {src.extraction_agent}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {isContradiction && field.contradicting_value && (
                <div style={{ borderTop: "1px border var(--neutral-200)", paddingTop: "0.5rem" }}>
                  <div style={{ fontSize: "0.6875rem", fontFamily: "var(--font-mono)", color: "var(--red)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 700, marginBottom: "0.5rem" }}>
                    {`Conflicting — "${field.contradicting_value}"`}
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    {conflictingSources.map((src) => (
                      <div key={src.id} style={{ display: "flex", gap: "0.625rem", fontSize: "0.75rem", opacity: 0.8 }}>
                        <span style={{ fontSize: "1rem", flexShrink: 0 }}>{SOURCE_ICONS[src.source_type] || "📄"}</span>
                        <div>
                          <div style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: "var(--red)" }}>{src.source_ref}</div>
                          {src.extracted_snippet && (
                            <div style={{ color: "var(--neutral-600)", fontStyle: "italic", marginTop: "0.125rem" }}>{`"${src.extracted_snippet}"`}</div>
                          )}
                          <div style={{ color: "var(--neutral-400)", fontSize: "0.6875rem", marginTop: "0.125rem" }}>via {src.extraction_agent}</div>
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
      <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--neutral-400)" }}>
        Loading product details...
      </div>
    );
  }

  if (!product) {
    return (
      <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--neutral-400)" }}>
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
    <div style={{ minHeight: "100vh", background: "var(--neutral-50)", padding: "3rem 1.5rem 5rem" }}>
      <div style={{ maxWidth: "64rem", margin: "0 auto" }}>

        {/* Back navigation link */}
        <div style={{ marginBottom: "1.5rem" }}>
          <Link href="/" style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--neutral-500)", textDecoration: "none" }}>
            ← Back to Main Dashboard
          </Link>
        </div>

        {/* Product header card */}
        <div style={{ background: "var(--white)", border: "1px solid var(--neutral-200)", borderTop: "4px solid var(--red)", borderRadius: "1rem", padding: "1.75rem", boxShadow: "var(--shadow-sm)", marginBottom: "2rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", flexWrap: "wrap" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                <span style={{
                  fontSize: "0.6875rem",
                  fontWeight: 700,
                  padding: "0.25rem 0.625rem",
                  borderRadius: "9999px",
                  textTransform: "uppercase",
                  background: product.status === "complete" ? "#DCFCE7" : product.status === "pending_review" ? "var(--red-light)" : "#FEF9C3",
                  color: product.status === "complete" ? "#15803D" : product.status === "pending_review" ? "var(--red)" : "#A16207",
                  border: `1px solid ${product.status === "complete" ? "#BBF7D0" : product.status === "pending_review" ? "rgba(200,16,46,0.3)" : "#FDE68A"}`
                }}>
                  {product.status.replace("_", " ")}
                </span>
                {product.category && (
                  <span style={{ fontSize: "0.75rem", color: "var(--neutral-500)", fontWeight: 600 }}>{product.category}</span>
                )}
              </div>

              <h1 style={{ fontSize: "2rem", fontWeight: 900, color: "var(--neutral-900)", letterSpacing: "-0.025em" }}>
                {product.name}
              </h1>
              <p style={{ fontSize: "0.75rem", color: "var(--neutral-400)", fontFamily: "var(--font-mono)", marginTop: "0.25rem" }}>
                ID: {product.id}
              </p>
            </div>

            <Link
              href="/analyze"
              className="submit-btn"
              style={{ width: "auto", padding: "0.625rem 1.25rem", fontSize: "0.8125rem" }}
            >
              + Analyze Another
            </Link>
          </div>

          {/* Stats strip */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginTop: "1.5rem", paddingTop: "1.5rem", borderTop: "1px solid var(--neutral-100)" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "1.75rem", fontWeight: 900, color: "var(--neutral-900)", fontFamily: "var(--font-mono)" }}>
                {product.fields.length}
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--neutral-500)", fontWeight: 600, marginTop: "0.125rem" }}>Total Fields</div>
            </div>

            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "1.75rem", fontWeight: 900, color: "#16A34A", fontFamily: "var(--font-mono)" }}>
                {verified.length}
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--neutral-500)", fontWeight: 600, marginTop: "0.125rem" }}>Verified (≥2 sources)</div>
            </div>

            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "1.75rem", fontWeight: 900, color: "var(--red)", fontFamily: "var(--font-mono)" }}>
                {(avgConf * 100).toFixed(0)}%
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--neutral-500)", fontWeight: 600, marginTop: "0.125rem" }}>Avg Confidence</div>
            </div>
          </div>
        </div>

        {/* Fields grid */}
        {product.fields.length === 0 ? (
          <div style={{ background: "var(--white)", border: "1px solid var(--neutral-200)", borderRadius: "1rem", padding: "3.5rem 1.5rem", textAlign: "center", color: "var(--neutral-500)" }}>
            {product.status === "processing" ? "Pipeline still running — fields will appear here shortly." : "No fields extracted."}
          </div>
        ) : (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h2 style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--neutral-900)" }}>
                Extracted Fields ({product.fields.length})
              </h2>
              <span style={{ fontSize: "0.75rem", color: "var(--neutral-400)", fontWeight: 600 }}>
                Click confidence badge to view source evidence
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1rem" }}>
              {product.fields.map((f) => (
                <FieldCard key={f.id} field={f} />
              ))}
            </div>
          </div>
        )}

        {/* Human review prompt card */}
        {review.length > 0 && (
          <div style={{ marginTop: "2.5rem", background: "var(--red-light)", border: "1px solid rgba(200,16,46,0.3)", borderLeft: "4px solid var(--red)", borderRadius: "0.75rem", padding: "1.25rem 1.5rem", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
            <div>
              <div style={{ fontSize: "0.875rem", fontWeight: 800, color: "var(--red-dark)" }}>
                {review.length} field{review.length !== 1 ? "s" : ""} flagged for human review
              </div>
              <div style={{ fontSize: "0.8125rem", color: "var(--neutral-700)", marginTop: "0.125rem" }}>
                Low confidence or single-source fields are in the review queue ready for manual approval or correction.
              </div>
            </div>
            <Link
              href="/review"
              style={{ background: "var(--red)", color: "white", padding: "0.625rem 1.25rem", borderRadius: "0.5rem", fontSize: "0.8125rem", fontWeight: 700, textDecoration: "none" }}
            >
              Go to Review Queue →
            </Link>
          </div>
        )}

      </div>
    </div>
  );
}
