/**
 * React Query hooks for company data
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getCompanies,
  getCompany,
  createCompany,
  deleteCompany,
  pauseCompany,
  resumeCompany,
  rescanCompany,
  getProgress,
  getEntities,
  getPages,
  getTokens,
  batchUpload,
  getVersions,
  compareVersions,
  type CompanyFilters,
  type EntityFilters,
  type PageFilters,
} from '../api/companies';
import type { CompanyCreateRequest } from '../types';

// Query keys
export const companyKeys = {
  all: ['companies'] as const,
  lists: () => [...companyKeys.all, 'list'] as const,
  list: (filters: CompanyFilters) => [...companyKeys.lists(), filters] as const,
  details: () => [...companyKeys.all, 'detail'] as const,
  detail: (id: string) => [...companyKeys.details(), id] as const,
  progress: (id: string) => [...companyKeys.all, 'progress', id] as const,
  entities: (id: string, filters: EntityFilters) => [...companyKeys.all, 'entities', id, filters] as const,
  pages: (id: string, filters: PageFilters) => [...companyKeys.all, 'pages', id, filters] as const,
  tokens: (id: string) => [...companyKeys.all, 'tokens', id] as const,
  versions: (id: string) => [...companyKeys.all, 'versions', id] as const,
};

// List companies
export function useCompanies(filters: CompanyFilters = {}) {
  return useQuery({
    queryKey: companyKeys.list(filters),
    queryFn: () => getCompanies(filters),
  });
}

// Get company detail
export function useCompany(id: string) {
  return useQuery({
    queryKey: companyKeys.detail(id),
    queryFn: () => getCompany(id),
    enabled: !!id,
  });
}

// Get progress (with polling)
export function useProgress(id: string, enabled = true) {
  return useQuery({
    queryKey: companyKeys.progress(id),
    queryFn: () => getProgress(id),
    enabled: enabled && !!id,
    refetchInterval: 2000, // Poll every 2 seconds
  });
}

// Get entities
export function useEntities(companyId: string, filters: EntityFilters = {}) {
  return useQuery({
    queryKey: companyKeys.entities(companyId, filters),
    queryFn: () => getEntities(companyId, filters),
    enabled: !!companyId,
  });
}

// Get pages
export function usePages(companyId: string, filters: PageFilters = {}) {
  return useQuery({
    queryKey: companyKeys.pages(companyId, filters),
    queryFn: () => getPages(companyId, filters),
    enabled: !!companyId,
  });
}

// Get tokens
export function useTokens(companyId: string) {
  return useQuery({
    queryKey: companyKeys.tokens(companyId),
    queryFn: () => getTokens(companyId),
    enabled: !!companyId,
  });
}

// Get versions
export function useVersions(companyId: string) {
  return useQuery({
    queryKey: companyKeys.versions(companyId),
    queryFn: () => getVersions(companyId),
    enabled: !!companyId,
  });
}

// Create company mutation
export function useCreateCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CompanyCreateRequest) => createCompany(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: companyKeys.lists() });
    },
  });
}

// Delete company mutation
export function useDeleteCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteCompany(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: companyKeys.lists() });
    },
  });
}

// Pause company mutation
export function usePauseCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => pauseCompany(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: companyKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: companyKeys.progress(id) });
      queryClient.invalidateQueries({ queryKey: companyKeys.lists() });
    },
  });
}

// Resume company mutation
export function useResumeCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => resumeCompany(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: companyKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: companyKeys.progress(id) });
      queryClient.invalidateQueries({ queryKey: companyKeys.lists() });
    },
  });
}

// Rescan company mutation
export function useRescanCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => rescanCompany(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: companyKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: companyKeys.versions(id) });
      queryClient.invalidateQueries({ queryKey: companyKeys.lists() });
    },
  });
}

// Batch upload mutation
export function useBatchUpload() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => batchUpload(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: companyKeys.lists() });
    },
  });
}

// Compare versions query
export function useCompareVersions(companyId: string, version1: number, version2: number) {
  return useQuery({
    queryKey: [...companyKeys.versions(companyId), 'compare', version1, version2] as const,
    queryFn: () => compareVersions(companyId, version1, version2),
    enabled: !!companyId && version1 > 0 && version2 > 0,
  });
}
