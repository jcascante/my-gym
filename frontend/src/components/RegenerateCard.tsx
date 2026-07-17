import { Button } from '@/components';

export interface RegenerateCardProps {
  onRegenerate?: () => void;
}

export function RegenerateCard({ onRegenerate }: RegenerateCardProps) {
  return (
    <div className="card rounded-lg p-6 border-2 border-secondary-600 bg-secondary-50 dark:bg-secondary-900/10">
      <div className="text-center space-y-4">
        <div>
          <h3 className="heading-lg text-secondary-900 dark:text-secondary-100 mb-2">
            Generate New Program
          </h3>
          <p className="body-sm text-secondary-700 dark:text-secondary-300">
            Create a personalized program based on your fitness goals and experience level
          </p>
        </div>

        <Button className="w-full btn btn-secondary" onClick={onRegenerate}>
          Create Program
        </Button>
      </div>
    </div>
  );
}
