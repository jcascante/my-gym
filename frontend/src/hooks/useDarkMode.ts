import { useEffect, useState } from 'react';

export function useDarkMode() {
  const [isDark, setIsDark] = useState<boolean | null>(null);

  useEffect(() => {
    // Get stored preference or system preference
    const stored = localStorage.getItem('theme');
    let prefersDark: boolean;

    if (stored) {
      prefersDark = stored === 'dark';
    } else {
      prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    setIsDark(prefersDark);
    applyTheme(prefersDark);

    // Listen for system theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e: MediaQueryListEvent) => {
      if (!localStorage.getItem('theme')) {
        setIsDark(e.matches);
        applyTheme(e.matches);
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  const applyTheme = (dark: boolean) => {
    const root = document.documentElement;
    if (dark) {
      root.classList.add('dark');
      root.setAttribute('data-theme', 'dark');
    } else {
      root.classList.remove('dark');
      root.setAttribute('data-theme', 'light');
    }
  };

  const toggleDarkMode = () => {
    setIsDark((prev) => {
      const newValue = !prev;
      localStorage.setItem('theme', newValue ? 'dark' : 'light');
      applyTheme(newValue);
      return newValue;
    });
  };

  return { isDark, toggleDarkMode };
}
