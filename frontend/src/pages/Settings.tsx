/**
 * Settings Page - Configuration settings
 *
 * Implements Task 8.7: Settings Page
 * - Default analysis config
 * - Quick/Thorough mode presets
 * - Save/Reset options
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Button,
  Card,
  Select,
  Slider,
  Checkbox,
  useToast,
} from '../components/ui';
import type { AnalysisMode, CompanyConfig } from '../types';

const ANALYSIS_MODE_OPTIONS = [
  { value: 'thorough', label: 'Thorough' },
  { value: 'quick', label: 'Quick' },
];

// Mode presets
const MODE_PRESETS: Record<AnalysisMode, Partial<CompanyConfig>> = {
  quick: {
    maxPages: 50,
    maxDepth: 2,
    timeLimitMinutes: 15,
    followLinkedIn: false,
    followTwitter: false,
    followFacebook: false,
  },
  thorough: {
    maxPages: 200,
    maxDepth: 4,
    timeLimitMinutes: 30,
    followLinkedIn: true,
    followTwitter: true,
    followFacebook: true,
  },
};

// Default settings
const DEFAULT_SETTINGS: CompanyConfig = {
  analysisMode: 'thorough',
  maxPages: 200,
  maxDepth: 4,
  timeLimitMinutes: 30,
  followLinkedIn: true,
  followTwitter: true,
  followFacebook: true,
  exclusionPatterns: [],
};

// Storage key
const SETTINGS_STORAGE_KEY = 'cira_default_settings';

// Load settings from localStorage
function loadSettings(): CompanyConfig {
  try {
    const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
    }
  } catch (e) {
    console.error('Failed to load settings:', e);
  }
  return DEFAULT_SETTINGS;
}

// Save settings to localStorage
function saveSettingsToStorage(settings: CompanyConfig): void {
  try {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  } catch (e) {
    console.error('Failed to save settings:', e);
  }
}

export default function Settings() {
  const { showToast } = useToast();

  // Form state
  const [settings, setSettings] = useState<CompanyConfig>(DEFAULT_SETTINGS);
  const [hasChanges, setHasChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Load settings on mount
  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  // Track changes
  const updateSetting = <K extends keyof CompanyConfig>(
    key: K,
    value: CompanyConfig[K]
  ) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  // Handle mode change with presets
  const handleModeChange = (mode: AnalysisMode) => {
    const preset = MODE_PRESETS[mode];
    setSettings((prev) => ({
      ...prev,
      analysisMode: mode,
      ...preset,
    }));
    setHasChanges(true);
  };

  // Handle save
  const handleSave = async () => {
    setIsSaving(true);
    try {
      saveSettingsToStorage(settings);
      showToast({
        type: 'success',
        message: 'Settings saved successfully',
      });
      setHasChanges(false);
    } catch {
      showToast({
        type: 'error',
        message: 'Failed to save settings',
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Handle reset
  const handleReset = () => {
    setSettings(DEFAULT_SETTINGS);
    saveSettingsToStorage(DEFAULT_SETTINGS);
    showToast({
      type: 'info',
      message: 'Settings reset to defaults',
    });
    setHasChanges(false);
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
        <h1 className="text-3xl font-bold text-neutral-900">Settings</h1>
      </div>

      {/* Settings Form */}
      <Card>
        <div className="space-y-8">
          {/* Analysis Mode Section */}
          <div>
            <h2 className="text-xl font-semibold text-neutral-900 mb-4">
              Default Analysis Settings
            </h2>
            <p className="text-sm text-neutral-500 mb-6">
              These settings will be used as defaults when adding new companies.
              You can override them on a per-company basis.
            </p>

            <div className="space-y-6">
              {/* Analysis Mode */}
              <div>
                <Select
                  label="Analysis Mode"
                  id="analysisMode"
                  options={ANALYSIS_MODE_OPTIONS}
                  value={settings.analysisMode}
                  onChange={(value) => handleModeChange(value as AnalysisMode)}
                />
                <p className="mt-1 text-sm text-neutral-500">
                  {settings.analysisMode === 'thorough'
                    ? 'Comprehensive analysis with more pages and external links'
                    : 'Faster analysis with fewer pages and no external links'}
                </p>
              </div>

              {/* Crawling Settings */}
              <div className="border-t border-neutral-200 pt-6">
                <h3 className="text-lg font-medium text-neutral-900 mb-4">
                  Crawling Settings
                </h3>

                <div className="space-y-6">
                  {/* Max Pages */}
                  <Slider
                    label="Maximum Pages"
                    id="maxPages"
                    value={settings.maxPages}
                    onChange={(value) => updateSetting('maxPages', value)}
                    min={10}
                    max={500}
                    step={10}
                    unit="pages"
                  />

                  {/* Max Depth */}
                  <Slider
                    label="Maximum Crawl Depth"
                    id="maxDepth"
                    value={settings.maxDepth}
                    onChange={(value) => updateSetting('maxDepth', value)}
                    min={1}
                    max={10}
                    step={1}
                    unit="levels"
                  />

                  {/* Time Limit */}
                  <Slider
                    label="Time Limit"
                    id="timeLimit"
                    value={settings.timeLimitMinutes}
                    onChange={(value) => updateSetting('timeLimitMinutes', value)}
                    min={5}
                    max={120}
                    step={5}
                    unit="minutes"
                  />
                </div>
              </div>

              {/* External Links */}
              <div className="border-t border-neutral-200 pt-6">
                <h3 className="text-lg font-medium text-neutral-900 mb-4">
                  External Link Settings
                </h3>
                <p className="text-sm text-neutral-500 mb-4">
                  Configure which external social media profiles to crawl when found.
                </p>

                <div className="space-y-3">
                  <Checkbox
                    label="Follow LinkedIn Links"
                    checked={settings.followLinkedIn}
                    onChange={(value) => updateSetting('followLinkedIn', value)}
                    description="Crawl linked LinkedIn company and employee pages"
                  />
                  <Checkbox
                    label="Follow Twitter/X Links"
                    checked={settings.followTwitter}
                    onChange={(value) => updateSetting('followTwitter', value)}
                    description="Crawl linked Twitter/X accounts"
                  />
                  <Checkbox
                    label="Follow Facebook Links"
                    checked={settings.followFacebook}
                    onChange={(value) => updateSetting('followFacebook', value)}
                    description="Crawl linked Facebook pages"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between pt-6 border-t border-neutral-200">
            <Button variant="ghost" onClick={handleReset}>
              Reset to Defaults
            </Button>
            <div className="flex items-center gap-3">
              {hasChanges && (
                <span className="text-sm text-warning">Unsaved changes</span>
              )}
              <Button
                onClick={handleSave}
                loading={isSaving}
                disabled={!hasChanges}
              >
                Save Settings
              </Button>
            </div>
          </div>
        </div>
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
            <p className="font-medium text-neutral-900 mb-1">About Analysis Modes</p>
            <ul className="list-disc list-inside space-y-1">
              <li>
                <strong>Thorough:</strong> Crawls up to 200 pages, 4 levels deep, and follows social media links. Best for comprehensive research.
              </li>
              <li>
                <strong>Quick:</strong> Crawls up to 50 pages, 2 levels deep. Faster results but less detailed analysis.
              </li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}
