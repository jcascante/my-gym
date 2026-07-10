import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import { login, getCurrentUser } from '@/api/auth';
import { Button, FormField, Alert, Card } from '@/components';

export default function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login({ email, password });

      const userData = await getCurrentUser();
      setAuth(userData, userData.profile);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 dark:from-neutral-900 dark:to-neutral-800 flex items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-neutral-900 dark:text-white mb-2">Welcome back</h1>
          <p className="text-neutral-600 dark:text-neutral-400">Sign in to your MyGym account</p>
        </div>

        {error && (
          <Alert type="error" dismissible onDismiss={() => setError('')} className="mb-6">
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="you@example.com"
          />

          <FormField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            placeholder="••••••••"
          />

          <Button type="submit" variant="primary" size="lg" isLoading={loading} className="w-full">
            Sign in
          </Button>
        </form>

        <p className="mt-6 text-center text-neutral-600 dark:text-neutral-400">
          Don't have an account?{' '}
          <Link
            to="/signup"
            className="font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400"
          >
            Sign up
          </Link>
        </p>
      </Card>
    </div>
  );
}
