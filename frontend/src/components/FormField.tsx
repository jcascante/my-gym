import { FC, InputHTMLAttributes, ReactNode, useState } from 'react';

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
  required?: boolean;
  children?: ReactNode;
}

export const FormField: FC<FormFieldProps> = ({
  label,
  error,
  hint,
  required,
  className = '',
  id,
  type,
  ...props
}) => {
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
  const [revealPassword, setRevealPassword] = useState(false);
  const isPassword = type === 'password';

  return (
    <div className="input-group">
      <label htmlFor={inputId} className="input-label">
        {label}
        {required && <span className="text-error-600 ml-1">*</span>}
      </label>
      <div className={isPassword ? 'relative' : undefined}>
        <input
          id={inputId}
          type={isPassword && revealPassword ? 'text' : type}
          className={`${isPassword ? 'pr-10' : ''} ${error ? 'ring-2 ring-error-500 dark:ring-error-400' : ''} ${className}`}
          {...props}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setRevealPassword((prev) => !prev)}
            className="absolute inset-y-0 right-0 flex items-center px-3 text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
            aria-label={revealPassword ? 'Hide password' : 'Show password'}
            tabIndex={-1}
          >
            {revealPassword ? (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"
                />
              </svg>
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
            )}
          </button>
        )}
      </div>
      {hint && !error && (
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{hint}</p>
      )}
      {error && <p className="input-error">{error}</p>}
    </div>
  );
};
