import { Link } from 'react-router-dom';
import { Card } from './Card';
import type { ProgramPreview } from '@/types/program';

export function ProgramListCard({ program }: { program: ProgramPreview }) {
  return (
    <Link to={`/programs/${program.program_id}`}>
      <Card className="hover:shadow-md dark:hover:shadow-lg transition-shadow">
        <h3 className="font-semibold text-lg text-neutral-900 dark:text-neutral-50">
          {program.name}
        </h3>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          {program.duration_weeks} week{program.duration_weeks !== 1 ? 's' : ''}
        </p>
        <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-2">
          Status: {program.status}
        </p>
      </Card>
    </Link>
  );
}
