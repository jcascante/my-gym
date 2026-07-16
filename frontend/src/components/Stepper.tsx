export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="flex gap-2 mb-6 text-sm">
      {steps.map((label, i) => (
        <li
          key={label}
          className={`px-2 py-1 rounded ${
            i === current
              ? 'bg-blue-600 text-white'
              : i < current
                ? 'text-blue-600'
                : 'text-gray-400'
          }`}
        >
          {i + 1}. {label}
        </li>
      ))}
    </ol>
  );
}
