'use client';

import { ScanLine, Terminal, Activity, Zap } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

export default function ScansPage() {
  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Scans</h1>
        <p className="text-sm text-text-muted mt-0.5">Live scan monitor</p>
      </div>

      {/* Terminal-inspired scan monitor */}
      <div className="terminal p-4 space-y-2">
        <div className="flex items-center gap-2 text-xs text-text-muted mb-3">
          <Zap className="w-3.5 h-3.5 text-success" />
          <span className="text-success font-medium">Scan Active</span>
          <span className="text-text-muted">· Censys + GitHub + Pastebin</span>
        </div>

        {/* Log lines */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-1"
        >
          {[
            { time: '07:16:04', level: 'INFO', msg: 'Starting scan cycle #42...' },
            { time: '07:16:05', level: 'INFO', msg: 'Censys query: services.http.response.body:"AKIA"' },
            { time: '07:16:12', level: 'INFO', msg: 'Censys: 23 findings collected' },
            { time: '07:16:13', level: 'INFO', msg: 'GitHub search: filename:.env "api_key"' },
            { time: '07:16:18', level: 'INFO', msg: 'GitHub: 7 findings collected' },
            { time: '07:16:19', level: 'INFO', msg: 'Pastebin archive scan starting...' },
            { time: '07:16:22', level: 'INFO', msg: 'Pastebin: 3 findings collected' },
            { time: '07:16:23', level: 'INFO', msg: 'Parser: 18 unique secrets extracted' },
            { time: '07:16:25', level: 'INFO', msg: 'Validator: 12 valid, 6 invalid' },
            { time: '07:16:26', level: 'OK', msg: 'Scan cycle complete. 33 findings processed.' },
          ].map((log, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-start gap-2"
            >
              <span className="text-text-muted shrink-0">{log.time}</span>
              <span className={cn(
                'shrink-0 font-medium',
                log.level === 'OK' ? 'text-success' : log.level === 'WARN' ? 'text-warning' : log.level === 'ERR' ? 'text-danger' : 'text-primary',
              )}>[{log.level}]</span>
              <span className="text-text-secondary">{log.msg}</span>
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* Scan stats */}
      <div className="card p-6 text-center">
        <ScanLine className="w-8 h-8 text-text-muted mx-auto mb-3" />
        <h2 className="text-lg font-semibold text-text-primary mb-1">Scan Control</h2>
        <p className="text-sm text-text-muted">Schedule new scans, configure crawler targets, and monitor verification queues from this panel.</p>
      </div>
    </div>
  );
}
