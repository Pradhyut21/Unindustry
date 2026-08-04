"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { createProduct, triggerPipeline } from "@/lib/api";

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
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-20">
        {/* Gradient orbs */}
        <div className="absolute top-32 left-1/4 w-96 h-96 bg-violet-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute top-40 right-1/4 w-80 h-80 bg-cyan-600/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 text-center max-w-3xl mx-auto mb-12">
          <div className="inline-flex items-center gap-2 text-xs font-mono text-violet-400 border border-violet-500/30 rounded-full px-3 py-1 mb-6 bg-violet-500/10">
            <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
            AI-powered · Provenance-verified · Commerce-ready
          </div>
          <h1 className="text-5xl sm:text-6xl font-bold tracking-tight mb-6">
            <span className="bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
              Every field.
            </span>{" "}
            <span className="bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
              Every source.
            </span>
          </h1>
          <p className="text-lg text-zinc-400 leading-relaxed">
            Give ProductTruth a product name, a spec sheet, or a photo — and get a
            structured, commerce-ready record where every field is confidence-scored
            and traceable to its source. Low-confidence fields go to a human reviewer.
            Nothing ships silently wrong.
          </p>
        </div>

        {/* Input card */}
        <form
          onSubmit={handleSubmit}
          className="relative z-10 w-full max-w-2xl glass rounded-2xl p-8 shadow-2xl"
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

        {/* How it works */}
        <div className="relative z-10 mt-16 grid grid-cols-3 gap-6 max-w-2xl w-full text-center">
          {[
            { icon: "⚡", title: "7 AI Agents", desc: "Extract from PDF, images, and the web in parallel" },
            { icon: "🔍", title: "2-Source Minimum", desc: "Every field verified against ≥2 independent sources" },
            { icon: "✋", title: "Human Review", desc: "Low-confidence fields routed to a reviewer, not shipped wrong" },
          ].map((item) => (
            <div key={item.title} className="glass rounded-xl p-5">
              <div className="text-2xl mb-2">{item.icon}</div>
              <div className="text-sm font-semibold text-zinc-200 mb-1">{item.title}</div>
              <div className="text-xs text-zinc-500">{item.desc}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
