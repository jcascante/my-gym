import { useEffect, useState } from 'react'
import { theme } from '@/styles/theme'

type Breakpoint = keyof typeof theme.breakpoints

/**
 * Hook to detect breakpoint changes and provide responsive values.
 * Usage: const isMobile = useResponsive('sm')
 */
export const useResponsive = (breakpoint: Breakpoint): boolean => {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    const breakpointPx = theme.breakpoints[breakpoint]
    const mediaQuery = window.matchMedia(`(min-width: ${breakpointPx}px)`)

    setMatches(mediaQuery.matches)

    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)
    mediaQuery.addEventListener('change', handler)

    return () => mediaQuery.removeEventListener('change', handler)
  }, [breakpoint])

  return matches
}

/**
 * Hook to get current breakpoint name.
 */
export const useBreakpoint = (): Breakpoint => {
  const [breakpoint, setBreakpoint] = useState<Breakpoint>('sm')

  useEffect(() => {
    const checkBreakpoint = () => {
      const width = window.innerWidth
      if (width >= theme.breakpoints['2xl']) setBreakpoint('2xl')
      else if (width >= theme.breakpoints.xl) setBreakpoint('xl')
      else if (width >= theme.breakpoints.lg) setBreakpoint('lg')
      else if (width >= theme.breakpoints.md) setBreakpoint('md')
      else setBreakpoint('sm')
    }

    checkBreakpoint()
    window.addEventListener('resize', checkBreakpoint)

    return () => window.removeEventListener('resize', checkBreakpoint)
  }, [])

  return breakpoint
}

/**
 * Hook to provide responsive values based on breakpoint.
 * Usage: const variant = useResponsiveValue({ sm: 'sm', md: 'md', lg: 'lg' })
 */
export const useResponsiveValue = <T,>(values: Partial<Record<Breakpoint, T>>): T | undefined => {
  const breakpoint = useBreakpoint()
  return values[breakpoint]
}
