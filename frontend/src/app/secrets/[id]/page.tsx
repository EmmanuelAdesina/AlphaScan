'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import { cn, formatDate, formatDateTime, formatRelativeTime } from '@/lib/utils';
import {
  VerificationBadge, ConfidenceBadge, ValidationLevelBadge, RiskBadge, SourceBadge,
} from '@/components/ui/badges';
import { ProviderLogo } from '@/components/ui/provider-logo';
import {
  ArrowLeft, Clock, GitBranch, FileCode, Hash, Shield, Eye, EyeOff,
  ExternalLink, Copy, AlertTriangle, CheckCircle2, Globe, Building2,
} from 'lucide-react';
import { useState } from 'react';

export async function generateStaticParams() {
  return [{ id: '1' }, { id: '2' }];
}

export default function SecretDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const [showRaw, setShowRaw] = useState(false);
  const [copied, setCopied] = useState(false);

  const findingQuery = useQuery({
    queryKey: ['finding', id],
    queryFn: () => api.getFinding(id),
    enabled: !!id,
  });

  const finding = findingQuery.data;

  if (!finding && !findingQuery.isLoading) {
    return (
      <div className="py-16 text-center">
        <AlertTriangle className="w-8 h-8 text-text-muted mx-auto mb-3" />
        <p className="text-sm text-text-muted">Finding not found</p>
      </div>
    );
  }

  if (findingQuery.isLoading) {
    return (
      <div className="space-y-4 max-w-[900px]">
        <div className="skeleton h-8 w-1/4" />
        <div className="skeleton h-6 w-1/2" />
        <div className="card p-6 space-y-4">
          <div className="skeleton h-4 w-1/3" />
          <div className="skeleton h-4 w-2/3" />
          <div className="skeleton h-4 w-1/2" />
        </div>
      </div>
    );
  }

  if (!finding) return null;

  return (
    <div className="space-y-6 max-w-[900px]">
      {/* Back button */}
      <button
        onClick={() => window.history.back()}
        className="flex items-center gap-1.5 text-sm text-text-muted hover:text-text-secondary transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Secrets
      </button>

      {/* Overview section */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-6"
      >
        <div className="flex items-start gap-4">
          <ProviderLogo provider={finding.secret_type.split(' ')[0].toLowerCase()} size="lg" showLabel />

          <div className="flex-1 space-y-4">
            {/* Title row */}
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-lg font-semibold text-text-primary">{finding.secret_type}</h1>
              <ConfidenceBadge score={finding.confidence ?? finding.confidence_score ?? 0} category={finding.confidence_category} size="lg" />
              <VerificationBadge status={(finding.verified as any) ?? finding.verification_status ?? 'unknown'} size="lg" />
              <ValidationLevelBadge level={finding.validation_level} size="md" />
              {finding.metadata && 'risk_classification' in finding.metadata && (
                <RiskBadge risk={String(finding.metadata.risk_classification)} />
              )}
              <SourceBadge source={finding.source} />
            </div>

            {/* Metadata row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              {finding.repository && (
                <div className="flex items-center gap-1.5 text-text-secondary">
                  <GitBranch className="w-3.5 h-3.5 text-text-muted" />
                  {finding.repository}
                </div>
              )}
              {finding.file && (
                <div className="flex items-center gap-1.5 text-text-secondary">
                  <FileCode className="w-3.5 h-3.5 text-text-muted" />
                  {finding.file}
                </div>
              )}
              <div className="flex items-center gap-1.5 text-text-secondary">
                <Clock className="w-3.5 h-3.5 text-text-muted" />
                {formatDateTime(finding.discovered_at)}
              </div>
              {finding.entropy > 0 && (
                <div className="flex items-center gap-1.5 text-text-secondary">
                  <Hash className="w-3.5 h-3.5 text-text-muted" />
                  Entropy: {finding.entropy.toFixed(2)}
                </div>
              )}
            </div>

            {/* Masked value with reveal toggle */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="section-header">Secret Value</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowRaw(!showRaw)}
                    className={cn(
                      'flex items-center gap-1 px-2 py-1 rounded text-2xs border transition-colors',
                      showRaw
                        ? 'bg-danger/10 border-danger/30 text-danger'
                        : 'bg-bg-hover border-border text-text-secondary hover:text-text-primary',
                    )}
                  >
                    {showRaw ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                    {showRaw ? 'Hide' : 'Reveal'}
                  </button>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(showRaw ? (finding.raw_value || finding.masked_value) : finding.masked_value);
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    }}
                    className="flex items-center gap-1 px-2 py-1 rounded text-2xs bg-bg-hover border border-border text-text-secondary hover:text-text-primary transition-colors"
                  >
                    <Copy className="w-3 h-3" />
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
              </div>
              <div className={cn(
                'mono text-sm bg-black/30 border border-border rounded-lg px-3 py-2',
                showRaw && 'border-danger/30 bg-danger/5',
              )}>
                {showRaw ? (finding.raw_value || '⚠️ Not available — requires authorization') : finding.masked_value}
              </div>
              {showRaw && (
                <div className="flex items-center gap-1.5 text-2xs text-danger font-medium">
                  <AlertTriangle className="w-3 h-3" />
                  Revealing raw secret values — audit this action
                </div>
              )}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Verification Section */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card p-6"
      >
        <h2 className="text-sm font-semibold text-text-primary mb-4">Verification</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <DetailRow label="Status" value={<VerificationBadge status={(finding.verified as any) ?? finding.verification_status ?? 'unknown'} size="md" />} />
            <DetailRow label="Validation Level" value={<ValidationLevelBadge level={finding.validation_level} size="md" />} />
            <DetailRow label="Reason" value={finding.verification_reason || 'No verification reason recorded'} />
          </div>
          <div className="space-y-3">
            <DetailRow label="Provider" value={finding.secret_type.includes(' ') ? finding.secret_type.split(' ')[0] : finding.provider || 'Unknown'} />
            <DetailRow label="Verified At" value={finding.verified_at ? formatDateTime(finding.verified_at) : 'Not verified'} />
            <DetailRow label="Method" value="Provider API verification" />
          </div>
        </div>
      </motion.div>

      {/* Context Section */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="card p-6"
      >
        <h2 className="text-sm font-semibold text-text-primary mb-4">Context</h2>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <DetailRow label="Source" value={finding.source} />
          <DetailRow label="Target" value={finding.finding_target} />
          <DetailRow label="Repository" value={finding.repository || 'N/A'} />
          <DetailRow label="File" value={finding.file || 'N/A'} />
          <DetailRow label="Family" value={finding.confidence_category} />
          <DetailRow label="Discovered" value={formatRelativeTime(finding.discovered_at)} />
        </div>
      </motion.div>

      {/* Confidence Breakdown */}
      {finding.metadata && 'confidence_breakdown' in finding.metadata && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card p-6"
        >
          <h2 className="text-sm font-semibold text-text-primary mb-4">Confidence Breakdown</h2>

          <div className="space-y-2">
            {Array.isArray((finding.metadata as any)?.confidence_breakdown?.factors) &&
              (finding.metadata as any)?.confidence_breakdown?.factors?.map((factor: any, i: number) => (
                <div key={i} className="flex items-center gap-3 py-1">
                  <span className="text-xs text-text-secondary w-[160px] truncate">{factor.name}</span>
                  <div className="flex-1 h-4 bg-bg-hover rounded overflow-hidden">
                    <motion.div
                      className="h-full bg-primary/30 rounded"
                      initial={{ width: 0 }}
                      animate={{ width: `${(factor.score / factor.max_score) * 100}%` }}
                      transition={{ duration: 0.4, delay: i * 0.05 }}
                    />
                  </div>
                  <span className="text-xs font-medium text-text-primary tabular-nums w-[60px] text-right">
                    {factor.score}/{factor.max_score}
                  </span>
                </div>
              ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-2xs text-text-muted uppercase tracking-wide font-medium min-w-[100px] shrink-0">{label}</span>
      <div className="text-sm text-text-secondary flex-1">{value}</div>
    </div>
  );
}
