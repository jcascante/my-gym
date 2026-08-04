import { useNavigate, useParams } from 'react-router-dom';
import { useWorkoutForDate } from '@/hooks/useSession';
import { useActiveProgram } from '@/hooks/usePrograms';
import { toIsoDate, addDays, programDateBounds } from '@/hooks/useSchedule';
import { Alert, Button, Card, SessionStatusBadge, Spinner } from '@/components';
import { formatEffortDisplay } from '@/utils/effortDisplay';
import type { LoggedSet } from '@/types/session';
import type { EffortTarget } from '@/types/program';

export default function SessionDetailPage() {
  const navigate = useNavigate();
  const { date } = useParams<{ date: string }>();
  const currentDate = date ?? toIsoDate(new Date());

  const { data: program } = useActiveProgram();
  const { session, isLoading, error } = useWorkoutForDate(currentDate);

  if (isLoading) return <Spinner />;

  if (error) {
    return (
      <div className="min-h-dvh flex items-center justify-center px-4">
        <Card padding="lg" className="text-center">
          <p className="body-md text-error-600 mb-4">This workout could not be loaded.</p>
          <Button onClick={() => navigate('/schedule')}>Back to schedule</Button>
        </Card>
      </div>
    );
  }

  const today = toIsoDate(new Date());
  const startDate = program?.start_date ?? today;
  const bounds = programDateBounds(startDate, program?.duration_weeks ?? 1);
  const prevDisabled = currentDate <= bounds.start;
  const nextDisabled = currentDate >= bounds.end;

  const [y, m, d] = currentDate.split('-').map(Number);
  const dateLabel = new Date(y, m - 1, d).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });

  const isDone = session?.status === 'completed';
  const isFuture = session ? session.scheduled_date > today : false;
  const canStart = session ? !isDone && session.status !== 'skipped' : false;

  const setsFor = (workoutExerciseId: number): LoggedSet[] =>
    (session?.logged_sets ?? [])
      .filter((s) => s.workout_exercise_id === workoutExerciseId)
      .sort((a, b) => a.set_number - b.set_number);

  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 py-8 px-4 pb-28">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <Button
            variant="secondary"
            aria-label="Previous day"
            disabled={prevDisabled}
            onClick={() => navigate(`/workout/${addDays(currentDate, -1)}`)}
          >
            ←
          </Button>
          <div className="text-center">
            <p className="label-sm text-neutral-600 dark:text-neutral-400">
              {dateLabel}
              {session && ` • Week ${session.week}`}
            </p>
            {session && (
              <SessionStatusBadge
                status={session.status}
                scheduledDate={session.scheduled_date}
                today={today}
              />
            )}
          </div>
          <Button
            variant="secondary"
            aria-label="Next day"
            disabled={nextDisabled}
            onClick={() => navigate(`/workout/${addDays(currentDate, 1)}`)}
          >
            →
          </Button>
        </div>

        {!session ? (
          <Card padding="lg" className="text-center">
            <p className="body-md text-neutral-600 dark:text-neutral-400">Rest day</p>
          </Card>
        ) : (
          <>
            <div className="mb-6">
              <h1 className="display-md">{session.workout_name}</h1>
              <p className="body-sm text-neutral-600 dark:text-neutral-400 mt-1">
                {session.program_name} • {session.exercise_count} exercises • {session.duration_min}{' '}
                min
              </p>
            </div>

            {session.reactive_deload && session.deload_reason && (
              <Alert type="info" className="mb-4">
                {session.deload_reason}
              </Alert>
            )}

            <Card padding="md">
              <ol className="divide-y divide-neutral-200 dark:divide-neutral-700">
                {session.slots.map((slot, index) => {
                  const logged = setsFor(slot.workout_exercise_id);
                  return (
                    <li
                      key={slot.workout_exercise_id}
                      className="py-3 flex items-baseline justify-between gap-4"
                    >
                      <span className="body-md text-neutral-900 dark:text-neutral-50">
                        {index + 1}. <span>{slot.exercise_name}</span>
                      </span>
                      <span className="body-sm text-neutral-600 dark:text-neutral-400 text-right">
                        {logged.length > 0
                          ? logged
                              .map((s) => {
                                const effortTarget: EffortTarget | null = s.effort_method
                                  ? {
                                      method: s.effort_method as EffortTarget['method'],
                                      value: s.actual_rpe ?? undefined,
                                    }
                                  : null;
                                return formatEffortDisplay(
                                  1,
                                  s.actual_reps ?? 0,
                                  s.actual_weight ?? null,
                                  session.weight_unit,
                                  effortTarget,
                                );
                              })
                              .join('  ')
                          : formatEffortDisplay(
                              slot.sets,
                              slot.reps,
                              slot.load,
                              session.weight_unit,
                              slot.effort_target,
                            )}
                      </span>
                    </li>
                  );
                })}
              </ol>
            </Card>
          </>
        )}
      </div>

      {canStart && session && (
        <div className="fixed bottom-0 left-0 right-0 px-4 pb-4 bg-gradient-to-t from-neutral-50 dark:from-neutral-900">
          <div className="max-w-2xl mx-auto">
            <Button
              className="w-full"
              onClick={() => navigate(`/sessions/${session.session_id}/track`)}
            >
              {isFuture ? 'Start early' : 'Start workout'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
