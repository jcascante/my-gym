import { FC, HTMLAttributes, ReactNode } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  padding?: 'sm' | 'md' | 'lg';
}

const paddingStyles = {
  sm: 'p-3 sm:p-4',
  md: 'p-4 sm:p-6',
  lg: 'p-6 sm:p-8',
};

export const Card: FC<CardProps> = ({ children, padding = 'md', className = '', ...props }) => (
  <div
    className={`card ${paddingStyles[padding]} transition-smooth hover:shadow-md ${className}`}
    {...props}
  >
    {children}
  </div>
);
