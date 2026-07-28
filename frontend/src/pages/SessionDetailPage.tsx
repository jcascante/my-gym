import { useNavigate, useParams } from 'react-router-dom';
import { useSession } from '@/hooks/useSession';
import { toIsoDate } from '@/hooks/useSchedule';
import { Alert, Button, Card, SessionStatusBadge, Spinner } from '@/components';
import type { LoggedSet } from '@/types/session';

export default function SessionDetailPage() {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId?: string }>();
  const id = sessionId ? Number(sessionId) : null;
  const { data: session, isLoading, error } = useSession(id);

  if (isLoading) return <Spinner />;

  if (error || !session) {
    return (
      <div className="min-h-dvh flex items-center justify-center px-4">
        <Card padding="lg" className="text-center">
          <p className="body-md text-error-600 mb-4">This session could not be loaded.</p>
          <Button onClick={() => navigate('/schedule')}>Back to schedule</Button>
        </Card>
      </div>
    );
  }

  const today = toIsoDate(new Date());
  const isDone = session.status === 'completed';
  const isFuture = session.scheduled_date > today;
  const canStart = !isDone && session.status !== 'skipped';

  const [y, m, d] = session.scheduled_date.split('-').map(Number);
  const dateLabel = new Date(y, m - 1, d).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });

  const setsFor = (workoutExerciseId: number): LoggedSet[] =>
    session.logged_sets
      .filter((s) => s.workout_exercise_id === workoutExerciseId)
      .sort((a, b) => a.set_number - b.set_number);

  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 py-8 px-4 pb-28">
      <div className="max-w-2xl mx-auto">
        <Button variant="secondary" className="mb-4" onClick={() => navigate('/schedule')}>
          ← Schedule
        </Button>

        <div className="mb-6">
          <div className="flex items-center gap-3 mb-1">
            <p className="label-sm text-neutral-600 dark:text-neutral-400">
              {dateLabel} • Week {session.week}
            </p>
            <SessionStatusBadge
              status={session.status}
              scheduledDate={session.scheduled_date}
              today={today}
            />
          </div>
          <h1 className="display-md">{session.workout_name}</h1>
          <p className="body-sm text-neutral-600 dark:text-neutral-400 mt-1">
            {session.program_name} • {session.exercise_count} exercises • {session.duration_min} min
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
                          .map((s) => `${s.actual_weight ?? '—'} × ${s.actual_reps ?? '—'}`)
                          .join('  ')
                      : `${slot.sets} × ${slot.reps}${slot.load ? ` @ ${slot.load}` : ''}`}
                  </span>
                </li>
              );
            })}
          </ol>
        </Card>
      </div>

      {canStart && (
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
