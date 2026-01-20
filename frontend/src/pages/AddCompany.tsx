/**
 * Add Company Page - Single company input form
 *
 * Implements Task 8.2: Add Company Form Page
 * - Fields: name, URL (with validation), industry
 * - Advanced config panel (collapsible)
 * - Submit creates and redirects to progress
 */

import { useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCreateCompany } from '../hooks/useCompanies';
import {
  Button,
  Input,
  Select,
  Checkbox,
  Card,
  Slider,
  useToast,
} from '../components/ui';
import type { AnalysisMode, CompanyConfig } from '../types';

const ANALYSIS_MODE_OPTIONS = [
  { value: 'thorough', label: 'Thorough - Comprehensive analysis (recommended)' },
  { value: 'quick', label: 'Quick - Faster, less detailed analysis' },
];

const INDUSTRY_OPTIONS = [
  { value: '', label: 'Select an industry...' },
  { value: 'Technology', label: 'Technology' },
  { value: 'Healthcare', label: 'Healthcare' },
  { value: 'Finance', label: 'Finance' },
  { value: 'E-commerce', label: 'E-commerce' },
  { value: 'Manufacturing', label: 'Manufacturing' },
  { value: 'Education', label: 'Education' },
  { value: 'Real Estate', label: 'Real Estate' },
  { value: 'Marketing', label: 'Marketing' },
  { value: 'Consulting', label: 'Consulting' },
  { value: 'Other', label: 'Other' },
];

interface FormErrors {
  companyName?: string;
  websiteUrl?: string;
}

function validateUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

export default function AddCompany() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const createMutation = useCreateCompany();

  // Form state
  const [companyName, setCompanyName] = useState('');
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [industry, setIndustry] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});

  // Advanced config state
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>('thorough');
  const [maxPages, setMaxPages] = useState(200);
  const [maxDepth, setMaxDepth] = useState(4);
  const [timeLimitMinutes, setTimeLimitMinutes] = useState(30);
  const [followLinkedIn, setFollowLinkedIn] = useState(true);
  const [followTwitter, setFollowTwitter] = useState(true);
  const [followFacebook, setFollowFacebook] = useState(true);

  // Validation
  const validate = useCallback((): boolean => {
    const newErrors: FormErrors = {};

    if (!companyName.trim()) {
      newErrors.companyName = 'Company name is required';
    } else if (companyName.trim().length > 200) {
      newErrors.companyName = 'Company name must be 200 characters or less';
    }

    if (!websiteUrl.trim()) {
      newErrors.websiteUrl = 'Website URL is required';
    } else if (!validateUrl(websiteUrl.trim())) {
      newErrors.websiteUrl = 'Please enter a valid URL (e.g., https://example.com)';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [companyName, websiteUrl]);

  // Auto-normalize URL
  const normalizeUrl = (url: string): string => {
    let normalized = url.trim();
    if (normalized && !normalized.match(/^https?:\/\//i)) {
      normalized = 'https://' + normalized;
    }
    return normalized;
  };

  // Handle submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    const normalizedUrl = normalizeUrl(websiteUrl);

    const config: Partial<CompanyConfig> = {
      analysisMode,
      maxPages,
      maxDepth,
      timeLimitMinutes,
      followLinkedIn,
      followTwitter,
      followFacebook,
      exclusionPatterns: [],
    };

    try {
      const response = await createMutation.mutateAsync({
        companyName: companyName.trim(),
        websiteUrl: normalizedUrl,
        industry: industry || undefined,
        config,
      });

      showToast({
        type: 'success',
        message: `Analysis started for ${companyName}`,
      });

      // Redirect to progress page
      navigate(`/companies/${response.data.companyId}/progress`);
    } catch (err: any) {
      let message = 'Failed to create company';
      
      // Handle 409 Conflict - company already exists
      if (err?.response?.status === 409) {
        const errorData = err?.response?.data?.error;
        const existingCompanyId = errorData?.details?.existingCompanyId;
        
        if (existingCompanyId) {
          message = `A company with this URL already exists. Redirecting to existing company...`;
          showToast({
            type: 'error',
            message,
          });
          // Navigate to existing company after a short delay
          setTimeout(() => {
            navigate(`/companies/${existingCompanyId}/progress`);
          }, 1500);
        } else {
          message = errorData?.message || 'A company with this URL already exists';
          showToast({
            type: 'error',
            message,
          });
        }
      } else {
        // Handle other errors - extract message from API error response
        if (err?.response?.data?.error?.message) {
          message = err.response.data.error.message;
        } else if (err instanceof Error) {
          message = err.message;
        }
        showToast({
          type: 'error',
          message,
        });
      }
    }
  };

  // Handle URL blur - auto-normalize
  const handleUrlBlur = () => {
    if (websiteUrl && !websiteUrl.match(/^https?:\/\//i)) {
      setWebsiteUrl('https://' + websiteUrl);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
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
        <h1 className="text-3xl font-bold text-neutral-900">Add Company</h1>
      </div>

      {/* Form */}
      <Card>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Company Name */}
          <Input
            label="Company Name"
            type="text"
            id="companyName"
            value={companyName}
            onChange={(value) => {
              setCompanyName(value);
              if (errors.companyName) {
                setErrors((prev) => ({ ...prev, companyName: undefined }));
              }
            }}
            placeholder="Acme Corp"
            error={errors.companyName}
            required
          />

          {/* Website URL */}
          <Input
            label="Website URL"
            type="url"
            id="websiteUrl"
            value={websiteUrl}
            onChange={(value) => {
              setWebsiteUrl(value);
              if (errors.websiteUrl) {
                setErrors((prev) => ({ ...prev, websiteUrl: undefined }));
              }
            }}
            onBlur={handleUrlBlur}
            placeholder="https://www.example.com"
            error={errors.websiteUrl}
            helperText="Enter the main website URL to analyze"
            required
          />

          {/* Industry */}
          <Select
            label="Industry"
            id="industry"
            options={INDUSTRY_OPTIONS}
            value={industry}
            onChange={setIndustry}
            placeholder="Select an industry..."
          />

          {/* Advanced Options Toggle */}
          <div className="border-t border-neutral-200 pt-4">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-neutral-600 hover:text-neutral-900"
            >
              <svg
                className={`h-5 w-5 transition-transform ${showAdvanced ? 'rotate-90' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
              <span className="font-medium">Advanced Options</span>
            </button>
          </div>

          {/* Advanced Options Panel */}
          {showAdvanced && (
            <div className="space-y-6 pl-4 border-l-2 border-neutral-200">
              {/* Analysis Mode */}
              <Select
                label="Analysis Mode"
                id="analysisMode"
                options={ANALYSIS_MODE_OPTIONS}
                value={analysisMode}
                onChange={(value) => {
                  setAnalysisMode(value as AnalysisMode);
                  // Set presets based on mode
                  if (value === 'quick') {
                    setMaxPages(50);
                    setMaxDepth(2);
                    setTimeLimitMinutes(15);
                    setFollowLinkedIn(false);
                    setFollowTwitter(false);
                    setFollowFacebook(false);
                  } else {
                    setMaxPages(200);
                    setMaxDepth(4);
                    setTimeLimitMinutes(30);
                    setFollowLinkedIn(true);
                    setFollowTwitter(true);
                    setFollowFacebook(true);
                  }
                }}
              />

              {/* Max Pages */}
              <Slider
                label="Max Pages"
                id="maxPages"
                value={maxPages}
                onChange={setMaxPages}
                min={10}
                max={500}
                step={10}
                unit="pages"
              />

              {/* Max Depth */}
              <Slider
                label="Max Crawl Depth"
                id="maxDepth"
                value={maxDepth}
                onChange={setMaxDepth}
                min={1}
                max={10}
                step={1}
                unit="levels"
              />

              {/* Time Limit */}
              <Slider
                label="Time Limit"
                id="timeLimit"
                value={timeLimitMinutes}
                onChange={setTimeLimitMinutes}
                min={5}
                max={120}
                step={5}
                unit="minutes"
              />

              {/* External Links */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-neutral-700">
                  Follow External Links
                </label>
                <div className="space-y-2">
                  <Checkbox
                    label="LinkedIn Profiles"
                    checked={followLinkedIn}
                    onChange={setFollowLinkedIn}
                    description="Crawl linked LinkedIn company and employee pages"
                  />
                  <Checkbox
                    label="Twitter/X Profiles"
                    checked={followTwitter}
                    onChange={setFollowTwitter}
                    description="Crawl linked Twitter/X accounts"
                  />
                  <Checkbox
                    label="Facebook Pages"
                    checked={followFacebook}
                    onChange={setFollowFacebook}
                    description="Crawl linked Facebook pages"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <div className="pt-4">
            <Button
              type="submit"
              className="w-full"
              size="lg"
              loading={createMutation.isPending}
            >
              {createMutation.isPending ? 'Starting Analysis...' : 'Start Analysis'}
            </Button>
          </div>
        </form>
      </Card>

      {/* Info Card */}
      <Card padding="sm">
        <div className="flex items-start gap-3">
          <svg
            className="h-5 w-5 text-primary mt-0.5 flex-shrink-0"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
              clipRule="evenodd"
            />
          </svg>
          <div className="text-sm text-neutral-600">
            <p className="font-medium text-neutral-900 mb-1">What happens next?</p>
            <p>
              CIRA will crawl the company website, extract key information about the
              company, team, products, and business model, then generate a comprehensive
              analysis report using AI.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
