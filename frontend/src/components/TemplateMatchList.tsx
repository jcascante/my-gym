import { TemplateMatchCard } from './TemplateMatchCard';
import type { TemplateMatch } from '@/types/program';

export function TemplateMatchList({
  matches,
  selectedId,
  onSelect,
}: {
  matches: TemplateMatch[];
  selectedId: number | null;
  onSelect: (m: TemplateMatch) => void;
}) {
  if (matches.length === 0)
    return <p className="text-gray-500">No matching templates for your setup.</p>;
  return (
    <div className="space-y-3">
      {matches.map((m) => (
        <TemplateMatchCard
          key={m.template_id}
          match={m}
          selected={m.template_id === selectedId}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}
