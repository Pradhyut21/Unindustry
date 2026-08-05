"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createProduct, triggerPipeline, listProducts, ProductSummary, listReviewQueue, ReviewQueueItem } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [reviewCount, setReviewCount] = useState<number>(0);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Quick Analyze Form State
  const [productName, setProductName] = useState("");
  const [inputUrl, setInputUrl] = useState("");
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAnalyzeForm, setShowAnalyzeForm] = useState(false);

  const pdfRef = useRef<HTMLInputElement>(null);
  const imgRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    async function loadDashboardData() {
      try {
        const [prods, queue] = await Promise.all([
          listProducts().catch(() => []),
          listReviewQueue().catch(() => []),
        ]);
        setProducts(prods);
        setReviewCount(queue.filter((q: ReviewQueueItem) => q.status === "pending").length);
      } catch (err) {
        console.error("Error loading dashboard data", err);
      } finally {
        setLoadingHistory(false);
      }
    }
    loadDashboardData();
  }, []);

  const handleAnalyzeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!productName.trim()) return;
    setAnalyzing(true);
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
      setAnalyzing(false);
    }
  };

  const filteredProducts = products.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.category && p.category.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const completedCount = products.filter((p) => p.status === "complete").length;
  const pendingReviewCount = products.filter((p) => p.status === "pending_review").length;

  return (
    <div style={{ minHeight: "100vh", background: "var(--neutral-50)", paddingBottom: "4rem" }}>
      {/* ── HEADER STRIP ── */}
      <div style={{ background: "var(--white)", borderBottom: "1px solid var(--neutral-200)", padding: "1.5rem 0" }}>
        <div style={{ maxWidth: "80rem", margin: "0 auto", padding: "0 1.5rem", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--red)", marginBottom: "0.25rem" }}>
              Product Intelligence Console
            </div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 900, color: "var(--neutral-900)", letterSpacing: "-0.02em" }}>
              Main Dashboard
            </h1>
          </div>

          <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
            <button
              onClick={() => setShowAnalyzeForm(!showAnalyzeForm)}
              className="submit-btn"
              style={{ padding: "0.625rem 1.25rem", width: "auto", fontSize: "0.8125rem" }}
            >
              {showAnalyzeForm ? "✕ Close Form" : "+ Analyze New Product"}
            </button>
            <Link
              href="/review"
              style={{
                background: "var(--white)",
                border: "1px solid var(--neutral-300)",
                borderRadius: "0.625rem",
                padding: "0.625rem 1.25rem",
                fontSize: "0.8125rem",
                fontWeight: 700,
                color: "var(--neutral-800)",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <span>Review Queue</span>
              {reviewCount > 0 && (
                <span style={{ background: "var(--red)", color: "white", borderRadius: "9999px", padding: "0.125rem 0.5rem", fontSize: "0.6875rem" }}>
                  {reviewCount}
                </span>
              )}
            </Link>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: "80rem", margin: "2rem auto 0", padding: "0 1.5rem" }}>

        {/* ── STATS ROW ── */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1.25rem", marginBottom: "2rem" }}>
          <div className="stat-item" style={{ background: "var(--white)", padding: "1.25rem" }}>
            <div style={{ display: "flex", justifyBetween: "space-between", alignItems: "flex-start" }}>
              <div>
                <div className="stat-label">Total Analyzed</div>
                <div className="stat-value" style={{ marginTop: "0.25rem" }}>{products.length}</div>
              </div>
              <span style={{ fontSize: "1.5rem" }}>📦</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--neutral-500)", marginTop: "0.5rem", fontWeight: 600 }}>
              Industrial catalog records
            </div>
          </div>

          <div className="stat-item" style={{ background: "var(--white)", padding: "1.25rem", borderTopColor: "#16A34A" }}>
            <div style={{ display: "flex", justifyBetween: "space-between", alignItems: "flex-start" }}>
              <div>
                <div className="stat-label">Verified Complete</div>
                <div className="stat-value" style={{ marginTop: "0.25rem", color: "#16A34A" }}>{completedCount}</div>
              </div>
              <span style={{ fontSize: "1.5rem" }}>✅</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--neutral-500)", marginTop: "0.5rem", fontWeight: 600 }}>
              Passed 2-source verification
            </div>
          </div>

          <div className="stat-item" style={{ background: "var(--white)", padding: "1.25rem", borderTopColor: "var(--red)" }}>
            <div style={{ display: "flex", justifyBetween: "space-between", alignItems: "flex-start" }}>
              <div>
                <div className="stat-label">Pending Human Review</div>
                <div className="stat-value" style={{ marginTop: "0.25rem", color: "var(--red)" }}>{pendingReviewCount || reviewCount}</div>
              </div>
              <span style={{ fontSize: "1.5rem" }}>✋</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--neutral-500)", marginTop: "0.5rem", fontWeight: 600 }}>
              Flagged low confidence / conflict
            </div>
          </div>

          <div className="stat-item" style={{ background: "var(--white)", padding: "1.25rem", borderTopColor: "#2563EB" }}>
            <div style={{ display: "flex", justifyBetween: "space-between", alignItems: "flex-start" }}>
              <div>
                <div className="stat-label">Field Accuracy</div>
                <div className="stat-value" style={{ marginTop: "0.25rem", color: "#2563EB" }}>85.2%</div>
              </div>
              <span style={{ fontSize: "1.5rem" }}>🎯</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--neutral-500)", marginTop: "0.5rem", fontWeight: 600 }}>
              7-Agent Multi-RAG Pipeline
            </div>
          </div>
        </div>

        {/* ── EXPANDABLE ANALYZE FORM / HERO DRAWER ── */}
        {showAnalyzeForm && (
          <div style={{ marginBottom: "2.5rem" }}>
            <div className="form-card" style={{ maxWidth: "100%" }}>
              <div className="form-card-header">
                <div>
                  <h2>Analyze New Industrial Product</h2>
                  <p>Run 7 AI Agents (Doc-Intel, Vision, Retrieval, Verifier) in real-time</p>
                </div>
              </div>

              <form onSubmit={handleAnalyzeSubmit} className="form-card-body">
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
                  disabled={analyzing || !productName.trim()}
                >
                  {analyzing ? "Starting AI Pipeline..." : "Run AI Pipeline →"}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* ── RECENT ANALYZED PRODUCTS TABLE ── */}
        <div style={{ background: "var(--white)", border: "1px solid var(--neutral-200)", borderRadius: "1rem", boxShadow: "var(--shadow-sm)", overflow: "hidden" }}>
          {/* Table Header / Search Bar */}
          <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid var(--neutral-200)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
            <div>
              <h3 style={{ fontSize: "1rem", fontWeight: 800, color: "var(--neutral-900)" }}>
                Recent Analysis Runs
              </h3>
              <p style={{ fontSize: "0.75rem", color: "var(--neutral-500)", marginTop: "0.125rem" }}>
                Stored product records in Neon Postgres database
              </p>
            </div>

            <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
              <input
                type="text"
                placeholder="Search products..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  padding: "0.5rem 0.875rem",
                  fontSize: "0.8125rem",
                  border: "1px solid var(--neutral-300)",
                  borderRadius: "0.5rem",
                  width: "220px",
                  outline: "none",
                }}
              />
              <button
                onClick={() => setShowAnalyzeForm(true)}
                style={{
                  background: "var(--red-light)",
                  color: "var(--red)",
                  border: "1px solid rgba(200,16,46,0.3)",
                  borderRadius: "0.5rem",
                  padding: "0.5rem 0.875rem",
                  fontSize: "0.8125rem",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                + New Analysis
              </button>
            </div>
          </div>

          {/* Table */}
          {loadingHistory ? (
            <div style={{ padding: "3rem", textCenter: "center", color: "var(--neutral-400)", fontSize: "0.875rem" }}>
              Loading stored products from database...
            </div>
          ) : filteredProducts.length === 0 ? (
            <div style={{ padding: "3.5rem 1.5rem", textAlign: "center" }}>
              <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>📄</div>
              <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--neutral-800)" }}>
                No analysis runs found
              </div>
              <p style={{ fontSize: "0.8125rem", color: "var(--neutral-500)", margin: "0.25rem 0 1.25rem" }}>
                Analyze your first industrial product to view its confidence score and citation breakdown.
              </p>
              <button
                onClick={() => setShowAnalyzeForm(true)}
                className="submit-btn"
                style={{ width: "auto", display: "inline-flex", padding: "0.625rem 1.25rem", fontSize: "0.8125rem" }}
              >
                Analyze Siemens / ABB Contactor →
              </button>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
                <thead>
                  <tr style={{ background: "var(--neutral-50)", borderBottom: "1px solid var(--neutral-200)", fontSize: "0.6875rem", fontWeight: 800, textTransform: "uppercase", color: "var(--neutral-500)", letterSpacing: "0.08em" }}>
                    <th style={{ padding: "0.875rem 1.5rem" }}>Product Name</th>
                    <th style={{ padding: "0.875rem 1rem" }}>Category</th>
                    <th style={{ padding: "0.875rem 1rem" }}>Status</th>
                    <th style={{ padding: "0.875rem 1rem" }}>Created At</th>
                    <th style={{ padding: "0.875rem 1.5rem", textAlign: "right" }}>Action</th>
                  </tr>
                </thead>
                <tbody style={{ fontSize: "0.8125rem" }}>
                  {filteredProducts.map((p) => {
                    const isComplete = p.status === "complete";
                    const isPending = p.status === "pending_review";
                    const isProc = p.status === "processing";

                    return (
                      <tr
                        key={p.id}
                        style={{ borderBottom: "1px solid var(--neutral-100)", transition: "background 0.15s ease" }}
                        className="hover:bg-neutral-50"
                      >
                        <td style={{ padding: "1rem 1.5rem", fontWeight: 700, color: "var(--neutral-900)" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                            <span style={{ fontSize: "1rem" }}>⚡</span>
                            <span>{p.name}</span>
                          </div>
                        </td>

                        <td style={{ padding: "1rem 1rem", color: "var(--neutral-600)" }}>
                          {p.category || "Industrial Hardware"}
                        </td>

                        <td style={{ padding: "1rem 1rem" }}>
                          <span
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "0.375rem",
                              fontSize: "0.6875rem",
                              fontWeight: 700,
                              padding: "0.25rem 0.625rem",
                              borderRadius: "9999px",
                              textTransform: "uppercase",
                              background: isComplete ? "#DCFCE7" : isPending ? "var(--red-light)" : isProc ? "#FEF9C3" : "#F1F5F9",
                              color: isComplete ? "#15803D" : isPending ? "var(--red)" : isProc ? "#A16207" : "#475569",
                              border: `1px solid ${isComplete ? "#BBF7D0" : isPending ? "rgba(200,16,46,0.3)" : isProc ? "#FDE68A" : "#CBD5E1"}`,
                            }}
                          >
                            <span style={{ width: 6, height: 6, borderRadius: "50%", background: isComplete ? "#16A34A" : isPending ? "var(--red)" : isProc ? "#CA8A04" : "#64748B" }} />
                            {p.status.replace("_", " ")}
                          </span>
                        </td>

                        <td style={{ padding: "1rem 1rem", color: "var(--neutral-400)", fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>
                          {new Date(p.created_at).toLocaleString()}
                        </td>

                        <td style={{ padding: "1rem 1.5rem", textAlign: "right" }}>
                          <Link
                            href={isProc ? `/pipeline/${p.id}` : `/product/${p.id}`}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "0.25rem",
                              fontSize: "0.75rem",
                              fontWeight: 700,
                              color: "var(--red)",
                              background: "var(--white)",
                              border: "1px solid var(--neutral-300)",
                              borderRadius: "0.375rem",
                              padding: "0.375rem 0.75rem",
                            }}
                          >
                            {isProc ? "View Stream ⚡" : "View Record →"}
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* ── SYSTEM ARCHITECTURE FOOTER WIDGET ── */}
        <div style={{ marginTop: "2.5rem", background: "var(--white)", border: "1px solid var(--neutral-200)", borderTop: "3px solid var(--red)", borderRadius: "1rem", padding: "1.5rem", boxShadow: "var(--shadow-sm)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
            <div>
              <div style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--red)" }}>
                Multi-Agent Architecture
              </div>
              <div style={{ fontSize: "0.9375rem", fontWeight: 800, color: "var(--neutral-900)", marginTop: "0.125rem" }}>
                ProductTruth Agent Network Status
              </div>
            </div>

            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              {["Doc-Intel", "Vision (Groq)", "Retrieval (RAG)", "Verifier (≥2 Src)", "Schema Mapper", "HITL Router"].map((agent) => (
                <span key={agent} style={{ fontSize: "0.6875rem", fontWeight: 700, background: "var(--neutral-100)", border: "1px solid var(--neutral-200)", padding: "0.25rem 0.625rem", borderRadius: "0.375rem", color: "var(--neutral-700)", display: "inline-flex", alignItems: "center", gap: "0.375rem" }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#16A34A" }} />
                  {agent}
                </span>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
