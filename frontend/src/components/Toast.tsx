import { useEffect, useState } from 'react';

export interface ToastProps {
  message: string;
  duration?: number;
  icon?: string;
  variant?: 'success' | 'info' | 'warning' | 'error';
  onClose?: () => void;
}

const variantClasses = {
  success: 'bg-success-600 text-white',
  info: 'bg-primary-600 text-white',
  warning: 'bg-warning-600 text-white',
  error: 'bg-error-600 text-white',
};

export function Toast({
  message,
  duration = 2000,
  icon,
  variant = 'success',
  onClose,
}: ToastProps) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      onClose?.();
    }, duration);

    return () => clearInterval(timer);
  }, [duration, onClose]);

  if (!isVisible) return null;

  return (
    <div
      className={`fixed bottom-6 left-1/2 transform -translate-x-1/2 px-6 py-3 rounded-lg ${variantClasses[variant]} flex items-center gap-2 shadow-lg z-50 animate-slide-in-up`}
    >
      {icon && <span className="text-lg">{icon}</span>}
      <p className="body-sm font-medium">{message}</p>
    </div>
  );
}
