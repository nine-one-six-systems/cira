/**
 * Toast Component and Context
 *
 * A notification system with toast messages.
 * The useToast hook is exported alongside ToastProvider as they are
 * tightly coupled - the hook requires the context from the provider.
 */
/* eslint-disable react-refresh/only-export-components */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

export interface ToastContextValue {
  toasts: Toast[];
  showToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

/**
 * Hook to access toast notifications.
 *
 * @example
 * ```tsx
 * const { showToast } = useToast();
 *
 * const handleSave = async () => {
 *   try {
 *     await saveData();
 *     showToast({ type: 'success', message: 'Saved successfully!' });
 *   } catch (error) {
 *     showToast({ type: 'error', message: 'Failed to save' });
 *   }
 * };
 * ```
 */
export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

const typeStyles = {
  success: {
    bg: 'bg-success-50 border-success-200',
    icon: 'text-success',
    iconPath: 'M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z',
  },
  error: {
    bg: 'bg-error-50 border-error-200',
    icon: 'text-error',
    iconPath: 'M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z',
  },
  warning: {
    bg: 'bg-warning-50 border-warning-200',
    icon: 'text-warning',
    iconPath: 'M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z',
  },
  info: {
    bg: 'bg-primary-50 border-primary-200',
    icon: 'text-primary',
    iconPath: 'M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z',
  },
};

interface ToastItemProps {
  toast: Toast;
  onRemove: (id: string) => void;
}

function ToastItem({ toast, onRemove }: ToastItemProps) {
  const styles = typeStyles[toast.type];

  return (
    <div
      role="alert"
      aria-live="polite"
      className={`
        flex items-center gap-3 px-4 py-3
        border rounded-lg shadow-lg
        transform transition-all duration-300
        ${styles.bg}
      `.trim()}
    >
      <svg
        className={`h-5 w-5 flex-shrink-0 ${styles.icon}`}
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        aria-hidden="true"
      >
        <path fillRule="evenodd" d={styles.iconPath} clipRule="evenodd" />
      </svg>
      <p className="text-sm text-neutral-700 flex-1">{toast.message}</p>
      <button
        type="button"
        onClick={() => onRemove(toast.id)}
        className="p-1 rounded text-neutral-400 hover:text-neutral-600 hover:bg-white/50 focus:outline-none focus:ring-2 focus:ring-primary-500"
        aria-label="Dismiss"
      >
        <svg
          className="h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
        </svg>
      </button>
    </div>
  );
}

interface ToastProviderProps {
  children: ReactNode;
}

/**
 * Provider for toast notifications.
 *
 * @example
 * ```tsx
 * // In App.tsx
 * <ToastProvider>
 *   <App />
 * </ToastProvider>
 * ```
 */
export function ToastProvider({ children }: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const showToast = useCallback(
    (toast: Omit<Toast, 'id'>) => {
      const id = Math.random().toString(36).substring(2, 9);
      const newToast: Toast = { ...toast, id };

      setToasts((prev) => [...prev, newToast]);

      // Auto-remove after duration
      const duration = toast.duration ?? 5000;
      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ toasts, showToast, removeToast }}>
      {children}
      {createPortal(
        <div
          aria-live="polite"
          aria-label="Notifications"
          className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm"
        >
          {toasts.map((toast) => (
            <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
          ))}
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  );
}

export default ToastProvider;
