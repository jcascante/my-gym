import { useState, useRef, useEffect } from 'react';
import { useAuthStore } from '@/store/auth';
import { useNavigate } from 'react-router-dom';
import { logout } from '@/api/auth';
import { getErrorMessage } from '@/api/errors';
import { useDarkMode } from '@/hooks/useDarkMode';
import {
  AlertCircle,
  ChevronDown,
  Dumbbell,
  LogOut,
  Settings,
  User,
  Moon,
  Sun,
} from 'lucide-react';

export default function Header() {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { user, clearAuth } = useAuthStore();
  const { isDark, toggleDarkMode } = useDarkMode();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }

    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isDropdownOpen]);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    setError(null);
    try {
      await logout();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      clearAuth();
      navigate('/login');
      setIsLoggingOut(false);
    }
  };

  return (
    <header className="bg-white border-b border-neutral-200 dark:bg-neutral-800 dark:border-neutral-700 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <button
            onClick={() => navigate('/')}
            className="flex-shrink-0 hover:opacity-80 transition-opacity focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500 rounded"
            aria-label="Go to dashboard"
          >
            <h1 className="text-2xl font-bold text-primary-600">MyGym</h1>
          </button>

          {/* User Menu */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
              aria-haspopup="true"
              aria-expanded={isDropdownOpen}
              aria-label="User menu"
            >
              <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center">
                <User className="w-4 h-4 text-white" />
              </div>
              <div className="hidden sm:flex flex-col items-start">
                <span className="text-sm font-medium text-neutral-900 dark:text-neutral-50">
                  {user?.first_name || 'User'}
                </span>
                <span className="text-xs text-neutral-600 dark:text-neutral-400">
                  {user?.email}
                </span>
              </div>
              <ChevronDown
                className={`w-4 h-4 text-neutral-600 dark:text-neutral-400 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`}
              />
            </button>

            {/* Dropdown Menu */}
            {isDropdownOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-white border border-neutral-200 rounded-lg shadow-lg dark:bg-neutral-800 dark:border-neutral-700">
                {error && (
                  <div className="px-4 py-2 border-b border-neutral-200 dark:border-neutral-700 bg-error-50 dark:bg-error-900">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-error-600 dark:text-error-400 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-error-800 dark:text-error-200">{error}</p>
                    </div>
                  </div>
                )}
                <div className="py-2">
                  {/* Profile Option */}
                  <button
                    onClick={() => {
                      navigate('/profile');
                      setIsDropdownOpen(false);
                    }}
                    className="w-full flex items-center gap-3 px-4 py-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
                  >
                    <User className="w-4 h-4" />
                    <span>My Profile</span>
                  </button>

                  {/* Training Environments Option */}
                  <button
                    onClick={() => {
                      navigate('/environments');
                      setIsDropdownOpen(false);
                    }}
                    className="w-full flex items-center gap-3 px-4 py-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
                  >
                    <Dumbbell className="w-4 h-4" />
                    <span>Training Environments</span>
                  </button>

                  {/* Settings Option */}
                  <button
                    onClick={() => {
                      navigate('/settings');
                      setIsDropdownOpen(false);
                    }}
                    className="w-full flex items-center gap-3 px-4 py-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
                  >
                    <Settings className="w-4 h-4" />
                    <span>Settings</span>
                  </button>

                  {/* Dark Mode Toggle */}
                  <button
                    onClick={toggleDarkMode}
                    className="w-full flex items-center gap-3 px-4 py-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
                  >
                    {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                    <span>{isDark ? 'Light Mode' : 'Dark Mode'}</span>
                  </button>

                  {/* Divider */}
                  <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-2" />

                  {/* Logout */}
                  <button
                    onClick={handleLogout}
                    disabled={isLoggingOut}
                    className="w-full flex items-center gap-3 px-4 py-2 text-sm text-error-600 dark:text-error-400 hover:bg-error-50 dark:hover:bg-error-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>{isLoggingOut ? 'Logging out...' : 'Logout'}</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
