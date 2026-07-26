'use client';

import { Building2, Globe, ShieldAlert } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export default function OrganizationsPage() {
  const findingsQuery = useQuery({
    queryKey: ['all-findings-orgs'],
    queryFn: () => api.getFindings({ limit: 200 }),
  });

  const orgMap = new Map<string, number>();
  for (const f of findingsQuery.data?.findings || []) {
    const org = f.repository?.split('/')[0] || 'unknown';
    orgMap.set(org, (orgMap.get(org) || 0) + 1);
  }

  const orgs = Array.from(orgMap.entries()).sort(([, a], [, b]) => b - a);

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Organizations</h1>
        <p className="text-sm text-text-muted mt-0.5">{orgs.length} organizations</p>
      </div>

      {orgs.length === 0 ? (
        <div className="py-12 text-center">
          <Building2 className="w-8 h-8 text-text-muted mx-auto mb-3" />
          <p className="text-sm text-text-muted">No organizations found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {orgs.map(([org, count], i) => (
            <motion.div
              key={org}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className="card-hover p-4 cursor-pointer"
            >
              <div className="flex items-center gap-2 mb-2">
                <Building2 className="w-4 h-4 text-text-muted" />
                <span className="text-sm font-medium text-text-primary">{org}</span>
              </div>
              <span className="text-2xs text-text-muted flex items-center gap-1">
                <ShieldAlert className="w-3 h-3" /> {count} findings
              </span>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
