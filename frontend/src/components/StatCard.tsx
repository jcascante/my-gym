export interface StatCardProps {
  label: string;
  value: string | number;
  icon?: string;
  variant?: 'primary' | 'success' | 'warning' | 'info';
}

const variantClasses = {
  primary: 'bg-primary-50 dark:bg-primary-900/30 text-primary-900 dark:text-primary-100',
  success: 'bg-success-50 dark:bg-success-900/30 text-success-900 dark:text-success-100',
  warning: 'bg-warning-50 dark:bg-warning-900/30 text-warning-900 dark:text-warning-100',
  info: 'bg-secondary-50 dark:bg-secondary-900/30 text-secondary-900 dark:text-secondary-100',
};

const labelClasses = {
  primary: 'text-primary-600 dark:text-primary-400',
  success: 'text-success-600 dark:text-success-400',
  warning: 'text-warning-600 dark:text-warning-400',
  info: 'text-secondary-600 dark:text-secondary-400',
};

export function StatCard({ label, value, icon, variant = 'primary' }: StatCardProps) {
  return (
    <div className={`rounded-lg p-6 ${variantClasses[variant]}`}>
      <div className="flex items-center gap-2 mb-2">
        {icon && <span>{icon}</span>}
        <p className={`label-sm ${labelClasses[variant]}`}>{label}</p>
      </div>
      <p className="text-display-md font-bold">{value}</p>
    </div>
  );
}
