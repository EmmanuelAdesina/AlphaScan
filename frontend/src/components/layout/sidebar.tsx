'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield,
  Search,
  KeyRound,
  GitBranch,
  Building2,
  Globe,
  ScanLine,
  BarChart3,
  Download,
  Code2,
  Settings,
  ChevronLeft,
  ChevronRight,
  Activity,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  id: string;
  label: string;
  icon: React.ElementType;
  badge?: number;
  section?: string;
}

const navItems: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: Activity, section: 'Overview' },
  { id: 'search', label: 'Search', icon: Search, section: 'Overview' },
  { id: 'secrets', label: 'Secrets', icon: KeyRound, badge: 0, section: 'Intelligence' },
  { id: 'repositories', label: 'Repositories', icon: GitBranch, section: 'Intelligence' },
  { id: 'organizations', label: 'Organizations', icon: Building2, section: 'Intelligence' },
  { id: 'assets', label: 'Assets', icon: Globe, section: 'Intelligence' },
  { id: 'scans', label: 'Scans', icon: ScanLine, section: 'Operations' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, section: 'Operations' },
  { id: 'downloads', label: 'Downloads', icon: Download, section: 'Operations' },
  { id: 'api', label: 'API', icon: Code2, section: 'System' },
  { id: 'settings', label: 'Settings', icon: Settings, section: 'System' },
];

interface SidebarProps {
  activeSection: string;
  onNavigate: (section: string) => void;
}

export function Sidebar({ activeSection, onNavigate }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  const groupedItems = navItems.reduce<Record<string, NavItem[]>>((acc, item) => {
    const section = item.section || 'Other';
    if (!acc[section]) acc[section] = [];
    acc[section].push(item);
    return acc;
  }, {});

  return (
    <motion.aside
      className={cn(
        'h-full flex flex-col bg-bg border-r border-border relative',
        collapsed ? 'w-[52px]' : 'w-[220px]',
      )}
      animate={{ width: collapsed ? 52 : 220 }}
      transition={{ duration: 0.2, ease: 'easeInOut' }}
    >
      {/* Logo */}
      <div className={cn(
        'flex items-center gap-3 px-3 h-14 border-b border-border',
        collapsed && 'justify-center',
      )}>
        <div className="flex items-center justify-center w-7 h-7 rounded-md bg-primary text-text-inverted">
          <Shield className="w-4 h-4" />
        </div>
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-baseline gap-1"
          >
            <span className="font-semibold text-sm text-text-primary">AlphaScan</span>
            <span className="text-2xs text-text-muted font-medium">v2.0</span>
          </motion.div>
        )}
      </div>

      {/* Nav Items */}
      <nav className="flex-1 overflow-y-auto no-scrollbar py-3 px-2 space-y-4">
        {Object.entries(groupedItems).map(([section, items]) => (
          <div key={section}>
            {!collapsed && (
              <div className="section-header px-2 mb-2">{section}</div>
            )}
            <div className="space-y-0.5">
              {items.map((item) => {
                const isActive = activeSection === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.id)}
                    className={cn(
                      'flex items-center gap-2.5 w-full rounded-md text-sm transition-all duration-150',
                      collapsed ? 'justify-center px-1 py-2' : 'px-2 py-1.5',
                      isActive
                        ? 'bg-primary/10 text-primary font-medium'
                        : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover',
                    )}
                    title={collapsed ? item.label : undefined}
                  >
                    <item.icon className={cn('w-4 h-4 shrink-0', isActive && 'text-primary')} />
                    {!collapsed && (
                      <motion.span
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="truncate"
                      >
                        {item.label}
                      </motion.span>
                    )}
                    {!collapsed && item.badge !== undefined && item.badge > 0 && (
                      <span className="ml-auto text-2xs font-medium bg-danger/20 text-danger rounded px-1.5 py-0.5">
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Collapse toggle */}
      <div className="border-t border-border p-2">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            'flex items-center gap-2 w-full rounded-md text-sm text-text-muted hover:text-text-secondary transition-colors',
            collapsed ? 'justify-center py-2' : 'px-2 py-1.5',
          )}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </motion.aside>
  );
}
