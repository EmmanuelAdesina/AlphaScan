'use client';

import { Search, Bell, Command, Sun, Moon, User, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TopNavProps {
  onOpenCommandPalette: () => void;
  onToggleTheme: () => void;
  isDark: boolean;
}

export function TopNav({ onOpenCommandPalette, onToggleTheme, isDark }: TopNavProps) {
  return (
    <header className="h-14 flex items-center justify-between px-4 border-b border-border bg-bg">
      {/* Left: Search trigger */}
      <div className="flex items-center gap-3 flex-1 max-w-xl">
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-2 w-full bg-bg-hover border border-border rounded-lg px-3 py-1.5 text-sm text-text-muted hover:border-border-hover hover:text-text-secondary transition-colors group"
        >
          <Search className="w-4 h-4 shrink-0" />
          <span className="flex-1 text-left">Search secrets, repos, providers...</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 text-2xs font-mono bg-bg px-1.5 py-0.5 rounded border border-border text-text-muted">
            <Command className="w-2.5 h-2.5" />K
          </kbd>
        </button>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {/* Live status indicator */}
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-success/10 text-success text-xs font-medium">
          <Zap className="w-3 h-3" />
          <span>Live</span>
        </div>

        {/* Notifications */}
        <button className="relative p-2 rounded-lg text-text-muted hover:text-text-secondary hover:bg-bg-hover transition-colors">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-danger rounded-full" />
        </button>

        {/* Theme toggle */}
        <button
          onClick={onToggleTheme}
          className="p-2 rounded-lg text-text-muted hover:text-text-secondary hover:bg-bg-hover transition-colors"
        >
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* User */}
        <button className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-bg-hover transition-colors">
          <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center">
            <User className="w-3.5 h-3.5 text-primary" />
          </div>
        </button>
      </div>
    </header>
  );
}
