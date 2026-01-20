/**
 * Company Progress Page - Real-time progress monitoring
 *
 * Implements Task 8.4: Progress View Page
 * - Progress bar with percentage
 * - Stats: Pages, Entities, Tokens
 * - Time elapsed/remaining
 * - Activity log
 * - Pause/Cancel buttons
 * - Auto-redirect on completion
 */

import { useEffect, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import {
  useCompany,
  useProgress,
  usePauseCompany,
  useStartCompany,
  useResumeCompany,
  useDeleteCompany,
} from '../hooks/useCompanies';
import {
  Button,
  Card,
  ProgressBar,
  Badge,
  getStatusBadgeVariant,
  Modal,
  Skeleton,
  useToast,
} from '../components/ui';
import type { ProcessingPhase, CompanyStatus } from '../types';

function formatTime(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  }
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
}

function formatCost(cost: number): string {
  return '$' + cost.toFixed(4);
}

const PHASE_LABELS: Record<ProcessingPhase, string> = {
  queued: 'Queued',
  crawling: 'Crawling Website',
  extracting: 'Extracting Entities',
  analyzing: 'Analyzing Content',
  generating: 'Generating Report',
  completed: 'Completed',
};

const PHASE_DESCRIPTIONS: Record<ProcessingPhase, string> = {
  queued: 'Waiting for analysis to start...',
  crawling: 'Discovering and fetching pages from the website',
  extracting: 'Identifying people, organizations, and key information',
  analyzing: 'Using AI to analyze the extracted data',
  generating: 'Creating the final analysis report',
  completed: 'Analysis complete!',
};

export default function CompanyProgress() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();

  // Modal state
  const [cancelModalOpen, setCancelModalOpen] = useState(false);

  // Fetch company details
  const { data: companyData, isLoading: companyLoading } = useCompany(id || '');

  // Fetch progress with polling (only when in_progress or paused)
  const shouldPoll =
    companyData?.data.company.status === 'in_progress' ||
    companyData?.data.company.status === 'paused';
  const {
    data: progressData,
    isLoading: progressLoading,
  } = useProgress(id || '', shouldPoll);

  // Mutations
  const pauseMutation = usePauseCompany();
  const startMutation = useStartCompany();
  const resumeMutation = useResumeCompany();
  const deleteMutation = useDeleteCompany();

  // Auto-redirect on completion
  useEffect(() => {
    if (companyData?.data.company.status === 'completed') {
      showToast({
        type: 'success',
        message: 'Analysis complete! Redirecting to results...',
      });
      const timeout = setTimeout(() => {
        navigate(`/companies/${id}`);
      }, 2000);
      return () => clearTimeout(timeout);
    }
  }, [companyData?.data.company.status, id, navigate, showToast]);

  // Handle pause
  const handlePause = async () => {
    if (!id) return;
    try {
      await pauseMutation.mutateAsync(id);
      showToast({
        type: 'success',
        message: 'Analysis paused. You can resume later.',
      });
    } catch {
      showToast({
        type: 'error',
        message: 'Failed to pause analysis',
      });
    }
  };

  // Handle start
  const handleStart = async () => {
    if (!id) return;
    try {
      await startMutation.mutateAsync(id);
      showToast({
        type: 'success',
        message: 'Analysis started!',
      });
    } catch {
      showToast({
        type: 'error',
        message: 'Failed to start analysis',
      });
    }
  };

  // Handle resume
  const handleResume = async () => {
    if (!id) return;
    try {
      await resumeMutation.mutateAsync(id);
      showToast({
        type: 'success',
        message: 'Analysis resumed!',
      });
    } catch {
      showToast({
        type: 'error',
        message: 'Failed to resume analysis',
      });
    }
  };

  // Handle cancel (delete)
  const handleCancel = async () => {
    if (!id) return;
    try {
      await deleteMutation.mutateAsync(id);
      showToast({
        type: 'success',
        message: 'Analysis cancelled and removed.',
      });
      navigate('/');
    } catch {
      showToast({
        type: 'error',
        message: 'Failed to cancel analysis',
      });
    }
    setCancelModalOpen(false);
  };

  // Loading state
  if (companyLoading || progressLoading) {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-6 w-16" />
          <Skeleton className="h-9 w-48" />
        </div>
        <Card>
          <div className="space-y-6">
            <Skeleton className="h-8 w-full" />
            <div className="grid grid-cols-3 gap-4">
              <Skeleton className="h-24" />
              <Skeleton className="h-24" />
              <Skeleton className="h-24" />
            </div>
            <Skeleton className="h-16" />
            <Skeleton className="h-10 w-full" />
          </div>
        </Card>
      </div>
    );
  }

  // Error or not found
  if (!companyData || !id) {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="text-neutral-500 hover:text-neutral-700 flex items-center gap-1"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            Back
          </Link>
          <h1 className="text-3xl font-bold text-neutral-900">Company Not Found</h1>
        </div>
        <Card>
          <p className="text-neutral-600 text-center py-8">
            The requested company could not be found.
          </p>
        </Card>
      </div>
    );
  }

  const company = companyData.data.company;
  const progress = progressData?.data;
  const status = company.status as CompanyStatus;
  const phase = progress?.phase || 'queued';
  const isPending = status === 'pending';
  const isPaused = status === 'paused';
  const isFailed = status === 'failed';
  const isCompleted = status === 'completed';
  const isInProgress = status === 'in_progress';

  // Calculate progress percentage
  let progressPercent = 0;
  if (progress) {
    if (progress.pagesTotal > 0) {
      progressPercent = Math.round((progress.pagesCrawled / progress.pagesTotal) * 100);
    } else if (phase === 'completed') {
      progressPercent = 100;
    } else if (phase === 'generating') {
      progressPercent = 90;
    } else if (phase === 'analyzing') {
      progressPercent = 75;
    } else if (phase === 'extracting') {
      progressPercent = 50;
    } else if (phase === 'crawling') {
      progressPercent = 25;
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/"
          className="text-neutral-500 hover:text-neutral-700 flex items-center gap-1"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10 19l-7-7m0 0l7-7m-7 7h18"
            />
          </svg>
          Back
        </Link>
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-neutral-900">{company.companyName}</h1>
          <p className="text-neutral-500">{company.websiteUrl}</p>
        </div>
        <Badge variant={getStatusBadgeVariant(status)} size="md">
          {status.replace('_', ' ')}
        </Badge>
      </div>

      {/* Progress Card */}
      <Card>
        <div className="space-y-6">
          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="font-medium text-neutral-900">
                {PHASE_LABELS[phase as ProcessingPhase]}
              </span>
              <span className="font-medium">{progressPercent}%</span>
            </div>
            <ProgressBar
              value={progressPercent}
              color={isFailed ? 'error' : isPaused ? 'warning' : 'primary'}
            />
            <p className="text-sm text-neutral-500">
              {isFailed
                ? 'Analysis failed. Please try again.'
                : isPaused
                ? 'Analysis paused. Click Resume to continue.'
                : isPending
                ? 'Analysis is ready to start. Click "Start Analysis" to begin.'
                : PHASE_DESCRIPTIONS[phase as ProcessingPhase]}
            </p>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-neutral-50 rounded-lg">
              <div className="text-2xl font-bold text-neutral-900">
                {progress?.pagesCrawled ?? 0}
                {progress?.pagesTotal ? (
                  <span className="text-sm font-normal text-neutral-500">
                    /{progress.pagesTotal}
                  </span>
                ) : null}
              </div>
              <div className="text-sm text-neutral-500">Pages Crawled</div>
            </div>
            <div className="text-center p-4 bg-neutral-50 rounded-lg">
              <div className="text-2xl font-bold text-neutral-900">
                {formatNumber(progress?.entitiesExtracted ?? 0)}
              </div>
              <div className="text-sm text-neutral-500">Entities Found</div>
            </div>
            <div className="text-center p-4 bg-neutral-50 rounded-lg">
              <div className="text-2xl font-bold text-neutral-900">
                {formatNumber(progress?.tokensUsed ?? 0)}
              </div>
              <div className="text-sm text-neutral-500">Tokens Used</div>
              <div className="text-xs text-neutral-400">
                {formatCost(company.estimatedCost || 0)}
              </div>
            </div>
          </div>

          {/* Time Info */}
          {progress && (
            <div className="flex items-center justify-center gap-8 text-sm">
              <div className="text-center">
                <div className="font-medium text-neutral-900">
                  {formatTime(progress.timeElapsed)}
                </div>
                <div className="text-neutral-500">Elapsed</div>
              </div>
              {progress.estimatedTimeRemaining > 0 && !isPaused && !isFailed && (
                <div className="text-center">
                  <div className="font-medium text-neutral-900">
                    ~{formatTime(progress.estimatedTimeRemaining)}
                  </div>
                  <div className="text-neutral-500">Remaining</div>
                </div>
              )}
            </div>
          )}

          {/* Current Activity */}
          {progress?.currentActivity && !isPaused && !isFailed && (
            <div className="text-center py-2 px-4 bg-primary-50 rounded-lg">
              <p className="text-sm text-primary">
                <span className="inline-block animate-pulse mr-2">●</span>
                {progress.currentActivity}
              </p>
            </div>
          )}

          {/* Actions */}
          {!isCompleted && (
            <div className="flex justify-center gap-4 pt-4 border-t border-neutral-200">
              {isPending ? (
                <>
                  <Button
                    onClick={handleStart}
                    loading={startMutation.isPending}
                  >
                    Start Analysis
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => setCancelModalOpen(true)}
                    disabled={startMutation.isPending}
                  >
                    Cancel
                  </Button>
                </>
              ) : isPaused ? (
                <>
                  <Button
                    onClick={handleResume}
                    loading={resumeMutation.isPending}
                  >
                    Resume
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => setCancelModalOpen(true)}
                    disabled={resumeMutation.isPending}
                  >
                    Cancel Analysis
                  </Button>
                </>
              ) : isFailed ? (
                <>
                  <Button
                    onClick={handleStart}
                    loading={startMutation.isPending}
                  >
                    Try Again
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => setCancelModalOpen(true)}
                    disabled={startMutation.isPending}
                  >
                    Delete
                  </Button>
                </>
              ) : isInProgress ? (
                <>
                  <Button
                    variant="secondary"
                    onClick={handlePause}
                    loading={pauseMutation.isPending}
                  >
                    Pause
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => setCancelModalOpen(true)}
                    disabled={pauseMutation.isPending}
                  >
                    Cancel
                  </Button>
                </>
              ) : null}
            </div>
          )}

          {/* Completion Message */}
          {isCompleted && (
            <div className="text-center py-4 bg-success-50 rounded-lg">
              <svg
                className="h-12 w-12 text-success mx-auto mb-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <p className="text-success font-medium">Analysis Complete!</p>
              <p className="text-sm text-neutral-600 mt-1">
                Redirecting to results...
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Cancel Confirmation Modal */}
      <Modal
        isOpen={cancelModalOpen}
        onClose={() => setCancelModalOpen(false)}
        title="Cancel Analysis"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-neutral-600">
            Are you sure you want to cancel the analysis for{' '}
            <strong>{company.companyName}</strong>? This will permanently delete all
            progress and data.
          </p>
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setCancelModalOpen(false)}>
              Keep Analyzing
            </Button>
            <Button
              variant="danger"
              onClick={handleCancel}
              loading={deleteMutation.isPending}
            >
              Cancel & Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
