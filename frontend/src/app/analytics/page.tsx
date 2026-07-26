'use client';

import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { MetricCard } from '@/components/ui/metric-card';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, AreaChart, Area,
} from 'recharts';
import {
  KeyRound, ShieldCheck, BarChart3, TrendingUp, AlertTriangle, Activity,
} from 'lucide-react';
import type { ScanMetrics } from '@/types';

const CHART_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#06B6D4',
  '#8B5CF6', '#F97316', '#EC4899', '#14B8A6', '#6366F1',
];

export default function AnalyticsPage() {
  const metricsQuery = useQuery({
    queryKey: ['metrics'],
    queryFn: () => api.getMetrics(),
  });

  const metrics = metricsQuery.data;

  // Prepare chart data
  const familyData = metrics?.family_distribution
    ? Object.entries(metrics.family_distribution)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 12)
        .map(([name, value]) => ({ name: name.replace(/_/g, ' '), value }))
    : [];

  const validationData = metrics?.validation_levels
    ? [
        { name: 'Format', value: metrics.validation_levels.format },
        { name: 'Structure', value: metrics.validation_levels.structure },
        { name: 'Heuristic', value: metrics.validation_levels.heuristic },
        { name: 'Provider', value: metrics.validation_levels.provider },
        { name: 'Active', value: metrics.validation_levels.active },
      ]
    : [];

  const verificationData = metrics
    ? [
        { name: 'Active', value: metrics.currently_active, color: '#10B981' },
        { name: 'Expired', value: metrics.expired, color: '#71717A' },
        { name: 'Revoked', value: metrics.revoked, color: '#EF4444' },
        { name: 'Disabled', value: metrics.disabled, color: '#71717A' },
        { name: 'Unknown', value: metrics.unknown, color: '#A1A1AA' },
        { name: 'Invalid', value: 0, color: '#EF4444' }, // from validation_results
      ]
    : [];

  const confidenceData = metrics
    ? [
        { name: 'Critical', range: '90-100', value: metrics.high_confidence_secrets, fill: '#EF4444' },
        { name: 'Medium', range: '40-69', value: metrics.medium_confidence_secrets, fill: '#3B82F6' },
        { name: 'Low', range: '0-39', value: metrics.low_confidence_secrets, fill: '#06B6D4' },
      ]
    : [];

  return (
    <div className="space-y-6 max-w-[1400px]">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Analytics</h1>
        <p className="text-sm text-text-muted mt-0.5">Secret intelligence statistics</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Total Secrets"
          value={metrics?.candidate_secrets ?? 0}
          icon={KeyRound}
          color="primary"
        />
        <MetricCard
          label="Verified"
          value={metrics?.provider_verified ?? 0}
          icon={ShieldCheck}
          color="success"
        />
        <MetricCard
          label="Avg Confidence"
          value={Math.round(metrics?.average_confidence ?? 0)}
          icon={BarChart3}
          color="info"
          format={false}
        />
        <MetricCard
          label="FP Removed"
          value={metrics?.false_positives_removed ?? 0}
          icon={AlertTriangle}
          color="default"
        />
      </div>

      {/* Charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Secrets by Family */}
        <div className="card p-4">
          <h2 className="text-sm font-semibold text-text-primary mb-4">Secrets by Family</h2>
          {familyData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={familyData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                <XAxis
                  dataKey="name"
                  tick={{ fill: '#A1A1AA', fontSize: 11 }}
                  axisLine={{ stroke: '#232326' }}
                  tickLine={{ stroke: '#232326' }}
                />
                <YAxis
                  tick={{ fill: '#A1A1AA', fontSize: 11 }}
                  axisLine={{ stroke: '#232326' }}
                  tickLine={{ stroke: '#232326' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111113',
                    border: '1px solid #232326',
                    borderRadius: 8,
                    color: '#FAFAFA',
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {familyData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="py-12 text-center text-sm text-text-muted">No data available</div>
          )}
        </div>

        {/* Verification Status Distribution */}
        <div className="card p-4">
          <h2 className="text-sm font-semibold text-text-primary mb-4">Verification Status</h2>
          {verificationData.some(d => d.value > 0) ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={verificationData.filter(d => d.value > 0)}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  innerRadius={60}
                  paddingAngle={2}
                  strokeWidth={0}
                >
                  {verificationData.filter(d => d.value > 0).map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Legend
                  wrapperStyle={{ fontSize: 11, color: '#A1A1AA' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111113',
                    border: '1px solid #232326',
                    borderRadius: 8,
                    color: '#FAFAFA',
                    fontSize: 12,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="py-12 text-center text-sm text-text-muted">No data available</div>
          )}
        </div>

        {/* Confidence Distribution */}
        <div className="card p-4">
          <h2 className="text-sm font-semibold text-text-primary mb-4">Confidence Distribution</h2>
          {confidenceData.some(d => d.value > 0) ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={confidenceData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                <XAxis
                  dataKey="name"
                  tick={{ fill: '#A1A1AA', fontSize: 11 }}
                  axisLine={{ stroke: '#232326' }}
                  tickLine={{ stroke: '#232326' }}
                />
                <YAxis
                  tick={{ fill: '#A1A1AA', fontSize: 11 }}
                  axisLine={{ stroke: '#232326' }}
                  tickLine={{ stroke: '#232326' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111113',
                    border: '1px solid #232326',
                    borderRadius: 8,
                    color: '#FAFAFA',
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {confidenceData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="py-12 text-center text-sm text-text-muted">No data available</div>
          )}
        </div>

        {/* Validation Levels */}
        <div className="card p-4">
          <h2 className="text-sm font-semibold text-text-primary mb-4">Validation Levels</h2>
          {validationData.some(d => d.value > 0) ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={validationData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                <XAxis
                  dataKey="name"
                  tick={{ fill: '#A1A1AA', fontSize: 11 }}
                  axisLine={{ stroke: '#232326' }}
                  tickLine={{ stroke: '#232326' }}
                />
                <YAxis
                  tick={{ fill: '#A1A1AA', fontSize: 11 }}
                  axisLine={{ stroke: '#232326' }}
                  tickLine={{ stroke: '#232326' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111113',
                    border: '1px solid #232326',
                    borderRadius: 8,
                    color: '#FAFAFA',
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="value" fill="#3B82F6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="py-12 text-center text-sm text-text-muted">No data available</div>
          )}
        </div>
      </div>

      {/* Scanner Statistics */}
      {metrics?.scanner_stats && Object.keys(metrics.scanner_stats).length > 0 && (
        <div className="card p-4">
          <h2 className="text-sm font-semibold text-text-primary mb-4">Scanner Statistics</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 text-text-muted section-header">Scanner</th>
                  <th className="text-right py-2 text-text-muted section-header">Count</th>
                  <th className="text-right py-2 text-text-muted section-header">High Confidence</th>
                  <th className="text-right py-2 text-text-muted section-header">Verified</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(metrics.scanner_stats).map(([scanner, stats]) => (
                  <tr key={scanner} className="border-b border-border/50 hover:bg-bg-hover transition-colors">
                    <td className="py-2 text-text-primary font-medium">{scanner}</td>
                    <td className="py-2 text-right text-text-secondary tabular-nums">{stats.count}</td>
                    <td className="py-2 text-right text-text-secondary tabular-nums">{stats.high_confidence}</td>
                    <td className="py-2 text-right text-text-secondary tabular-nums">{stats.verified}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
