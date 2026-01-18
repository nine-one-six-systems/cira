/**
 * ProgressBar Component
 *
 * A progress indicator with optional label and percentage display.
 */

export interface ProgressBarProps {
  /** Progress value (0-100) */
  value: number;
  /** Optional label text */
  label?: string;
  /** Whether to show percentage */
  showPercentage?: boolean;
  /** Color variant */
  color?: 'primary' | 'success' | 'warning' | 'error';
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Additional CSS classes */
  className?: string;
}

const colorStyles = {
  primary: 'bg-primary',
  success: 'bg-success',
  warning: 'bg-warning',
  error: 'bg-error',
};

const sizeStyles = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
};

/**
 * ProgressBar component for showing completion status.
 *
 * @example
 * ```tsx
 * <ProgressBar value={75} label="Crawling" showPercentage />
 *
 * <ProgressBar value={100} color="success" />
 * ```
 */
export function ProgressBar({
  value,
  label,
  showPercentage = false,
  color = 'primary',
  size = 'md',
  className = '',
}: ProgressBarProps) {
  // Clamp value between 0 and 100
  const normalizedValue = Math.min(100, Math.max(0, value));

  return (
    <div className={`w-full ${className}`}>
      {(label || showPercentage) && (
        <div className="flex justify-between items-center mb-1">
          {label && (
            <span className="text-sm font-medium text-neutral-700">{label}</span>
          )}
          {showPercentage && (
            <span className="text-sm font-medium text-neutral-700">
              {Math.round(normalizedValue)}%
            </span>
          )}
        </div>
      )}
      <div
        className={`w-full bg-neutral-200 rounded-full overflow-hidden ${sizeStyles[size]}`}
        role="progressbar"
        aria-valuenow={normalizedValue}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label || 'Progress'}
      >
        <div
          className={`${sizeStyles[size]} ${colorStyles[color]} rounded-full transition-all duration-300 ease-out`}
          style={{ width: `${normalizedValue}%` }}
        />
      </div>
    </div>
  );
}

export default ProgressBar;
