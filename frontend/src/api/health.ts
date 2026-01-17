/**
 * Health check API functions
 */

import apiClient from './client';
import type { ApiResponse, HealthCheckResponse } from '../types';

// Health check
export async function getHealth(): Promise<ApiResponse<HealthCheckResponse>> {
  const response = await apiClient.get<ApiResponse<HealthCheckResponse>>('/health');
  return response.data;
}
