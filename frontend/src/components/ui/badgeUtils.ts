/**
 * Badge utility functions
 *
 * Separated from Badge.tsx for Fast Refresh compatibility.
 */

import type { BadgeVariant } from './Badge';

/**
 * Maps company status to badge variant.
 *
 * @example
 * ```tsx
 * const variant = getStatusBadgeVariant('completed'); // returns 'success'
 * <Badge variant={variant}>Completed</Badge>
 * ```
 */
export function getStatusBadgeVariant(status: string): BadgeVariant {
  switch (status) {
    case 'completed':
      return 'success';
    case 'in_progress':
      return 'warning';
    case 'failed':
      return 'error';
    case 'paused':
      return 'info';
    case 'pending':
    default:
      return 'default';
  }
}
