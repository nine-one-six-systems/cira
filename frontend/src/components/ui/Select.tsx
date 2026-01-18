/**
 * Select Component
 *
 * A dropdown select component with label, error state, and accessibility features.
 */

import { type SelectHTMLAttributes, forwardRef, useId } from 'react';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'onChange'> {
  /** Select label text */
  label: string;
  /** Available options */
  options: SelectOption[];
  /** Current value */
  value?: string;
  /** Change handler */
  onChange?: (value: string) => void;
  /** Error message to display */
  error?: string;
  /** Placeholder text when no value selected */
  placeholder?: string;
}

/**
 * Select component with label, options, and accessibility features.
 *
 * @example
 * ```tsx
 * <Select
 *   label="Analysis Mode"
 *   options={[
 *     { value: 'quick', label: 'Quick' },
 *     { value: 'thorough', label: 'Thorough' },
 *   ]}
 *   value={mode}
 *   onChange={setMode}
 * />
 * ```
 */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      label,
      options,
      value,
      onChange,
      error,
      placeholder,
      disabled,
      required,
      className = '',
      id: providedId,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const id = providedId || generatedId;
    const errorId = `${id}-error`;

    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
      onChange?.(e.target.value);
    };

    const hasError = !!error;

    return (
      <div className={`flex flex-col gap-1 ${className}`}>
        <label
          htmlFor={id}
          className="block text-sm font-medium text-neutral-700"
        >
          {label}
          {required && <span className="text-error ml-1" aria-hidden="true">*</span>}
        </label>
        <div className="relative">
          <select
            ref={ref}
            id={id}
            value={value}
            onChange={handleChange}
            disabled={disabled}
            required={required}
            aria-invalid={hasError}
            aria-describedby={hasError ? errorId : undefined}
            className={`
              w-full px-3 py-2 pr-10
              border rounded-md
              text-neutral-900
              appearance-none
              bg-white
              transition-colors duration-150
              focus:outline-none focus:ring-2 focus:ring-offset-0
              disabled:bg-neutral-100 disabled:text-neutral-500 disabled:cursor-not-allowed
              ${hasError
                ? 'border-error focus:border-error focus:ring-error-500'
                : 'border-neutral-300 focus:border-primary focus:ring-primary-500'
              }
            `.trim().replace(/\s+/g, ' ')}
            {...props}
          >
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}
            {options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
            <svg
              className="h-4 w-4 text-neutral-400"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        </div>
        {hasError && (
          <p
            id={errorId}
            className="text-sm text-error"
            role="alert"
          >
            {error}
          </p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';

export default Select;
