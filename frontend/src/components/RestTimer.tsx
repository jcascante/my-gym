import { useEffect, useState } from 'react';

export interface RestTimerProps {
  restSeconds: number;
  onComplete?: () => void;
  autoStart?: boolean;
}

export function RestTimer({ restSeconds, onComplete, autoStart = false }: RestTimerProps) {
  const [secondsLeft, setSecondsLeft] = useState(restSeconds);
  const [isRunning, setIsRunning] = useState(autoStart);

  useEffect(() => {
    if (!isRunning || secondsLeft <= 0) {
      if (secondsLeft <= 0 && isRunning) {
        onComplete?.();
        setIsRunning(false);
      }
      return;
    }

    const interval = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          setIsRunning(false);
          onComplete?.();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isRunning, secondsLeft, onComplete]);

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  const percentage = (secondsLeft / restSeconds) * 100;

  return (
    <div className="space-y-4">
      <div className="text-center">
        <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-3">Rest Time</p>

        {/* Timer Display */}
        <div className="relative w-32 h-32 mx-auto mb-6">
          {/* Background Circle */}
          <svg className="absolute inset-0 w-full h-full" viewBox="0 0 120 120">
            <circle
              cx="60"
              cy="60"
              r="55"
              fill="none"
              stroke="currentColor"
              strokeWidth="8"
              className="text-neutral-200 dark:text-neutral-700"
            />
            {/* Progress Circle */}
            <circle
              cx="60"
              cy="60"
              r="55"
              fill="none"
              stroke="currentColor"
              strokeWidth="8"
              strokeDasharray={`${(percentage / 100) * 2 * Math.PI * 55} ${2 * Math.PI * 55}`}
              className="text-primary-600 dark:text-primary-400 transition-all duration-500"
              style={{ transform: 'rotate(-90deg)', transformOrigin: '60px 60px' }}
            />
          </svg>

          {/* Time Text */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <p className="text-4xl font-bold text-neutral-900 dark:text-neutral-100 font-variant-numeric tabular-nums">
                {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Control Button */}
      <button onClick={() => setIsRunning(!isRunning)} className="w-full btn btn-outline py-3">
        {isRunning ? 'Pause' : 'Resume'}
      </button>
    </div>
  );
}
