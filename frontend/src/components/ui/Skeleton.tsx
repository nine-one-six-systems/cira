/**
 * Skeleton Component
 *
 * Loading placeholder with animation.
 */

export interface SkeletonProps {
  /** Shape variant */
  variant?: 'text' | 'rect' | 'circle';
  /** Width (CSS value or number in px) */
  width?: string | number;
  /** Height (CSS value or number in px) */
  height?: string | number;
  /** Number of lines for text variant */
  lines?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Skeleton component for loading states.
 *
 * @example
 * ```tsx
 * // Single text line
 * <Skeleton variant="text" width="200px" />
 *
 * // Multiple text lines
 * <Skeleton variant="text" lines={3} />
 *
 * // Rectangle (e.g., for cards)
 * <Skeleton variant="rect" width="100%" height={200} />
 *
 * // Circle (e.g., for avatars)
 * <Skeleton variant="circle" width={48} height={48} />
 * ```
 */
export function Skeleton({
  variant = 'rect',
  width,
  height,
  lines = 1,
  className = '',
}: SkeletonProps) {
  const baseClass = 'animate-pulse bg-neutral-200';

  const getWidth = () => {
    if (width === undefined) {
      return variant === 'text' ? '100%' : '100%';
    }
    return typeof width === 'number' ? `${width}px` : width;
  };

  const getHeight = () => {
    if (height === undefined) {
      return variant === 'text' ? '1rem' : variant === 'circle' ? getWidth() : '100px';
    }
    return typeof height === 'number' ? `${height}px` : height;
  };

  if (variant === 'text' && lines > 1) {
    return (
      <div className={`flex flex-col gap-2 ${className}`}>
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            className={`${baseClass} rounded`}
            style={{
              width: index === lines - 1 ? '75%' : getWidth(),
              height: getHeight(),
            }}
            aria-hidden="true"
          />
        ))}
      </div>
    );
  }

  const variantStyles = {
    text: 'rounded',
    rect: 'rounded-md',
    circle: 'rounded-full',
  };

  return (
    <div
      className={`${baseClass} ${variantStyles[variant]} ${className}`}
      style={{
        width: getWidth(),
        height: getHeight(),
      }}
      role="status"
      aria-label="Loading"
      aria-hidden="true"
    />
  );
}

// Compound components for common patterns
export function SkeletonText({
  lines = 3,
  className = '',
}: {
  lines?: number;
  className?: string;
}) {
  return <Skeleton variant="text" lines={lines} className={className} />;
}

export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-neutral-200 p-4 ${className}`}>
      <Skeleton variant="text" width="60%" height={20} className="mb-3" />
      <Skeleton variant="text" lines={2} className="mb-3" />
      <div className="flex gap-2">
        <Skeleton variant="rect" width={80} height={32} />
        <Skeleton variant="rect" width={80} height={32} />
      </div>
    </div>
  );
}

export function SkeletonTable({
  rows = 5,
  columns = 4,
  className = '',
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) {
  return (
    <div className={`overflow-hidden rounded-lg border border-neutral-200 ${className}`}>
      {/* Header */}
      <div className="bg-neutral-50 px-4 py-3 flex gap-4">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} variant="text" width={100} height={16} />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="px-4 py-3 border-t border-neutral-200 flex gap-4">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} variant="text" width={colIndex === 0 ? 150 : 100} height={16} />
          ))}
        </div>
      ))}
    </div>
  );
}

export default Skeleton;
