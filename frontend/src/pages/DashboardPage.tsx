import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import { useActiveProgram } from '@/hooks/usePrograms';
import { Button, Card, WorkoutCard, ProgressBar, StatCard, Spinner } from '@/components';

export default function DashboardPage() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const userProfile = useAuthStore((state) => state.userProfile);

  const { data: program, isLoading } = useActiveProgram();
  const activeProgramId = program?.program_id ?? null;

  const today = new Date();
  const dayOfWeek = today.toLocaleDateString('en-US', { weekday: 'long' });
  const dateStr = today.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });

  const getTodayWorkout = () => {
    if (!program?.weeks) return null;

    const weekKeys = Object.keys(program.weeks).sort((a, b) => Number(a) - Number(b));
    if (weekKeys.length === 0) return null;

    const currentWeekKey =
      program.current_week != null ? String(program.current_week) : weekKeys[0];
    const currentWeekWorkouts = program.weeks[currentWeekKey] ?? program.weeks[weekKeys[0]];
    if (!currentWeekWorkouts || currentWeekWorkouts.length === 0) return null;

    return currentWeekWorkouts[0];
  };

  const todayWorkout = getTodayWorkout();
  const displayWeekNumber = program?.current_week ?? 1;

  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-1">
            {dayOfWeek}, {dateStr}
          </p>
          <h1 className="display-md">
            Good {getTimeOfDay()}, {user?.first_name}
          </h1>
        </div>

        {/* Today's Workout Section */}
        {activeProgramId ? (
          isLoading ? (
            <Card padding="lg" className="mb-8 flex items-center justify-center gap-3">
              <Spinner size="sm" />
              <p className="body-md text-neutral-600 dark:text-neutral-400">Loading workout...</p>
            </Card>
          ) : todayWorkout ? (
            <div className="mb-8">
              <h2 className="sr-only">Today&apos;s workout</h2>
              <WorkoutCard
                workout={todayWorkout}
                programName={program?.name || 'Your Program'}
                weekNumber={displayWeekNumber}
                durationMin={userProfile?.workout_duration_min || 45}
                onStartClick={() =>
                  navigate(`/workouts/${todayWorkout.workout_id}?programId=${activeProgramId}`)
                }
              />
            </div>
          ) : (
            <Card
              padding="lg"
              className="mb-8 border-l-4 border-neutral-300 dark:border-neutral-600"
            >
              <p className="body-md text-neutral-600 dark:text-neutral-400">
                No workouts scheduled for today.
              </p>
            </Card>
          )
        ) : (
          <Card padding="lg" className="mb-8 border-l-4 border-secondary-600">
            <h2 className="heading-lg mb-2">Get Started</h2>
            <p className="body-md text-neutral-600 dark:text-neutral-400 mb-4">
              Create your first workout program to get started.
            </p>
            <Button variant="primary" onClick={() => navigate('/programs/new')}>
              Create Program
            </Button>
          </Card>
        )}

        {/* This Week Section */}
        {activeProgramId && program && (
          <Card className="mb-8">
            <h2 className="heading-lg mb-6">This Week</h2>
            <ProgressBar completed={0} total={5} showPercentage label="Weekly Progress" />
          </Card>
        )}

        {/* Stats Section */}
        <Card>
          <h2 className="heading-lg mb-6">Your Stats</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Workouts This Month" value="0" icon="🏋️" variant="primary" />
            <StatCard label="Current Streak" value="0 days" icon="🔥" variant="success" />
            <StatCard label="Personal Records" value="0" icon="🥇" variant="warning" />
            <StatCard label="Total Volume" value="0 lbs" icon="⚖️" variant="info" />
          </div>
        </Card>
      </div>
    </div>
  );
}

function getTimeOfDay(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'morning';
  if (hour < 18) return 'afternoon';
  return 'evening';
}
