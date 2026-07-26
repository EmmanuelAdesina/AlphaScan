'use client';

import { useState, useEffect } from 'react';
import { Command } from 'cmdk';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  KeyRound,
  GitBranch,
  Building2,
  BarChart3,
  Download,
  ScanLine,
  Settings,
  Shield,
  Globe,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onNavigate: (section: string) => void;
  onSearch: (query: string) => void;
}

const commands = [
  { id: 'dashboard', label: 'Go to Dashboard', icon: Shield, group: 'Navigation' },
  { id: 'secrets', label: 'Go to Secrets', icon: KeyRound, group: 'Navigation' },
  { id: 'repositories', label: 'Go to Repositories', icon: GitBranch, group: 'Navigation' },
  { id: 'organizations', label: 'Go to Organizations', icon: Building2, group: 'Navigation' },
  { id: 'analytics', label: 'Go to Analytics', icon: BarChart3, group: 'Navigation' },
  { id: 'downloads', label: 'Go to Downloads', icon: Download, group: 'Navigation' },
  { id: 'scans', label: 'Start New Scan', icon: ScanLine, group: 'Actions' },
  { id: 'assets', label: 'Go to Assets', icon: Globe, group: 'Navigation' },
  { id: 'settings', label: 'Go to Settings', icon: Settings, group: 'Navigation' },
  { id: 'export-json', label: 'Export Findings as JSON', icon: Download, group: 'Actions' },
  { id: 'export-csv', label: 'Export Findings as CSV', icon: Download, group: 'Actions' },
];

export function CommandPalette({ open, onClose, onNavigate, onSearch }: CommandPaletteProps) {
  const [query, setQuery] = useState('');

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        if (open) {
          onClose();
        } else {
          // Trigger parent to open
        }
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [open, onClose]);

  // Handle escape
  useEffect(() => {
    if (!open) setQuery('');
  }, [open]);

  const handleSelect = (id: string) => {
    if (id.startsWith('search:')) {
      onSearch(id.replace('search:', ''));
    } else if (id === 'export-json' || id === 'export-csv') {
      // Trigger download
      onNavigate('downloads');
    } else {
      onNavigate(id);
    }
    onClose();
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Palette */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
            transition={{ duration: 0.15 }}
            className="fixed top-[20%] left-1/2 -translate-x-1/2 z-50 w-[560px] max-w-[90vw]"
          >
            <Command
              className="bg-bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
              loop
            >
              {/* Search input */}
              <div className="flex items-center gap-2 px-4 border-b border-border">
                <Search className="w-4 h-4 text-text-muted shrink-0" />
                <Command.Input
                  value={query}
                  onValueChange={setQuery}
                  placeholder="Search secrets, providers, commands..."
                  className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted py-3 outline-none"
                />
                <kbd className="text-2xs font-mono text-text-muted bg-bg px-1.5 py-0.5 rounded border border-border">
                  ESC
                </kbd>
              </div>

              {/* Results */}
              <Command.List className="max-h-[320px] overflow-y-auto p-2">
                <Command.Empty className="py-6 text-center text-sm text-text-muted">
                  No results found.
                </Command.Empty>

                {/* Search suggestion if query present */}
                {query && (
                  <Command.Group heading="Search">
                    <Command.Item
                      value={`search:${query}`}
                      onSelect={handleSelect}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-bg-hover data-[selected]:bg-primary/10 data-[selected]:text-primary cursor-pointer"
                    >
                      <Search className="w-4 h-4" />
                      <span>Search for <strong className="text-text-primary">{query}</strong></span>
                    </Command.Item>
                  </Command.Group>
                )}

                {/* Commands */}
                <Command.Group heading="Commands">
                  {commands.map((cmd) => (
                    <Command.Item
                      key={cmd.id}
                      value={cmd.id + ' ' + cmd.label}
                      onSelect={handleSelect}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-bg-hover data-[selected]:bg-primary/10 data-[selected]:text-primary cursor-pointer"
                    >
                      <cmd.icon className="w-4 h-4 shrink-0 text-text-muted" />
                      <span>{cmd.label}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              </Command.List>

              {/* Footer */}
              <div className="flex items-center justify-between px-4 py-2 border-t border-border text-2xs text-text-muted">
                <span>Navigate or search</span>
                <div className="flex items-center gap-2">
                  <kbd className="bg-bg px-1.5 py-0.5 rounded border border-border">↑↓</kbd>
                  <span>navigate</span>
                  <kbd className="bg-bg px-1.5 py-0.5 rounded border border-border">↵</kbd>
                  <span>select</span>
                  <kbd className="bg-bg px-1.5 py-0.5 rounded border border-border">esc</kbd>
                  <span>close</span>
                </div>
              </div>
            </Command>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
