import { useState, useEffect } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  SetLogger,
  CompletedSets,
  Toast,
  Button,
  Card,
  ReadinessModal,
  Spinner,
} from '@/components';
import type { EffortMethod } from '@/types/programCreation';
import { useAuthStore } from '@/store/auth';
import { useWorkoutDetails } from '@/hooks/useWorkoutDetails';
import { logSetLog } from '@/api/logging';
import { postWorkoutReadiness } from '@/api/workouts';

interface LoggedSet {
  setNumber: number;
  weight?: number;
  reps?: number;
  effort?: number;
  effort_method?: EffortMethod;
  timestamp: Date;
}

interface ExerciseProgress {
  workout_exercise_id: number;
  exercise_name: string;
  sets: number;
  reps: number;
  load: number | null;
  rest_seconds: number;
  note: string | null;
  completedSets: LoggedSet[];
}

export default function WorkoutTrackingPage() {
  const navigate = useNavigate();
  const { workoutId } = useParams<{ workoutId?: string }>();
  const [searchParams] = useSearchParams();
  const { userProfile } = useAuthStore();

  const programId = searchParams.get('programId') ? Number(searchParams.get('programId')) : null;
  const workoutIdNum = workoutId ? Number(workoutId) : null;

  const {
    data: workoutDetails,
    isLoading,
    error,
  } = useWorkoutDetails(workoutIdNum ?? 0, programId);

  const rawEffortMethod = userProfile?.effort_method;
  const effortMethod: EffortMethod =
    rawEffortMethod === 'rpe' ||
    rawEffortMethod === 'rir' ||
    rawEffortMethod === 'borg' ||
    rawEffortMethod === 'percent_1rm'
      ? rawEffortMethod
      : 'rpe';

  const [currentExerciseIndex, setCurrentExerciseIndex] = useState(0);
  const [exercises, setExercises] = useState<ExerciseProgress[]>([]);
  const [toast, setToast] = useState<{ message: string; icon?: string } | null>(null);
  const [readinessOpen, setReadinessOpen] = useState<'pre' | 'post' | null>(null);

  // Initialize exercises from workout details
  useEffect(() => {
    if (workoutDetails?.slots) {
      const exs = workoutDetails.slots.map((slot) => ({
        workout_exercise_id: slot.workout_exercise_id,
        exercise_name: slot.exercise_name,
        sets: slot.sets,
        reps: slot.reps,
        load: slot.load,
        rest_seconds: slot.rest_seconds,
        note: slot.note,
        completedSets: [],
      }));
      setExercises(exs);
      setCurrentExerciseIndex(0);
    }
  }, [workoutDetails]);

  if (isLoading) return <Spinner />;
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Failed to load workout: {error.message}</p>
          <Button onClick={() => navigate(-1)}>Go Back</Button>
        </div>
      </div>
    );
  }

  if (!workoutDetails || exercises.length === 0) {
    return <Spinner />;
  }

  const currentExercise = exercises[currentExerciseIndex];
  const completedSetsCount = currentExercise.completedSets.length;
  const totalSets = currentExercise.sets;
  const isExerciseComplete = completedSetsCount >= totalSets;
  const repsRemaining = totalSets - completedSetsCount;
  const totalExercises = exercises.length;
  const completedExercises = exercises.filter((ex) => ex.completedSets.length >= ex.sets).length;
  const progressPercentage = (completedExercises / totalExercises) * 100;

  const handleLogSet = async (data: {
    weight?: number;
    reps?: number;
    effort: number;
    effort_method: EffortMethod;
  }) => {
    if (!workoutIdNum) {
      console.error('Workout ID is missing');
      return;
    }

    try {
      await logSetLog(
        workoutIdNum,
        currentExercise.workout_exercise_id,
        completedSetsCount + 1,
        data.weight,
        data.reps,
        data.effort,
        effortMethod,
      );

      const newSet: LoggedSet = {
        setNumber: completedSetsCount + 1,
        weight: data.weight,
        reps: data.reps,
        effort: data.effort,
        effort_method: data.effort_method,
        timestamp: new Date(),
      };

      const newExercises = [...exercises];
      newExercises[currentExerciseIndex].completedSets.push(newSet);
      setExercises(newExercises);

      const isNowComplete = newExercises[currentExerciseIndex].completedSets.length >= totalSets;
      if (isNowComplete) {
        setToast({
          message: `Great! ${currentExercise.exercise_name} complete! 💪`,
          icon: '🎉',
        });

        // Auto-advance to next exercise after 1.5s
        if (currentExerciseIndex < exercises.length - 1) {
          const nextIndex = currentExerciseIndex + 1;
          const nextExerciseName = newExercises[nextIndex].exercise_name;
          setTimeout(() => {
            setCurrentExerciseIndex(nextIndex);
            setToast({
              message: `Next up: ${nextExerciseName}`,
              icon: '▶️',
            });
          }, 1500);
        }
      } else {
        const remaining = totalSets - newExercises[currentExerciseIndex].completedSets.length;
        setToast({
          message: `Set logged! ${remaining} more to go! 💪`,
          icon: '✓',
        });
      }
    } catch (err) {
      console.error('Failed to log set:', err);
      setToast({
        message: 'Failed to log set. Please try again.',
        icon: '⚠️',
      });
    }
  };

  const handleCompleteWorkout = () => {
    setReadinessOpen('post');
  };

  const handleSubmitReadiness = async (readiness: number) => {
    if (!workoutIdNum) {
      console.error('Workout ID is missing');
      return;
    }

    try {
      await postWorkoutReadiness(workoutIdNum, readiness, readinessOpen === 'pre' ? 'pre' : 'post');
      setToast({
        message: `Readiness recorded: ${readiness}/5`,
        icon: '✓',
      });

      if (readinessOpen === 'post') {
        navigate('/dashboard');
      }
    } catch (err) {
      console.error('Failed to record readiness:', err);
      setToast({
        message: 'Failed to record readiness. Please try again.',
        icon: '⚠️',
      });
    } finally {
      setReadinessOpen(null);
    }
  };

  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 flex flex-col">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-neutral-50 dark:bg-neutral-900">
        <div className="max-w-2xl mx-auto bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-sm mt-4 p-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs text-neutral-600 dark:text-neutral-400">
                Exercise {currentExerciseIndex + 1} of {totalExercises}
              </p>
              <h1 className="text-2xl font-bold">{currentExercise.exercise_name}</h1>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setReadinessOpen('pre')}
                className="px-3 py-1 text-sm bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 rounded hover:bg-primary-200 dark:hover:bg-primary-800 transition-colors"
              >
                Check In
              </button>
              <button
                onClick={() => navigate(-1)}
                className="text-2xl text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs text-neutral-600 dark:text-neutral-400">
                {completedExercises}/{totalExercises} exercises
              </p>
              <p className="text-xs text-neutral-600 dark:text-neutral-400">
                {Math.round(progressPercentage)}%
              </p>
            </div>
            <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2">
              <div
                className="bg-primary-600 h-full rounded-full transition-all duration-500"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto p-4 pb-24">
          {/* Set Logger */}
          <Card className="mb-8">
            <SetLogger effort_method={effortMethod} onSetLogged={handleLogSet} />
          </Card>

          {/* Completed Sets */}
          {completedSetsCount > 0 && (
            <Card className="mb-8">
              <CompletedSets
                sets={currentExercise.completedSets
                  .filter((s) => s.weight !== undefined && s.reps !== undefined)
                  .map((s) => ({
                    setNumber: s.setNumber,
                    weight: s.weight || 0,
                    reps: s.reps || 0,
                  }))}
              />
            </Card>
          )}

          {/* Exercise Info */}
          <Card className="mb-8">
            <div className="space-y-3">
              <div>
                <p className="text-xs text-neutral-600 dark:text-neutral-400">Target</p>
                <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  {currentExercise.load ?? '—'} × {currentExercise.reps}
                </p>
              </div>
              <div>
                <p className="text-xs text-neutral-600 dark:text-neutral-400">Rest Time</p>
                <p className="text-3xl font-bold text-neutral-900 dark:text-neutral-100">
                  {Math.floor(currentExercise.rest_seconds / 60)}:
                  {String(currentExercise.rest_seconds % 60).padStart(2, '0')}
                </p>
              </div>

              {currentExercise.note && (
                <div className="pt-4 border-t border-neutral-200 dark:border-neutral-700">
                  <p className="text-xs text-neutral-600 dark:text-neutral-400 mb-2">Note</p>
                  <p className="text-sm text-neutral-700 dark:text-neutral-300">
                    {currentExercise.note}
                  </p>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-neutral-50 dark:bg-neutral-900">
        <div className="max-w-2xl mx-auto bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-sm mb-4 p-4">
          {isExerciseComplete && currentExerciseIndex === totalExercises - 1 ? (
            <Button className="w-full" onClick={handleCompleteWorkout}>
              Complete Workout
            </Button>
          ) : isExerciseComplete ? (
            <Button
              className="w-full"
              onClick={() => setCurrentExerciseIndex(currentExerciseIndex + 1)}
            >
              Next Exercise
            </Button>
          ) : (
            <p className="text-center text-sm text-neutral-600 dark:text-neutral-400">
              {repsRemaining} {repsRemaining === 1 ? 'set' : 'sets'} remaining
            </p>
          )}
        </div>
      </div>

      {/* Toast Notification */}
      {toast && (
        <Toast
          message={toast.message}
          icon={toast.icon}
          variant="success"
          onClose={() => setToast(null)}
        />
      )}

      {/* Readiness Modal */}
      <ReadinessModal
        title={readinessOpen === 'pre' ? 'How are you feeling?' : 'How was that workout?'}
        isOpen={readinessOpen !== null}
        onRate={handleSubmitReadiness}
        onClose={() => setReadinessOpen(null)}
      />
    </div>
  );
}
