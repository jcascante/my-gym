import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import { useProgramPreview } from '@/hooks/usePrograms';
import { Card, WorkoutCard, ProgressBar, StatCard } from '@/components';

export default function DashboardPage() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const userProfile = useAuthStore((state) => state.userProfile);
  const [activeProgramId] = useState<number | null>(null);

  const { data: program, isLoading } = useProgramPreview(activeProgramId);

  const today = new Date();
  const dayOfWeek = today.toLocaleDateString('en-US', { weekday: 'long' });
  const dateStr = today.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });

  const getTodayWorkout = () => {
    if (!program?.weeks) return null;

    const weekKeys = Object.keys(program.weeks).sort();
    if (weekKeys.length === 0) return null;

    const firstWeekWorkouts = program.weeks[weekKeys[0]];
    if (firstWeekWorkouts.length === 0) return null;

    return firstWeekWorkouts[0];
  };

  const todayWorkout = getTodayWorkout();

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900 py-8 px-4">
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
            <div className="card card-elevated p-8 text-center">
              <p className="text-neutral-600 dark:text-neutral-400">Loading workout...</p>
            </div>
          ) : todayWorkout ? (
            <div className="mb-8">
              <WorkoutCard
                workout={todayWorkout}
                programName={program?.name || 'Your Program'}
                weekNumber={1}
                durationMin={userProfile?.workout_duration_min || 45}
                onStartClick={() => navigate(`/workouts/${todayWorkout.workout_id}/track`)}
              />
            </div>
          ) : (
            <div className="card card-elevated border-l-4 border-neutral-300 dark:border-neutral-600 mb-8 p-6">
              <p className="body-md text-neutral-600 dark:text-neutral-400">
                No workouts scheduled for today.
              </p>
            </div>
          )
        ) : (
          <div className="card card-elevated border-l-4 border-secondary-600 mb-8 p-6">
            <h2 className="heading-lg mb-2">Get Started</h2>
            <p className="body-md text-neutral-600 dark:text-neutral-400 mb-4">
              Create your first workout program to get started.
            </p>
            <button onClick={() => navigate('/programs/new')} className="btn btn-secondary">
              Create Program
            </button>
          </div>
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
