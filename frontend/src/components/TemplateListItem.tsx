import { Card } from '@/components';
import type { Template } from '@/types/template';

interface TemplateListItemProps {
  template: Template;
  isExpanded: boolean;
  onToggle: () => void;
}

export default function TemplateListItem({
  template,
  isExpanded,
  onToggle,
}: TemplateListItemProps) {
  const chevron = isExpanded ? '▼' : '▶';

  return (
    <Card className="mb-4">
      {/* Compact Row */}
      <button
        type="button"
        onClick={onToggle}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onToggle();
          }
        }}
        aria-expanded={isExpanded}
        className="w-full text-left p-4 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 rounded"
      >
        <div className="flex items-start gap-3">
          <span className="text-lg flex-shrink-0 mt-0.5">{chevron}</span>
          <div className="flex-1">
            <h3 className="heading-md text-neutral-900 dark:text-neutral-50 mb-1">
              {template.name}
            </h3>
            <p className="body-sm text-neutral-600 dark:text-neutral-400">
              {template.experience_levels.join(', ')} • {template.goals.join(', ')} •{' '}
              {template.days_per_week_min}-{template.days_per_week_max} days/week •{' '}
              {template.session_duration_min}-{template.session_duration_max} min
            </p>
          </div>
        </div>
      </button>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="border-t border-neutral-200 dark:border-neutral-700 p-4 space-y-6">
          {/* Description */}
          <div>
            <p className="body-md text-neutral-700 dark:text-neutral-300">{template.description}</p>
          </div>

          {/* Configuration Section */}
          <div>
            <h4 className="label-lg text-neutral-900 dark:text-neutral-50 mb-2">Configuration</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400">Experience Levels</p>
                <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                  {template.experience_levels.join(', ')}
                </p>
              </div>
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400">Goals</p>
                <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                  {template.goals.join(', ')}
                </p>
              </div>
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400">Days Per Week</p>
                <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                  {template.days_per_week_min}-{template.days_per_week_max}
                </p>
              </div>
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400">Session Duration</p>
                <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                  {template.session_duration_min}-{template.session_duration_max} min
                </p>
              </div>
            </div>
          </div>

          {/* Progression Section */}
          <div>
            <h4 className="label-lg text-neutral-900 dark:text-neutral-50 mb-2">Progression</h4>
            <div className="space-y-2">
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400">Model</p>
                <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                  {template.progression_ref.model_key}
                </p>
              </div>
              {Object.keys(template.progression_ref.params).length > 0 && (
                <div>
                  <p className="label-sm text-neutral-600 dark:text-neutral-400">Parameters</p>
                  <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                    {Object.entries(template.progression_ref.params)
                      .map(([k, v]) => `${k}: ${String(v)}`)
                      .join(', ')}
                  </p>
                </div>
              )}
              {template.progression_ref.deload_every && (
                <div>
                  <p className="label-sm text-neutral-600 dark:text-neutral-400">Deload Every</p>
                  <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                    {template.progression_ref.deload_every} weeks
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Workout Split Section */}
          <div>
            <h4 className="label-lg text-neutral-900 dark:text-neutral-50 mb-3">Workout Split</h4>
            <div className="space-y-3">
              {template.split.sessions.map((session) => (
                <div key={session.key} className="bg-neutral-50 dark:bg-neutral-800 p-3 rounded-lg">
                  <p className="label-md text-neutral-900 dark:text-neutral-50 mb-2">
                    {session.order}. <span>{session.name}</span>
                  </p>
                  <div className="space-y-1">
                    {session.slots.map((slot, idx) => (
                      <p key={idx} className="body-sm text-neutral-600 dark:text-neutral-400">
                        • {slot.pattern || slot.region} ({slot.priority}, {slot.scheme} scheme)
                      </p>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Set/Rep Schemes Section */}
          <div>
            <h4 className="label-lg text-neutral-900 dark:text-neutral-50 mb-3">Set/Rep Schemes</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-200 dark:border-neutral-700">
                    <th className="text-left py-2 px-2 font-medium text-neutral-900 dark:text-neutral-50">
                      Scheme
                    </th>
                    <th className="text-center py-2 px-2 font-medium text-neutral-900 dark:text-neutral-50">
                      Sets
                    </th>
                    <th className="text-center py-2 px-2 font-medium text-neutral-900 dark:text-neutral-50">
                      Reps
                    </th>
                    <th className="text-center py-2 px-2 font-medium text-neutral-900 dark:text-neutral-50">
                      Rest (s)
                    </th>
                    {Object.values(template.split.schemes).some((s) => s.target_rpe) && (
                      <th className="text-center py-2 px-2 font-medium text-neutral-900 dark:text-neutral-50">
                        RPE
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(template.split.schemes).map(([name, scheme]) => (
                    <tr key={name} className="border-b border-neutral-100 dark:border-neutral-800">
                      <td className="py-2 px-2 text-neutral-900 dark:text-neutral-50">{name}</td>
                      <td className="py-2 px-2 text-center text-neutral-900 dark:text-neutral-50">
                        {scheme.sets}
                      </td>
                      <td className="py-2 px-2 text-center text-neutral-900 dark:text-neutral-50">
                        {scheme.reps_min === scheme.reps_max
                          ? scheme.reps_min
                          : `${scheme.reps_min}-${scheme.reps_max}`}
                      </td>
                      <td className="py-2 px-2 text-center text-neutral-900 dark:text-neutral-50">
                        {scheme.rest_seconds}
                      </td>
                      {scheme.target_rpe !== undefined && (
                        <td className="py-2 px-2 text-center text-neutral-900 dark:text-neutral-50">
                          {scheme.target_rpe}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Required Inputs Section */}
          {template.required_inputs.length > 0 && (
            <div>
              <h4 className="label-lg text-neutral-900 dark:text-neutral-50 mb-3">
                Required Inputs
              </h4>
              <div className="space-y-2">
                {template.required_inputs.map((input) => (
                  <div key={input.key} className="bg-neutral-50 dark:bg-neutral-800 p-3 rounded-lg">
                    <p className="label-sm text-neutral-900 dark:text-neutral-50">{input.label}</p>
                    <p className="body-sm text-neutral-600 dark:text-neutral-400">
                      Type: {input.type}
                      {input.applies_to && ` • Applies to: ${input.applies_to}`}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
