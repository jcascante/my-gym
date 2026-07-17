export interface VolumeDataPoint {
  week: string;
  volume: number;
}

export interface VolumeChartProps {
  data: VolumeDataPoint[];
  maxVolume?: number;
}

export function VolumeChart({ data, maxVolume }: VolumeChartProps) {
  const max = maxVolume || Math.max(...data.map((d) => d.volume), 1);
  const chartHeight = 200;
  const barWidth = Math.max(20, 100 / data.length);
  const padding = 40;

  return (
    <div className="w-full">
      <svg
        width="100%"
        height={chartHeight + padding}
        viewBox={`0 0 ${data.length * barWidth + padding * 2} ${chartHeight + padding * 2}`}
        className="w-full h-auto"
      >
        {/* Y-axis */}
        <line
          x1={padding}
          y1={padding}
          x2={padding}
          y2={chartHeight + padding}
          stroke="currentColor"
          strokeWidth="1"
          className="text-neutral-300 dark:text-neutral-600"
        />

        {/* X-axis */}
        <line
          x1={padding}
          y1={chartHeight + padding}
          x2={data.length * barWidth + padding}
          y2={chartHeight + padding}
          stroke="currentColor"
          strokeWidth="1"
          className="text-neutral-300 dark:text-neutral-600"
        />

        {/* Grid lines */}
        {[0.25, 0.5, 0.75].map((pct) => (
          <line
            key={`grid-${pct}`}
            x1={padding}
            y1={padding + chartHeight * (1 - pct)}
            x2={data.length * barWidth + padding}
            y2={padding + chartHeight * (1 - pct)}
            stroke="currentColor"
            strokeWidth="0.5"
            strokeDasharray="4"
            className="text-neutral-200 dark:text-neutral-700"
          />
        ))}

        {/* Bars */}
        {data.map((point, index) => {
          const barHeight = (point.volume / max) * chartHeight;
          const x = padding + index * barWidth + barWidth * 0.1;
          const y = chartHeight + padding - barHeight;

          return (
            <g key={`bar-${index}`}>
              {/* Bar */}
              <rect
                x={x}
                y={y}
                width={barWidth * 0.8}
                height={barHeight}
                fill="currentColor"
                className="text-primary-600 dark:text-primary-500 transition-colors"
                rx="2"
              />

              {/* Label */}
              <text
                x={x + barWidth * 0.4}
                y={chartHeight + padding + 20}
                textAnchor="middle"
                fontSize="12"
                fill="currentColor"
                className="text-neutral-600 dark:text-neutral-400"
              >
                {point.week}
              </text>
            </g>
          );
        })}

        {/* Y-axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
          const value = Math.round((pct * max) / 1000) * 1000;
          return (
            <text
              key={`y-label-${pct}`}
              x={padding - 10}
              y={chartHeight + padding - chartHeight * pct + 4}
              textAnchor="end"
              fontSize="12"
              fill="currentColor"
              className="text-neutral-600 dark:text-neutral-400"
            >
              {value > 0 ? `${(value / 1000).toFixed(0)}k` : '0'}
            </text>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex items-center gap-2 mt-4 justify-center">
        <div className="w-4 h-4 rounded bg-primary-600 dark:bg-primary-500" />
        <p className="text-body-sm text-neutral-600 dark:text-neutral-400">
          Volume (lbs) — Total weight lifted per week
        </p>
      </div>
    </div>
  );
}
