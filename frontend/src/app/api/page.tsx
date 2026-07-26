'use client';

import { Code2, ExternalLink, Copy } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

const endpoints = [
  { method: 'GET', path: '/', description: 'Service status', auth: false },
  { method: 'GET', path: '/health', description: 'Health check', auth: false },
  { method: 'GET', path: '/findings', description: 'Paginated findings with filtering', auth: false },
  { method: 'GET', path: '/findings/{id}', description: 'Single finding detail', auth: false },
  { method: 'GET', path: '/export/json', description: 'Stream all findings as JSON', auth: false },
  { method: 'GET', path: '/export/csv', description: 'Stream all findings as CSV', auth: false },
  { method: 'GET', path: '/metrics', description: 'Scan metrics', auth: false },
  { method: 'GET', path: '/exports', description: 'Export history index', auth: false },
];

const filterParams = [
  { name: 'source', type: 'string', description: 'Filter by scanner source' },
  { name: 'repository', type: 'string', description: 'Filter by repository (partial match)' },
  { name: 'secret_type', type: 'string', description: 'Filter by secret type' },
  { name: 'confidence_min', type: 'float', description: 'Minimum confidence score' },
  { name: 'confidence_max', type: 'float', description: 'Maximum confidence score' },
  { name: 'validation_level', type: 'string', description: 'none, format, structure, heuristic, provider, active' },
  { name: 'verified', type: 'string|bool', description: 'Verification status filter' },
  { name: 'date', type: 'string', description: 'YYYY-MM-DD' },
  { name: 'date_from', type: 'string', description: 'Start date' },
  { name: 'date_to', type: 'string', description: 'End date' },
  { name: 'provider', type: 'string', description: 'Filter by provider name' },
];

export default function ApiPage() {
  const [copied, setCopied] = useState('');

  return (
    <div className="space-y-6 max-w-[1000px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">API Reference</h1>
          <p className="text-sm text-text-muted mt-0.5">Findings Export API v1.0.0</p>
        </div>
        <span className="text-2xs text-text-muted bg-bg-hover border border-border px-2 py-1 rounded">
          Base URL: /api
        </span>
      </div>

      {/* Security note */}
      <div className="card p-4 border-warning/30">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-warning text-xs font-semibold">⚠️ Security</span>
        </div>
        <p className="text-sm text-text-secondary">
          By default, only <strong>masked values</strong> are exported. Full (unmasked) values require
          explicit authorization via <code className="mono bg-bg px-1 rounded">X-Allow-Full-Values</code> header
          or <code className="mono bg-bg px-1 rounded">EXPORT_AUTH_TOKENS</code> configuration.
          Never expose raw secret values without authorization.
        </p>
      </div>

      {/* Endpoints */}
      <div className="card p-4">
        <h2 className="text-sm font-semibold text-text-primary mb-4">Endpoints</h2>
        <div className="space-y-2">
          {endpoints.map((ep) => (
            <div key={ep.path} className="flex items-center gap-3 py-2 hover:bg-bg-hover rounded-lg transition-colors">
              <span className={cn(
                'px-2 py-0.5 rounded text-2xs font-medium tracking-wide',
                ep.method === 'GET' ? 'bg-success/20 text-success' : 'bg-primary/20 text-primary',
              )}>{ep.method}</span>
              <code className="mono text-sm text-text-primary">{ep.path}</code>
              <span className="text-sm text-text-muted">{ep.description}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Filter parameters */}
      <div className="card p-4">
        <h2 className="text-sm font-semibold text-text-primary mb-4">Query Parameters</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 text-text-muted section-header">Parameter</th>
                <th className="text-left py-2 text-text-muted section-header">Type</th>
                <th className="text-left py-2 text-text-muted section-header">Description</th>
              </tr>
            </thead>
            <tbody>
              {filterParams.map((p) => (
                <tr key={p.name} className="border-b border-border/50 hover:bg-bg-hover transition-colors">
                  <td className="py-2 mono text-text-primary">{p.name}</td>
                  <td className="py-2 text-text-muted">{p.type}</td>
                  <td className="py-2 text-text-secondary">{p.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
