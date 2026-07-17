import { Link } from 'react-router-dom';
import { Card } from './Card';
import type { ProgramPreview } from '@/types/program';

export function ProgramListCard({ program }: { program: ProgramPreview }) {
  return (
    <Link to={`/programs/${program.program_id}`}>
      <Card className="hover:shadow-md transition-shadow">
        <h3 className="font-semibold text-lg">{program.name}</h3>
        <p className="text-sm text-gray-500">
          {program.duration_weeks} week{program.duration_weeks !== 1 ? 's' : ''}
        </p>
        <p className="text-xs text-gray-400 mt-2">Status: {program.status}</p>
      </Card>
    </Link>
  );
}
