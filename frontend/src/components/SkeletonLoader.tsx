export interface SkeletonLoaderProps {
  lines?: number;
  height?: 'sm' | 'md' | 'lg';
}

const heightClasses = {
  sm: 'h-4',
  md: 'h-6',
  lg: 'h-8',
};

export function SkeletonLoader({ lines = 3, height = 'md' }: SkeletonLoaderProps) {
  return (
    <div className="space-y-3">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`${heightClasses[height]} bg-neutral-200 dark:bg-neutral-700 rounded-lg animate-pulse`}
          style={{
            animation: `pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite`,
            animationDelay: `${i * 100}ms`,
          }}
        />
      ))}
    </div>
  );
}
