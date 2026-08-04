import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import { useActiveProgram } from '@/hooks/usePrograms';
import { useTodaySession, useWeeklyProgress, useUserStats } from '@/hooks/useSchedule';
import { Button, Card, WorkoutCard, ProgressBar, StatCard, Spinner } from '@/components';

export default function DashboardPage() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);

  const { data: program, isLoading: programLoading } = useActiveProgram();
  const { session: todaySession, isLoading } = useTodaySession();
  const { completed: weekCompleted, total: weekTotal } = useWeeklyProgress(
    program?.start_date,
    program?.current_week,
  );
  const { stats } = useUserStats();

  if (programLoading) return <Spinner />;

  const today = new Date();
  const dayOfWeek = today.toLocaleDateString('en-US', { weekday: 'long' });
  const dateStr = today.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });

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
        {!program ? (
          <Card padding="lg" className="mb-8 border-l-4 border-secondary-600">
            <h2 className="heading-lg mb-2">Get Started</h2>
            <p className="body-md text-neutral-600 dark:text-neutral-400 mb-4">
              Create your first workout program to get started.
            </p>
            <Button variant="primary" onClick={() => navigate('/programs/new')}>
              Create Program
            </Button>
          </Card>
        ) : isLoading ? (
          <Card padding="lg" className="mb-8 flex items-center justify-center gap-3">
            <Spinner size="sm" />
            <p className="body-md text-neutral-600 dark:text-neutral-400">Loading workout...</p>
          </Card>
        ) : todaySession ? (
          <div className="mb-8">
            <h2 className="sr-only">Today&apos;s workout</h2>
            <WorkoutCard
              entry={todaySession}
              programName={program.name}
              onSelect={() => navigate(`/workout/${todaySession.scheduled_date}`)}
            />
          </div>
        ) : (
          <Card padding="lg" className="mb-8 border-l-4 border-neutral-300 dark:border-neutral-600">
            <p className="body-md text-neutral-600 dark:text-neutral-400 mb-4">
              Nothing scheduled today.
            </p>
            <Button variant="secondary" onClick={() => navigate('/schedule')}>
              View schedule →
            </Button>
          </Card>
        )}

        {/* This Week Section */}
        {program && (
          <Card className="mb-8">
            <h2 className="heading-lg mb-6">This Week</h2>
            <ProgressBar
              completed={weekCompleted}
              total={weekTotal}
              showPercentage
              label="Weekly Progress"
            />
          </Card>
        )}

        {/* Stats Section */}
        <Card>
          <h2 className="heading-lg mb-6">Your Stats</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Workouts This Month"
              value={stats?.workouts_this_month ?? 0}
              icon="🏋️"
              variant="primary"
            />
            <StatCard
              label="Current Streak"
              value={`${stats?.current_streak_days ?? 0} days`}
              icon="🔥"
              variant="success"
            />
            <StatCard
              label="Personal Records"
              value={stats?.personal_records ?? 0}
              icon="🥇"
              variant="warning"
            />
            <StatCard
              label="Total Volume"
              value={`${Math.round(stats?.total_volume ?? 0).toLocaleString()} ${stats?.weight_unit ?? 'lbs'}`}
              icon="⚖️"
              variant="info"
            />
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
