'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { SecretCard } from '@/components/secrets/secret-card';
import { VerificationBadge, ConfidenceBadge, ValidationLevelBadge, SourceBadge } from '@/components/ui/badges';
import {
  Search, Filter, ChevronLeft, ChevronRight, Download, FileJson, FileText,
  SlidersHorizontal, X,
} from 'lucide-react';
import type { FindingsFilters, VerificationStatus, ValidationLevel } from '@/types';

const SOURCES = ['github', 'censys', 'pastebin'];
const VERIFICATION_STATUSES: VerificationStatus[] = ['active', 'valid_format', 'expired', 'revoked', 'disabled', 'invalid', 'unknown'];
const VALIDATION_LEVELS: ValidationLevel[] = ['none', 'format', 'structure', 'heuristic', 'provider', 'active'];
const CONFIDENCE_RANGES = [
  { label: 'Critical (90+)', min: 90, max: 100 },
  { label: 'High (70-89)', min: 70, max: 89 },
  { label: 'Medium (40-69)', min: 40, max: 69 },
  { label: 'Low (<40)', min: 0, max: 39 },
];

export default function SecretsPage() {
  const [filters, setFilters] = useState<FindingsFilters>({});
  const [page, setPage] = useState(0);
  const [showFilters, setShowFilters] = useState(false);
  const limit = 20;

  const findingsQuery = useQuery({
    queryKey: ['findings', filters, page],
    queryFn: () => api.getFindings({ ...filters, offset: page * limit, limit }),
  });

  const metricsQuery = useQuery({
    queryKey: ['metrics'],
    queryFn: () => api.getMetrics(),
  });

  const findings = findingsQuery.data?.findings || [];
  const total = findingsQuery.data?.total || 0;
  const totalPages = Math.ceil(total / limit);

  const updateFilter = (key: string, value: string | number | boolean | undefined) => {
    setFilters(prev => {
      const next = { ...prev };
      if (value === undefined || value === '' || value === false) {
        delete next[key as keyof FindingsFilters];
      } else {
        (next as any)[key] = value;
      }
      return next;
    });
    setPage(0);
  };

  const clearFilters = () => {
    setFilters({});
    setPage(0);
  };

  const activeFilterCount = Object.values(filters).filter(v => v !== undefined && v !== '' && v !== false).length;

  return (
    <div className="space-y-4 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Secrets</h1>
          <p className="text-sm text-text-muted mt-0.5">
            {total} findings · {metricsQuery.data?.high_confidence_secrets ?? 0} high confidence · {metricsQuery.data?.currently_active ?? 0} active
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border transition-colors',
              activeFilterCount > 0
                ? 'bg-primary/10 border-primary/30 text-primary'
                : 'bg-bg-hover border-border text-text-secondary hover:text-text-primary',
            )}
          >
            <SlidersHorizontal className="w-4 h-4" />
            Filters
            {activeFilterCount > 0 && (
              <span className="text-2xs font-medium bg-primary px-1.5 py-0.5 rounded text-text-inverted">
                {activeFilterCount}
              </span>
            )}
          </button>
          <a
            href={api.getExportJsonUrl(filters)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm bg-bg-hover border border-border text-text-secondary hover:text-text-primary transition-colors"
          >
            <FileJson className="w-4 h-4" />
            JSON
          </a>
          <a
            href={api.getExportCsvUrl(filters)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm bg-bg-hover border border-border text-text-secondary hover:text-text-primary transition-colors"
          >
            <FileText className="w-4 h-4" />
            CSV
          </a>
        </div>
      </div>

      {/* Filter panel */}
      {showFilters && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="card p-4 space-y-4"
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-text-primary">Filters</span>
            {activeFilterCount > 0 && (
              <button
                onClick={clearFilters}
                className="flex items-center gap-1 text-2xs text-text-muted hover:text-danger transition-colors"
              >
                <X className="w-3 h-3" />
                Clear all
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {/* Source filter */}
            <div>
              <label className="section-header mb-1.5 block">Source</label>
              <select
                value={filters.source || ''}
                onChange={(e) => updateFilter('source', e.target.value)}
                className="w-full bg-bg-hover border border-border rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-primary"
              >
                <option value="">All sources</option>
                {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            {/* Verification status filter */}
            <div>
              <label className="section-header mb-1.5 block">Verification</label>
              <select
                value={filters.verified || ''}
                onChange={(e) => updateFilter('verified', e.target.value)}
                className="w-full bg-bg-hover border border-border rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-primary"
              >
                <option value="">All statuses</option>
                {VERIFICATION_STATUSES.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
              </select>
            </div>

            {/* Validation level filter */}
            <div>
              <label className="section-header mb-1.5 block">Validation Level</label>
              <select
                value={filters.validation_level || ''}
                onChange={(e) => updateFilter('validation_level', e.target.value)}
                className="w-full bg-bg-hover border border-border rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-primary"
              >
                <option value="">All levels</option>
                {VALIDATION_LEVELS.map(l => <option key={l} value={l}>{l.replace('_', ' ')}</option>)}
              </select>
            </div>

            {/* Confidence range filter */}
            <div>
              <label className="section-header mb-1.5 block">Confidence</label>
              <select
                value={filters.confidence_min !== undefined ? `${filters.confidence_min}-${filters.confidence_max}` : ''}
                onChange={(e) => {
                  if (!e.target.value) {
                    updateFilter('confidence_min', undefined);
                    updateFilter('confidence_max', undefined);
                  } else {
                    const [min, max] = e.target.value.split('-').map(Number);
                    updateFilter('confidence_min', min);
                    updateFilter('confidence_max', max);
                  }
                }}
                className="w-full bg-bg-hover border border-border rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-primary"
              >
                <option value="">All confidence</option>
                {CONFIDENCE_RANGES.map(r => <option key={`${r.min}-${r.max}`} value={`${r.min}-${r.max}`}>{r.label}</option>)}
              </select>
            </div>

            {/* Provider filter */}
            <div>
              <label className="section-header mb-1.5 block">Provider</label>
              <input
                type="text"
                value={filters.provider || ''}
                onChange={(e) => updateFilter('provider', e.target.value)}
                placeholder="e.g. github, aws, openai"
                className="w-full bg-bg-hover border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-primary"
              />
            </div>

            {/* Repository filter */}
            <div>
              <label className="section-header mb-1.5 block">Repository</label>
              <input
                type="text"
                value={filters.repository || ''}
                onChange={(e) => updateFilter('repository', e.target.value)}
                placeholder="e.g. org/repo"
                className="w-full bg-bg-hover border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-primary"
              />
            </div>

            {/* Date filter */}
            <div>
              <label className="section-header mb-1.5 block">Date</label>
              <input
                type="date"
                value={filters.date || ''}
                onChange={(e) => updateFilter('date', e.target.value)}
                className="w-full bg-bg-hover border border-border rounded-lg px-3 py-2 text-sm text-text-primary outline-none focus:border-primary"
              />
            </div>
          </div>
        </motion.div>
      )}

      {/* Results */}
      <div className="space-y-2">
        {findingsQuery.isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="card p-4 space-y-3">
                <div className="skeleton h-4 w-1/3" />
                <div className="skeleton h-3 w-2/3" />
                <div className="skeleton h-3 w-1/2" />
              </div>
            ))}
          </div>
        )}

        {!findingsQuery.isLoading && findings.length === 0 && (
          <div className="py-16 text-center">
            <KeyRound className="w-8 h-8 text-text-muted mx-auto mb-3" />
            <p className="text-sm text-text-muted">No secrets found matching your filters</p>
            {activeFilterCount > 0 && (
              <button onClick={clearFilters} className="mt-2 text-sm text-primary hover:text-primary-hover">
                Clear filters
              </button>
            )}
          </div>
        )}

        {!findingsQuery.isLoading && findings.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {findings.map((finding, i) => (
              <SecretCard key={finding.id} secret={finding} index={i} />
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-border">
          <span className="text-sm text-text-muted">
            Showing {page * limit + 1}–{Math.min((page + 1) * limit, total)} of {total}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm border border-border bg-bg-hover text-text-secondary hover:text-text-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </button>
            <span className="text-sm text-text-muted tabular-nums">
              {page + 1} / {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm border border-border bg-bg-hover text-text-secondary hover:text-text-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
