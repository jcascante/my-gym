import { useState } from 'react';
import { Card, VolumeChart, PRList, StreakBadge } from '@/components';
import type { VolumeDataPoint } from '@/components/VolumeChart';
import type { PersonalRecord } from '@/components/PRList';

type TimePeriod = 'week' | 'month' | 'all';

// Mock data for demonstration
const mockWeeklyData: VolumeDataPoint[] = [
  { week: 'W1', volume: 12000 },
  { week: 'W2', volume: 15500 },
  { week: 'W3', volume: 18200 },
  { week: 'W4', volume: 16800 },
  { week: 'W5', volume: 19500 },
  { week: 'W6', volume: 21200 },
  { week: 'W7', volume: 20800 },
];

const mockMonthlyData: VolumeDataPoint[] = [
  { week: 'Jan', volume: 45000 },
  { week: 'Feb', volume: 52000 },
  { week: 'Mar', volume: 61000 },
  { week: 'Apr', volume: 58000 },
  { week: 'May', volume: 72000 },
  { week: 'Jun', volume: 85000 },
];

const mockAllTimeData: VolumeDataPoint[] = [
  { week: 'Y1', volume: 480000 },
  { week: 'Y2', volume: 620000 },
  { week: 'Y3', volume: 750000 },
];

const mockPRs: PersonalRecord[] = [
  {
    id: 1,
    exercise: 'Bench Press',
    weight: 245,
    reps: 3,
    unit: 'lbs',
    date: new Date(2026, 6, 15),
    isNew: true,
  },
  {
    id: 2,
    exercise: 'Deadlift',
    weight: 405,
    reps: 1,
    unit: 'lbs',
    date: new Date(2026, 6, 10),
    isNew: true,
  },
  {
    id: 3,
    exercise: 'Squat',
    weight: 315,
    reps: 5,
    unit: 'lbs',
    date: new Date(2026, 6, 8),
  },
  {
    id: 4,
    exercise: 'Barbell Row',
    weight: 275,
    reps: 3,
    unit: 'lbs',
    date: new Date(2026, 6, 1),
  },
];

export default function ProgressPage() {
  const [timePeriod, setTimePeriod] = useState<TimePeriod>('week');

  const chartData =
    timePeriod === 'week'
      ? mockWeeklyData
      : timePeriod === 'month'
        ? mockMonthlyData
        : mockAllTimeData;

  const totalVolume = chartData.reduce((sum, d) => sum + d.volume, 0);
  const avgVolume = Math.round(totalVolume / chartData.length);
  const maxVolume = Math.max(...chartData.map((d) => d.volume));

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900 py-8 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <h1 className="display-md mb-2">Your Progress</h1>
          <p className="body-md text-neutral-600 dark:text-neutral-400">
            Track your fitness journey and celebrate your gains
          </p>
        </div>

        {/* Time Period Selector */}
        <div className="mb-8 flex gap-3">
          {(['week', 'month', 'all'] as const).map((period) => (
            <button
              key={period}
              onClick={() => setTimePeriod(period)}
              className={`px-6 py-2 rounded-lg font-medium transition-all ${
                timePeriod === period
                  ? 'bg-primary-600 text-white'
                  : 'bg-neutral-200 dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100 hover:bg-neutral-300 dark:hover:bg-neutral-600'
              }`}
            >
              {period === 'week' ? 'This Week' : period === 'month' ? 'This Month' : 'All Time'}
            </button>
          ))}
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <Card>
            <div>
              <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-2">Total Volume</p>
              <p className="display-md text-primary-600 dark:text-primary-400 font-variant-numeric tabular-nums">
                {(totalVolume / 1000).toFixed(1)}k
              </p>
              <p className="text-body-sm text-neutral-600 dark:text-neutral-400 mt-2">lbs lifted</p>
            </div>
          </Card>

          <Card>
            <div>
              <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-2">Average Volume</p>
              <p className="display-md text-secondary-600 dark:text-secondary-400 font-variant-numeric tabular-nums">
                {(avgVolume / 1000).toFixed(1)}k
              </p>
              <p className="text-body-sm text-neutral-600 dark:text-neutral-400 mt-2">per period</p>
            </div>
          </Card>

          <Card>
            <div>
              <p className="label-sm text-neutral-600 dark:text-neutral-400 mb-2">Peak Volume</p>
              <p className="display-md text-success-600 dark:text-success-400 font-variant-numeric tabular-nums">
                {(maxVolume / 1000).toFixed(1)}k
              </p>
              <p className="text-body-sm text-neutral-600 dark:text-neutral-400 mt-2">max volume</p>
            </div>
          </Card>
        </div>

        {/* Volume Chart */}
        <Card className="mb-12">
          <h2 className="heading-lg mb-6">Volume Over Time</h2>
          <VolumeChart data={chartData} />
        </Card>

        {/* Streak and PRs */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-12">
          <div className="lg:col-span-1">
            <StreakBadge days={7} label="Workout Streak" />
          </div>

          <div className="lg:col-span-2">
            <Card>
              <h2 className="heading-lg mb-6">Personal Records</h2>
              <PRList records={mockPRs} />
            </Card>
          </div>
        </div>

        {/* Stats Summary */}
        <Card className="bg-primary-50 dark:bg-primary-900/10 border-primary-200 dark:border-primary-800">
          <div className="space-y-4">
            <h2 className="heading-md text-primary-900 dark:text-primary-100">Your Stats</h2>
            <ul className="space-y-2 text-body-md text-primary-800 dark:text-primary-200">
              <li>✓ {mockPRs.length} personal records tracked</li>
              <li>
                ✓ Consistent progress over the last{' '}
                {timePeriod === 'week' ? 'week' : timePeriod === 'month' ? 'month' : 'year'}
              </li>
              <li>✓ Keep up the momentum to reach your goals! 🎯</li>
            </ul>
          </div>
        </Card>
      </div>
    </div>
  );
}
