import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function Input({ className, ...props }) {
    return (
        <input
            className={twMerge(
                'bg-slate-950/50 border border-slate-800 rounded-lg px-4 py-2 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all',
                className
            )}
            {...props}
        />
    );
}
