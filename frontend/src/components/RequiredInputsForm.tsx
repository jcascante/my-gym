import { useState } from 'react';
import { Button } from './Button';
import { FormField } from './FormField';
import type { RequiredInput } from '@/types/program';

export function RequiredInputsForm({
  inputs,
  onSubmit,
}: {
  inputs: RequiredInput[];
  onSubmit: (values: Record<string, number | string>) => void;
}) {
  const [values, setValues] = useState<Record<string, string>>({});

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const coerced: Record<string, number | string> = {};
    for (const inp of inputs) {
      const raw = values[inp.key] ?? '';
      coerced[inp.key] = inp.type === 'number' ? Number(raw) : raw;
    }
    onSubmit(coerced);
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      {inputs.map((inp) => (
        <FormField
          key={inp.key}
          id={inp.key}
          label={inp.label}
          type={inp.type}
          value={values[inp.key] ?? ''}
          onChange={(e) => setValues((v) => ({ ...v, [inp.key]: e.target.value }))}
        />
      ))}
      <Button type="submit">Continue</Button>
    </form>
  );
}
