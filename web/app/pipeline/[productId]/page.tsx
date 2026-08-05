"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { createPipelineStream, AgentEvent } from "@/lib/api";

const AGENTS = [
  { id: "orchestrator", label: "Orchestrator", desc: "Planning extraction strategy" },
  { id: "doc_intel_agent", label: "Doc-Intel", desc: "Parsing PDF / datasheet" },
  { id: "vision_agent", label: "Vision", desc: "Reading product images" },
  { id: "retrieval_agent", label: "Retrieval", desc: "RAG over catalog index" },
  { id: "verifier_agent", label: "Verifier", desc: "Cross-checking ≥2 sources" },
  { id: "schema_mapper", label: "Schema Mapper", desc: "Mapping to ETIM schema" },
  { id: "hitl_router", label: "HITL Router", desc: "Routing low-confidence fields" },
];

type AgentStatus = "idle" | "active" | "complete" | "error";

export default function PipelinePage() {
  const { productId } = useParams<{ productId: string }>();
  const router = useRouter();
  const [agentStatuses, setAgentStatuses] = useState<Record<string, AgentStatus>>({});
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [complete, setComplete] = useState(false);
  const [hitlCount, setHitlCount] = useState(0);
  const [totalFields, setTotalFields] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const startTimeRef = useRef<number>(Date.now());
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    startTimeRef.current = Date.now();
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!productId) return;

    const es = createPipelineStream(
      productId,
      (event) => {
        setEvents((prev) => [...prev.slice(-50), event]);

        if (event.event_type === "agent_start") {
          setAgentStatuses((prev) => ({ ...prev, [event.agent_name]: "active" }));
        } else if (event.event_type === "agent_complete") {
          setAgentStatuses((prev) => ({ ...prev, [event.agent_name]: "complete" }));
        } else if (event.event_type === "agent_error") {
          setAgentStatuses((prev) => ({ ...prev, [event.agent_name]: "error" }));
        } else if (event.event_type === "pipeline_complete") {
          setHitlCount(event.hitl_count || 0);
          setTotalFields(event.total_count || 0);
          setComplete(true);
          if (timerRef.current) clearInterval(timerRef.current);
        }
      },
      () => {
        setComplete(true);
        if (timerRef.current) clearInterval(timerRef.current);
      },
      () => {}
    );

    return () => es.close();
  }, [productId]);

  const completedCount = Object.values(agentStatuses).filter(
    (s) => s === "complete" || s === "error"
  ).length;
  const progressPct = Math.round((completedCount / AGENTS.length) * 100);

  const statusColor = (s: AgentStatus) => {
    if (s === "active") return "border-violet-500 bg-violet-500/10 agent-active";
    if (s === "complete") return "border-emerald-500/50 bg-emerald-500/10";
    if (s === "error") return "border-red-500/50 bg-red-500/10";
    return "border-zinc-700/40 bg-zinc-900/40";
  };

  const statusDot = (s: AgentStatus) => {
    if (s === "active") return "bg-violet-400 animate-pulse";
    if (s === "complete") return "bg-emerald-400";
    if (s === "error") return "bg-red-400";
    return "bg-zinc-600";
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-12">
      <div className="mb-10">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-3">
            {!complete ? (
              <span className="flex gap-1 items-center text-violet-400 text-sm font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-violet-400 stream-dot" />
                <span className="w-1.5 h-1.5 rounded-full bg-violet-400 stream-dot" />
                <span className="w-1.5 h-1.5 rounded-full bg-violet-400 stream-dot" />
                Pipeline running...
              </span>
            ) : (
              <span className="text-emerald-400 text-sm font-mono flex items-center gap-1.5">
                ✓ Pipeline complete
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 text-xs font-mono text-zinc-500">
            <span className="tabular-nums">
              {String(Math.floor(elapsed / 60)).padStart(2, "0")}:{String(elapsed % 60).padStart(2, "0")}
            </span>
            {!complete && (
              <span className="text-violet-400">{progressPct}%</span>
            )}
          </div>
        </div>
        {/* Progress bar */}
        <div className="h-1 w-full bg-zinc-800 rounded-full mb-3 overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${complete ? 100 : progressPct}%`,
              background: complete
                ? "linear-gradient(to right, #10b981, #34d399)"
                : "linear-gradient(to right, #7c3aed, #06b6d4)",
            }}
          />
        </div>
        <h1 className="text-3xl font-bold text-zinc-100">Extracting Product Data</h1>
        <p className="text-zinc-500 mt-1 text-sm font-mono">{productId}</p>
      </div>

      {/* Agent grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
        {AGENTS.map((agent) => {
          const s: AgentStatus = agentStatuses[agent.id] || "idle";
          return (
            <div
              key={agent.id}
              className={`rounded-xl border p-4 transition-all duration-300 ${statusColor(s)}`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot(s)}`} />
                <span className="text-sm font-semibold text-zinc-200">{agent.label}</span>
              </div>
              <p className="text-xs text-zinc-500">{agent.desc}</p>
            </div>
          );
        })}
      </div>

      {/* Live event log */}
      <div className="glass rounded-xl p-5 mb-8">
        <h2 className="text-xs font-mono text-zinc-500 uppercase tracking-wider mb-3">
          Live Event Log
        </h2>
        <div className="space-y-1.5 max-h-64 overflow-y-auto font-mono text-xs">
          {events.length === 0 ? (
            <span className="text-zinc-600">Waiting for events...</span>
          ) : (
            events.map((e, i) => (
              <div key={i} className="flex gap-3 text-zinc-400">
                <span className="text-zinc-600 flex-shrink-0">
                  {e.agent_name}
                </span>
                <span className={
                  e.event_type === "agent_error" ? "text-red-400" :
                  e.event_type === "pipeline_complete" ? "text-emerald-400" :
                  "text-zinc-400"
                }>
                  {e.message}
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Done CTA */}
      {complete && (
        <div className="glass rounded-xl p-6 border border-emerald-500/20 bg-emerald-500/5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-emerald-400 mb-1">
                Analysis Complete
              </h2>
              <p className="text-sm text-zinc-400">
                {totalFields} fields extracted.{" "}
                {hitlCount > 0 ? (
                  <span className="text-amber-400">
                    {hitlCount} low-confidence field{hitlCount !== 1 ? "s" : ""} need{hitlCount === 1 ? "s" : ""} review.
                  </span>
                ) : (
                  <span className="text-emerald-400">All fields verified — no review needed.</span>
                )}
              </p>
            </div>
            <div className="flex gap-3">
              {hitlCount > 0 && (
                <button
                  onClick={() => router.push("/review")}
                  className="text-sm font-medium bg-amber-500/15 border border-amber-500/30 text-amber-400 hover:bg-amber-500/25 rounded-lg px-4 py-2 transition-colors"
                >
                  Review Queue ({hitlCount})
                </button>
              )}
              <button
                id="view-product-btn"
                onClick={() => router.push(`/product/${productId}`)}
                className="text-sm font-medium bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 text-white rounded-lg px-4 py-2 transition-all"
              >
                View Product Record →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
