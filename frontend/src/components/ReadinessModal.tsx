import React, { useState } from 'react';

export interface ReadinessModalProps {
  title: string;
  onRate: (readiness: number) => Promise<void>;
  isOpen: boolean;
  onClose: () => void;
}

export const ReadinessModal: React.FC<ReadinessModalProps> = ({
  title,
  onRate,
  isOpen,
  onClose,
}) => {
  const [selected, setSelected] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleRate = async (readiness: number) => {
    setIsLoading(true);
    try {
      await onRate(readiness);
      onClose();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-neutral-800 p-6 rounded-lg shadow-lg max-w-sm">
        <h2 className="text-lg font-semibold mb-4 text-neutral-900 dark:text-neutral-100">
          {title}
        </h2>

        <div className="flex gap-2 mb-6">
          {[1, 2, 3, 4, 5].map((num) => (
            <button
              key={num}
              onClick={() => setSelected(num)}
              disabled={isLoading}
              className={`px-4 py-2 rounded border-2 font-medium transition-colors ${
                selected === num
                  ? 'border-primary-600 dark:border-primary-500 bg-primary-100 dark:bg-primary-900 text-primary-900 dark:text-primary-100'
                  : 'border-neutral-300 dark:border-neutral-600 hover:border-neutral-500 dark:hover:border-neutral-400 text-neutral-700 dark:text-neutral-300'
              } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {num}
            </button>
          ))}
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => onClose()}
            disabled={isLoading}
            className="flex-1 px-4 py-2 border border-neutral-300 dark:border-neutral-600 rounded text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            Skip
          </button>
          <button
            onClick={() => selected && handleRate(selected)}
            disabled={!selected || isLoading}
            className="flex-1 px-4 py-2 bg-primary-600 dark:bg-primary-700 text-white rounded hover:bg-primary-700 dark:hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  );
};
