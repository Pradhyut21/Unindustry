"use client";

import React from "react";

type Props = {
  field: string;
  valueA: string;
  sourceA: string;
  valueB: string;
  sourceB: string;
};

export function ContradictionCard({ field, valueA, sourceA, valueB, sourceB }: Props) {
  return (
    <div
      style={{
        border: "1px solid #FCD34D",
        background: "#FEFCE8",
        borderRadius: "0.75rem",
        padding: "1rem",
        margin: "0.75rem 0",
        boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          fontWeight: 700,
          color: "#92400E",
          marginBottom: "0.75rem",
          fontSize: "0.875rem",
        }}
      >
        <span>⚡ Contradiction detected —</span>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            background: "#FEF3C7",
            padding: "0.125rem 0.375rem",
            borderRadius: "0.25rem",
          }}
        >
          {field}
        </span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", fontSize: "0.875rem" }}>
        <div style={{ background: "white", borderRadius: "0.5rem", padding: "0.75rem", border: "1px solid #FDE68A" }}>
          <div style={{ fontSize: "0.75rem", color: "#6B7280", marginBottom: "0.25rem" }}>{sourceA}</div>
          <div style={{ fontWeight: 700, fontSize: "1.125rem", color: "#111827" }}>{valueA}</div>
        </div>
        <div style={{ background: "white", borderRadius: "0.5rem", padding: "0.75rem", border: "1px solid #FDE68A" }}>
          <div style={{ fontSize: "0.75rem", color: "#6B7280", marginBottom: "0.25rem" }}>{sourceB}</div>
          <div style={{ fontWeight: 700, fontSize: "1.125rem", color: "#DC2626" }}>{valueB}</div>
        </div>
      </div>
      <p style={{ fontSize: "0.75rem", color: "#B45309", marginTop: "0.5rem", fontWeight: 600 }}>
        Both values have been surfaced to the human review queue.
      </p>
    </div>
  );
}
