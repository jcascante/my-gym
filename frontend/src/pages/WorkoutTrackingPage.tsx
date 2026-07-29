import { useRef, useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ExerciseSection, Toast, Button, ReadinessModal, Spinner, Alert } from '@/components';
import type { EffortMethod, WeightUnit } from '@/types/programCreation';
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
    rawEffortMethod === 'rpe' || rawEffortMethod === 'rir' || rawEffortMethod === 'borg'
      ? rawEffortMethod
      : 'rpe';

  const rawWeightUnit = userProfile?.weight_unit;
  const weightUnit: WeightUnit =
    rawWeightUnit === 'kg' || rawWeightUnit === 'lbs' ? rawWeightUnit : 'lbs';

  const {
    exercises,
    totalSets,
    completedSetsTotal,
    completedExercises,
    progressPercentage,
    recordSet,
  } = useSessionProgress(session?.slots ?? [], session?.logged_sets ?? []);

  const [openIds, setOpenIds] = useState<Set<number>>(new Set());
  const seededSessionRef = useRef<number | null>(null);
  const [toast, setToast] = useState<{ message: string; icon?: string } | null>(null);
  const [readinessOpen, setReadinessOpen] = useState<'pre' | 'post' | null>(null);
  const [deloadBannerDismissed, setDeloadBannerDismissed] = useState(false);
  const [confirmIncomplete, setConfirmIncomplete] = useState(false);
  // Tracks whether the modal is closing as a direct result of a rating attempt
  // (success or failure) so the fallback completion path in handleReadinessClose
  // never double-fires alongside handleSubmitReadiness's own completion call.
  const ratingInFlightRef = useRef(false);

  // Seeds the open sections once per session ("first incomplete open, rest
  // collapsed") - guarded by session_id so a reload re-seeds but toggling
  // sections afterward (or logging a set) never resets the user's choices.
  useEffect(() => {
    if (!session || exercises.length === 0) return;
    if (seededSessionRef.current === session.session_id) return;
    seededSessionRef.current = session.session_id;
    // When nothing is incomplete (e.g. resuming an already fully-logged session),
    // fall back to opening the first exercise rather than leaving everything
    // collapsed with no way to see/correct the logged sets.
    const firstIncomplete =
      exercises.find((ex) => ex.completedSets.length < ex.sets) ?? exercises[0];
    setOpenIds(new Set(firstIncomplete ? [firstIncomplete.workout_exercise_id] : []));
  }, [session, exercises]);

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

  if (!session) return <Spinner />;

  const unloggedCount = Math.max(0, totalSets - completedSetsTotal);

  const toggleSection = (workoutExerciseId: number) => {
    setOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(workoutExerciseId)) {
        next.delete(workoutExerciseId);
      } else {
        next.add(workoutExerciseId);
      }
      return next;
    });
  };

  const handleLogSet = async (
    workoutExerciseId: number,
    setNumber: number,
    data: { weight?: number; reps?: number; effort: number; effort_method: EffortMethod },
  ) => {
    if (!sessionIdNum) throw new Error('No active session');

    try {
      await logSessionSet(sessionIdNum, {
        workout_exercise_id: workoutExerciseId,
        set_number: setNumber,
        actual_weight: data.weight,
        actual_reps: data.reps,
        actual_rpe: data.effort,
        effort_method: effortMethod,
      });

      recordSet(workoutExerciseId, setNumber, {
        weight: data.weight,
        reps: data.reps,
        effort: data.effort,
        effort_method: data.effort_method,
      });

      setToast({ message: `Set ${setNumber} logged! 💪`, icon: '✓' });
    } catch (err) {
      console.error('Failed to log set:', err);
      setToast({ message: 'Failed to log set. Please try again.', icon: '⚠️' });
      throw err;
    }
  };

  const handleCompleteWorkout = () => {
    setConfirmIncomplete(false);
    ratingInFlightRef.current = false;
    setReadinessOpen('post');
  };

  const handleCompleteWorkoutClick = () => {
    if (unloggedCount > 0) {
      setConfirmIncomplete(true);
      return;
    }
    handleCompleteWorkout();
  };

  const handleSubmitReadiness = async (readiness: number) => {
    if (!sessionIdNum) return;
    ratingInFlightRef.current = true;
    const phase = readinessOpen === 'pre' ? 'pre' : 'post';

    try {
      await postSessionReadiness(sessionIdNum, readiness, phase);
      setToast({ message: `Readiness recorded: ${readiness}/5`, icon: '✓' });

      if (phase === 'post') {
        await completeSession(sessionIdNum);
        navigate('/');
      }
    } catch (err) {
      // Whether postSessionReadiness or completeSession failed, this attempt did
      // not complete the session - clear the flag so handleReadinessClose's own
      // fallback (fired next, via ReadinessModal's onClose-after-onRate) retries
      // completion instead of assuming this function already handled it.
      ratingInFlightRef.current = false;
      console.error('Failed to record readiness:', err);
      setToast({ message: 'Failed to record readiness. Please try again.', icon: '⚠️' });
    } finally {
      setReadinessOpen(null);
    }
  };

  const handleReadinessClose = async () => {
    const wasRatingAttempt = ratingInFlightRef.current;
    ratingInFlightRef.current = false;

    if (readinessOpen === 'post' && !wasRatingAttempt && sessionIdNum) {
      try {
        await completeSession(sessionIdNum);
        navigate('/');
      } catch (err) {
        console.error('Failed to complete workout:', err);
        setToast({ message: 'Failed to complete workout. Please try again.', icon: '⚠️' });
      }
    }

    setReadinessOpen(null);
  };

  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 flex flex-col">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-neutral-50 dark:bg-neutral-900">
        <div className="max-w-2xl mx-auto bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-sm mt-4 p-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs text-neutral-600 dark:text-neutral-400">
                {session.workout_name}
              </p>
              <h1 className="text-2xl font-bold">
                {completedSetsTotal}/{totalSets} sets
              </h1>
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

          <div className="flex items-center gap-2 mb-3">
            <button
              onClick={() => setOpenIds(new Set(exercises.map((ex) => ex.workout_exercise_id)))}
              className="flex-1 px-3 py-1.5 text-sm border border-neutral-300 dark:border-neutral-600 rounded text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
            >
              Expand All
            </button>
            <button
              onClick={() => setOpenIds(new Set())}
              className="flex-1 px-3 py-1.5 text-sm border border-neutral-300 dark:border-neutral-600 rounded text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
            >
              Collapse All
            </button>
          </div>

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

          {exercises.map((exercise) => (
            <ExerciseSection
              key={exercise.workout_exercise_id}
              exercise={exercise}
              effort_method={effortMethod}
              weightUnit={weightUnit}
              isOpen={openIds.has(exercise.workout_exercise_id)}
              onToggle={() => toggleSection(exercise.workout_exercise_id)}
              onLogSet={(setNumber, data) =>
                handleLogSet(exercise.workout_exercise_id, setNumber, data)
              }
            />
          ))}
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-neutral-50 dark:bg-neutral-900">
        <div className="max-w-2xl mx-auto bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-sm mb-4 p-4">
          <Button className="w-full" onClick={handleCompleteWorkoutClick}>
            Complete Workout
          </Button>
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

      {/* Incomplete-workout confirmation */}
      {confirmIncomplete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-neutral-800 p-6 rounded-lg shadow-lg max-w-sm">
            <h2 className="text-lg font-semibold mb-2 text-neutral-900 dark:text-neutral-100">
              Finish anyway?
            </h2>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-6">
              {unloggedCount} {unloggedCount === 1 ? 'set is' : 'sets are'} not logged.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setConfirmIncomplete(false)}
                className="flex-1 px-4 py-2 border border-neutral-300 dark:border-neutral-600 rounded text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleCompleteWorkout}
                className="flex-1 px-4 py-2 bg-primary-600 dark:bg-primary-700 text-white rounded hover:bg-primary-700 dark:hover:bg-primary-600 transition-colors font-medium"
              >
                Finish anyway
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Readiness Modal */}
      <ReadinessModal
        title={readinessOpen === 'pre' ? 'How are you feeling?' : 'How was that workout?'}
        isOpen={readinessOpen !== null}
        onRate={handleSubmitReadiness}
        onClose={handleReadinessClose}
      />
    </div>
  );
}
