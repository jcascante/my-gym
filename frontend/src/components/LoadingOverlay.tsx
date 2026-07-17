import { Spinner } from '@/components';

export interface LoadingOverlayProps {
  isVisible: boolean;
  message?: string;
}

export function LoadingOverlay({ isVisible, message = 'Loading...' }: LoadingOverlayProps) {
  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50 animate-fade-in">
      <div className="bg-white dark:bg-neutral-800 rounded-lg p-8 flex flex-col items-center gap-4 shadow-lg animate-scale-in">
        <Spinner size="lg" color="primary" />
        <p className="text-body-md text-neutral-700 dark:text-neutral-200">{message}</p>
      </div>
    </div>
  );
}
