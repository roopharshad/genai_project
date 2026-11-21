import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: string;
  highlight?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  highlight = false,
}) => {
  return (
    <div className={`p-5 rounded-card bg-surface border transition-all duration-200 ${
      highlight 
        ? 'border-royal-purple/40 shadow-card-hover bg-gradient-to-br from-white to-purple-50/30' 
        : 'border-border shadow-card hover:shadow-card-hover'
    }`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">{title}</span>
        {icon && (
          <div className="p-2 rounded-lg bg-surface-muted text-royal-purple">
            {icon}
          </div>
        )}
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold font-display text-text-primary tracking-tight">{value}</span>
        {trend && (
          <span className="text-xs font-medium text-success bg-success/10 px-1.5 py-0.5 rounded">
            {trend}
          </span>
        )}
      </div>
      {subtitle && (
        <p className="mt-1 text-xs text-text-secondary">{subtitle}</p>
      )}
    </div>
  );
};

