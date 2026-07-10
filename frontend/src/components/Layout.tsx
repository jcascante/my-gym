import { useAuthStore } from '@/store/auth';
import Header from './Header';

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900">
      {isAuthenticated && <Header />}
      <main className={isAuthenticated ? 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8' : ''}>
        {children}
      </main>
    </div>
  );
}
