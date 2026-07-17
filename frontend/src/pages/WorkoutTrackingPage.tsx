import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { SetLogger, CompletedSets, Toast, Button, Card } from '@/components';
import type { SlotPreview } from '@/types/program';

interface LoggedSet {
  setNumber: number;
  weight: number;
  reps: number;
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
  },
];

export default function WorkoutTrackingPage() {
  const navigate = useNavigate();
  useParams<{ workoutId?: string }>();

  const [currentExerciseIndex, setCurrentExerciseIndex] = useState(0);
  const [exercises, setExercises] = useState<ExerciseProgress[]>(
    mockExercises.map((ex) => ({
      exercise: ex,
      completedSets: [],
      isCurrentExercise: false,
    })),
  );
  const [toast, setToast] = useState<{ message: string; icon?: string } | null>(null);

  exercises[currentExerciseIndex].isCurrentExercise = true;

  const currentExerciseProgress = exercises[currentExerciseIndex];
  const currentExercise = currentExerciseProgress.exercise;
  const completedSetsCount = currentExerciseProgress.completedSets.length;
  const totalSets = currentExercise.sets;
  const isExerciseComplete = completedSetsCount >= totalSets;
  const repsRemaining = totalSets - completedSetsCount;

  const handleLogSet = (weight: number, reps: number) => {
    const newSet: LoggedSet = {
      setNumber: completedSetsCount + 1,
      weight,
      reps,
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
  };

  const handleSkipExercise = () => {
    if (currentExerciseIndex < exercises.length - 1) {
      setCurrentExerciseIndex(currentExerciseIndex + 1);
      setToast({
        message: `Skipped ${currentExercise.exercise_name}. Moving to next exercise.`,
        icon: '⏭️',
      });
    }
  };

  const handleCompleteWorkout = () => {
    navigate('/workouts/summary', { state: { exercises } });
  };

  const totalExercises = exercises.length;
  const completedExercises = exercises.filter(
    (ex) => ex.completedSets.length >= ex.exercise.sets,
  ).length;
  const progressPercentage = (completedExercises / totalExercises) * 100;

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900 flex flex-col">
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
            <button
              onClick={() => navigate(-1)}
              className="text-2xl text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100"
            >
              ✕
            </button>
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
            <SetLogger
              exerciseName={currentExercise.exercise_name}
              suggestedWeight={currentExercise.load ?? 0}
              suggestedReps={currentExercise.reps}
              currentSet={completedSetsCount + 1}
              totalSets={totalSets}
              onLogSet={handleLogSet}
              onSkipExercise={handleSkipExercise}
            />
          </Card>

          {/* Completed Sets */}
          {completedSetsCount > 0 && (
            <Card className="mb-8">
              <CompletedSets
                sets={currentExerciseProgress.completedSets.map((s) => ({
                  setNumber: s.setNumber,
                  weight: s.weight,
                  reps: s.reps,
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
    </div>
  );
}
