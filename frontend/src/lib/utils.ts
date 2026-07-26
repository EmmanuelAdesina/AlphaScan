import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { formatDistanceToNow, format } from 'date-fns';
import type { ConfidenceCategory, VerificationStatus, ValidationLevel } from '@/types';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string): string {
  try {
    return format(new Date(date), 'MMM d, yyyy');
  } catch {
    return date;
  }
}

export function formatDateTime(date: string): string {
  try {
    return format(new Date(date), 'MMM d, yyyy HH:mm');
  } catch {
    return date;
  }
}

export function formatRelativeTime(date: string): string {
  try {
    return formatDistanceToNow(new Date(date), { addSuffix: true });
  } catch {
    return date;
  }
}

export function formatConfidence(score: number): string {
  return `${Math.round(score)}%`;
}

export function getConfidenceColor(category: ConfidenceCategory): string {
  switch (category) {
    case 'critical': return 'text-danger';
    case 'high': return 'text-warning';
    case 'medium': return 'text-primary';
    case 'low': return 'text-info';
    case 'unlikely': return 'text-text-muted';
    default: return 'text-text-secondary';
  }
}

export function getConfidenceBg(category: ConfidenceCategory): string {
  switch (category) {
    case 'critical': return 'bg-danger/20 text-danger';
    case 'high': return 'bg-warning/20 text-warning';
    case 'medium': return 'bg-primary/20 text-primary';
    case 'low': return 'bg-info/20 text-info';
    case 'unlikely': return 'bg-text-muted/20 text-text-muted';
    default: return 'bg-text-muted/20 text-text-secondary';
  }
}

export function getVerificationColor(status: VerificationStatus): string {
  switch (status) {
    case 'active': return 'bg-success/20 text-success';
    case 'valid_format': return 'bg-warning/20 text-warning';
    case 'expired': return 'bg-text-muted/20 text-text-muted';
    case 'revoked': return 'bg-danger/20 text-danger';
    case 'disabled': return 'bg-text-muted/20 text-text-muted';
    case 'invalid': return 'bg-danger/20 text-danger';
    case 'unknown': return 'bg-text-muted/20 text-text-muted';
    case 'unsupported': return 'bg-text-muted/20 text-text-muted';
    case 'insufficient_scope': return 'bg-warning/20 text-warning';
    case 'rate_limited': return 'bg-warning/20 text-warning';
    case 'unreachable': return 'bg-text-muted/20 text-text-muted';
    default: return 'bg-text-muted/20 text-text-muted';
  }
}

export function getValidationLevelLabel(level: ValidationLevel): string {
  switch (level) {
    case 'none': return 'None';
    case 'format': return 'Format Valid';
    case 'structure': return 'Structure Valid';
    case 'heuristic': return 'Heuristic Valid';
    case 'provider': return 'Provider Verified';
    case 'active': return 'Active Verified';
    default: return level;
  }
}

export function getValidationLevelColor(level: ValidationLevel): string {
  switch (level) {
    case 'none': return 'bg-text-muted/20 text-text-muted';
    case 'format': return 'bg-info/20 text-info';
    case 'structure': return 'bg-info/20 text-info';
    case 'heuristic': return 'bg-primary/20 text-primary';
    case 'provider': return 'bg-warning/20 text-warning';
    case 'active': return 'bg-success/20 text-success';
    default: return 'bg-text-muted/20 text-text-secondary';
  }
}

export function maskSecretDisplay(masked: string): string {
  if (!masked) return '[empty]';
  // If the backend already provides a masked value, use it
  // but add visual masking for display
  return masked;
}

export function truncate(str: string, length: number = 50): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

export function formatNumber(num: number): string {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return String(num);
}

export function pluralize(count: number, singular: string, plural?: string): string {
  return count === 1 ? singular : (plural || `${singular}s`);
}
