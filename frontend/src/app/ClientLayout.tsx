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
      staleTime: 30 * 1000,
      refetchInterval: 60 * 1000,
      retry: 2,
    },
  },
});

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const [activeSection, setActiveSection] = useState('dashboard');
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [isDark, setIsDark] = useState(true);

  const handleNavigate = (section: string) => {
    setActiveSection(section);
  };

  const handleSearch = (query: string) => {
    setActiveSection('search');
  };

  const handleToggleTheme = () => {
    setIsDark(!isDark);
  };



  return (
    <>
      <QueryClientProvider client={queryClient}>
        <div className="flex h-screen overflow-hidden">
          <Sidebar activeSection={activeSection} onNavigate={handleNavigate} />
          <div className="flex-1 flex flex-col overflow-hidden">
            <TopNav
              onOpenCommandPalette={() => setCommandPaletteOpen(true)}
              onToggleTheme={handleToggleTheme}
              isDark={isDark}
            />
            <main className="flex-1 overflow-y-auto p-6">
              {children}
            </main>
          </div>
        </div>
        <CommandPalette
          open={commandPaletteOpen}
          onClose={() => setCommandPaletteOpen(false)}
          onNavigate={handleNavigate}
          onSearch={handleSearch}
        />
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
    </>
  );
}
