// API client for ProductTruth backend
// All fetch calls go through here so the base URL is configured once.

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Product {
  id: string;
  name: string;
  category: string | null;
  status: "processing" | "pending_review" | "complete" | "failed";
  created_at: string;
  updated_at: string;
  fields: ProductField[];
}

export interface ProductSummary {
  id: string;
  name: string;
  category: string | null;
  status: string;
  created_at: string;
}

export interface ProductField {
  id: string;
  field_name: string;
  value: string | null;
  contradicting_value: string | null;
  confidence: number;
  verification_status: string;
  uncertainty_reason: string;
  schema_field_id: string | null;
  sources: FieldSource[];
  created_at: string;
  updated_at: string;
}

export interface FieldSource {
  id: string;
  source_type: "doc" | "image" | "web" | "kg" | "human";
  source_ref: string;
  extracted_snippet: string | null;
  extraction_agent: string;
  extracted_at: string;
}

export interface ReviewQueueItem {
  id: string;
  field_id: string;
  status: "pending" | "accepted" | "edited" | "rejected";
  reviewer: string | null;
  reviewed_at: string | null;
  human_corrected_value: string | null;
  field: ProductField;
}

export interface AgentEvent {
  event_type: string;
  agent_name: string;
  message: string;
  partial_fields?: ProductField[];
  product_id?: string;
  field_count?: number;
  verified_count?: number;
  total_count?: number;
  hitl_count?: number;
  status?: string;
}

// ─── Products ─────────────────────────────────────────────────────────────────

export async function listProducts(): Promise<ProductSummary[]> {
  const res = await fetch(`${API_BASE}/api/v1/products/`);
  if (!res.ok) throw new Error("Failed to fetch products");
  return res.json();
}

export async function getProduct(id: string): Promise<Product> {
  const res = await fetch(`${API_BASE}/api/v1/products/${id}`);
  if (!res.ok) throw new Error("Product not found");
  return res.json();
}

export async function createProduct(formData: FormData): Promise<Product> {
  const res = await fetch(`${API_BASE}/api/v1/products/`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to create product");
  return res.json();
}

export async function triggerPipeline(productId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/products/${productId}/run`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to start pipeline");
}

// ─── Review ────────────────────────────────────────────────────────────────────

export async function listReviewQueue(): Promise<ReviewQueueItem[]> {
  const res = await fetch(`${API_BASE}/api/v1/review/`);
  if (!res.ok) throw new Error("Failed to fetch review queue");
  return res.json();
}

export async function submitReviewAction(
  itemId: string,
  action: "accepted" | "edited" | "rejected",
  reviewer: string,
  humanCorrectedValue?: string
): Promise<ReviewQueueItem> {
  const res = await fetch(`${API_BASE}/api/v1/review/${itemId}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action,
      reviewer,
      human_corrected_value: humanCorrectedValue,
    }),
  });
  if (!res.ok) throw new Error("Failed to submit review action");
  return res.json();
}

// ─── SSE Stream ────────────────────────────────────────────────────────────────

export function createPipelineStream(
  productId: string,
  onEvent: (event: AgentEvent) => void,
  onComplete: () => void,
  onError: (error: Event) => void
): { close: () => void } {
  let es: EventSource | null = null;
  let closed = false;
  let retries = 0;
  let pollInterval: ReturnType<typeof setInterval> | null = null;
  const MAX_RETRIES = 10;

  function startPollingFallback() {
    if (pollInterval || closed) return;
    pollInterval = setInterval(async () => {
      try {
        const product = await getProduct(productId);
        if (
          product.status === "complete" ||
          product.status === "pending_review" ||
          product.status === "failed"
        ) {
          if (pollInterval) clearInterval(pollInterval);
          if (!closed) {
            closed = true;
            onEvent({
              event_type: "pipeline_complete",
              agent_name: "orchestrator",
              message: `Pipeline complete. ${product.fields.length} fields extracted.`,
              total_count: product.fields.length,
              hitl_count: product.fields.filter((f) => f.confidence < 0.7).length,
              status: product.status,
            });
            onComplete();
          }
        }
      } catch { /* ignore poll errors */ }
    }, 2000);
  }

  function connect() {
    if (closed) return;
    es = new EventSource(`${API_BASE}/api/v1/stream/${productId}`);

    es.onmessage = (e) => {
      retries = 0;
      try {
        const data: AgentEvent = JSON.parse(e.data);
        if (data.event_type === "ping") return;
        onEvent(data);
        if (data.event_type === "pipeline_complete" || data.event_type === "pipeline_error") {
          closed = true;
          if (pollInterval) clearInterval(pollInterval);
          es?.close();
          onComplete();
        }
      } catch { /* ignore parse errors */ }
    };

    es.onerror = () => {
      es?.close();
      if (closed) return;
      retries++;
      if (retries <= MAX_RETRIES) {
        const delay = Math.min(1000 * Math.pow(2, retries - 1), 10000);
        setTimeout(connect, delay);
      } else {
        startPollingFallback();
      }
    };
  }

  // Safety net: if SSE never delivers pipeline_complete, start polling after 90s
  const safetyTimer = setTimeout(startPollingFallback, 90000);

  connect();

  return {
    close: () => {
      closed = true;
      clearTimeout(safetyTimer);
      if (pollInterval) clearInterval(pollInterval);
      es?.close();
    },
  };
}
