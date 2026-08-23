import React from 'react';

export function Input({ className = '', icon: Icon, error, ...props }) {
  return (
    <div className="relative w-full">
      {Icon && (
        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
          <Icon className="h-4 w-4 text-slate-400 dark:text-slate-500" />
        </div>
      )}
      <input
        className={`w-full bg-white dark:bg-slate-900 border ${error ? 'border-rose-500' : 'border-slate-200 dark:border-slate-700'} text-slate-900 dark:text-white rounded-xl text-sm transition-all focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-blue-400 placeholder-slate-400 dark:placeholder-slate-500 ${Icon ? 'pl-10' : 'pl-4'} pr-4 py-2.5 ${className}`}
        {...props}
      />
      {error && <p className="mt-1.5 text-xs text-rose-500 font-medium">{error}</p>}
    </div>
  );
}
