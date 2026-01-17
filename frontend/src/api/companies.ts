/**
 * Company API functions
 */

import apiClient from './client';
import type {
  ApiResponse,
  PaginatedResponse,
  Company,
  CompanyCreateRequest,
  ProgressUpdate,
  Entity,
  Page,
  Analysis,
  TokenBreakdown,
  BatchUploadResult,
  ComparisonResult,
} from '../types';

// Company list filters
export interface CompanyFilters {
  status?: string;
  sort?: string;
  order?: 'asc' | 'desc';
  page?: number;
  pageSize?: number;
  search?: string;
}

// Create company
export async function createCompany(data: CompanyCreateRequest): Promise<ApiResponse<{ companyId: string; status: string; createdAt: string }>> {
  const response = await apiClient.post<ApiResponse<{ companyId: string; status: string; createdAt: string }>>('/companies', data);
  return response.data;
}

// List companies
export async function getCompanies(filters: CompanyFilters = {}): Promise<PaginatedResponse<Company>> {
  const params = new URLSearchParams();
  if (filters.status) params.append('status', filters.status);
  if (filters.sort) params.append('sort', filters.sort);
  if (filters.order) params.append('order', filters.order);
  if (filters.page) params.append('page', String(filters.page));
  if (filters.pageSize) params.append('pageSize', String(filters.pageSize));
  if (filters.search) params.append('search', filters.search);

  const response = await apiClient.get<PaginatedResponse<Company>>(`/companies?${params.toString()}`);
  return response.data;
}

// Get company by ID
export async function getCompany(id: string): Promise<ApiResponse<{
  company: Company;
  analysis: Analysis | null;
  entityCount: number;
  pageCount: number;
}>> {
  const response = await apiClient.get<ApiResponse<{
    company: Company;
    analysis: Analysis | null;
    entityCount: number;
    pageCount: number;
  }>>(`/companies/${id}`);
  return response.data;
}

// Delete company
export async function deleteCompany(id: string): Promise<ApiResponse<{
  deleted: boolean;
  deletedRecords: { pages: number; entities: number; analyses: number };
}>> {
  const response = await apiClient.delete<ApiResponse<{
    deleted: boolean;
    deletedRecords: { pages: number; entities: number; analyses: number };
  }>>(`/companies/${id}`);
  return response.data;
}

// Get progress
export async function getProgress(id: string): Promise<ApiResponse<ProgressUpdate>> {
  const response = await apiClient.get<ApiResponse<ProgressUpdate>>(`/companies/${id}/progress`);
  return response.data;
}

// Pause company
export async function pauseCompany(id: string): Promise<ApiResponse<{
  status: string;
  checkpointSaved: boolean;
  pausedAt: string;
}>> {
  const response = await apiClient.post<ApiResponse<{
    status: string;
    checkpointSaved: boolean;
    pausedAt: string;
  }>>(`/companies/${id}/pause`);
  return response.data;
}

// Resume company
export async function resumeCompany(id: string): Promise<ApiResponse<{
  status: string;
  resumedFrom: {
    pagesCrawled: number;
    entitiesExtracted: number;
    phase: string;
  };
}>> {
  const response = await apiClient.post<ApiResponse<{
    status: string;
    resumedFrom: {
      pagesCrawled: number;
      entitiesExtracted: number;
      phase: string;
    };
  }>>(`/companies/${id}/resume`);
  return response.data;
}

// Rescan company
export async function rescanCompany(id: string): Promise<ApiResponse<{
  newAnalysisId: string;
  versionNumber: number;
  status: string;
}>> {
  const response = await apiClient.post<ApiResponse<{
    newAnalysisId: string;
    versionNumber: number;
    status: string;
  }>>(`/companies/${id}/rescan`);
  return response.data;
}

// Get entities
export interface EntityFilters {
  type?: string;
  minConfidence?: number;
  page?: number;
  pageSize?: number;
}

export async function getEntities(companyId: string, filters: EntityFilters = {}): Promise<PaginatedResponse<Entity>> {
  const params = new URLSearchParams();
  if (filters.type) params.append('type', filters.type);
  if (filters.minConfidence !== undefined) params.append('minConfidence', String(filters.minConfidence));
  if (filters.page) params.append('page', String(filters.page));
  if (filters.pageSize) params.append('pageSize', String(filters.pageSize));

  const response = await apiClient.get<PaginatedResponse<Entity>>(`/companies/${companyId}/entities?${params.toString()}`);
  return response.data;
}

// Get pages
export interface PageFilters {
  pageType?: string;
  page?: number;
  pageSize?: number;
}

export async function getPages(companyId: string, filters: PageFilters = {}): Promise<PaginatedResponse<Page>> {
  const params = new URLSearchParams();
  if (filters.pageType) params.append('pageType', filters.pageType);
  if (filters.page) params.append('page', String(filters.page));
  if (filters.pageSize) params.append('pageSize', String(filters.pageSize));

  const response = await apiClient.get<PaginatedResponse<Page>>(`/companies/${companyId}/pages?${params.toString()}`);
  return response.data;
}

// Get token usage
export async function getTokens(companyId: string): Promise<ApiResponse<TokenBreakdown>> {
  const response = await apiClient.get<ApiResponse<TokenBreakdown>>(`/companies/${companyId}/tokens`);
  return response.data;
}

// Batch upload
export async function batchUpload(file: File): Promise<ApiResponse<BatchUploadResult>> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<ApiResponse<BatchUploadResult>>('/companies/batch', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
}

// Download template
export async function downloadTemplate(): Promise<Blob> {
  const response = await apiClient.get('/companies/template', {
    responseType: 'blob',
  });
  return response.data;
}

// Export analysis
export async function exportAnalysis(companyId: string, format: string, includeRawData = false): Promise<Blob> {
  const params = new URLSearchParams();
  params.append('format', format);
  params.append('includeRawData', String(includeRawData));

  const response = await apiClient.get(`/companies/${companyId}/export?${params.toString()}`, {
    responseType: 'blob',
  });
  return response.data;
}

// Get versions
export async function getVersions(companyId: string): Promise<ApiResponse<Array<{
  analysisId: string;
  versionNumber: number;
  createdAt: string;
  tokensUsed: number;
}>>> {
  const response = await apiClient.get<ApiResponse<Array<{
    analysisId: string;
    versionNumber: number;
    createdAt: string;
    tokensUsed: number;
  }>>>(`/companies/${companyId}/versions`);
  return response.data;
}

// Compare versions
export async function compareVersions(companyId: string, version1: number, version2: number): Promise<ApiResponse<ComparisonResult>> {
  const response = await apiClient.get<ApiResponse<ComparisonResult>>(
    `/companies/${companyId}/compare?version1=${version1}&version2=${version2}`
  );
  return response.data;
}
