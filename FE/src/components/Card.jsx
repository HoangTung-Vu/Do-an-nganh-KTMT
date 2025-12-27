import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function Card({ className, children, ...props }) {
    return (
        <div
            className={twMerge(
                'bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-xl p-6 shadow-xl',
                className
            )}
            {...props}
        >
            {children}
        </div>
    );
}
