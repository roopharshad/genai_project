import React from 'react';

interface NeonButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ai' | 'outline' | 'outline-dark' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  glow?: boolean;
  icon?: React.ReactNode;
}

export const NeonButton: React.FC<NeonButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  glow = true,
  icon,
  className = '',
  disabled,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium transition-all duration-200 rounded-btn select-none disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-focus focus:ring-offset-2';

  const sizeStyles = {
    sm: 'px-3 py-1.5 text-xs gap-1.5',
    md: 'px-4 py-2 text-sm gap-2',
    lg: 'px-6 py-3 text-base gap-2.5 font-semibold',
  };

  const variantStyles = {
    primary: `bg-gradient-brand text-white hover:opacity-95 active:scale-[0.98] ${
      glow && !disabled ? 'shadow-glow-purple hover:shadow-glow-brand' : ''
    }`,
    ai: `bg-gradient-ai text-white hover:opacity-95 active:scale-[0.98] ${
      glow && !disabled ? 'shadow-glow-pink hover:shadow-glow-blue' : ''
    }`,
    secondary: `bg-royal-blue text-white hover:bg-electric-blue active:scale-[0.98] ${
      glow && !disabled ? 'shadow-glow-blue' : ''
    }`,
    outline: 'border border-border-strong text-text-primary bg-white hover:bg-surface-muted hover:border-royal-purple active:scale-[0.98]',
    'outline-dark': `border border-neon-violet/50 text-white bg-sidebar-panel hover:bg-white/10 hover:border-laser-blue active:scale-[0.98] ${
      glow && !disabled ? 'shadow-glow-purple' : ''
    }`,
    ghost: 'text-text-secondary hover:text-text-primary hover:bg-surface-muted',
    danger: 'bg-error text-white hover:opacity-90 active:scale-[0.98]',
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      disabled={disabled}
      {...props}
    >
      {icon && <span className="inline-flex shrink-0">{icon}</span>}
      <span>{children}</span>
    </button>
  );
};

