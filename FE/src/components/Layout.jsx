import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, BookOpen, Settings, Library } from 'lucide-react';
import { clsx } from 'clsx';

export function Layout({ children }) {
    const location = useLocation();

    const navItems = [
        { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
        { icon: MessageSquare, label: 'AI Chat', path: '/chat' },
    ];

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 flex font-sans selection:bg-blue-500/30">
            {/* Sidebar */}
            <aside className="w-64 border-r border-slate-800 bg-slate-900/50 backdrop-blur-xl flex flex-col fixed h-full z-10">
                <div className="p-6 border-b border-slate-800">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
                            <BookOpen className="w-5 h-5 text-white" />
                        </div>
                        <span className="font-bold text-lg tracking-tight">Control Theory</span>
                    </div>
                </div>

                <nav className="flex-1 p-4 space-y-2">
                    {navItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = location.pathname === item.path;
                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={clsx(
                                    'flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 group',
                                    isActive
                                        ? 'bg-blue-600/10 text-blue-400 border border-blue-600/20'
                                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                                )}
                            >
                                <Icon className={clsx('w-5 h-5', isActive ? 'text-blue-400' : 'text-slate-500 group-hover:text-slate-300')} />
                                <span className="font-medium">{item.label}</span>
                            </Link>
                        );
                    })}
                </nav>

                <div className="p-4 border-t border-slate-800">
                    <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-slate-900 border border-slate-800">
                        <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center">
                            <span className="text-xs font-bold text-slate-400">US</span>
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-slate-200 truncate">User Session</p>
                            <p className="text-xs text-slate-500 truncate">Active</p>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 ml-64 p-8 overflow-y-auto">
                <div className="max-w-7xl mx-auto">
                    {children}
                </div>
            </main>
        </div>
    );
}
