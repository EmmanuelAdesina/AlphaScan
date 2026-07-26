'use client';

import { cn } from '@/lib/utils';
import {
  Github, Cloud, Sparkles, Brain, CreditCard, Search,
  GitBranch, MessageCircle, Hash, Shield, Mail, Phone,
  Database, Coins, Terminal, KeyRound, Server,
} from 'lucide-react';
import { PROVIDER_DISPLAY } from '@/types';

const iconMap: Record<string, React.ElementType> = {
  github: Github,
  cloud: Cloud,
  sparkles: Sparkles,
  brain: Brain,
  credit_card: CreditCard,
  search: Search,
  git_branch: GitBranch,
  message_circle: MessageCircle,
  hash: Hash,
  shield: Shield,
  mail: Mail,
  phone: Phone,
  database: Database,
  coins: Coins,
  terminal: Terminal,
  key: KeyRound,
  server: Server,
};

interface ProviderLogoProps {
  provider: string;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export function ProviderLogo({ provider, size = 'md', showLabel = false, className }: ProviderLogoProps) {
  const display = PROVIDER_DISPLAY[provider] || { name: provider, color: '#71717A', icon: 'key' };
  const Icon = iconMap[display.icon] || KeyRound;

  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  const containerSizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-10 h-10',
  };

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div
        className={cn(
          'flex items-center justify-center rounded-md shrink-0',
          containerSizeClasses[size],
        )}
        style={{ backgroundColor: `${display.color}20` }}
      >
        <Icon
          className={cn(sizeClasses[size])}
          style={{ color: display.color }}
        />
      </div>
      {showLabel && (
        <span className="text-sm font-medium text-text-primary">{display.name}</span>
      )}
    </div>
  );
}
