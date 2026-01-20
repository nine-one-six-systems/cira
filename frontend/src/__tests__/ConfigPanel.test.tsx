/**
 * Settings/Configuration Panel Component Tests
 *
 * Verifies UI-08: Configuration panel with mode presets
 * - Settings page rendering with configuration options
 * - Quick/Thorough mode presets
 * - Crawling settings (max pages, depth, time limit)
 * - External link settings
 * - Save/Reset functionality
 * - Accessibility
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach, type Mock } from 'vitest';
import Settings from '../pages/Settings';
import { useToast } from '../components/ui';

// Mock the hooks
vi.mock('../components/ui', async () => {
  const actual = await vi.importActual('../components/ui');
  return {
    ...actual,
    useToast: vi.fn(),
  };
});

// Mock localStorage
const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    reset: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
});

// Test wrapper with providers
function createTestWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  };
}

describe('TestConfigurationDisplay (UI-08)', () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockLocalStorage.reset();

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  afterEach(() => {
    mockLocalStorage.reset();
  });

  it('renders settings page with configuration options', () => {
    render(<Settings />, { wrapper: createTestWrapper() });

    // Assert heading visible
    expect(screen.getByText('Settings')).toBeInTheDocument();

    // Assert configuration form elements present
    expect(screen.getByText(/default analysis settings/i)).toBeInTheDocument();
  });

  it('displays Quick and Thorough mode options', () => {
    render(<Settings />, { wrapper: createTestWrapper() });

    // Assert analysis mode select is present
    const modeSelect = screen.getByLabelText(/analysis mode/i);
    expect(modeSelect).toBeInTheDocument();

    // Assert has Thorough and Quick options (check select options)
    expect(screen.getByRole('option', { name: /thorough/i })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /quick/i })).toBeInTheDocument();
  });

  it('shows max pages slider or input', () => {
    render(<Settings />, { wrapper: createTestWrapper() });

    // Assert max pages control present
    expect(screen.getByLabelText(/maximum pages/i)).toBeInTheDocument();
  });

  it('shows max depth control', () => {
    render(<Settings />, { wrapper: createTestWrapper() });

    // Assert depth limit control present
    expect(screen.getByLabelText(/maximum crawl depth/i)).toBeInTheDocument();
  });

  it('shows time limit control', () => {
    render(<Settings />, { wrapper: createTestWrapper() });

    // Assert time limit control present
    expect(screen.getByLabelText(/time limit/i)).toBeInTheDocument();
  });

  it('shows external link checkboxes', () => {
    render(<Settings />, { wrapper: createTestWrapper() });

    // Assert external link settings visible
    expect(screen.getByText(/external link settings/i)).toBeInTheDocument();

    // Assert checkboxes for social links
    expect(screen.getByRole('checkbox', { name: /linkedin/i })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: /twitter/i })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: /facebook/i })).toBeInTheDocument();
  });

  it('displays mode description based on selection', () => {
    render(<Settings />, { wrapper: createTestWrapper() });

    // Default is thorough, so thorough description should be visible
    expect(screen.getByText(/comprehensive analysis/i)).toBeInTheDocument();
  });
});

describe('TestModePresets (UI-08)', () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockLocalStorage.reset();

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  afterEach(() => {
    mockLocalStorage.reset();
  });

  it('Quick mode sets fast configuration', async () => {
    const user = userEvent.setup();
    render(<Settings />, { wrapper: createTestWrapper() });

    // Select Quick mode
    const modeSelect = screen.getByLabelText(/analysis mode/i);
    await user.selectOptions(modeSelect, 'quick');

    // Assert max pages is lower value (50 for quick)
    const maxPagesSlider = screen.getByLabelText(/maximum pages/i);
    expect(maxPagesSlider).toHaveValue('50');

    // Assert depth is limited (2 for quick)
    const maxDepthSlider = screen.getByLabelText(/maximum crawl depth/i);
    expect(maxDepthSlider).toHaveValue('2');
  });

  it('Quick mode disables social link following', async () => {
    const user = userEvent.setup();
    render(<Settings />, { wrapper: createTestWrapper() });

    // Select Quick mode
    const modeSelect = screen.getByLabelText(/analysis mode/i);
    await user.selectOptions(modeSelect, 'quick');

    // Assert social links are unchecked
    expect(screen.getByRole('checkbox', { name: /linkedin/i })).not.toBeChecked();
    expect(screen.getByRole('checkbox', { name: /twitter/i })).not.toBeChecked();
    expect(screen.getByRole('checkbox', { name: /facebook/i })).not.toBeChecked();
  });

  it('Thorough mode sets comprehensive configuration', async () => {
    const user = userEvent.setup();
    render(<Settings />, { wrapper: createTestWrapper() });

    // First select quick, then thorough to test mode change
    const modeSelect = screen.getByLabelText(/analysis mode/i);
    await user.selectOptions(modeSelect, 'quick');
    await user.selectOptions(modeSelect, 'thorough');

    // Assert max pages is higher value (200 for thorough)
    const maxPagesSlider = screen.getByLabelText(/maximum pages/i);
    expect(maxPagesSlider).toHaveValue('200');

    // Assert depth allows more (4 for thorough)
    const maxDepthSlider = screen.getByLabelText(/maximum crawl depth/i);
    expect(maxDepthSlider).toHaveValue('4');
  });

  it('Thorough mode enables social link following', async () => {
    const user = userEvent.setup();
    render(<Settings />, { wrapper: createTestWrapper() });

    // Select Quick mode first then switch back to Thorough
    const modeSelect = screen.getByLabelText(/analysis mode/i);
    await user.selectOptions(modeSelect, 'quick');
    await user.selectOptions(modeSelect, 'thorough');

    // Assert social links are checked
    expect(screen.getByRole('checkbox', { name: /linkedin/i })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: /twitter/i })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: /facebook/i })).toBeChecked();
  });

  it('mode selection updates form values', async () => {
    const user = userEvent.setup();
    render(<Settings />, { wrapper: createTestWrapper() });

    const modeSelect = screen.getByLabelText(/analysis mode/i);
    const maxPagesSlider = screen.getByLabelText(/maximum pages/i);

    // Initial thorough mode
    expect(maxPagesSlider).toHaveValue('200');

    // Switch to quick
    await user.selectOptions(modeSelect, 'quick');
    expect(maxPagesSlider).toHaveValue('50');

    // Switch back to thorough
    await user.selectOptions(modeSelect, 'thorough');
    expect(maxPagesSlider).toHaveValue('200');
  });

  it('mode description updates on selection', async () => {
    const user = userEvent.setup();
    render(<Settings />, { wrapper: createTestWrapper() });

    // Initial thorough mode description
    expect(screen.getByText(/comprehensive analysis/i)).toBeInTheDocument();

    // Switch to quick
    const modeSelect = screen.getByLabelText(/analysis mode/i);
    await user.selectOptions(modeSelect, 'quick');

    // Quick mode description
    expect(screen.getByText(/faster analysis/i)).toBeInTheDocument();
  });
});

describe('TestConfigurationPersistence', () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockLocalStorage.reset();

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  afterEach(() => {
    mockLocalStorage.reset();
  });

  it('save button is present', () => {
    render(<Settings />, { wrapper: createTestWrapper() });

    // Assert save button visible
    expect(screen.getByRole('button', { name: /save settings/i })).toBeInTheDocument();
  });

  it('save button is disabled when no changes', () => {
    render(<Settings />, { wrapper: createTestWrapper() });

    // Assert save button is disabled initially
    const saveButton = screen.getByRole('button', { name: /save settings/i });
    expect(saveButton).toBeDisabled();
  });

  it('save button enables after making changes', async () => {
    const user = userEvent.setup();
    render(<Settings />, { wrapper: createTestWrapper() });

    // Make a change
    const modeSelect = screen.getByLabelText(/analysis mode/i);
    await user.selectOptions(modeSelect, 'quick');

    // Assert save button is now enabled
    const saveButton = screen.getByRole('button', { name: /save settings/i });
    expect(saveButton).not.toBeDisabled();
  });

  it('save button triggers save action', async () => {
    const user = userEvent.setup();
    render(<Settings />, { wrapper: createTestWrapper() });

    // Make a change to enable save button
    const modeSelect = screen.getByLabelText(/analysis mode/i);
    await user.selectOptions(modeSelect, 'quick');

    // Click save button
    const saveButton = screen.getByRole('button', { name: /save settings/i });
    await user.click(saveButton);

    // Assert localStorage.setItem was called
    await waitFor(() => {
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'cira_default_settings',
        expect.any(String)
      );
    });
  });

  it('shows success feedback on save', async () => {
    const user = userEvent.setup();
    render(<Settings />, { wrapper: createTestWrapper() });

    // Make a change
    const modeSelect = screen.getByLabelText(/analysis mode/i);
    await user.selectOptions(modeSelect, 'quick');

    // Click save
    const saveButton = screen.getByRole('button', { name: /save settings/i });
    await user.click(saveButton);

    // Assert success toast
    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'success',
        })
      );
    });
  });

  it('reset button restores defaults', async () => {
    const user = userEvent.setup();
    render(<Settings />, { wrapper: createTestWrapper() });

    // Change from default
    const modeSelect = screen.getByLabelText(/analysis mode/i);
    await user.selectOptions(modeSelect, 'quick');

    // Verify quick mode is set
    const maxPagesSlider = screen.getByLabelText(/maximum pages/i);
    expect(maxPagesSlider).toHaveValue('50');

    // Click reset button
    const resetButton = screen.getByRole('button', { name: /reset to defaults/i });
    await user.click(resetButton);

    // Assert values reset to defaults (thorough mode values)
    expect(maxPagesSlider).toHaveValue('200');
    expect(modeSelect).toHaveValue('thorough');
  });

  it('reset button shows info toast', async () => {
    const user = userEvent.setup();
    render(<Settings />, { wrapper: createTestWrapper() });

    // Click reset
    const resetButton = screen.getByRole('button', { name: /reset to defaults/i });
    await user.click(resetButton);

    // Assert info toast
    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'info',
        })
      );
    });
  });

  it('shows unsaved changes indicator', async () => {
    const user = userEvent.setup();
    render(<Settings />, { wrapper: createTestWrapper() });

    // Make a change
    const modeSelect = screen.getByLabelText(/analysis mode/i);
    await user.selectOptions(modeSelect, 'quick');

    // Assert unsaved changes indicator
    expect(screen.getByText(/unsaved changes/i)).toBeInTheDocument();
  });

  it('loads saved settings on mount', () => {
    // Set up saved settings
    const savedSettings = {
      analysisMode: 'quick',
      maxPages: 50,
      maxDepth: 2,
      timeLimitMinutes: 15,
      followLinkedIn: false,
      followTwitter: false,
      followFacebook: false,
    };
    mockLocalStorage.getItem.mockReturnValue(JSON.stringify(savedSettings));

    render(<Settings />, { wrapper: createTestWrapper() });

    // Assert loaded values
    const maxPagesSlider = screen.getByLabelText(/maximum pages/i);
    expect(maxPagesSlider).toHaveValue('50');

    // Reset mock after this test to not affect others
    mockLocalStorage.getItem.mockReturnValue(null);
  });
});

describe('TestAccessibility', () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockLocalStorage.reset();

    (useToast as Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  afterEach(() => {
    mockLocalStorage.reset();
  });

  it('form controls have labels', () => {
    render(<Settings />, { wrapper: createTestWrapper() });

    // All inputs should have associated labels
    expect(screen.getByLabelText(/analysis mode/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/maximum pages/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/maximum crawl depth/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/time limit/i)).toBeInTheDocument();
  });

  it('checkboxes have accessible labels', () => {
    render(<Settings />, { wrapper: createTestWrapper() });

    // Checkboxes should be findable by their labels
    const linkedInCheckbox = screen.getByRole('checkbox', { name: /linkedin/i });
    const twitterCheckbox = screen.getByRole('checkbox', { name: /twitter/i });
    const facebookCheckbox = screen.getByRole('checkbox', { name: /facebook/i });

    expect(linkedInCheckbox).toBeInTheDocument();
    expect(twitterCheckbox).toBeInTheDocument();
    expect(facebookCheckbox).toBeInTheDocument();
  });

  it('can navigate back to dashboard', () => {
    render(<Settings />, { wrapper: createTestWrapper() });

    // Assert Back link is present
    const backLink = screen.getByRole('link', { name: /back/i });
    expect(backLink).toBeInTheDocument();
    expect(backLink).toHaveAttribute('href', '/');
  });

  it('sliders are interactive', async () => {
    const user = userEvent.setup();
    render(<Settings />, { wrapper: createTestWrapper() });

    // Get max pages slider
    const maxPagesSlider = screen.getByLabelText(/maximum pages/i);

    // Slider should be focusable and interactive
    await user.click(maxPagesSlider);
    expect(maxPagesSlider).toHaveFocus();
  });

  it('checkboxes are toggleable', async () => {
    const user = userEvent.setup();
    render(<Settings />, { wrapper: createTestWrapper() });

    // Get LinkedIn checkbox (default thorough mode = checked)
    const linkedInCheckbox = screen.getByRole('checkbox', { name: /linkedin/i });
    expect(linkedInCheckbox).toBeChecked();

    // Toggle it off
    await user.click(linkedInCheckbox);
    expect(linkedInCheckbox).not.toBeChecked();

    // Toggle it back on
    await user.click(linkedInCheckbox);
    expect(linkedInCheckbox).toBeChecked();
  });

  it('displays info card with mode explanations', () => {
    render(<Settings />, { wrapper: createTestWrapper() });

    // Assert info card explains modes
    expect(screen.getByText(/about analysis modes/i)).toBeInTheDocument();
    // Text is split across elements due to <strong> tags
    expect(screen.getByText('Thorough:')).toBeInTheDocument();
    expect(screen.getByText(/crawls up to 200 pages/i)).toBeInTheDocument();
    expect(screen.getByText('Quick:')).toBeInTheDocument();
    expect(screen.getByText(/crawls up to 50 pages/i)).toBeInTheDocument();
  });
});
