import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ProgramGridCard, RegenerateCard, Card } from '@/components';

interface Program {
  id: number;
  name: string;
  duration_weeks: number;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  daysPerWeek: number;
  isActive: boolean;
}

// Mock data for demonstration
const mockPrograms: Program[] = [
  {
    id: 1,
    name: 'Upper/Lower Split',
    duration_weeks: 12,
    difficulty: 'intermediate',
    daysPerWeek: 4,
    isActive: true,
  },
  {
    id: 2,
    name: 'Push/Pull/Legs',
    duration_weeks: 8,
    difficulty: 'intermediate',
    daysPerWeek: 6,
    isActive: false,
  },
  {
    id: 3,
    name: 'Full Body (3x/week)',
    duration_weeks: 10,
    difficulty: 'beginner',
    daysPerWeek: 3,
    isActive: false,
  },
  {
    id: 4,
    name: 'Strength Focus',
    duration_weeks: 6,
    difficulty: 'advanced',
    daysPerWeek: 5,
    isActive: false,
  },
  {
    id: 5,
    name: 'Hypertrophy Program',
    duration_weeks: 12,
    difficulty: 'intermediate',
    daysPerWeek: 4,
    isActive: false,
  },
  {
    id: 6,
    name: 'Bodyweight Mastery',
    duration_weeks: 8,
    difficulty: 'advanced',
    daysPerWeek: 5,
    isActive: false,
  },
];

export default function ProgramsListPage() {
  const navigate = useNavigate();
  const [programs] = useState<Program[]>(mockPrograms);

  const activeProgram = programs.find((p) => p.isActive);

  const handleSelectProgram = (id: number) => {
    // Future: navigate to program details view
    console.log('Selected program:', id);
  };

  const handleStartProgram = (id: number) => {
    // In production: call API to activate program
    navigate(`/programs/${id}/preview`);
  };

  const handleRegenerateProgram = () => {
    navigate('/programs/new');
  };

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900 py-8 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <h1 className="display-md mb-2">Your Programs</h1>
          <p className="body-md text-neutral-600 dark:text-neutral-400">
            {activeProgram
              ? `Currently training: ${activeProgram.name}`
              : 'Create your first program to get started'}
          </p>
        </div>

        {/* Active Program Section (if exists) */}
        {activeProgram && (
          <Card className="mb-12 border-l-4 border-primary-600">
            <div className="flex items-start justify-between mb-4">
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-1">
                  Active Program
                </p>
                <h2 className="heading-lg">{activeProgram.name}</h2>
              </div>
              <span className="inline-block px-3 py-1 bg-success-100 dark:bg-success-900/30 text-success-800 dark:text-success-300 rounded-full text-xs font-medium">
                ✓ Active
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-1">Duration</p>
                <p className="body-lg font-semibold">{activeProgram.duration_weeks} weeks</p>
              </div>
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-1">
                  Days Per Week
                </p>
                <p className="body-lg font-semibold">{activeProgram.daysPerWeek} days</p>
              </div>
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-1">Difficulty</p>
                <p className="body-lg font-semibold capitalize">{activeProgram.difficulty}</p>
              </div>
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-1">Progress</p>
                <p className="body-lg font-semibold">Week 3 of {activeProgram.duration_weeks}</p>
              </div>
            </div>
          </Card>
        )}

        {/* Programs Grid */}
        <div className="mb-12">
          <h2 className="heading-lg mb-6">Available Programs</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {programs.map((program) => (
              <ProgramGridCard
                key={program.id}
                id={program.id}
                name={program.name}
                duration_weeks={program.duration_weeks}
                difficulty={program.difficulty}
                daysPerWeek={program.daysPerWeek}
                isActive={program.isActive}
                onSelect={handleSelectProgram}
                onStart={handleStartProgram}
              />
            ))}
          </div>
        </div>

        {/* Regenerate Section */}
        <div className="mb-12">
          <h2 className="heading-lg mb-6">Ready for Something New?</h2>
          <RegenerateCard onRegenerate={handleRegenerateProgram} />
        </div>

        {/* Info Section */}
        <Card className="bg-secondary-50 dark:bg-secondary-900/10 border-secondary-200 dark:border-secondary-800">
          <div className="space-y-4">
            <h3 className="heading-md text-secondary-900 dark:text-secondary-100">
              How Program Selection Works
            </h3>
            <ul className="space-y-2 text-body-md text-secondary-800 dark:text-secondary-200">
              <li>✓ Choose from pre-made programs or create a custom one</li>
              <li>✓ Only one program can be active at a time</li>
              <li>✓ Switch programs anytime to start a new training phase</li>
              <li>✓ Your workout history is saved independently</li>
            </ul>
          </div>
        </Card>
      </div>
    </div>
  );
}
