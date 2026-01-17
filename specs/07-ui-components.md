# UI Components Specification

## Overview

The frontend uses React 18+ with TypeScript, TanStack Query for data fetching, and Tailwind CSS for styling. This specification covers the design system and component library.

## Design System

### Color Palette

| Name | Hex | CSS Variable | Usage |
|------|-----|--------------|-------|
| Primary Blue | #2563eb | --color-primary | Primary actions, links |
| Success Green | #10b981 | --color-success | Completed status, success messages |
| Warning Yellow | #f59e0b | --color-warning | In-progress status, warnings |
| Error Red | #ef4444 | --color-error | Failed status, errors |
| Neutral Gray | #6b7280 | --color-neutral | Secondary text, borders |
| Background | #f9fafb | --color-bg | Page background |
| Surface | #ffffff | --color-surface | Card backgrounds |
| Text Primary | #111827 | --color-text | Primary text |
| Text Secondary | #6b7280 | --color-text-secondary | Secondary text |

### Typography

| Element | Font | Size | Weight | Line Height |
|---------|------|------|--------|-------------|
| H1 | Inter / system-ui | 30px | 700 | 1.2 |
| H2 | Inter / system-ui | 24px | 600 | 1.25 |
| H3 | Inter / system-ui | 20px | 600 | 1.3 |
| Body | System stack | 16px | 400 | 1.5 |
| Small | System stack | 14px | 400 | 1.4 |
| Code | Monospace | 14px | 400 | 1.4 |

### Spacing (8px base)

| Token | Value | Usage |
|-------|-------|-------|
| space-1 | 4px | Tight spacing |
| space-2 | 8px | Default spacing |
| space-3 | 12px | Related elements |
| space-4 | 16px | Section padding |
| space-6 | 24px | Component gaps |
| space-8 | 32px | Large sections |

## Core Components

### Button

```typescript
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'danger' | 'ghost';
  size: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}
```

**Variants:**
- Primary: Blue background, white text
- Secondary: White background, gray border
- Danger: Red background, white text
- Ghost: Transparent, primary text color

### Input

```typescript
interface InputProps {
  type: 'text' | 'url' | 'number' | 'email';
  label: string;
  placeholder?: string;
  error?: string;
  value: string;
  onChange: (value: string) => void;
}
```

**States:** Default, Focus, Error, Disabled

### Select

```typescript
interface SelectProps {
  label: string;
  options: Array<{ value: string; label: string }>;
  value: string;
  onChange: (value: string) => void;
  allowCustom?: boolean;
  searchable?: boolean;
}
```

### Table

```typescript
interface TableProps<T> {
  columns: Array<{
    key: keyof T;
    header: string;
    sortable?: boolean;
    render?: (value: T[keyof T], row: T) => React.ReactNode;
  }>;
  data: T[];
  onSort?: (key: keyof T, direction: 'asc' | 'desc') => void;
  onRowClick?: (row: T) => void;
}
```

### Card

```typescript
interface CardProps {
  title?: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}
```

### Modal

```typescript
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
}
```

### Toast

```typescript
interface ToastProps {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

// Usage via context
const { showToast } = useToast();
showToast({ type: 'success', message: 'Company added!' });
```

### ProgressBar

```typescript
interface ProgressBarProps {
  value: number;      // 0-100
  label?: string;
  showPercentage?: boolean;
  color?: 'primary' | 'success' | 'warning' | 'error';
}
```

### Badge

```typescript
interface BadgeProps {
  variant: 'default' | 'success' | 'warning' | 'error' | 'info';
  children: React.ReactNode;
}
```

**Status Mapping:**
- pending: default (gray)
- in_progress: warning (yellow)
- completed: success (green)
- failed: error (red)
- paused: info (blue)

### Tabs

```typescript
interface TabsProps {
  tabs: Array<{ id: string; label: string; content: React.ReactNode }>;
  defaultTab?: string;
  onChange?: (tabId: string) => void;
}
```

### Skeleton

```typescript
interface SkeletonProps {
  variant: 'text' | 'rect' | 'circle';
  width?: string | number;
  height?: string | number;
  lines?: number;
}
```

## Domain Components

### CompanyCard

```typescript
interface CompanyCardProps {
  company: Company;
  onView: () => void;
  onExport: (format: ExportFormat) => void;
  onDelete: () => void;
}
```

**Features:**
- Shows company name, URL, status badge
- Token count and estimated cost
- Created/completed timestamps
- Action dropdown menu

### ProgressTracker

```typescript
interface ProgressTrackerProps {
  progress: ProgressUpdate;
}
```

**Features:**
- Overall progress bar
- Phase indicator (Crawling, Extracting, Analyzing, etc.)
- Stats: Pages, Entities, Tokens
- Time elapsed / estimated remaining
- Current activity text

### TokenCounter

```typescript
interface TokenCounterProps {
  tokensUsed: number;
  estimatedCost: number;
  animate?: boolean;
}
```

**Features:**
- Animated counter during updates
- Cost formatted as currency
- Tooltip with breakdown

### AnalysisSummary

```typescript
interface AnalysisSummaryProps {
  analysis: Analysis;
}
```

**Features:**
- Markdown rendering with styling
- Source links as footnotes
- Confidence indicators
- Collapsible sections

### EntityTable

```typescript
interface EntityTableProps {
  entities: Entity[];
  filters: {
    type?: EntityType;
    minConfidence?: number;
    search?: string;
  };
  onFilterChange: (filters: Partial<typeof filters>) => void;
}
```

**Features:**
- Filter by entity type
- Filter by confidence threshold
- Search within entities
- Sort by confidence/type
- Click to view context

### ExportDropdown

```typescript
interface ExportDropdownProps {
  onExport: (format: ExportFormat) => void;
  loading?: boolean;
}
```

**Options:**
- Markdown (.md)
- Word (.docx)
- PDF (.pdf)
- JSON (.json)

### ConfigPanel

```typescript
interface ConfigPanelProps {
  config: AnalysisConfig;
  onChange: (config: AnalysisConfig) => void;
}
```

**Fields:**
- Analysis Mode toggle (Quick/Thorough)
- Time Limit slider
- Max Pages input
- Max Depth input
- External Links checkboxes
- Exclusion Patterns textarea

### BatchPreview

```typescript
interface BatchPreviewProps {
  rows: ParsedRow[];
  errors: Record<number, string[]>;
  onConfirm: () => void;
  onCancel: () => void;
}
```

**Features:**
- Table showing parsed CSV
- Error highlighting per row
- Valid/invalid counts
- Confirm only valid rows

### VersionSelector

```typescript
interface VersionSelectorProps {
  versions: Array<{ id: string; versionNumber: number; createdAt: Date }>;
  currentVersion: number;
  onSelect: (versionNumber: number) => void;
}
```

### ChangeHighlight

```typescript
interface ChangeHighlightProps {
  comparison: ComparisonResult;
}
```

**Features:**
- Side-by-side diff view
- Color coding: green (added), red (removed), yellow (modified)
- Expandable change details

## Accessibility Requirements

- WCAG 2.1 Level AA compliance
- Full keyboard navigation
- Screen reader compatible (ARIA labels)
- Color contrast >= 4.5:1
- Focus indicators on all interactive elements
- Skip links for main content

## Responsive Breakpoints

| Breakpoint | Width | Target |
|------------|-------|--------|
| sm | 640px | - |
| md | 768px | - |
| lg | 1024px | Minimum supported |
| xl | 1280px | Default desktop |
| 2xl | 1536px | Large displays |

Note: Desktop-first design, minimum 1024px width supported.
