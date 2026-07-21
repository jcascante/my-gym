import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Spinner, WeekTabs, SlotRow, CheckInWidget } from '@/components';
import { useProgramPreview } from '@/hooks/usePrograms';

export default function ProgramPreviewPage() {
  const { id } = useParams();
  const programId = Number(id);
  const { data, isLoading } = useProgramPreview(programId);
  const [active, setActive] = useState(1);
  if (isLoading || !data) return <Spinner />;
  const weeks = Object.keys(data.weeks)
    .map(Number)
    .sort((a, b) => a - b);
  return (
    <div className="max-w-2xl mx-auto p-4 space-y-4">
      <h1 className="text-2xl font-bold mb-4">{data.name}</h1>
      {data.status === 'active' && <CheckInWidget programId={programId} />}
      <WeekTabs weeks={weeks} active={active} onSelect={setActive} />
      <div className="space-y-4">
        {(data.weeks[String(active)] ?? []).map((w) => (
          <Card key={w.workout_id}>
            <h3 className="font-semibold mb-2">{w.name}</h3>
            {w.slots.map((s) => (
              <SlotRow key={s.workout_exercise_id} slot={s} readOnly={true} />
            ))}
          </Card>
        ))}
      </div>
    </div>
  );
}
