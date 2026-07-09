import { FC, InputHTMLAttributes, ReactNode } from 'react'

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
  hint?: string
  required?: boolean
  children?: ReactNode
}

export const FormField: FC<FormFieldProps> = ({
  label,
  error,
  hint,
  required,
  className = '',
  id,
  ...props
}) => {
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`

  return (
    <div className="input-group">
      <label htmlFor={inputId} className="input-label">
        {label}
        {required && <span className="text-error-600 ml-1">*</span>}
      </label>
      <input
        id={inputId}
        className={`${error ? 'ring-2 ring-error-500 dark:ring-error-400' : ''} ${className}`}
        {...props}
      />
      {hint && !error && <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{hint}</p>}
      {error && <p className="input-error">{error}</p>}
    </div>
  )
}
