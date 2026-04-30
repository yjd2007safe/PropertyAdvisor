const API_BASE_URL = process.env.PROPERTY_ADVISOR_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    headers: { Accept: "application/json" }
  });

  if (!response.ok) {
    const fallback = `Request failed with status ${response.status}`;
    let message = fallback;
    try {
      const payload = await response.json();
      if (payload?.detail) {
        message = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
      }
    } catch {
      message = fallback;
    }
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}


async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    cache: "no-store",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const fallback = `Request failed with status ${response.status}`;
    let message = fallback;
    try {
      const payload = await response.json();
      if (payload?.detail) {
        message = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
      }
    } catch {
      message = fallback;
    }
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}

function buildSearch(params: Record<string, string | number | undefined | null>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && `${value}`.length > 0) {
      query.set(key, String(value));
    }
  }
  const encoded = query.toString();
  return encoded ? `?${encoded}` : "";
}

export type WorkflowLink = { label: string; href: string; context: string };
export type SummaryCard = { title: string; value: string; detail: string };
export type WorkflowSnapshot = {
  stage: string;
  primary_suburb_slug?: string | null;
  next_step: string;
  next_href: string;
  investor_message: string;
};

export type AlertScanAcknowledgementState = {
  status: "active" | "expired" | "superseded";
  acknowledged_by: string;
  reason: string;
  deferred_until?: string | null;
  acknowledged_at: string;
  expires_at?: string | null;
  stale: boolean;
  stale_reason?: string | null;
};


export type DataSourceStatus = {
  mode: "mock" | "postgres";
  source: "mock" | "postgres" | "fallback_mock";
  is_fallback: boolean;
  message: string;
  status_label: "live_db" | "fallback" | "sample_data";
  investor_note: string;
  consistency: "uniform" | "mixed";
  upstream_sources: Record<string, "mock" | "postgres" | "fallback_mock">;
  source_breakdown: Record<"mock" | "postgres" | "fallback_mock", number>;
  fallback_reason?: string | null;
};

export type SuburbOverviewItem = {
  slug: string;
  name: string;
  state: string;
  median_price: number;
  median_rent: number;
  trend: "watching" | "steady" | "improving";
  note: string;
  avg_days_on_market: number;
  vacancy_rate_pct: number;
};

export type SuburbsOverviewResponse = {
  generated_at: string;
  data_source: DataSourceStatus;
  summary: {
    tracked_suburbs: number;
    watchlist_suburbs: number;
    data_freshness: string;
  };
  items: SuburbOverviewItem[];
  investor_signals: SummaryCard[];
  workflow_links: WorkflowLink[];
  workflow_snapshot: WorkflowSnapshot;
};

export type PropertyAdvisorResponse = {
  generated_at: string;
  data_source: DataSourceStatus;
  property: {
    address: string;
    property_type: string;
    beds: number;
    baths: number;
  };
  advice: {
    recommendation: "watch" | "consider" | "pass";
    confidence: "low" | "medium" | "high";
    headline: string;
    summary?: string | null;
    stance?: "watch" | "consider" | "pass" | null;
    rationale_bullets?: string[];
    warnings?: string[];
    fallback_notes?: string[];
    confidence_reasons?: string[];
    fallback_state?: "none" | "insufficient_evidence" | "stale_evidence" | "low_sample" | "conflicting_evidence" | "missing_subject_attributes" | "missing_listing_context" | "missing_market_context";
    fallback_reasons?: string[];
    limitations?: string[];
    freshness?: "fresh" | "stale" | "unknown";
    sample_depth?: "none" | "low" | "moderate" | "high";
    evidence_agreement?: "aligned" | "mixed" | "conflicting" | "unknown";
    risks: string[];
    strengths: string[];
    next_steps: string[];
    evidence_summary?: {
      contract_version: string;
      algorithm_version: string;
      freshness_status: "fresh" | "stale" | "unknown";
      required_inputs: Record<string, boolean>;
      optional_inputs: Record<string, boolean>;
      sections: { name: string; status: "available" | "missing" | "stale" | "insufficient"; summary: string }[];
      warnings: string[];
      fallback_notes: string[];
      limitations: string[];
      confidence_reasons: string[];
      fallback_state: "none" | "insufficient_evidence" | "stale_evidence" | "low_sample" | "conflicting_evidence" | "missing_subject_attributes" | "missing_listing_context" | "missing_market_context";
      fallback_reasons: string[];
      sample_depth: "none" | "low" | "moderate" | "high";
      evidence_agreement: "aligned" | "mixed" | "conflicting" | "unknown";
      evidence_strength: "weak" | "moderate" | "strong";
    } | null;
  };
  market_context: {
    suburb: string;
    strategy_focus: string;
    demand_signal: string;
    supply_signal: string;
  };
  comparable_snapshot: {
    sample_size: number;
    price_position: "below_range" | "in_range" | "above_range" | "insufficient_data";
    summary: string;
  };
  decision_summary: string;
  rationale: { signal: string; stance: "supporting" | "caution" | "neutral"; evidence: string }[];
  investor_signals: { title: string; status: "positive" | "neutral" | "risk"; detail: string }[];
  summary_cards: SummaryCard[];
  workflow_links: WorkflowLink[];
  workflow_snapshot: WorkflowSnapshot;
  inputs: {
    query: string;
    query_type: "address" | "slug" | "auto";
    suburb_slug?: string | null;
  };
};

export type ComparablesResponse = {
  generated_at: string;
  data_source: DataSourceStatus;
  subject: string;
  set_quality: string;
  query: string;
  summary: {
    count: number;
    min_price: number;
    max_price: number;
    average_price: number;
    sample_state?: "empty" | "low" | "adequate";
    quality_score?: number | null;
    quality_label?: string | null;
    algorithm_version?: string | null;
  };
  narrative: {
    price_position: "discount" | "aligned" | "premium" | "insufficient_data";
    spread_commentary: string;
    investor_takeaway: string;
    action_prompt: string;
  };
  summary_cards: SummaryCard[];
  workflow_links: WorkflowLink[];
  workflow_snapshot: WorkflowSnapshot;
  items: {
    property_id?: string | null;
    address: string;
    price: number;
    distance_km: number;
    match_reason: string;
    sold_date: string;
    beds: number;
    baths: number;
    score?: number | null;
    rationale?: Record<string, unknown>;
  }[];
};



export type AlertScanLedgerRun = {
  run_id: string;
  timestamp: string;
  mode: string;
  filters: Record<string, unknown>;
  status: "success" | "failed";
  error?: string | null;
  persistence_attempted: boolean;
  counts: { entries_scanned: number; alerts_scanned: number; persisted: number; new: number; changed: number; unchanged: number };
  regenerate_command: string;
};

export type AlertScanLedgerSummary = {
  latest_run?: AlertScanLedgerRun | null;
  recent_runs: AlertScanLedgerRun[];
};

export type AlertScanHealthSummary = {
  status: "healthy" | "warning" | "stale" | "failed" | "no_recent_run";
  reasons: string[];
  recommended_command: string;
  age_minutes?: number | null;
  stale_after_minutes: number;
  latest_run?: AlertScanLedgerRun | null;
};

export type DecisionOutcomeSummary = {
  outcome: "continue_monitoring" | "revisit_later" | "close_for_now" | "escalate_for_closer_review";
  summary: string;
  rationale?: string | null;
  acted_at?: string | null;
  source_event_id?: string | null;
  source_surface: "orchestration" | "watchlist";
};

export type OrchestrationPlanItem = {
  event_id: string;
  event_type: string;
  bucket: string;
  action: string;
  requires_human_review: boolean;
  auto_continue: boolean;
  created_at?: string | null;
  queued_at?: string | null;
  strategy_summary: string;
  follow_up_state: string;
  next_step_outcome: string;
  revisit_reason: string;
  is_carry_forward_follow_up: boolean;
  reviewer_action_state: "pending" | "acknowledged" | "closed";
  reviewer_available_actions: Array<"acknowledge" | "close_follow_up">;
  reviewer_last_action_at?: string | null;
  reviewer_last_action?: "acknowledge" | "close_follow_up" | null;
  reviewer_last_action_rationale?: string | null;
  reviewer_decision_outcome?: "continue_monitoring" | "revisit_later" | "close_for_now" | "escalate_for_closer_review" | null;
  reviewer_decision_summary?: string | null;
  reviewer_decision_record?: DecisionOutcomeSummary | null;
  revisit_guidance: string;
  next_review_cue: string;
  next_step_action_cue: string;
  next_step_batch_cue: string;
  decision_support_state: "active_attention" | "mostly_stable" | "reopen_for_closer_review";
  compact_rationale_cue: string;
  message?: string | null;
};

export type OrchestrationReviewResponse = {
  summary: {
    current_state: "awaiting_review" | "auto_progressing" | "idle";
    latest_event_at?: string | null;
    generated_at: string;
    freshness: "fresh" | "stale" | "empty";
    review_needed: boolean;
    review_required_count: number;
    auto_continue_count: number;
    queued_count: number;
    pending_count: number;
    total_pending_count: number;
    next_action: string;
    decision_outcome_cue: string;
    decision_outcome_breakdown: Record<string, number>;
    latest_outcome_distribution: Array<{
      outcome: "continue_monitoring" | "revisit_later" | "close_for_now" | "escalate_for_closer_review" | "unrecorded";
      label: string;
      count: number;
      is_actionable: boolean;
    }>;
    active_decision_outcome_filter?: "continue_monitoring" | "revisit_later" | "close_for_now" | "escalate_for_closer_review" | "unrecorded" | null;
    active_reviewer_action_state_filter?: "pending" | "acknowledged" | "closed" | null;
    active_follow_up_state_filter?: string | null;
    recent_reviewer_action_snapshot: string;
    action_scan_default_cue: string;
    next_step_batching_cue: string;
    compact_follow_up_grouping_cue: string;
    review_session_packet_cue: string;
    review_session_packet_low_volume_note: string;
    review_session_packet_breakdown: Record<"do_now" | "batch_later" | "recently_closed", number>;
  };
  plans: OrchestrationPlanItem[];
  alert_scan_ledger?: AlertScanLedgerSummary | null;
  alert_scan_health?: AlertScanHealthSummary | null;
  alert_scan_acknowledgement?: AlertScanAcknowledgementState | null;
};

export type WatchlistAlert = {
  severity: "info" | "watch" | "high";
  title: string;
  detail: string;
  metric: string;
  observed_at: string;
  event_key?: string | null;
  event_status?: string | null;
  event_action_state?: string | null;
  event_occurrence_count?: number | null;
  event_last_observed_at?: string | null;
  event_change_state?: string | null;
  event_last_changed_at?: string | null;
  event_last_seen_at?: string | null;
  event_change_summary?: string | null;
};
export type WatchlistEvent = {
  event_id: string;
  category: "watchlist" | "alert" | "advisory" | "orchestration";
  occurred_at: string;
  title: string;
  detail: string;
  suburb_slug?: string | null;
  suburb_name?: string | null;
  latest_decision?: DecisionOutcomeSummary | null;
  latest_decision_triage_cue?: string | null;
  reviewer_action_state?: "pending" | "acknowledged" | "closed" | null;
  follow_up_state?: string | null;
  decision_support_state?: "active_attention" | "mostly_stable" | "reopen_for_closer_review" | null;
  follow_up_posture: "do_now" | "batch_later" | "recently_closed";
  follow_up_href: string;
  follow_up_label: string;
};

export type WatchlistEntry = {
  suburb_slug: string;
  suburb_name: string;
  state: string;
  strategy: "yield" | "owner-occupier" | "balanced";
  watch_status: "active" | "review" | "paused" | "archived";
  notes: string;
  target_buy_range_min: number;
  target_buy_range_max: number;
  alerts: WatchlistAlert[];
  alert_event_summary?: {
    total: number;
    active: number;
    unresolved: number;
    open: number;
    dismissed: number;
    archived: number;
    lifecycle: { new: number; changed: number; unchanged: number };
  } | null;
  latest_context?: {
    advisory: string;
    comparables: string;
    orchestration: string;
    recent_reviewer_action_summary?: string | null;
    latest_decision?: DecisionOutcomeSummary | null;
    latest_decision_triage_cue?: string | null;
    latest_decision_next_step_cue?: string | null;
    latest_decision_batch_cue?: string | null;
    latest_decision_rationale_cue?: string | null;
    alert_event_summary?: {
      total: number;
      active: number;
      unresolved: number;
      open: number;
      dismissed: number;
      archived: number;
      lifecycle: { new: number; changed: number; unchanged: number };
    } | null;
    updated_at: string;
  } | null;
};

export type WatchlistResponse = {
  generated_at: string;
  mode: "mock" | "postgres";
  data_source: DataSourceStatus;
  summary: {
    total_entries: number;
    active_entries: number;
    grouped_view: "none" | "state" | "strategy";
    alert_counts: Record<string, number>;
    by_status: Record<string, number>;
    by_strategy: Record<string, number>;
    action_counts: Record<string, number>;
    latest_outcome_breakdown: Record<string, number>;
    latest_outcome_distribution: Array<{
      outcome: "continue_monitoring" | "revisit_later" | "close_for_now" | "escalate_for_closer_review" | "unrecorded";
      label: string;
      count: number;
      is_actionable: boolean;
    }>;
    active_latest_outcome_filter?: "continue_monitoring" | "revisit_later" | "close_for_now" | "escalate_for_closer_review" | null;
    latest_outcome_focus_cue: string;
    next_step_scan_cue: string;
    next_step_batching_cue: string;
    compact_follow_up_grouping_cue: string;
    review_session_packet_cue: string;
    review_session_packet_low_volume_note: string;
    review_session_packet_breakdown: Record<"do_now" | "batch_later" | "recently_closed", number>;
    alert_event_summary?: {
      total: number;
      active: number;
      unresolved: number;
      open: number;
      dismissed: number;
      archived: number;
      lifecycle: { new: number; changed: number; unchanged: number };
    } | null;
    investor_brief: string;
    alert_scan_ledger?: AlertScanLedgerSummary | null;
    alert_scan_health?: AlertScanHealthSummary | null;
    alert_scan_acknowledgement?: AlertScanAcknowledgementState | null;
  };
  summary_cards: SummaryCard[];
  workflow_links: WorkflowLink[];
  workflow_snapshot: WorkflowSnapshot;
  items: WatchlistEntry[];
  groups: { key: string; label: string; entries: WatchlistEntry[]; action_required: number; high_alerts: number; compact_rationale_cue: string }[];
};

export const getSuburbsOverview = () => getJson<SuburbsOverviewResponse>("/api/suburbs/overview");

export const getPropertyAdvisor = (params?: { query?: string; query_type?: "address" | "slug" | "auto"; focus_strategy?: "yield" | "owner-occupier" | "balanced" }) =>
  getJson<PropertyAdvisorResponse>(`/api/advisor/property${buildSearch(params ?? {})}`);

export const getComparables = (params?: { query?: string; max_items?: number; min_price?: number; max_price?: number; max_distance_km?: number }) =>
  getJson<ComparablesResponse>(`/api/comparables${buildSearch(params ?? {})}`);

export const getWatchlist = (params?: {
  suburb_slug?: string;
  strategy?: "yield" | "owner-occupier" | "balanced";
  state?: string;
  watch_status?: "active" | "review" | "paused" | "archived";
  latest_outcome?: "continue_monitoring" | "revisit_later" | "close_for_now" | "escalate_for_closer_review";
  group_by?: "none" | "state" | "strategy";
}) => getJson<WatchlistResponse>(`/api/watchlist${buildSearch(params ?? {})}`);

export const getOrchestrationReview = (params?: {
  outcome_focus?: "continue_monitoring" | "revisit_later" | "close_for_now" | "escalate_for_closer_review" | "unrecorded";
  reviewer_action_state_focus?: "pending" | "acknowledged" | "closed";
  follow_up_state_focus?: string;
}) => getJson<OrchestrationReviewResponse>(`/api/orchestration/review${buildSearch(params ?? {})}`);

export const getWatchlistDetail = (suburb_slug: string) =>
  getJson<{ generated_at: string; mode: "mock" | "postgres"; data_source: DataSourceStatus; item: WatchlistEntry }>(`/api/watchlist/${suburb_slug}`);

export const getWatchlistAlerts = (severity?: "info" | "watch" | "high") =>
  getJson<{ generated_at: string; mode: "mock" | "postgres"; data_source: DataSourceStatus; total: number; items: WatchlistAlert[] }>(`/api/watchlist/alerts${buildSearch({ severity })}`);

export const getWatchlistEvents = (limit?: number) =>
  getJson<{ generated_at: string; mode: "mock" | "postgres"; data_source: DataSourceStatus; total: number; items: WatchlistEvent[] }>(
    `/api/watchlist/events${buildSearch({ limit })}`
  );

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-AU", {
    style: "currency",
    currency: "AUD",
    maximumFractionDigits: 0
  }).format(value);
}

export function formatTimestampUTC(value?: string | null): string {
  if (!value) return "Not available";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-AU", { timeZone: "UTC", hour12: false }) + " UTC";
}

export const postOrchestrationReviewAction = (payload: {
  event_id: string;
  action: "acknowledge" | "close_follow_up";
}) =>
  postJson<{ summary: OrchestrationReviewResponse["summary"]; updated_plan: OrchestrationPlanItem }>(
    "/api/orchestration/review/actions",
    payload
  );


export const postWatchlistAction = (payload: {
  suburb_slug: string;
  source_surface: "advisor" | "comparables" | "watchlist" | "suburbs";
  strategy?: "yield" | "owner-occupier" | "balanced";
  watch_status?: "active" | "review" | "paused" | "archived";
  notes?: string;
}) => postJson<{ action: "created" | "updated"; item: WatchlistEntry }>("/api/watchlist/actions", payload);


export const postAlertScanAcknowledge = (payload: { acknowledged_by: string; reason: string; deferred_until?: string; expires_at?: string }) =>
  postJson<{ generated_at: string; acknowledgement: AlertScanAcknowledgementState; alert_scan_health: AlertScanHealthSummary }>("/api/alert-scan/acknowledge", payload);
