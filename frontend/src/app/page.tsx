'use client';

import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import { cn, formatDate } from '@/lib/utils';
import { MetricCard } from '@/components/ui/metric-card';
import { VerificationBadge, ConfidenceBadge, SourceBadge, SecretTypeBadge } from '@/components/ui/badges';
import { ProviderLogo } from '@/components/ui/provider-logo';
import {
  KeyRound, ShieldCheck, XCircle, CheckCircle2, TrendingUp,
  BarChart3, Globe, FileCode, Clock, AlertTriangle, Zap,
  GitBranch, Eye, Activity,
} from 'lucide-react';
import type { ScanMetrics, SecretExportDict, VerificationStatus } from '@/types';

export default function DashboardPage() {
  const metricsQuery = useQuery({
    queryKey: ['metrics'],
    queryFn: () => api.getMetrics(),
  });

  const findingsQuery = useQuery({
    queryKey: ['recent-findings'],
    queryFn: () => api.getFindings({ limit: 8, sort_by: 'discovered_at' }),
  });

  const metrics = metricsQuery.data;
  const recentFindings = findingsQuery.data?.findings || [];

  return (
    <div className="space-y-6 max-w-[1400px]">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Dashboard</h1>
          <p className="text-sm text-text-muted mt-0.5">
            Secret intelligence overview
          </p>
        </div>
        <div className="flex items-center gap-2 text-2xs text-text-muted">
          <Activity className="w-3.5 h-3.5 text-success" />
          <span>Last scan: {metrics?.scan_timestamp ? formatDate(metrics.scan_timestamp) : '—'}</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
        <MetricCard
          label="Candidate Secrets"
          value={metrics?.candidate_secrets ?? 0}
          icon={KeyRound}
          color="primary"
          subtitle="All detected candidates"
        />
        <MetricCard
          label="Verified Secrets"
          value={metrics?.provider_verified ?? 0}
          icon={ShieldCheck}
          color="success"
          subtitle="Provider confirmed"
        />
        <MetricCard
          label="Currently Active"
          value={metrics?.currently_active ?? 0}
          icon={Zap}
          color="critical"
          subtitle="Confirmed live credentials"
        />
        <MetricCard
          label="False Positives Removed"
          value={metrics?.false_positives_removed ?? 0}
          icon={XCircle}
          color="default"
          subtitle="Filtered from results"
        />
        <MetricCard
          label="Avg Confidence"
          value={Math.round(metrics?.average_confidence ?? 0)}
          icon={BarChart3}
          color="info"
          format={false}
          subtitle="Mean across all secrets"
        />
        <MetricCard
          label="Expired Keys"
          value={metrics?.expired ?? 0}
          icon={Clock}
          color="warning"
        />
        <MetricCard
          label="Revoked Keys"
          value={metrics?.revoked ?? 0}
          icon={XCircle}
          color="danger"
        />
        <MetricCard
          label="Needs Review"
          value={metrics?.needs_review ?? 0}
          icon={AlertTriangle}
          color="warning"
        />
        <MetricCard
          label="Repos Scanned"
          value={metrics?.assets_crawled ?? 0}
          icon={GitBranch}
          color="default"
        />
        <MetricCard
          label="Dupes Merged"
          value={metrics?.duplicate_secrets_merged ?? 0}
          icon={CheckCircle2}
          color="default"
        />
      </div>

      {/* Two-column: Activity Feed + Family Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Live Activity Feed */}
        <div className="card p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text-primary">Live Activity</h2>
            <span className="flex items-center gap-1 text-2xs text-success font-medium">
              <Zap className="w-3 h-3" />
              Realtime
            </span>
          </div>

          <div className="space-y-2">
            {recentFindings.length === 0 ? (
              <div className="py-8 text-center text-sm text-text-muted">
                No recent findings
              </div>
            ) : (
              recentFindings.map((finding, i) => (
                <motion.div
                  key={finding.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.2, delay: i * 0.04 }}
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-bg-hover transition-colors cursor-pointer group"
                >
                  <ProviderLogo provider={finding.secret_type.split(' ')[0].toLowerCase()} size="sm" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-medium text-text-primary truncate">{finding.secret_type}</span>
                      <VerificationBadge status={finding.verified} size="sm" />
                      <ConfidenceBadge score={finding.confidence} category={finding.confidence_category} size="sm" />
                    </div>
                    <div className="flex items-center gap-2 text-2xs text-text-muted">
                      {finding.repository && <span>{finding.repository}</span>}
                      {finding.file && <span>· {finding.file}</span>}
                      <span>· {formatDate(finding.discovered_at)}</span>
                    </div>
                  </div>
                  <SourceBadge source={finding.source} />
                </motion.div>
              ))
            )}
          </div>
        </div>

        {/* Family Distribution */}
        <div className="card p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text-primary">Secret Families</h2>
            <span className="text-2xs text-text-muted">{metrics ? Object.keys(metrics.family_distribution).length : 0} families</span>
          </div>

          <div className="space-y-2">
            {metrics?.family_distribution && Object.entries(metrics.family_distribution)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 10)
              .map(([family, count], i) => {
                const maxCount = Math.max(...Object.values(metrics.family_distribution));
                const percentage = maxCount > 0 ? (count / maxCount) * 100 : 0;

                return (
                  <motion.div
                    key={family}
                    initial={{ opacity: 0, x: -4 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.15, delay: i * 0.02 }}
                    className="flex items-center gap-3"
                  >
                    <span className="text-xs text-text-secondary w-[140px] truncate">{family.replace('_', ' ')}</span>
                    <div className="flex-1 h-5 bg-bg-hover rounded overflow-hidden">
                      <motion.div
                        className="h-full bg-primary/30 rounded"
                        initial={{ width: 0 }}
                        animate={{ width: `${percentage}%` }}
                        transition={{ duration: 0.5, delay: i * 0.03 }}
                      />
                    </div>
                    <span className="text-xs font-medium text-text-primary tabular-nums w-[40px] text-right">{count}</span>
                  </motion.div>
                );
              })}
          </div>

          {/* Validation level breakdown */}
          {metrics?.validation_levels && (
            <div className="mt-4 pt-4 border-t border-border">
              <div className="section-header mb-2">Validation Levels</div>
              <div className="grid grid-cols-5 gap-2">
                {Object.entries(metrics.validation_levels).map(([level, count]) => (
                  <div key={level} className="text-center">
                    <div className="text-sm font-semibold text-text-primary tabular-nums">{count}</div>
                    <div className="text-2xs text-text-muted uppercase tracking-wide">{level}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
