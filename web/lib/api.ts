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
): EventSource {
  const es = new EventSource(`${API_BASE}/api/v1/stream/${productId}`);
  es.onmessage = (e) => {
    try {
      const data: AgentEvent = JSON.parse(e.data);
      if (data.event_type === "ping") return;
      onEvent(data);
      if (data.event_type === "pipeline_complete" || data.event_type === "pipeline_error") {
        es.close();
        onComplete();
      }
    } catch {}
  };
  es.onerror = (e) => {
    onError(e);
    es.close();
  };
  return es;
}
