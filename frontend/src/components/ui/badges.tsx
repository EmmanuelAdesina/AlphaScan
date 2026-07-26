'use client';

import { cn } from '@/lib/utils';
import { getConfidenceBg, getVerificationColor, getValidationLevelColor } from '@/lib/utils';
import type { ConfidenceCategory, VerificationStatus, ValidationLevel } from '@/types';
import { VERIFICATION_BADGES } from '@/types';

// ── Verification Badge ────────────────────────────────────────

export function VerificationBadge({ status, size = 'sm' }: { status: VerificationStatus; size?: 'sm' | 'md' | 'lg' }) {
  const badge = VERIFICATION_BADGES[status];
  const colorClass = getVerificationColor(status);

  return (
    <span className={cn(
      'inline-flex items-center gap-1 rounded font-medium tabular-nums',
      colorClass,
      size === 'sm' && 'px-1.5 py-0.5 text-2xs',
      size === 'md' && 'px-2 py-1 text-xs',
      size === 'lg' && 'px-2.5 py-1.5 text-sm',
      status === 'active' && 'shadow-glow-success',
      status === 'invalid' && 'shadow-glow-danger',
    )}>
      <span className="leading-none">{badge.emoji}</span>
      <span className="tracking-wide uppercase">{badge.label}</span>
    </span>
  );
}

// ── Confidence Badge ───────────────────────────────────────────

export function ConfidenceBadge({ score, category, size = 'sm' }: { score: number; category: ConfidenceCategory; size?: 'sm' | 'md' | 'lg' }) {
  const colorClass = getConfidenceBg(category);

  return (
    <span className={cn(
      'inline-flex items-center gap-1 rounded font-medium tabular-nums',
      colorClass,
      size === 'sm' && 'px-1.5 py-0.5 text-2xs',
      size === 'md' && 'px-2 py-1 text-xs',
      size === 'lg' && 'px-2.5 py-1.5 text-sm',
      category === 'critical' && 'shadow-glow-critical',
    )}>
      <span className="font-semibold">{Math.round(score)}%</span>
      <span className="tracking-wide uppercase hidden sm:inline">{category}</span>
    </span>
  );
}

// ── Validation Level Badge ─────────────────────────────────────

export function ValidationLevelBadge({ level, size = 'sm' }: { level: ValidationLevel; size?: 'sm' | 'md' | 'lg' }) {
  const colorClass = getValidationLevelColor(level);
  const label = level.replace('_', ' ');

  return (
    <span className={cn(
      'inline-flex items-center gap-1 rounded font-medium tracking-wide uppercase',
      colorClass,
      size === 'sm' && 'px-1.5 py-0.5 text-2xs',
      size === 'md' && 'px-2 py-1 text-xs',
      size === 'lg' && 'px-2.5 py-1.5 text-sm',
    )}>
      {label}
    </span>
  );
}

// ── Risk Badge ──────────────────────────────────────────────────

export function RiskBadge({ risk }: { risk: string }) {
  const colorMap: Record<string, string> = {
    critical: 'bg-danger/20 text-danger shadow-glow-danger',
    high: 'bg-warning/20 text-warning',
    medium: 'bg-primary/20 text-primary',
    low: 'bg-text-muted/20 text-text-muted',
    informational: 'bg-info/20 text-info',
  };

  return (
    <span className={cn(
      'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-2xs font-medium tracking-wide uppercase',
      colorMap[risk] || 'bg-text-muted/20 text-text-muted',
    )}>
      {risk}
    </span>
  );
}

// ── Source Badge ────────────────────────────────────────────────

export function SourceBadge({ source }: { source: string }) {
  const colorMap: Record<string, string> = {
    github: 'bg-provider-github/20 text-provider-github',
    censys: 'bg-primary/20 text-primary',
    pastebin: 'bg-warning/20 text-warning',
  };

  return (
    <span className={cn(
      'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-2xs font-medium tracking-wide uppercase',
      colorMap[source] || 'bg-text-muted/20 text-text-secondary',
    )}>
      {source}
    </span>
  );
}

// ── Secret Type Badge ──────────────────────────────────────────

export function SecretTypeBadge({ type }: { type: string }) {
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-2xs font-medium bg-bg-hover text-text-secondary">
      {type}
    </span>
  );
}
