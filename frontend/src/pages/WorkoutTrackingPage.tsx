import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { SetLogger, CompletedSets, Toast, Button, Card, ReadinessModal } from '@/components';
import type { SlotPreview } from '@/types/program';
import type { EffortMethod } from '@/types/programCreation';
import { useAuthStore } from '@/store/auth';
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
  exercise: SlotPreview;
  completedSets: LoggedSet[];
  isCurrentExercise: boolean;
}

// Mock data for demonstration
const mockExercises: SlotPreview[] = [
  {
    workout_exercise_id: 1,
    exercise_id: 1,
    exercise_name: 'Bench Press',
    sets: 4,
    reps: 6,
    load: 185,
    rest_seconds: 180,
    note: null,
    is_locked: false,
    is_user_swapped: false,
    effort_target: null,
    rotation_pool: [1],
    tempo: 'controlled',
    warmup_sets: [],
  },
  {
    workout_exercise_id: 2,
    exercise_id: 2,
    exercise_name: 'Incline Dumbbell Press',
    sets: 3,
    reps: 8,
    load: 70,
    rest_seconds: 120,
    note: null,
    is_locked: false,
    is_user_swapped: false,
    effort_target: null,
    rotation_pool: [2],
    tempo: 'controlled',
    warmup_sets: [],
  },
  {
    workout_exercise_id: 3,
    exercise_id: 3,
    exercise_name: 'Barbell Rows',
    sets: 4,
    reps: 6,
    load: 225,
    rest_seconds: 180,
    note: null,
    is_locked: false,
    is_user_swapped: false,
    effort_target: null,
    rotation_pool: [3],
    tempo: 'controlled',
    warmup_sets: [],
  },
];

export default function WorkoutTrackingPage() {
  const navigate = useNavigate();
  const { workoutId } = useParams<{ workoutId?: string }>();
  const { userProfile } = useAuthStore();

  const rawEffortMethod = userProfile?.effort_method;
  const effortMethod: EffortMethod =
    rawEffortMethod === 'rpe' ||
    rawEffortMethod === 'rir' ||
    rawEffortMethod === 'borg' ||
    rawEffortMethod === 'percent_1rm'
      ? rawEffortMethod
      : 'rpe';
  const [currentExerciseIndex, setCurrentExerciseIndex] = useState(0);
  const [exercises, setExercises] = useState<ExerciseProgress[]>(
    mockExercises.map((ex) => ({
      exercise: ex,
      completedSets: [],
      isCurrentExercise: false,
    })),
  );
  const [toast, setToast] = useState<{ message: string; icon?: string } | null>(null);
  const [readinessOpen, setReadinessOpen] = useState<'pre' | 'post' | null>(null);

  exercises[currentExerciseIndex].isCurrentExercise = true;

  const currentExerciseProgress = exercises[currentExerciseIndex];
  const currentExercise = currentExerciseProgress.exercise;
  const completedSetsCount = currentExerciseProgress.completedSets.length;
  const totalSets = currentExercise.sets;
  const isExerciseComplete = completedSetsCount >= totalSets;
  const repsRemaining = totalSets - completedSetsCount;

  const handleLogSet = async (data: {
    weight?: number;
    reps?: number;
    effort: number;
    effort_method: EffortMethod;
  }) => {
    if (!workoutId) {
      console.error('Workout ID is missing');
      return;
    }

    try {
      await logSetLog(
        Number(workoutId),
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

      // Show celebratory toast
      if (isExerciseComplete) {
        setToast({
          message: `Great! ${currentExercise.exercise_name} complete! 💪`,
          icon: '🎉',
        });

        // Auto-advance to next exercise after 1.5s
        setTimeout(() => {
          if (currentExerciseIndex < exercises.length - 1) {
            setCurrentExerciseIndex(currentExerciseIndex + 1);
            setToast({
              message: `Next up: ${mockExercises[currentExerciseIndex + 1].exercise_name}`,
              icon: '▶️',
            });
          }
        }, 1500);
      } else {
        setToast({
          message: `Set logged! ${repsRemaining - 1} more to go! 💪`,
          icon: '✓',
        });
      }
    } catch (error) {
      console.error('Failed to log set:', error);
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
    if (!workoutId) {
      console.error('Workout ID is missing');
      return;
    }

    try {
      await postWorkoutReadiness(
        Number(workoutId),
        readiness,
        readinessOpen === 'pre' ? 'pre' : 'post',
      );
      setToast({
        message: `Readiness recorded: ${readiness}/5`,
        icon: '✓',
      });

      if (readinessOpen === 'post') {
        navigate('/workouts/summary', { state: { exercises } });
      }
    } catch (error) {
      console.error('Failed to record readiness:', error);
      setToast({
        message: 'Failed to record readiness. Please try again.',
        icon: '⚠️',
      });
    } finally {
      setReadinessOpen(null);
    }
  };

  const totalExercises = exercises.length;
  const completedExercises = exercises.filter(
    (ex) => ex.completedSets.length >= ex.exercise.sets,
  ).length;
  const progressPercentage = (completedExercises / totalExercises) * 100;

  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 flex flex-col">
      {/* Header */}
      <div className="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700 p-4 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="label-sm text-neutral-600 dark:text-neutral-400">
                Exercise {currentExerciseIndex + 1} of {totalExercises}
              </p>
              <h1 className="heading-lg">{currentExercise.exercise_name}</h1>
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
                sets={currentExerciseProgress.completedSets
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
              <p className="label-sm text-neutral-600 dark:text-neutral-400">Rest Time</p>
              <p className="text-3xl font-bold text-neutral-900 dark:text-neutral-100">
                {Math.floor(currentExercise.rest_seconds / 60)}:
                {String(currentExercise.rest_seconds % 60).padStart(2, '0')}
              </p>

              {currentExercise.note && (
                <div className="pt-4 border-t border-neutral-200 dark:border-neutral-700">
                  <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-2">Note</p>
                  <p className="body-sm text-neutral-700 dark:text-neutral-300">
                    {currentExercise.note}
                  </p>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-neutral-800 border-t border-neutral-200 dark:border-neutral-700 p-4">
        <div className="max-w-2xl mx-auto">
          {isExerciseComplete && currentExerciseIndex === totalExercises - 1 ? (
            <Button className="w-full btn btn-success" onClick={handleCompleteWorkout}>
              Complete Workout
            </Button>
          ) : isExerciseComplete ? (
            <Button
              className="w-full btn btn-primary"
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
