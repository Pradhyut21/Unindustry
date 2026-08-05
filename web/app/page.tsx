"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { createProduct, triggerPipeline } from "@/lib/api";

const METRICS = [
  { value: "85.2%", label: "Field Accuracy", sub: "on 27 labeled fields" },
  { value: "100%", label: "HITL Precision", sub: "every wrong field flagged" },
  { value: "+0.45", label: "Calibration Gap", sub: "lower conf when wrong" },
  { value: "7", label: "AI Agents", sub: "parallel extraction" },
];

export default function HomePage() {
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
    <div className="min-h-[calc(100vh-3.5rem)] flex flex-col">
      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-16">
        {/* Background orbs */}
        <div className="absolute top-28 left-1/4 w-[500px] h-[500px] bg-violet-600/8 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute top-36 right-1/4 w-96 h-96 bg-cyan-600/8 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-1/4 left-1/3 w-64 h-64 bg-indigo-600/6 rounded-full blur-3xl pointer-events-none" />

        {/* Badge */}
        <div className="relative z-10 inline-flex items-center gap-2 text-xs font-mono text-violet-400 border border-violet-500/30 rounded-full px-4 py-1.5 mb-8 bg-violet-500/10 backdrop-blur-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
          AI-powered · Provenance-verified · Commerce-ready
        </div>

        {/* Headline */}
        <div className="relative z-10 text-center max-w-3xl mx-auto mb-10">
          <h1 className="text-5xl sm:text-6xl font-bold tracking-tight mb-5 leading-tight">
            <span className="bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
              Every field.
            </span>{" "}
            <span className="bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
              Every source.
            </span>
          </h1>
          <p className="text-lg text-zinc-400 leading-relaxed max-w-2xl mx-auto">
            Give ProductTruth a product name, a spec sheet, or a photo — and get a
            structured, commerce-ready record where every field is confidence-scored
            and traceable to its source. Low-confidence fields go to a human reviewer.
            Nothing ships silently wrong.
          </p>
        </div>

        {/* Input card */}
        <form
          onSubmit={handleSubmit}
          className="relative z-10 w-full max-w-2xl glass rounded-2xl p-8 shadow-2xl shadow-violet-500/5"
        >
          <div className="space-y-5">
            {/* Product name */}
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-2 uppercase tracking-wider">
                Product Name *
              </label>
              <input
                id="product-name"
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="e.g. Siemens 3RT2015 Contactor, ABB S201 Circuit Breaker..."
                className="w-full bg-zinc-900/80 border border-zinc-700/60 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/20 transition-all text-sm"
                required
              />
            </div>

            {/* File uploads */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-2 uppercase tracking-wider">
                  Spec Sheet PDF
                </label>
                <button
                  type="button"
                  onClick={() => pdfRef.current?.click()}
                  className="w-full border border-dashed border-zinc-700/60 rounded-xl px-4 py-3 text-sm text-zinc-500 hover:border-violet-500/40 hover:text-zinc-300 transition-all text-left"
                >
                  {pdfFile ? (
                    <span className="text-violet-400 truncate">{pdfFile.name}</span>
                  ) : (
                    <span>+ Upload PDF</span>
                  )}
                </button>
                <input
                  ref={pdfRef}
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-2 uppercase tracking-wider">
                  Product Photos (up to 3)
                </label>
                <button
                  type="button"
                  onClick={() => imgRef.current?.click()}
                  className="w-full border border-dashed border-zinc-700/60 rounded-xl px-4 py-3 text-sm text-zinc-500 hover:border-cyan-500/40 hover:text-zinc-300 transition-all text-left"
                >
                  {imageFiles.length > 0 ? (
                    <span className="text-cyan-400">{imageFiles.length} image(s)</span>
                  ) : (
                    <span>+ Upload Images</span>
                  )}
                </button>
                <input
                  ref={imgRef}
                  type="file"
                  accept="image/*"
                  multiple
                  className="hidden"
                  onChange={(e) =>
                    setImageFiles(Array.from(e.target.files || []).slice(0, 3))
                  }
                />
              </div>
            </div>

            {/* URL */}
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-2 uppercase tracking-wider">
                Competitor / Manufacturer URL (optional)
              </label>
              <input
                id="input-url"
                type="url"
                value={inputUrl}
                onChange={(e) => setInputUrl(e.target.value)}
                placeholder="https://manufacturer.com/product/..."
                className="w-full bg-zinc-900/80 border border-zinc-700/60 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/20 transition-all text-sm"
              />
            </div>

            {error && (
              <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              id="analyze-btn"
              type="submit"
              disabled={loading || !productName.trim()}
              className="w-full bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 disabled:from-zinc-700 disabled:to-zinc-700 disabled:cursor-not-allowed text-white font-semibold rounded-xl py-3.5 transition-all duration-200 text-sm shadow-lg shadow-violet-500/20"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-white stream-dot" />
                  <span className="w-1.5 h-1.5 rounded-full bg-white stream-dot" />
                  <span className="w-1.5 h-1.5 rounded-full bg-white stream-dot" />
                  <span>Starting pipeline...</span>
                </span>
              ) : (
                "Analyze Product →"
              )}
            </button>
          </div>
        </form>

        {/* Feature cards */}
        <div className="relative z-10 mt-10 grid grid-cols-3 gap-4 max-w-2xl w-full text-center">
          {[
            {
              icon: "⚡",
              title: "7 AI Agents",
              desc: "Doc-Intel, Vision, Retrieval, Verifier, Schema Mapper, HITL Router run in parallel",
            },
            {
              icon: "🔍",
              title: "2-Source Minimum",
              desc: "Every field requires ≥2 independent sources to agree before it's marked verified",
            },
            {
              icon: "✋",
              title: "Human Review",
              desc: "Low-confidence and contradicted fields go to a reviewer — not shipped silently wrong",
            },
          ].map((item) => (
            <div key={item.title} className="glass rounded-xl p-5 hover:border-zinc-600/60 transition-colors">
              <div className="text-2xl mb-2">{item.icon}</div>
              <div className="text-sm font-semibold text-zinc-200 mb-1">{item.title}</div>
              <div className="text-xs text-zinc-500 leading-relaxed">{item.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Eval results strip */}
      <section className="relative border-t border-zinc-800/60 bg-zinc-950/50 py-12 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest mb-2">
              Evaluation Results
            </div>
            <p className="text-sm text-zinc-500">
              Tested on 12 synthetic industrial products — 27 labeled fields including 4 adversarial cases designed to produce wrong answers.{" "}
              <a href="https://github.com/Pradhyut21/Unindustry/blob/main/docs/EVALUATION.md" target="_blank" rel="noopener noreferrer" className="text-violet-400 hover:text-violet-300 transition-colors">
                Full methodology →
              </a>
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {METRICS.map((m) => (
              <div
                key={m.label}
                className="glass rounded-xl p-5 text-center border border-zinc-800/40 hover:border-violet-500/20 transition-colors"
              >
                <div className="text-3xl font-bold font-mono bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent mb-1">
                  {m.value}
                </div>
                <div className="text-sm font-semibold text-zinc-200 mb-0.5">{m.label}</div>
                <div className="text-xs text-zinc-600">{m.sub}</div>
              </div>
            ))}
          </div>

          {/* Key differentiator callout */}
          <div className="mt-6 glass rounded-xl p-5 border border-amber-500/15 bg-amber-500/5">
            <div className="flex items-start gap-3">
              <span className="text-amber-400 text-lg flex-shrink-0">⚡</span>
              <div>
                <div className="text-sm font-semibold text-amber-400 mb-1">
                  SOURCE_CONTRADICTION Detection
                </div>
                <div className="text-xs text-zinc-400 leading-relaxed">
                  When two sources disagree (e.g. datasheet says 230V, nameplate says 400V), ProductTruth surfaces{" "}
                  <strong className="text-zinc-200">both values</strong> to a human reviewer rather than silently picking one.
                  Most AI enrichment tools don't do this — they quietly hallucinate a winner.
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

