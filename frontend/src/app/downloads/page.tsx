'use client';

import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import { cn, formatDate } from '@/lib/utils';
import {
  Download, FileJson, FileText, FileArchive, Calendar, Clock,
  HardDrive, ArrowDownToLine,
} from 'lucide-react';
import type { ExportIndex } from '@/types';

export default function DownloadsPage() {
  const exportsQuery = useQuery({
    queryKey: ['exports'],
    queryFn: () => api.getExportHistory(),
  });

  const exports = exportsQuery.data?.exports || [];

  return (
    <div className="space-y-6 max-w-[1000px]">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Downloads</h1>
        <p className="text-sm text-text-muted mt-0.5">Export findings and reports</p>
      </div>

      {/* Quick export buttons */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="card-hover p-6 flex items-center gap-4 cursor-pointer group"
        >
          <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 shrink-0">
            <FileJson className="w-6 h-6 text-primary" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-text-primary">Export JSON</h3>
            <p className="text-2xs text-text-muted mt-0.5">All findings as JSON with masked values</p>
          </div>
          <a
            href={api.getExportJsonUrl()}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm bg-primary text-text-inverted font-medium hover:bg-primary-hover transition-colors"
          >
            <ArrowDownToLine className="w-4 h-4" />
            Download
          </a>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="card-hover p-6 flex items-center gap-4 cursor-pointer group"
        >
          <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-success/10 shrink-0">
            <FileText className="w-6 h-6 text-success" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-text-primary">Export CSV</h3>
            <p className="text-2xs text-text-muted mt-0.5">All findings as CSV with masked values</p>
          </div>
          <a
            href={api.getExportCsvUrl()}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm bg-success text-text-inverted font-medium hover:bg-success-hover transition-colors"
          >
            <ArrowDownToLine className="w-4 h-4" />
            Download
          </a>
        </motion.div>
      </div>

      {/* Previous exports */}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-text-primary">Previous Exports</h2>
          <span className="text-2xs text-text-muted">{exports.length} exports</span>
        </div>

        {exports.length === 0 ? (
          <div className="py-8 text-center text-sm text-text-muted">
            <Calendar className="w-6 h-6 mx-auto mb-2 text-text-muted" />
            No previous exports. Daily exports are created after each scan cycle.
          </div>
        ) : (
          <div className="space-y-2">
            {exports.map((exportItem, i) => (
              <motion.div
                key={exportItem.id}
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.02 }}
                className="flex items-center gap-3 p-3 rounded-lg hover:bg-bg-hover transition-colors"
              >
                <div className="flex items-center justify-center w-8 h-8 rounded-md bg-bg-hover shrink-0">
                  <HardDrive className="w-4 h-4 text-text-muted" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-text-primary">{exportItem.export_date}</span>
                    <span className="text-2xs text-text-muted tabular-nums">{exportItem.findings_count} findings</span>
                  </div>
                  <span className="text-2xs text-text-muted">{exportItem.export_dir}</span>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <Clock className="w-3 h-3 text-text-muted" />
                  <span className="text-2xs text-text-muted">{formatDate(exportItem.created_at)}</span>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
