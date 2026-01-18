/**
 * Badge Component
 *
 * A small label for status indicators or counts.
 */

export type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info';

export interface BadgeProps {
  /** Badge visual variant */
  variant?: BadgeVariant;
  /** Badge content */
  children: React.ReactNode;
  /** Size variant */
  size?: 'sm' | 'md';
  /** Additional CSS classes */
  className?: string;
}

const variantStyles = {
  default: 'bg-neutral-100 text-neutral-700',
  success: 'bg-success-100 text-success-800',
  warning: 'bg-warning-100 text-warning-800',
  error: 'bg-error-100 text-error-800',
  info: 'bg-primary-100 text-primary-800',
};

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
};

/**
 * Badge component for status indicators.
 *
 * @example
 * ```tsx
 * <Badge variant="success">Completed</Badge>
 * <Badge variant="warning">In Progress</Badge>
 * <Badge variant="error">Failed</Badge>
 * ```
 */
export function Badge({
  variant = 'default',
  children,
  size = 'md',
  className = '',
}: BadgeProps) {
  return (
    <span
      className={`
        inline-flex items-center
        font-medium rounded-full
        ${variantStyles[variant]}
        ${sizeStyles[size]}
        ${className}
      `.trim().replace(/\s+/g, ' ')}
    >
      {children}
    </span>
  );
}

export default Badge;
