'use client';

import { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { SecretCard } from '@/components/secrets/secret-card';
import { VerificationBadge, ConfidenceBadge } from '@/components/ui/badges';
import { ProviderLogo } from '@/components/ui/provider-logo';
import { Search, X, Loader2, Filter, Command } from 'lucide-react';
import type { FindingsFilters } from '@/types';

const SEARCH_SUGGESTIONS = [
  'stripe', 'openai', 'aws', 'discord', 'github', 'coinbase',
  'jwt', 'rsa', 'ethereum', 'mongodb', 'sk_live_', 'ghp_',
];

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [filters, setFilters] = useState<FindingsFilters>({});

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  // Build filters from query
  const searchFilters: FindingsFilters = {
    ...filters,
    ...(debouncedQuery ? { provider: debouncedQuery } : {}),
  };

  // Also try secret_type and repository search
  const providerQuery = useQuery({
    queryKey: ['search-provider', debouncedQuery],
    queryFn: () => api.getFindings({ provider: debouncedQuery, limit: 50 }),
    enabled: !!debouncedQuery,
  });

  const typeQuery = useQuery({
    queryKey: ['search-type', debouncedQuery],
    queryFn: () => api.getFindings({ secret_type: debouncedQuery, limit: 50 }),
    enabled: !!debouncedQuery,
  });

  const repoQuery = useQuery({
    queryKey: ['search-repo', debouncedQuery],
    queryFn: () => api.getFindings({ repository: debouncedQuery, limit: 50 }),
    enabled: !!debouncedQuery,
  });

  // Merge results, deduplicate by id
  const allResults = new Map<string, any>();
  const isLoading = providerQuery.isLoading || typeQuery.isLoading || repoQuery.isLoading;

  for (const finding of [...(providerQuery.data?.findings || []), ...(typeQuery.data?.findings || []), ...(repoQuery.data?.findings || [])]) {
    allResults.set(finding.id, finding);
  }

  const results = Array.from(allResults.values());
  const hasResults = results.length > 0;

  return (
    <div className="space-y-6 max-w-[1400px]">
      {/* Search header */}
      <div className="text-center pt-8 pb-4">
        <h1 className="text-2xl font-bold text-text-primary mb-2">
          Search Secrets
        </h1>
        <p className="text-sm text-text-muted">
          Search by provider, secret type, repository, IP, or domain
        </p>
      </div>

      {/* Search bar */}
      <div className="max-w-2xl mx-auto">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="stripe, openai, aws, discord, github, 8.8.8.8, *.env..."
            className="w-full bg-bg-card border border-border rounded-xl pl-12 pr-12 py-3.5 text-base text-text-primary placeholder:text-text-muted outline-none focus:border-primary focus:shadow-glow-primary transition-all"
            autoFocus
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Suggestions */}
      {!debouncedQuery && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="max-w-2xl mx-auto"
        >
          <div className="section-header mb-2 text-center">Popular searches</div>
          <div className="flex items-center justify-center gap-2 flex-wrap">
            {SEARCH_SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => setQuery(suggestion)}
                className="px-3 py-1.5 rounded-lg text-sm bg-bg-hover border border-border text-text-secondary hover:text-text-primary hover:border-border-hover transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </motion.div>
      )}

      {/* Results */}
      {debouncedQuery && (
        <div className="space-y-4">
          {/* Results header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isLoading && <Loader2 className="w-4 h-4 text-primary animate-spin" />}
              <span className="text-sm text-text-secondary">
                {hasResults
                  ? `${results.length} results for "${debouncedQuery}"`
                  : isLoading ? 'Searching...' : 'No results found'
                }
              </span>
            </div>
          </div>

          {/* Results grid */}
          {hasResults && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {results.map((finding, i) => (
                <SecretCard key={finding.id} secret={finding} index={i} compact />
              ))}
            </div>
          )}

          {/* No results */}
          {!isLoading && !hasResults && debouncedQuery && (
            <div className="py-12 text-center">
              <Search className="w-8 h-8 text-text-muted mx-auto mb-3" />
              <p className="text-sm text-text-muted">No secrets found for "{debouncedQuery}"</p>
              <p className="text-2xs text-text-muted mt-1">Try searching for a provider name, secret type, or repository</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
