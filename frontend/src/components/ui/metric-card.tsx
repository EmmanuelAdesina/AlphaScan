'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { AnimatedCounter } from './animated-counter';
import type { LucideIcon } from 'lucide-react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: number;
  icon: LucideIcon;
  trend?: { value: number; label: string };
  color?: 'default' | 'primary' | 'success' | 'danger' | 'warning' | 'info' | 'critical';
  format?: boolean;
  subtitle?: string;
  className?: string;
}

const colorMap = {
  default: {
    icon: 'text-text-muted',
    bg: 'bg-bg-hover',
    glow: '',
  },
  primary: {
    icon: 'text-primary',
    bg: 'bg-primary/10',
    glow: 'shadow-glow-primary',
  },
  success: {
    icon: 'text-success',
    bg: 'bg-success/10',
    glow: 'shadow-glow-success',
  },
  danger: {
    icon: 'text-danger',
    bg: 'bg-danger/10',
    glow: 'shadow-glow-danger',
  },
  warning: {
    icon: 'text-warning',
    bg: 'bg-warning/10',
    glow: '',
  },
  info: {
    icon: 'text-info',
    bg: 'bg-info/10',
    glow: '',
  },
  critical: {
    icon: 'text-danger',
    bg: 'bg-danger/10',
    glow: 'shadow-glow-critical',
  },
};

export function MetricCard({
  label,
  value,
  icon: Icon,
  trend,
  color = 'default',
  format = true,
  subtitle,
  className,
}: MetricCardProps) {
  const colors = colorMap[color];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.05 }}
      className={cn(
        'card p-4 flex flex-col gap-3',
        colors.glow,
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="section-header">{label}</span>
        <div className={cn('flex items-center justify-center w-8 h-8 rounded-lg', colors.bg)}>
          <Icon className={cn('w-4 h-4', colors.icon)} />
        </div>
      </div>

      {/* Value */}
      <div className="flex items-baseline gap-2">
        <AnimatedCounter
          value={value}
          className="text-2xl font-bold text-text-primary"
          format={format}
        />
        {trend && (
          <div className="flex items-center gap-0.5 text-2xs font-medium">
            {trend.value > 0 ? (
              <TrendingUp className="w-3 h-3 text-success" />
            ) : trend.value < 0 ? (
              <TrendingDown className="w-3 h-3 text-danger" />
            ) : (
              <Minus className="w-3 h-3 text-text-muted" />
            )}
            <span className={cn(
              trend.value > 0 ? 'text-success' : trend.value < 0 ? 'text-danger' : 'text-text-muted',
            )}>
              {trend.value > 0 ? '+' : ''}{trend.value}%
            </span>
          </div>
        )}
      </div>

      {/* Subtitle */}
      {subtitle && (
        <span className="text-2xs text-text-muted">{subtitle}</span>
      )}
    </motion.div>
  );
}
