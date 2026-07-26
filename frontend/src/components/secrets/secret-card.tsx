'use client';

import { motion } from 'framer-motion';
import { cn, formatRelativeTime, truncate } from '@/lib/utils';
import { VerificationBadge, ConfidenceBadge, SourceBadge, SecretTypeBadge } from '@/components/ui/badges';
import { ProviderLogo } from '@/components/ui/provider-logo';
import { FileCode, Clock, ChevronRight } from 'lucide-react';
import type { SecretExportDict } from '@/types';

interface SecretCardProps {
  secret: SecretExportDict;
  onClick?: (id: string) => void;
  compact?: boolean;
  className?: string;
  index?: number;
}

export function SecretCard({ secret, onClick, compact = false, className, index = 0 }: SecretCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.03 }}
      className={cn(
        'card-hover group cursor-pointer',
        compact ? 'p-3' : 'p-4',
        secret.verified === 'active' && 'shadow-glow-success',
        secret.verified === 'invalid' && 'shadow-glow-danger',
        className,
      )}
      onClick={() => onClick?.(secret.id)}
    >
      <div className={cn('flex items-start gap-3', compact ? '' : 'gap-4')}>
        {/* Provider icon */}
        <ProviderLogo provider={secret.secret_type.split(' ')[0].toLowerCase()} size={compact ? 'sm' : 'md'} />

        {/* Main content */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* Top row: type + badges */}
          <div className="flex items-center gap-2 flex-wrap">
            <SecretTypeBadge type={secret.secret_type} />
            <ConfidenceBadge score={secret.confidence} category={secret.confidence_category} size={compact ? 'sm' : 'md'} />
            <VerificationBadge status={secret.verified} size={compact ? 'sm' : 'md'} />
            <SourceBadge source={secret.source} />
          </div>

          {/* File / target info */}
          {!compact && (
            <div className="flex items-center gap-3 text-sm text-text-secondary">
              {secret.repository && (
                <span className="flex items-center gap-1 truncate">
                  <GitBranch className="w-3 h-3 text-text-muted shrink-0" />
                  {truncate(secret.repository, 40)}
                </span>
              )}
              {secret.file && (
                <span className="flex items-center gap-1 truncate">
                  <FileCode className="w-3 h-3 text-text-muted shrink-0" />
                  {truncate(secret.file, 30)}
                </span>
              )}
              <span className="flex items-center gap-1 text-text-muted shrink-0">
                <Clock className="w-3 h-3" />
                {formatRelativeTime(secret.discovered_at)}
              </span>
            </div>
          )}

          {/* Masked value */}
          <div className="mono text-text-muted text-xs bg-black/30 px-2 py-1 rounded">
            {secret.masked_value}
          </div>
        </div>

        {/* Chevron */}
        <ChevronRight className="w-4 h-4 text-text-muted group-hover:text-text-secondary transition-colors shrink-0 mt-1" />
      </div>
    </motion.div>
  );
}

function GitBranch(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <line x1="6" x2="6" y1="3" y2="15" /><circle cx="18" cy="18" r="3" /><circle cx="6" cy="18" r="3" /><path d="M6 15a6 6 0 0 0 6 6h3" />
    </svg>
  );
}
