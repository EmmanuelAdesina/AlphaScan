/**
 * AlphaScan API Client.
 * Connects to the FastAPI backend for all data operations.
 * Uses React Query for caching, refetching, and state management.
 */

import type {
  Secret,
  SecretExportDict,
  FindingDetail,
  FindingsListResponse,
  FindingsFilters,
  ScanMetrics,
  ExportIndex,
  HealthResponse,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, error.detail || res.statusText);
    }

    // For streaming responses, return the raw Response
    if (res.headers.get('content-type')?.includes('text/csv') ||
        res.headers.get('content-type')?.includes('application/json') &&
        res.headers.get('content-disposition')?.includes('attachment')) {
      return res as unknown as T;
    }

    return res.json();
  }

  // ── Health ────────────────────────────────────────────────────

  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  // ── Findings ──────────────────────────────────────────────────

  async getFindings(filters: FindingsFilters & { offset?: number; limit?: number } = {}): Promise<FindingsListResponse> {
    const params = new URLSearchParams();

    const { offset = 0, limit = 50, ...filterParams } = filters;

    params.set('offset', String(offset));
    params.set('limit', String(limit));

    for (const [key, value] of Object.entries(filterParams)) {
      if (value !== undefined && value !== null && value !== '') {
        params.set(key, String(value));
      }
    }

    return this.request<FindingsListResponse>(`/findings?${params.toString()}`);
  }

  async getFinding(id: string): Promise<FindingDetail> {
    return this.request<FindingDetail>(`/findings/${id}`);
  }

  // ── Metrics ───────────────────────────────────────────────────

  async getMetrics(): Promise<ScanMetrics> {
    return this.request<ScanMetrics>('/metrics');
  }

  // ── Export ────────────────────────────────────────────────────

  getExportJsonUrl(filters: FindingsFilters = {}): string {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== null && value !== '') {
        params.set(key, String(value));
      }
    }
    return `${this.baseUrl}/export/json?${params.toString()}`;
  }

  getExportCsvUrl(filters: FindingsFilters = {}): string {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== null && value !== '') {
        params.set(key, String(value));
      }
    }
    return `${this.baseUrl}/export/csv?${params.toString()}`;
  }

  // ── Export History ─────────────────────────────────────────────

  async getExportHistory(): Promise<{ exports: ExportIndex[]; total_exports: number }> {
    return this.request('/exports');
  }
}

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

export const api = new ApiClient();
export { ApiError };
