"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { createPipelineStream, AgentEvent } from "@/lib/api";

const AGENTS = [
  { id: "orchestrator",    label: "Orchestrator",   desc: "Planning extraction strategy",    icon: "🎯" },
  { id: "doc_intel_agent", label: "Doc-Intel",       desc: "Parsing PDF / datasheet",         icon: "📄" },
  { id: "vision_agent",   label: "Vision",          desc: "Reading product images",           icon: "👁️" },
  { id: "retrieval_agent",label: "Retrieval",       desc: "RAG over catalog index",           icon: "🔍" },
  { id: "verifier_agent", label: "Verifier",        desc: "Cross-checking >=2 sources",       icon: "✅" },
  { id: "schema_mapper",  label: "Schema Mapper",   desc: "Mapping to ETIM schema",           icon: "📐" },
  { id: "hitl_router",    label: "HITL Router",     desc: "Routing low-confidence fields",    icon: "✋" },
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
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // Start timer
    timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);

    const es = createPipelineStream(
      productId,
      (event: AgentEvent) => {
        setEvents((prev) => [...prev, event]);
        if (event.event_type === "agent_start" && event.agent_name) {
          setAgentStatuses((prev) => ({ ...prev, [event.agent_name]: "active" }));
        } else if (event.event_type === "agent_complete" && event.agent_name) {
          setAgentStatuses((prev) => ({ ...prev, [event.agent_name]: "complete" }));
        } else if (event.event_type === "agent_error" && event.agent_name) {
          setAgentStatuses((prev) => ({ ...prev, [event.agent_name]: "error" }));
        } else if (event.event_type === "pipeline_complete") {
          setHitlCount(event.hitl_count || 0);
          setTotalFields(event.total_count || 0);
          setComplete(true);
          if (timerRef.current) clearInterval(timerRef.current);
          setTimeout(() => router.push(`/product/${productId}`), 2000);
        }
      },
      () => {
        setComplete(true);
        if (timerRef.current) clearInterval(timerRef.current);
        setTimeout(() => router.push(`/product/${productId}`), 2000);
      },
      () => {}
    );

    return () => es.close();
  }, [productId]);

  const completedCount = Object.values(agentStatuses).filter(
    (s) => s === "complete" || s === "error"
  ).length;
  const progressPct = Math.round((completedCount / AGENTS.length) * 100);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  };

  return (
    <div style={{ background: "var(--neutral-50)", minHeight: "100vh" }}>
      <div className="pipeline-page">

        {/* Header card */}
        <div className="pipeline-header">
          <div className="pipeline-status-row">
            <div className={`pipeline-status-badge${complete ? " complete" : ""}`}>
              {complete ? (
                <>✓ Pipeline Complete</>
              ) : (
                <>
                  <span className="hero-label-dot" style={{ width: 8, height: 8 }} />
                  Pipeline running
                  <span className="stream-dot">.</span>
                  <span className="stream-dot">.</span>
                  <span className="stream-dot">.</span>
                </>
              )}
            </div>
            <div className="pipeline-meta">
              <span className="pipeline-timer">{formatTime(elapsed)}</span>
              <span className="pipeline-pct">{complete ? "100" : progressPct}%</span>
            </div>
          </div>

          <div className="pipeline-title">Extracting Product Data</div>
          <div className="pipeline-id">{productId}</div>

          {/* Progress bar */}
          <div style={{ marginTop: "1rem" }}>
            <div className="progress-track">
              <div
                className={`progress-fill${complete ? " complete" : ""}`}
                style={{ width: `${complete ? 100 : progressPct}%` }}
              />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "0.375rem" }}>
              <span style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--neutral-400)" }}>
                {completedCount} / {AGENTS.length} agents complete
              </span>
              {complete && totalFields > 0 && (
                <span style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#16A34A" }}>
                  {totalFields} fields extracted · {hitlCount} for review
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Agent grid */}
        <div className="agents-grid">
          {AGENTS.map((agent) => {
            const status = agentStatuses[agent.id] || "idle";
            return (
              <div key={agent.id} className={`agent-card ${status}`}>
                <div style={{ fontSize: "1.25rem", flexShrink: 0 }}>{agent.icon}</div>
                <div className="agent-status-dot" data-status={status} style={{
                  background: status === "active" ? "var(--red)" :
                              status === "complete" ? "#16A34A" :
                              status === "error" ? "#EF4444" :
                              "var(--neutral-200)"
                }} />
                <div className="agent-info">
                  <div className="agent-name">{agent.label}</div>
                  <div className="agent-desc">
                    {status === "active" ? (
                      <span style={{ color: "var(--red)", fontWeight: 600 }}>
                        Running<span className="stream-dot">.</span><span className="stream-dot">.</span><span className="stream-dot">.</span>
                      </span>
                    ) : status === "complete" ? (
                      <span style={{ color: "#16A34A", fontWeight: 600 }}>Done</span>
                    ) : status === "error" ? (
                      <span style={{ color: "#EF4444", fontWeight: 600 }}>Error</span>
                    ) : (
                      agent.desc
                    )}
                  </div>
                </div>
                <div className="agent-check">
                  {status === "complete" ? "✅" : status === "active" ? "⏳" : status === "error" ? "❌" : ""}
                </div>
              </div>
            );
          })}
        </div>

        {/* Event log */}
        {events.length > 0 && (
          <div style={{
            marginTop: "1.5rem",
            background: "var(--white)",
            border: "1px solid var(--neutral-200)",
            borderRadius: "0.75rem",
            overflow: "hidden",
            boxShadow: "var(--shadow-sm)",
          }}>
            <div style={{
              padding: "0.875rem 1.25rem",
              borderBottom: "1px solid var(--neutral-100)",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--red)" }} />
              <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--neutral-700)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Live Event Log
              </span>
            </div>
            <div style={{ padding: "0.75rem 1.25rem", maxHeight: "200px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "0.375rem" }}>
              {events.filter(e => e.event_type !== "ping").slice(-12).map((ev, i) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", fontSize: "0.75rem" }}>
                  <span style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.625rem",
                    padding: "0.125rem 0.375rem",
                    borderRadius: "0.25rem",
                    fontWeight: 700,
                    background: ev.event_type === "agent_complete" ? "#DCFCE7" :
                                ev.event_type === "agent_start" ? "var(--red-light)" :
                                ev.event_type === "pipeline_complete" ? "#DCFCE7" :
                                "var(--neutral-100)",
                    color: ev.event_type === "agent_complete" ? "#15803D" :
                           ev.event_type === "agent_start" ? "var(--red)" :
                           ev.event_type === "pipeline_complete" ? "#15803D" :
                           "var(--neutral-500)",
                    flexShrink: 0,
                    textTransform: "uppercase",
                  }}>
                    {ev.event_type.replace("agent_", "").replace("pipeline_", "")}
                  </span>
                  <span style={{ color: "var(--neutral-600)", fontWeight: 500, lineHeight: 1.5 }}>{ev.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Complete card */}
        {complete && (
          <div style={{
            marginTop: "1.5rem",
            background: "#F0FDF4",
            border: "1px solid #BBF7D0",
            borderLeft: "4px solid #16A34A",
            borderRadius: "0.75rem",
            padding: "1.25rem 1.5rem",
            display: "flex",
            alignItems: "center",
            gap: "0.875rem",
          }}>
            <span style={{ fontSize: "1.5rem" }}>✅</span>
            <div>
              <div style={{ fontWeight: 700, color: "#15803D", fontSize: "0.9375rem" }}>
                Pipeline complete — redirecting to results...
              </div>
              <div style={{ fontSize: "0.8125rem", color: "#16A34A", marginTop: "0.125rem" }}>
                {totalFields} fields extracted · {hitlCount} routed to human review
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
