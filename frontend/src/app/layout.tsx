'use client';

import { useState } from 'react';
import { Sidebar } from '@/components/layout/sidebar';
import { TopNav } from '@/components/layout/top-nav';
import { CommandPalette } from '@/components/layout/command-palette';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30s
      refetchInterval: 60 * 1000, // 1 min for live data
      retry: 2,
    },
  },
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [activeSection, setActiveSection] = useState('dashboard');
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [isDark, setIsDark] = useState(true);

  const handleNavigate = (section: string) => {
    setActiveSection(section);
  };

  const handleSearch = (query: string) => {
    setActiveSection('search');
    // Search component will receive the query via URL state
  };

  const handleToggleTheme = () => {
    setIsDark(!isDark);
    document.documentElement.classList.toggle('light');
  };

  // Keyboard shortcut for command palette
  useState(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setCommandPaletteOpen(prev => !prev);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  });

  return (
    <html lang="en" className={isDark ? '' : 'light'}>
      <head>
        <title>AlphaScan — Secret Intelligence Platform</title>
        <meta name="description" content="Enterprise secret intelligence engine" />
        <link rel="icon" href="/favicon.ico" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
      </head>
      <body className="min-h-screen">
        <QueryClientProvider client={queryClient}>
          <div className="flex h-screen overflow-hidden">
            {/* Sidebar */}
            <Sidebar activeSection={activeSection} onNavigate={handleNavigate} />

            {/* Main area */}
            <div className="flex-1 flex flex-col overflow-hidden">
              <TopNav
                onOpenCommandPalette={() => setCommandPaletteOpen(true)}
                onToggleTheme={handleToggleTheme}
                isDark={isDark}
              />

              {/* Content */}
              <main className="flex-1 overflow-y-auto p-6">
                {children}
              </main>
            </div>
          </div>

          {/* Command Palette */}
          <CommandPalette
            open={commandPaletteOpen}
            onClose={() => setCommandPaletteOpen(false)}
            onNavigate={handleNavigate}
            onSearch={handleSearch}
          />

          {/* Toast notifications */}
          <Toaster
            theme={isDark ? 'dark' : 'light'}
            position="bottom-right"
            toastOptions={{
              style: {
                background: isDark ? '#111113' : '#f9f9fa',
                border: `1px solid ${isDark ? '#232326' : '#e4e4e7'}`,
                color: isDark ? '#fafafa' : '#09090b',
              },
            }}
          />
        </QueryClientProvider>
      </body>
    </html>
  );
}
