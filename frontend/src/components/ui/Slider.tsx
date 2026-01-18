/**
 * Slider Component
 *
 * A range input with label and value display.
 */

import { type InputHTMLAttributes, forwardRef, useId } from 'react';

export interface SliderProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'type'> {
  /** Slider label text */
  label: string;
  /** Current value */
  value: number;
  /** Change handler */
  onChange: (value: number) => void;
  /** Minimum value */
  min?: number;
  /** Maximum value */
  max?: number;
  /** Step increment */
  step?: number;
  /** Whether to show current value */
  showValue?: boolean;
  /** Unit label (e.g., "pages", "minutes") */
  unit?: string;
  /** Helper text */
  helperText?: string;
}

/**
 * Slider component for selecting numeric values within a range.
 *
 * @example
 * ```tsx
 * <Slider
 *   label="Max Pages"
 *   value={maxPages}
 *   onChange={setMaxPages}
 *   min={10}
 *   max={500}
 *   step={10}
 *   showValue
 *   unit="pages"
 * />
 * ```
 */
export const Slider = forwardRef<HTMLInputElement, SliderProps>(
  (
    {
      label,
      value,
      onChange,
      min = 0,
      max = 100,
      step = 1,
      showValue = true,
      unit,
      helperText,
      disabled,
      className = '',
      id: providedId,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const id = providedId || generatedId;
    const helperId = `${id}-helper`;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange(Number(e.target.value));
    };

    // Calculate fill percentage for custom styling
    const fillPercentage = ((value - min) / (max - min)) * 100;

    return (
      <div className={`flex flex-col gap-2 ${className}`}>
        <div className="flex justify-between items-center">
          <label
            htmlFor={id}
            className="block text-sm font-medium text-neutral-700"
          >
            {label}
          </label>
          {showValue && (
            <span className="text-sm font-medium text-neutral-900">
              {value}
              {unit && <span className="text-neutral-500 ml-1">{unit}</span>}
            </span>
          )}
        </div>
        <div className="relative">
          <input
            ref={ref}
            id={id}
            type="range"
            value={value}
            onChange={handleChange}
            min={min}
            max={max}
            step={step}
            disabled={disabled}
            aria-describedby={helperText ? helperId : undefined}
            className={`
              w-full h-2 rounded-full appearance-none cursor-pointer
              disabled:opacity-50 disabled:cursor-not-allowed
              focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
            `.trim()}
            style={{
              background: `linear-gradient(to right, #2563eb ${fillPercentage}%, #e5e7eb ${fillPercentage}%)`,
            }}
            {...props}
          />
        </div>
        <div className="flex justify-between text-xs text-neutral-500">
          <span>{min}{unit && ` ${unit}`}</span>
          <span>{max}{unit && ` ${unit}`}</span>
        </div>
        {helperText && (
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

Slider.displayName = 'Slider';

export default Slider;
