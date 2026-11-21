import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'primary' | 'ai' | 'success' | 'warning' | 'error' | 'neutral' | 'pending';
  size?: 'sm' | 'md';
  glow?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  glow = false,
}) => {
  const sizeStyles = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs font-medium',
  };

  const variantStyles = {
    primary: `bg-royal-purple/10 text-royal-purple border border-royal-purple/30 ${glow ? 'shadow-glow-purple' : ''}`,
    ai: `bg-neon-violet/15 text-neon-violet border border-neon-violet/40 ${glow ? 'shadow-glow-pink' : ''}`,
    success: 'bg-success/15 text-success border border-success/30',
    warning: 'bg-warning/15 text-warning border border-warning/30',
    error: 'bg-error/15 text-error border border-error/30',
    pending: 'bg-pending/15 text-pending border border-pending/30',
    neutral: 'bg-surface-muted text-text-secondary border border-border',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-mono ${sizeStyles[size]} ${variantStyles[variant]}`}>
      {children}
    </span>
  );
};

