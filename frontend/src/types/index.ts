/**
 * Core TypeScript types for CIRA application
 */

// Company Status
export type CompanyStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'paused';

// Processing Phase
export type ProcessingPhase = 'queued' | 'crawling' | 'extracting' | 'analyzing' | 'generating' | 'completed';

// Analysis Mode
export type AnalysisMode = 'quick' | 'thorough';

// Page Type
export type PageType = 'about' | 'team' | 'product' | 'service' | 'contact' | 'careers' | 'pricing' | 'blog' | 'news' | 'other';

// Entity Type
export type EntityType = 'person' | 'org' | 'location' | 'product' | 'date' | 'money' | 'email' | 'phone' | 'address' | 'social_handle' | 'tech_stack';

// Export Format
export type ExportFormat = 'markdown' | 'word' | 'pdf' | 'json';

// API Call Type
export type ApiCallType = 'extraction' | 'summarization' | 'analysis';

// Company
export interface Company {
  id: string;
  companyName: string;
  websiteUrl: string;
  industry?: string;
  analysisMode: AnalysisMode;
  status: CompanyStatus;
  totalTokensUsed: number;
  estimatedCost: number;
  createdAt: string;
  completedAt?: string;
}

// Company Config
export interface CompanyConfig {
  analysisMode: AnalysisMode;
  timeLimitMinutes: number;
  maxPages: number;
  maxDepth: number;
  followLinkedIn: boolean;
  followTwitter: boolean;
  followFacebook: boolean;
  exclusionPatterns: string[];
}

// Company Create Request
export interface CompanyCreateRequest {
  companyName: string;
  websiteUrl: string;
  industry?: string;
  config?: Partial<CompanyConfig>;
}

// Progress Update
export interface ProgressUpdate {
  companyId: string;
  status: CompanyStatus;
  phase: ProcessingPhase;
  pagesCrawled: number;
  pagesTotal: number;
  entitiesExtracted: number;
  tokensUsed: number;
  timeElapsed: number;
  estimatedTimeRemaining: number;
  currentActivity: string;
}

// Entity
export interface Entity {
  id: string;
  entityType: EntityType;
  entityValue: string;
  contextSnippet: string;
  sourceUrl: string;
  confidenceScore: number;
}

// Page
export interface Page {
  id: string;
  url: string;
  pageType: PageType;
  crawledAt: string;
  isExternal: boolean;
}

// Analysis Section
export interface SectionContent {
  content: string;
  sources: string[];
  confidence: number;
}

// Analysis Sections
export interface AnalysisSections {
  companyOverview: SectionContent;
  businessModelProducts: SectionContent;
  teamLeadership: SectionContent;
  marketPosition: SectionContent;
  technologyOperations: SectionContent;
  keyInsights: SectionContent;
  redFlags: SectionContent | null;
}

// Analysis
export interface Analysis {
  id: string;
  versionNumber: number;
  executiveSummary: string;
  fullAnalysis: AnalysisSections;
  createdAt: string;
}

// Token Breakdown
export interface TokenBreakdown {
  totalTokens: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  estimatedCost: number;
  byApiCall: Array<{
    callType: ApiCallType;
    section: string;
    inputTokens: number;
    outputTokens: number;
    timestamp: string;
  }>;
}

// API Response
export interface ApiResponse<T> {
  success: true;
  data: T;
}

// API Error Response
export interface ApiErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

// Paginated Response
export interface PaginatedResponse<T> {
  success: true;
  data: T[];
  meta: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
  };
}

// Batch Upload Result
export interface BatchUploadResult {
  totalCount: number;
  successful: number;
  failed: number;
  companies: Array<{
    companyName: string;
    companyId: string | null;
    error: string | null;
  }>;
}

// Version Comparison
export interface VersionChange {
  field: string;
  previousValue: string | null;
  currentValue: string | null;
  changeType: 'added' | 'removed' | 'modified';
}

export interface ComparisonResult {
  companyId: string;
  previousVersion: number;
  currentVersion: number;
  changes: {
    team: VersionChange[];
    products: VersionChange[];
    content: VersionChange[];
  };
  significantChanges: boolean;
}

// Health Check Response
export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  database: 'connected' | 'disconnected';
  redis: 'connected' | 'disconnected';
}
