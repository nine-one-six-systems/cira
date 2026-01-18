/**
 * Input Component
 *
 * A form input component with label, error state, and accessibility features.
 */

import { type InputHTMLAttributes, forwardRef, useId } from 'react';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  /** Input label text */
  label: string;
  /** Error message to display */
  error?: string;
  /** Current value */
  value?: string;
  /** Change handler */
  onChange?: (value: string) => void;
  /** Helper text shown below input */
  helperText?: string;
}

/**
 * Input component with label, error handling, and accessibility features.
 *
 * @example
 * ```tsx
 * <Input
 *   label="Company Name"
 *   placeholder="Enter company name"
 *   value={name}
 *   onChange={setName}
 *   error={errors.name}
 * />
 * ```
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      value,
      onChange,
      helperText,
      type = 'text',
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
    const helperId = `${id}-helper`;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
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
        <input
          ref={ref}
          id={id}
          type={type}
          value={value}
          onChange={handleChange}
          disabled={disabled}
          required={required}
          aria-invalid={hasError}
          aria-describedby={
            hasError ? errorId : helperText ? helperId : undefined
          }
          className={`
            w-full px-3 py-2
            border rounded-md
            text-neutral-900 placeholder:text-neutral-400
            transition-colors duration-150
            focus:outline-none focus:ring-2 focus:ring-offset-0
            disabled:bg-neutral-100 disabled:text-neutral-500 disabled:cursor-not-allowed
            ${hasError
              ? 'border-error focus:border-error focus:ring-error-500'
              : 'border-neutral-300 focus:border-primary focus:ring-primary-500'
            }
          `.trim().replace(/\s+/g, ' ')}
          {...props}
        />
        {hasError && (
          <p
            id={errorId}
            className="text-sm text-error"
            role="alert"
          >
            {error}
          </p>
        )}
        {!hasError && helperText && (
          <p
            id={helperId}
            className="text-sm text-neutral-500"
          >
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;
