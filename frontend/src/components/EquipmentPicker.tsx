import { useState } from 'react';
import { EQUIPMENT_CATEGORIES, ENVIRONMENT_EQUIPMENT_PRESETS } from '@/types/trainingEnvironment';
import type { EnvironmentType } from '@/types/trainingEnvironment';

interface EquipmentPickerProps {
  selected: string[];
  onChange: (tags: string[]) => void;
  environmentType: EnvironmentType;
}

export function EquipmentPicker({ selected, onChange, environmentType }: EquipmentPickerProps) {
  const [showAll, setShowAll] = useState(false);

  const preset = ENVIRONMENT_EQUIPMENT_PRESETS[environmentType];
  const isNarrowed = !showAll && preset.length > 0;

  // Always keep already-selected tags visible, even if they fall outside the
  // archetype's preset (e.g. a manual addition, or the type changed after
  // equipment was picked) - narrowing should hide unpicked options, not hide
  // a selection the user already made.
  const categories = isNarrowed
    ? EQUIPMENT_CATEGORIES.map((category) => ({
        ...category,
        options: category.options.filter(
          (option) => preset.includes(option.value) || selected.includes(option.value),
        ),
      })).filter((category) => category.options.length > 0)
    : EQUIPMENT_CATEGORIES;

  const toggleTag = (tag: string) => {
    onChange(selected.includes(tag) ? selected.filter((t) => t !== tag) : [...selected, tag]);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="input-label">Available Equipment</span>
        {preset.length > 0 && (
          <button
            type="button"
            className="text-sm text-primary-600 hover:underline"
            onClick={() => setShowAll((prev) => !prev)}
          >
            {showAll ? 'Show typical equipment' : 'Show all equipment'}
          </button>
        )}
      </div>
      <div className="space-y-4">
        {categories.map((category) => (
          <div key={category.key}>
            <h4 className="text-sm font-medium text-neutral-600 dark:text-neutral-300 mb-1">
              {category.label}
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {category.options.map((option) => (
                <label key={option.value} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selected.includes(option.value)}
                    onChange={() => toggleTag(option.value)}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
