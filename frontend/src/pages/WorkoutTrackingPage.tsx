import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  SetLogger,
  CompletedSets,
  Toast,
  Button,
  Card,
  ReadinessModal,
  Spinner,
  Alert,
} from '@/components';
import { formatSlotNote } from '@/utils/slotNote';
import type { EffortMethod } from '@/types/programCreation';
import { useAuthStore } from '@/store/auth';
import { useSession } from '@/hooks/useSession';
import { useSessionProgress } from '@/hooks/useSessionProgress';
import { logSessionSet, postSessionReadiness, completeSession } from '@/api/sessions';

export default function WorkoutTrackingPage() {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId?: string }>();
  const sessionIdNum = sessionId ? Number(sessionId) : null;
  const { data: session, isLoading, error } = useSession(sessionIdNum);
  const { userProfile } = useAuthStore();

  const rawEffortMethod = userProfile?.effort_method;
  const effortMethod: EffortMethod =
    rawEffortMethod === 'rpe' ||
    rawEffortMethod === 'rir' ||
    rawEffortMethod === 'borg' ||
    rawEffortMethod === 'percent_1rm'
      ? rawEffortMethod
      : 'rpe';

  const {
    currentExercise,
    currentIndex,
    exercises,
    completedSetsCount,
    isExerciseComplete,
    completedExercises,
    progressPercentage,
    isLastExercise,
    recordSet,
    goToNext,
  } = useSessionProgress(session?.slots ?? [], session?.logged_sets ?? []);

  const [toast, setToast] = useState<{ message: string; icon?: string } | null>(null);
  const [readinessOpen, setReadinessOpen] = useState<'pre' | 'post' | null>(null);
  const [deloadBannerDismissed, setDeloadBannerDismissed] = useState(false);

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

  if (!session || !currentExercise) return <Spinner />;

  const totalSets = currentExercise.sets;
  const repsRemaining = totalSets - completedSetsCount;

  const handleLogSet = async (data: {
    weight?: number;
    reps?: number;
    effort: number;
    effort_method: EffortMethod;
  }) => {
    if (!sessionIdNum || !currentExercise) return;

    try {
      await logSessionSet(sessionIdNum, {
        workout_exercise_id: currentExercise.workout_exercise_id,
        set_number: completedSetsCount + 1,
        actual_weight: data.weight,
        actual_reps: data.reps,
        actual_rpe: data.effort,
        effort_method: effortMethod,
      });

      const didComplete = recordSet({
        weight: data.weight,
        reps: data.reps,
        effort: data.effort,
        effort_method: data.effort_method,
      });

      if (!didComplete) {
        const remaining = currentExercise.sets - (completedSetsCount + 1);
        setToast({ message: `Set logged! ${remaining} more to go! 💪`, icon: '✓' });
        return;
      }

      setToast({ message: `Great! ${currentExercise.exercise_name} complete! 💪`, icon: '🎉' });

      if (!isLastExercise) {
        const nextName = exercises[currentIndex + 1].exercise_name;
        setTimeout(() => {
          goToNext();
          setToast({ message: `Next up: ${nextName}`, icon: '▶️' });
        }, 1500);
      }
    } catch (err) {
      console.error('Failed to log set:', err);
      setToast({ message: 'Failed to log set. Please try again.', icon: '⚠️' });
    }
  };

  const handleCompleteWorkout = () => {
    setReadinessOpen('post');
  };

  const handleSubmitReadiness = async (readiness: number) => {
    if (!sessionIdNum) return;
    const phase = readinessOpen === 'pre' ? 'pre' : 'post';

    try {
      await postSessionReadiness(sessionIdNum, readiness, phase);
      setToast({ message: `Readiness recorded: ${readiness}/5`, icon: '✓' });

      if (phase === 'post') {
        await completeSession(sessionIdNum);
        navigate('/');
      }
    } catch (err) {
      console.error('Failed to record readiness:', err);
      setToast({ message: 'Failed to record readiness. Please try again.', icon: '⚠️' });
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
                Exercise {currentIndex + 1} of {exercises.length}
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
                {completedExercises}/{exercises.length} exercises
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
          {/* Reactive Deload Banner */}
          {session.reactive_deload && !deloadBannerDismissed && session.deload_reason && (
            <Alert
              type="info"
              dismissible
              onDismiss={() => setDeloadBannerDismissed(true)}
              className="mb-4"
            >
              {session.deload_reason}
            </Alert>
          )}

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
                    {formatSlotNote(currentExercise.note)}
                  </p>
                  {currentExercise.adjustment_reason && (
                    <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                      {currentExercise.adjustment_reason}
                    </p>
                  )}
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-neutral-50 dark:bg-neutral-900">
        <div className="max-w-2xl mx-auto bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-sm mb-4 p-4">
          {isExerciseComplete && isLastExercise ? (
            <Button className="w-full" onClick={handleCompleteWorkout}>
              Complete Workout
            </Button>
          ) : isExerciseComplete ? (
            <Button className="w-full" onClick={goToNext}>
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
