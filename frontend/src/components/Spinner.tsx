import { FC, SVGProps } from 'react';

interface SpinnerProps extends SVGProps<SVGSVGElement> {
  size?: 'sm' | 'md' | 'lg';
  fullscreen?: boolean;
}

const sizeStyles = {
  sm: 'w-4 h-4',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
};

export const Spinner: FC<SpinnerProps> = ({
  size = 'md',
  fullscreen = false,
  className = '',
  ...props
}) => {
  const spinner = (
    <svg
      className={`animate-spin ${sizeStyles[size]} ${className}`}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      {...props}
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );

  if (fullscreen) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
        {spinner}
      </div>
    );
  }

  return spinner;
};
