"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { createProduct, triggerPipeline } from "@/lib/api";

export default function AnalyzePage() {
  const router = useRouter();
  const [productName, setProductName] = useState("");
  const [inputUrl, setInputUrl] = useState("");
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pdfRef = useRef<HTMLInputElement>(null);
  const imgRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!productName.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("name", productName.trim());
      if (inputUrl) fd.append("input_url", inputUrl);
      if (pdfFile) fd.append("pdf_file", pdfFile);
      imageFiles.forEach((f) => fd.append("image_files", f));

      const product = await createProduct(fd);
      await triggerPipeline(product.id);
      router.push(`/pipeline/${product.id}`);
    } catch (err) {
      setError((err as Error).message);
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--neutral-50)" }}>
      {/* ── HERO ── */}
      <section className="hero">
        <div className="hero-inner">
          {/* Left: copy + form */}
          <div>
            <div className="hero-label">
              <span className="hero-label-dot" />
              AI-Powered · Provenance-Verified · Commerce-Ready
            </div>

            <h1 className="hero-title">
              Industrial data,{" "}
              <span className="hero-title-accent">verified</span>{" "}
              at every field.
            </h1>
            <p className="hero-desc">
              Give ProductTruth a product name, spec sheet, or photo — and get a
              structured, commerce-ready record where every field is
              confidence-scored and traceable to its source.
            </p>

            {/* Stats */}
            <div className="stats-strip">
              <div className="stat-item">
                <div className="stat-value">85.2%</div>
                <div className="stat-label">Field Accuracy</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">7</div>
                <div className="stat-label">AI Agents</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">100%</div>
                <div className="stat-label">HITL Precision</div>
              </div>
            </div>
          </div>

          {/* Right: 3D product card visual */}
          <div className="hero-visual">
            <div className="product-3d-scene">
              <div className="product-card-3d back2" />
              <div className="product-card-3d back1" />
              <div className="product-card-3d main">
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <div className="product-icon">⚡</div>
                  <div>
                    <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--neutral-900)" }}>
                      Siemens 3RT2015
                    </div>
                    <div style={{ fontSize: "0.625rem", color: "var(--neutral-400)", fontWeight: 600 }}>
                      Industrial Contactor
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "0.625rem", marginTop: "0.5rem" }}>
                  {[
                    { key: "Voltage", val: "24V DC", pct: 92 },
                    { key: "Current Rating", val: "7A AC-3", pct: 88 },
                    { key: "IP Rating", val: "IP20", pct: 95 },
                  ].map((f) => (
                    <div key={f.key} className="product-field-row">
                      <div className="product-field-key">{f.key}</div>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <div className="product-field-val">{f.val}</div>
                        <span className="conf-badge high">{f.pct}%</span>
                      </div>
                      <div className="product-conf-bar">
                        <div className="product-conf-fill" style={{ width: `${f.pct}%` }} />
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: "0.5rem", paddingTop: "0.625rem", borderTop: "1px solid var(--neutral-100)" }}>
                  <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--neutral-400)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    Sources
                  </div>
                  <div style={{ display: "flex", gap: "0.375rem", marginTop: "0.25rem", flexWrap: "wrap" }}>
                    {["doc", "catalog", "llm:groq"].map((s) => (
                      <span key={s} style={{ fontSize: "0.5625rem", background: "var(--neutral-100)", color: "var(--neutral-600)", padding: "0.125rem 0.375rem", borderRadius: "0.25rem", fontWeight: 600, border: "1px solid var(--neutral-200)" }}>
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="floating-badge b1">
                <span className="badge-dot green" /> 9 fields verified
              </div>
              <div className="floating-badge b2">
                <span className="badge-dot amber" /> 2 for review
              </div>
              <div className="floating-badge b3">
                <span className="badge-dot red" /> 3 sources
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── FORM ── */}
      <section className="form-section">
        <div className="form-card">
          <div className="form-card-header">
            <div>
              <h2>Analyze a Product</h2>
              <p>Enter a product name and optionally upload a spec sheet or photos</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="form-card-body">
            <div className="form-group">
              <label className="form-label" htmlFor="product-name">
                Product Name *
              </label>
              <input
                id="product-name"
                type="text"
                className="form-input"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="e.g. Siemens 3RT2015 Contactor, ABB S201 Circuit Breaker..."
                required
              />
            </div>

            <div className="form-grid">
              <div>
                <label className="form-label">Spec Sheet PDF</label>
                <button
                  type="button"
                  className={`upload-btn${pdfFile ? " has-file" : ""}`}
                  onClick={() => pdfRef.current?.click()}
                >
                  📎 {pdfFile ? pdfFile.name : "Upload PDF"}
                </button>
                <input
                  ref={pdfRef}
                  type="file"
                  accept=".pdf"
                  style={{ display: "none" }}
                  onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
                />
              </div>

              <div>
                <label className="form-label">Product Photos (up to 3)</label>
                <button
                  type="button"
                  className={`upload-btn${imageFiles.length > 0 ? " has-file" : ""}`}
                  onClick={() => imgRef.current?.click()}
                >
                  🖼️ {imageFiles.length > 0 ? `${imageFiles.length} image(s) selected` : "Upload Images"}
                </button>
                <input
                  ref={imgRef}
                  type="file"
                  accept="image/*"
                  multiple
                  style={{ display: "none" }}
                  onChange={(e) => setImageFiles(Array.from(e.target.files || []).slice(0, 3))}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="input-url">
                Manufacturer URL (optional)
              </label>
              <input
                id="input-url"
                type="url"
                className="form-input"
                value={inputUrl}
                onChange={(e) => setInputUrl(e.target.value)}
                placeholder="https://manufacturer.com/product/..."
              />
            </div>

            {error && <div className="error-msg">⚠ {error}</div>}

            <button
              id="analyze-btn"
              type="submit"
              className="submit-btn"
              disabled={loading || !productName.trim()}
            >
              {loading ? "Starting pipeline..." : "Run AI Pipeline →"}
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
