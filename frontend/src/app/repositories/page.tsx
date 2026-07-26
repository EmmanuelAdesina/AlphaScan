'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { GitBranch, Star, ShieldAlert, ExternalLink } from 'lucide-react';
import { motion } from 'framer-motion';

export default function RepositoriesPage() {
  const findingsQuery = useQuery({
    queryKey: ['all-findings-repos'],
    queryFn: () => api.getFindings({ limit: 200 }),
  });

  // Group findings by repository
  const repoMap = new Map<string, { count: number; verified: number; highConf: number; latest: string }>();
  for (const f of findingsQuery.data?.findings || []) {
    if (!f.repository) continue;
    const existing = repoMap.get(f.repository) || { count: 0, verified: 0, highConf: 0, latest: f.discovered_at };
    existing.count++;
    if (f.verified === 'active') existing.verified++;
    if (f.confidence >= 70) existing.highConf++;
    if (f.discovered_at > existing.latest) existing.latest = f.discovered_at;
    repoMap.set(f.repository, existing);
  }

  const repos = Array.from(repoMap.entries())
    .sort(([, a], [, b]) => b.count - a.count);

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Repositories</h1>
        <p className="text-sm text-text-muted mt-0.5">{repos.length} repositories with findings</p>
      </div>

      {repos.length === 0 ? (
        <div className="py-12 text-center">
          <GitBranch className="w-8 h-8 text-text-muted mx-auto mb-3" />
          <p className="text-sm text-text-muted">No repositories found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {repos.map(([repo, stats], i) => (
            <motion.div
              key={repo}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className="card-hover p-4 cursor-pointer"
            >
              <div className="flex items-center gap-2 mb-2">
                <GitBranch className="w-4 h-4 text-text-muted" />
                <span className="text-sm font-medium text-text-primary truncate">{repo}</span>
              </div>
              <div className="flex items-center gap-3 text-2xs text-text-muted">
                <span className="flex items-center gap-1"><ShieldAlert className="w-3 h-3" /> {stats.count} secrets</span>
                <span className="flex items-center gap-1 text-success">✅ {stats.verified} verified</span>
                <span className="flex items-center gap-1 text-warning">⚠️ {stats.highConf} high</span>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
