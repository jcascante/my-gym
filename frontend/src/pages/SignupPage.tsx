import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import { signup, login, getCurrentUser } from '@/api/auth';
import { Button, FormField, Alert, Card } from '@/components';

export default function SignupPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await signup(formData);
      await login({
        email: formData.email,
        password: formData.password,
      });

      const userData = await getCurrentUser();
      setAuth(userData, userData.profile);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 dark:from-neutral-900 dark:to-neutral-800 flex items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-neutral-900 dark:text-white mb-2">
            Create your account
          </h1>
          <p className="text-neutral-600 dark:text-neutral-400">
            Join MyGym and start your fitness journey
          </p>
        </div>

        {error && (
          <Alert type="error" dismissible onDismiss={() => setError('')} className="mb-6">
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField
              label="First Name"
              type="text"
              name="first_name"
              value={formData.first_name}
              onChange={handleChange}
              required
              placeholder="John"
            />
            <FormField
              label="Last Name"
              type="text"
              name="last_name"
              value={formData.last_name}
              onChange={handleChange}
              required
              placeholder="Doe"
            />
          </div>

          <FormField
            label="Email"
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
            placeholder="you@example.com"
          />

          <FormField
            label="Password"
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            required
            minLength={8}
            placeholder="••••••••"
            hint="Minimum 8 characters"
          />

          <Button type="submit" variant="primary" size="lg" isLoading={loading} className="w-full">
            Create account
          </Button>
        </form>

        <p className="mt-6 text-center text-neutral-600 dark:text-neutral-400">
          Already have an account?{' '}
          <Link
            to="/login"
            className="font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400"
          >
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}
