// All shared TypeScript types for the KMRL portal frontend.
// Extracted from the original monolithic main.tsx.

export type User = {
  id: string;
  name: string;
  email: string;
  role: string;
  department: string | null;
  department_id?: string | null;
};

export type Doc = {
  id: string;
  title: string;
  type: string;
  owner_name: string;
  classification: string;
  sensitivity: string;
  created_at: string;
  version_id: string;
  version_label: string;
  status: string;
  uploaded_at: string;
};

export type Page = {
  id: string;
  page_no: number;
  ocr_text: string | null;
  ocr_confidence: number | null;
  low_confidence: boolean;
};

export type Detail = {
  document: Doc;
  pages: Page[];
  source_url: string;
};

export type IntelligenceField = {
  prediction_id: string;
  field: string;
  value: string;
  confidence: number;
  source_span: { page_no: number; start: number; end: number; quote: string } | null;
  review_state: string;
  source: "AI-suggested" | "human-entered";
};

export type IntelligenceCardData = {
  version_id: string;
  document_id: string;
  title: string;
  classification: IntelligenceField;
  summary: IntelligenceField;
  key_facts: IntelligenceField[];
  entities: IntelligenceField[];
  actions: IntelligenceField[];
  deadline: IntelligenceField;
  priority: IntelligenceField;
  routing: IntelligenceField;
};

export type RAGCitation = {
  citation_id: string;
  chunk_id: string;
  document_id: string;
  version_id: string;
  document_title: string;
  page_no: number;
  quote: string;
  source_url: string;
};

export type RAGResponse = {
  answer: string;
  refusal: boolean;
  citations: RAGCitation[];
  disclaimer: string;
};

export type AlertItem = {
  id: string;
  title: string;
  priority: string;
  reason_codes: string[];
  suggested_department: string | null;
  suggested_action: string | null;
  deadline: string | null;
  source_excerpt: string | null;
  source_version_id: string;
  status: string;
  routing_state: string;
  assigned_user_id: string | null;
  document_title: string | null;
};

export type ActionEventItem = {
  id: string;
  event_type: string;
  timestamp: string;
  actor_id: string;
  detail: Record<string, unknown>;
};

export type ActionItem = {
  id: string;
  source_version_id: string;
  title: string;
  owner_id: string | null;
  due_at: string | null;
  priority: string;
  status: string;
  comments: string;
  completion_evidence: string | null;
  acknowledged_at: string | null;
  completed_at: string | null;
  verified_by: string | null;
  verified_at: string | null;
  events: ActionEventItem[];
};

export type ChangeItem = {
  id: string;
  change_type: string;
  old_span: { page_no: number; quote: string } | null;
  new_span: { page_no: number; quote: string } | null;
  impact: string;
  interpretation: string;
  affected_department: string | null;
  priority: string;
  required_action: string | null;
  action_id: string | null;
};

export type ComparisonItem = {
  id: string;
  old_version_id: string;
  new_version_id: string;
  status: string;
  old_title?: string;
  new_title?: string;
  old_document_id?: string;
  new_document_id?: string;
  changes: ChangeItem[];
};

export type AuditEventItem = {
  id: string;
  actor_id: string | null;
  event_type: string;
  object_type: string;
  object_id: string;
  timestamp: string;
  hash: string;
  detail: Record<string, unknown>;
};

export type DepartmentItem = {
  id: string;
  name: string;
  parent_id: string | null;
};

export type AnalyticsSummary = {
  total_documents: number;
  documents_by_status: Record<string, number>;
  total_alerts: number;
  alerts_by_priority: Record<string, number>;
  alerts_by_department: Record<string, number>;
  total_actions: number;
  actions_by_status: Record<string, number>;
  overdue_actions: number;
  avg_days_to_complete: number | null;
};

// Role label map shared across components
export const roleLabels: Record<string, string> = {
  system_administrator: "System Administrator",
  document_administrator: "Document Administrator",
  reviewer: "Reviewer",
  department_user: "Department User",
  executive_viewer: "Executive Viewer",
  auditor: "Auditor",
};

export const allowedExt = [".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".txt", ".md", ".csv"];

export const REVIEWER_ROLES = new Set(["reviewer", "system_administrator", "document_administrator"]);
