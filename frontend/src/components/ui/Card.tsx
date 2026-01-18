/**
 * Card Component
 *
 * A container component with optional title and actions.
 */

export interface CardProps {
  /** Card title */
  title?: string;
  /** Card content */
  children: React.ReactNode;
  /** Action buttons/elements */
  actions?: React.ReactNode;
  /** Padding size */
  padding?: 'none' | 'sm' | 'md' | 'lg';
  /** Additional CSS classes */
  className?: string;
}

const paddingStyles = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
};

/**
 * Card component for grouping related content.
 *
 * @example
 * ```tsx
 * <Card title="Company Details" padding="lg">
 *   <p>Company information goes here</p>
 * </Card>
 *
 * <Card
 *   title="Analysis Results"
 *   actions={<Button variant="secondary">Export</Button>}
 * >
 *   <AnalysisSummary data={analysis} />
 * </Card>
 * ```
 */
export function Card({
  title,
  children,
  actions,
  padding = 'md',
  className = '',
}: CardProps) {
  return (
    <div
      className={`
        bg-white rounded-lg shadow-sm border border-neutral-200
        ${className}
      `.trim()}
    >
      {(title || actions) && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
          {title && (
            <h3 className="text-lg font-semibold text-neutral-900">{title}</h3>
          )}
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={paddingStyles[padding]}>{children}</div>
    </div>
  );
}

export default Card;
