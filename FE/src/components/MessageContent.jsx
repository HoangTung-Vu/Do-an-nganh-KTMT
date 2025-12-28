import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronDown, ChevronRight, Brain } from 'lucide-react';

const ThinkBlock = ({ content }) => {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="my-2 border border-blue-500/30 rounded-lg overflow-hidden bg-blue-500/5">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center gap-2 p-2 text-xs font-medium text-blue-400 hover:bg-blue-500/10 transition-colors"
            >
                {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                <Brain className="w-4 h-4" />
                <span>Thought Process</span>
            </button>
            {isOpen && (
                <div className="p-3 text-sm text-slate-400 border-t border-blue-500/10 bg-slate-900/50">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {content}
                    </ReactMarkdown>
                </div>
            )}
        </div>
    );
};

export const MessageContent = ({ content }) => {
    if (!content) return null;

    // Regex to capture <think>...</think> blocks including newlines
    const parts = content.split(/(<think>[\s\S]*?<\/think>)/g);

    return (
        <div className="prose prose-invert prose-sm max-w-none">
            {parts.map((part, index) => {
                if (part.startsWith('<think>') && part.endsWith('</think>')) {
                    const thinkContent = part.slice(7, -8); // Remove tags
                    return <ThinkBlock key={index} content={thinkContent} />;
                }
                // Don't render empty strings resulting from split
                if (!part) return null;

                return (
                    <ReactMarkdown key={index} remarkPlugins={[remarkGfm]}>
                        {part}
                    </ReactMarkdown>
                );
            })}
        </div>
    );
};
