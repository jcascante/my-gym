import { useState, useMemo } from 'react';
import { Button } from './Button';
import { ExercisePreviewModal } from './ExercisePreviewModal';
import { useExercises } from '@/hooks/useExercises';
import type { Exercise, ExerciseResponse } from '@/types/exercise';

interface ExerciseSelectionProps {
  onComplete: (exerciseIds: number[]) => void;
  onBack: () => void;
  selectedExercises?: number[];
}

// Map exercise response to UI-friendly format
function mapExerciseResponse(response: ExerciseResponse): Exercise {
  const muscleGroupMap: Record<string, string> = {
    upper_body: 'Upper Body',
    lower_body: 'Lower Body',
    core: 'Core',
    full_body: 'Full Body',
  };

  return {
    id: response.id,
    name: response.name,
    muscleGroup: muscleGroupMap[response.body_region] || response.body_region,
    equipment: response.equipment_tags.map((tag) => tag.replace(/_/g, ' ')),
    difficulty:
      response.difficulty_level.charAt(0).toUpperCase() + response.difficulty_level.slice(1),
    description: response.instructions,
    targetMuscles: [...response.primary_muscles, ...response.secondary_muscles].map((m) =>
      m
        .split('_')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' '),
    ),
    instructions: response.instructions,
    formCues: response.form_cues,
    safetyNotes: response.safety_notes,
  };
}

type EquipmentFilter = 'All' | 'Barbell' | 'Dumbbells' | 'Bodyweight' | 'Cable';

export function ExerciseSelection({
  onComplete,
  onBack,
  selectedExercises = [],
}: ExerciseSelectionProps) {
  const [search, setSearch] = useState('');
  const [equipmentFilter, setEquipmentFilter] = useState<EquipmentFilter>('All');
  const [selected, setSelected] = useState<Set<number>>(new Set(selectedExercises));
  const [previewExercise, setPreviewExercise] = useState<Exercise | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(['Upper Body', 'Lower Body', 'Core']),
  );

  const { data: apiExercises = [], isLoading } = useExercises();

  const filtered = useMemo(() => {
    const exercises = apiExercises.map(mapExerciseResponse);
    return exercises.filter((ex) => {
      const matchesSearch = ex.name.toLowerCase().includes(search.toLowerCase());
      const matchesEquipment =
        equipmentFilter === 'All' ||
        ex.equipment.some((e) => e.toLowerCase().includes(equipmentFilter.toLowerCase()));
      return matchesSearch && matchesEquipment;
    });
  }, [apiExercises, search, equipmentFilter]);

  const grouped = useMemo(() => {
    const groups: Record<string, Exercise[]> = {};
    filtered.forEach((ex) => {
      if (!groups[ex.muscleGroup]) {
        groups[ex.muscleGroup] = [];
      }
      groups[ex.muscleGroup].push(ex);
    });
    return Object.entries(groups).map(([muscleGroup, exercises]) => ({
      muscleGroup,
      exercises,
    }));
  }, [filtered]);

  const toggleExpanded = (muscleGroup: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(muscleGroup)) {
      newExpanded.delete(muscleGroup);
    } else {
      newExpanded.add(muscleGroup);
    }
    setExpandedGroups(newExpanded);
  };

  const toggleExercise = (id: number) => {
    const newSelected = new Set(selected);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelected(newSelected);
  };

  const handleSubmit = () => {
    onComplete(Array.from(selected));
  };

  return (
    <div className="w-full space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50 mb-1">
          Select Your Exercises
        </h2>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Customize your workout selection
        </p>
      </div>

      <div className="bg-neutral-50 dark:bg-neutral-900/50 rounded-lg p-3 text-center text-xs font-semibold text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">
        Step 2 of 2
      </div>

      {/* Search */}
      <div className="relative">
        <input
          type="text"
          placeholder="Search exercises..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full px-4 py-3 pl-10 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-neutral-900 dark:text-neutral-50 placeholder-neutral-500 dark:placeholder-neutral-400 focus:outline-none focus:border-teal-500 dark:focus:border-teal-400"
        />
        <svg
          className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-neutral-400 dark:text-neutral-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </div>

      {/* Equipment Filter */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {(['All', 'Barbell', 'Dumbbells', 'Bodyweight', 'Cable'] as const).map((filter) => (
          <button
            key={filter}
            onClick={() => setEquipmentFilter(filter)}
            className={`px-4 py-2 rounded-full text-sm font-semibold whitespace-nowrap transition-colors ${
              equipmentFilter === filter
                ? 'bg-teal-600 dark:bg-teal-500 text-white'
                : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700'
            }`}
          >
            {filter}
          </button>
        ))}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="text-center">
            <div className="inline-block w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
              Loading exercises...
            </p>
          </div>
        </div>
      )}

      {/* Exercise Groups */}
      {!isLoading && (
        <div className="space-y-4 max-h-96 overflow-y-auto">
          {grouped.map(({ muscleGroup, exercises }) => (
            <div key={muscleGroup}>
              <button
                onClick={() => toggleExpanded(muscleGroup)}
                className="w-full flex items-center justify-between px-4 py-3 bg-neutral-50 dark:bg-neutral-900/50 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800/50 transition-colors"
              >
                <h3 className="font-semibold text-neutral-900 dark:text-neutral-50">
                  {muscleGroup}
                </h3>
                <svg
                  className={`w-5 h-5 text-neutral-600 dark:text-neutral-400 transform transition-transform ${
                    expandedGroups.has(muscleGroup) ? 'rotate-180' : ''
                  }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 14l-7 7m0 0l-7-7m7 7V3"
                  />
                </svg>
              </button>

              {expandedGroups.has(muscleGroup) && (
                <div className="mt-2 space-y-2 pl-2">
                  {exercises.map((exercise) => (
                    <div
                      key={exercise.id}
                      onClick={() => setPreviewExercise(exercise)}
                      className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                        selected.has(exercise.id)
                          ? 'border-teal-600 dark:border-teal-400 bg-teal-50 dark:bg-teal-900/20'
                          : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 hover:border-neutral-300 dark:hover:border-neutral-600'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <h4 className="font-semibold text-neutral-900 dark:text-neutral-50 mb-1">
                            {exercise.name}
                          </h4>
                          <div className="flex flex-wrap gap-2">
                            <span className="text-xs bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 px-2 py-1 rounded">
                              {exercise.equipment}
                            </span>
                            <span className="text-xs bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 px-2 py-1 rounded">
                              {exercise.difficulty}
                            </span>
                          </div>
                        </div>
                        <input
                          type="checkbox"
                          checked={selected.has(exercise.id)}
                          onChange={() => toggleExercise(exercise.id)}
                          className="w-6 h-6 rounded cursor-pointer accent-teal-600 dark:accent-teal-400 flex-shrink-0 mt-1"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Action Buttons */}
      <div className="space-y-3 pt-6 border-t border-neutral-200 dark:border-neutral-700">
        <Button type="button" variant="primary" onClick={handleSubmit} className="w-full">
          Continue to Review
        </Button>
        <Button type="button" variant="secondary" onClick={onBack} className="w-full">
          Back
        </Button>
      </div>

      {/* Preview Modal */}
      {previewExercise && (
        <ExercisePreviewModal exercise={previewExercise} onClose={() => setPreviewExercise(null)} />
      )}
    </div>
  );
}
