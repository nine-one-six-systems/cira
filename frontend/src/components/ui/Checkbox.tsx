/**
 * Checkbox Component
 *
 * A checkbox input with label and accessibility features.
 */

import { type InputHTMLAttributes, forwardRef, useId } from 'react';

export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'type'> {
  /** Checkbox label text */
  label: string;
  /** Whether the checkbox is checked */
  checked?: boolean;
  /** Change handler */
  onChange?: (checked: boolean) => void;
  /** Optional description text */
  description?: string;
}

/**
 * Checkbox component with label and accessibility features.
 *
 * @example
 * ```tsx
 * <Checkbox
 *   label="Follow LinkedIn profiles"
 *   checked={followLinkedIn}
 *   onChange={setFollowLinkedIn}
 *   description="Include LinkedIn company pages in analysis"
 * />
 * ```
 */
export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  (
    {
      label,
      checked,
      onChange,
      description,
      disabled,
      className = '',
      id: providedId,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const id = providedId || generatedId;
    const descriptionId = `${id}-description`;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange?.(e.target.checked);
    };

    return (
      <div className={`flex items-start gap-3 ${className}`}>
        <div className="flex items-center h-5">
          <input
            ref={ref}
            id={id}
            type="checkbox"
            checked={checked}
            onChange={handleChange}
            disabled={disabled}
            aria-describedby={description ? descriptionId : undefined}
            className={`
              h-4 w-4
              rounded
              border-neutral-300
              text-primary
              focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
              disabled:opacity-50 disabled:cursor-not-allowed
            `.trim().replace(/\s+/g, ' ')}
            {...props}
          />
        </div>
        <div className="flex flex-col">
          <label
            htmlFor={id}
            className={`
              text-sm font-medium
              ${disabled ? 'text-neutral-400 cursor-not-allowed' : 'text-neutral-700 cursor-pointer'}
            `.trim()}
          >
            {label}
          </label>
          {description && (
            <p
              id={descriptionId}
              className="text-sm text-neutral-500"
            >
              {description}
            </p>
          )}
        </div>
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';

export default Checkbox;
