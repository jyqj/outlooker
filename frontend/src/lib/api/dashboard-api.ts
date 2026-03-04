import type { ApiResponse, DashboardSummary, HealthCheckResult } from '@/types';
import api from './client';

export async function getDashboardSummary(): Promise<ApiResponse<DashboardSummary>> {
  const res = await api.get<ApiResponse<DashboardSummary>>('/api/dashboard/summary');
  return res.data;
}

export async function runHealthCheck(): Promise<ApiResponse<HealthCheckResult>> {
  const res = await api.post<ApiResponse<HealthCheckResult>>('/api/accounts/health-check');
  return res.data;
}
