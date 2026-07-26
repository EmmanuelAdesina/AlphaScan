/**
 * AlphaScan TypeScript types.
 * Canonical type definitions for the entire frontend.
 */

// ── Verification ──────────────────────────────────────────────

export type ValidationLevel = 'none' | 'format' | 'structure' | 'heuristic' | 'provider' | 'active';

export type VerificationStatus =
  | 'unknown'
  | 'unsupported'
  | 'valid_format'
  | 'active'
  | 'expired'
  | 'revoked'
  | 'disabled'
  | 'insufficient_scope'
  | 'rate_limited'
  | 'unreachable'
  | 'invalid';

export type ConfidenceCategory = 'critical' | 'high' | 'medium' | 'low' | 'unlikely';

export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'informational';

// ── Secret (canonical model) ──────────────────────────────────

export interface Secret {
  id: string;
  source: string;
  finding_target: string;
  repository: string;
  organization: string;
  branch: string;
  commit: string;
  file: string;
  line_number: number | null;
  scanner: string;
  collector: string;
  discovered_at: string;
  last_seen: string;
  secret_family: string;
  secret_type: string;
  provider: string;
  confidence_score: number;
  confidence_category: ConfidenceCategory;
  validation_level: ValidationLevel;
  validation_level_description?: string;
  provider_status: string | null;
  verification_status: VerificationStatus;
  verification_badge?: string;
  verification_reason: string;
  verified_at: string | null;
  masked_value: string;
  raw_value?: string; // only present when include_raw=true
  entropy: number;
  metadata: Record<string, unknown>;
  history: HistoryEntry[];
}

export interface SecretExportDict {
  id: string;
  source: string;
  repository: string;
  file: string;
  finding_target: string;
  secret_type: string;
  confidence: number;
  confidence_category: ConfidenceCategory;
  validation_level: ValidationLevel;
  verified: VerificationStatus;
  verification_badge?: string;
  masked_value: string;
  entropy: number;
  discovered_at: string;
  raw_value?: string;
}

export interface HistoryEntry {
  timestamp: string;
  event: string;
  details: Record<string, unknown>;
}

// ── API Responses ─────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
  filters?: Record<string, unknown>;
  include_raw?: boolean;
}

export interface FindingsListResponse {
  findings: SecretExportDict[];
  total: number;
  offset: number;
  limit: number;
  filters: Record<string, unknown>;
  include_raw: boolean;
}

export interface ExportJsonResponse {
  findings: SecretExportDict[];
  total: number;
  filters: Record<string, unknown>;
  include_raw: boolean;
  exported_at: string;
}

// ── Metrics ───────────────────────────────────────────────────

export interface ScanMetrics {
  assets_crawled: number;
  files_analyzed: number;
  candidate_secrets: number;
  false_positives_removed: number;
  duplicate_secrets_merged: number;
  high_confidence_secrets: number;
  medium_confidence_secrets: number;
  low_confidence_secrets: number;
  provider_verified: number;
  currently_active: number;
  expired: number;
  revoked: number;
  disabled: number;
  unknown: number;
  needs_review: number;
  verification_failures: number;
  average_confidence: number;
  validation_levels: {
    format: number;
    structure: number;
    heuristic: number;
    provider: number;
    active: number;
  };
  scanner_stats: Record<string, ScannerStat>;
  family_distribution: Record<string, number>;
  scan_timestamp: string;
}

export interface ScannerStat {
  count: number;
  high_confidence: number;
  verified: number;
}

// ── Filters ───────────────────────────────────────────────────

export interface FindingsFilters {
  source?: string;
  repository?: string;
  secret_type?: string;
  secret_family?: string;
  confidence_min?: number;
  confidence_max?: number;
  validation_level?: ValidationLevel;
  verified?: string | boolean;
  date?: string;
  date_from?: string;
  date_to?: string;
  provider?: string;
}

// ── Export Index ───────────────────────────────────────────────

export interface ExportIndex {
  id: string;
  export_date: string;
  export_dir: string;
  findings_count: number;
  created_at: string;
}

// ── Health ─────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  total_findings: number;
  timestamp: string;
}

// ── Sidebar Nav ───────────────────────────────────────────────

export type NavSection = 'dashboard' | 'search' | 'secrets' | 'repositories' | 'organizations' | 'assets' | 'scans' | 'analytics' | 'downloads' | 'api' | 'settings';

// ── Provider Logo Map ──────────────────────────────────────────

export const PROVIDER_DISPLAY: Record<string, { name: string; color: string; icon: string }> = {
  github: { name: 'GitHub', color: '#6E40C9', icon: 'github' },
  aws: { name: 'AWS', color: '#FF9900', icon: 'cloud' },
  openai: { name: 'OpenAI', color: '#412991', icon: 'sparkles' },
  anthropic: { name: 'Anthropic', color: '#D97706', icon: 'brain' },
  stripe: { name: 'Stripe', color: '#635BFF', icon: 'credit-card' },
  google: { name: 'Google', color: '#4285F4', icon: 'search' },
  gitlab: { name: 'GitLab', color: '#FC6D26', icon: 'git-branch' },
  discord: { name: 'Discord', color: '#5865F2', icon: 'message-circle' },
  slack: { name: 'Slack', color: '#4A154B', icon: 'hash' },
  cloudflare: { name: 'Cloudflare', color: '#F38020', icon: 'shield' },
  sendgrid: { name: 'SendGrid', color: '#1B3F8B', icon: 'mail' },
  twilio: { name: 'Twilio', color: '#F22F46', icon: 'phone' },
  mongodb: { name: 'MongoDB', color: '#47A248', icon: 'database' },
  postgresql: { name: 'PostgreSQL', color: '#336791', icon: 'database' },
  redis: { name: 'Redis', color: '#DC382D', icon: 'database' },
  ethereum: { name: 'Ethereum', color: '#8C8C8C', icon: 'coins' },
  bitcoin: { name: 'Bitcoin', color: '#F7931A', icon: 'coins' },
  ssh: { name: 'SSH', color: '#71717A', icon: 'terminal' },
  jwt: { name: 'JWT', color: '#06B6D4', icon: 'key' },
  mistral: { name: 'Mistral', color: '#F97316', icon: 'sparkles' },
  coinbase: { name: 'Coinbase', color: '#0052FF', icon: 'coins' },
  solana: { name: 'Solana', color: '#9945FF', icon: 'coins' },
  azure: { name: 'Azure', color: '#0078D4', icon: 'cloud' },
  mailgun: { name: 'Mailgun', color: '#F2762F', icon: 'mail' },
  pgp: { name: 'PGP', color: '#71717A', icon: 'shield-check' },
};

// ── Verification Badge Map ─────────────────────────────────────

export const VERIFICATION_BADGES: Record<VerificationStatus, { label: string; emoji: string; color: string }> = {
  active: { label: 'Currently Active', emoji: '✅', color: 'success' },
  valid_format: { label: 'Format Valid', emoji: '🟡', color: 'warning' },
  expired: { label: 'Expired', emoji: '⏰', color: 'text-muted' },
  revoked: { label: 'Revoked', emoji: '🔒', color: 'danger' },
  disabled: { label: 'Disabled', emoji: '⛔', color: 'text-muted' },
  insufficient_scope: { label: 'Insufficient Scope', emoji: '⚠️', color: 'warning' },
  rate_limited: { label: 'Rate Limited', emoji: '⏳', color: 'warning' },
  unreachable: { label: 'Unreachable', emoji: '🔌', color: 'text-muted' },
  invalid: { label: 'Invalid', emoji: '❌', color: 'danger' },
  unknown: { label: 'Unknown', emoji: '❓', color: 'text-muted' },
  unsupported: { label: 'Unsupported', emoji: '🚫', color: 'text-muted' },
};
