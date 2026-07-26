'use client';

import { Globe, Zap } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { MetricCard } from '@/components/ui/metric-card';

export default function AssetsPage() {
  const metricsQuery = useQuery({ queryKey: ['metrics'], queryFn: () => api.getMetrics() });
  const metrics = metricsQuery.data;

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Assets</h1>
        <p className="text-sm text-text-muted mt-0.5">Domains, IPs, hosts, and certificates</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <MetricCard label="Assets Crawled" value={metrics?.assets_crawled ?? 0} icon={Globe} color="primary" />
        <MetricCard label="Files Analyzed" value={metrics?.files_analyzed ?? 0} icon={Globe} color="default" />
        <MetricCard label="Hosts Indexed" value={0} icon={Globe} color="default" subtitle="Coming soon" />
      </div>

      <div className="card p-8 text-center">
        <Globe className="w-10 h-10 text-text-muted mx-auto mb-3" />
        <h2 className="text-lg font-semibold text-text-primary mb-1">Asset Intelligence</h2>
        <p className="text-sm text-text-muted">Full asset inventory — domains, IPs, hosts, and certificates — will be available here as crawlers expand.</p>
      </div>
    </div>
  );
}
