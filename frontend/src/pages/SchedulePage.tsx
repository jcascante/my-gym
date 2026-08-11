import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useActiveProgram } from '@/hooks/usePrograms';
import { useSchedule, weekRange, toIsoDate } from '@/hooks/useSchedule';
import { Button, Card, ScheduleRow, Spinner } from '@/components';

export default function SchedulePage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: program, isLoading: programLoading } = useActiveProgram();

  const initialWeek = Number(searchParams.get('week')) || program?.current_week || 1;
  const [week, setWeek] = useState(initialWeek);

  // Keeps `week` in sync when `?week=` changes from outside goToWeek (e.g. browser
  // Back/Forward), which react-router's searchParams reflect but this component's
  // own state otherwise wouldn't pick up.
  useEffect(() => {
    setWeek(Number(searchParams.get('week')) || program?.current_week || 1);
  }, [searchParams, program?.current_week]);

  const startDate = program?.start_date ?? toIsoDate(new Date());
  const { start, end } = weekRange(startDate, week);
  const { data: sessions, isLoading } = useSchedule(start, end);

  const today = toIsoDate(new Date());
  const durationWeeks = program?.duration_weeks ?? 1;

  const goToWeek = (next: number) => {
    setWeek(next);
    setSearchParams({ week: String(next) });
  };

  if (programLoading) return <Spinner />;

  if (!program) {
    return (
      <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 py-8 px-4">
        <div className="max-w-2xl mx-auto">
          <Card padding="lg">
            <h1 className="heading-lg mb-2">No active program</h1>
            <p className="body-md text-neutral-600 dark:text-neutral-400 mb-4">
              Create a program to see your training schedule.
            </p>
            <Button variant="primary" onClick={() => navigate('/programs/new')}>
              Create Program
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="display-md mb-6">Schedule</h1>

        <Card padding="md">
          <div className="flex items-center justify-between mb-4">
            <Button
              variant="secondary"
              aria-label="Previous week"
              disabled={week <= 1}
              onClick={() => goToWeek(week - 1)}
            >
              ←
            </Button>
            <p className="heading-md">
              Week {week} of {durationWeeks}
            </p>
            <Button
              variant="secondary"
              aria-label="Next week"
              disabled={week >= durationWeeks}
              onClick={() => goToWeek(week + 1)}
            >
              →
            </Button>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner size="sm" />
            </div>
          ) : sessions && sessions.length > 0 ? (
            <div className="divide-y divide-neutral-200 dark:divide-neutral-700">
              {sessions.map((entry) => (
                <ScheduleRow
                  key={entry.session_id}
                  entry={entry}
                  today={today}
                  onSelect={(date) => navigate(`/workout/${date}`)}
                />
              ))}
            </div>
          ) : (
            <p className="body-md text-neutral-600 dark:text-neutral-400 py-8 text-center">
              No sessions in this week. Programs activated before scheduling was added need to be
              re-activated to generate their schedule.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}
