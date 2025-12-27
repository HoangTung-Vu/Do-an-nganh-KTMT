import { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader2, FileText, Trash2 } from 'lucide-react';
import { Layout } from '../components/Layout';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Card } from '../components/Card';
import { agentService } from '../api/agent';
import { embeddingService } from '../api/embedding';
import { useAuth } from '../hooks/useAuth';
import { clsx } from 'clsx';

export default function Chat() {
    const { userId } = useAuth();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [collections, setCollections] = useState([]);
    const [selectedCollection, setSelectedCollection] = useState(null);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        // Load collections for context selection
        const loadCollections = async () => {
            try {
                const data = await embeddingService.listCollections();
                setCollections(data.collections || []);
            } catch (error) {
                console.error('Failed to load collections:', error);
            }
        };
        loadCollections();
    }, []);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim() || !userId) return;

        const userMessage = { role: 'user', content: input };
        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            // Use userId as sessionId as requested
            const response = await agentService.chat(
                userId,
                userId, // sessionId
                userMessage.content,
                selectedCollection // db_name
            );

            const botMessage = {
                role: 'assistant',
                content: response.response,
                artifacts: response.artifacts
            };
            setMessages((prev) => [...prev, botMessage]);
        } catch (error) {
            console.error('Chat failed:', error);
            setMessages((prev) => [...prev, {
                role: 'system',
                content: 'Error: Failed to get response from agent.'
            }]);
        } finally {
            setLoading(false);
        }
    };

    const handleClearSession = async () => {
        if (!confirm('Clear chat history?')) return;
        try {
            await agentService.deleteSession(userId, userId);
            setMessages([]);
        } catch (error) {
            console.error('Failed to clear session:', error);
        }
    };

    return (
        <Layout>
            <div className="flex h-[calc(100vh-8rem)] gap-6">
                {/* Chat Area */}
                <div className="flex-1 flex flex-col bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-xl overflow-hidden shadow-xl">
                    {/* Chat Header */}
                    <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
                                <Bot className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h2 className="font-semibold text-slate-200">AI Assistant</h2>
                                <p className="text-xs text-slate-400">
                                    {selectedCollection
                                        ? `Context: ${selectedCollection}`
                                        : 'General Knowledge'}
                                </p>
                            </div>
                        </div>
                        <Button variant="ghost" size="icon" onClick={handleClearSession} title="Clear History">
                            <Trash2 className="w-5 h-5 text-slate-400 hover:text-red-400" />
                        </Button>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-6 space-y-6">
                        {messages.length === 0 && (
                            <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-4">
                                <Bot className="w-16 h-16 opacity-20" />
                                <p>Ask me anything about your textbooks!</p>
                            </div>
                        )}

                        {messages.map((msg, idx) => (
                            <div
                                key={idx}
                                className={clsx(
                                    'flex gap-4 max-w-3xl',
                                    msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''
                                )}
                            >
                                <div className={clsx(
                                    'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                                    msg.role === 'user' ? 'bg-slate-700' : 'bg-blue-600'
                                )}>
                                    {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                                </div>

                                <div className={clsx(
                                    'rounded-2xl p-4 shadow-sm',
                                    msg.role === 'user'
                                        ? 'bg-slate-800 text-slate-200 rounded-tr-none'
                                        : 'bg-slate-900/80 border border-slate-800 text-slate-300 rounded-tl-none'
                                )}>
                                    <div className="prose prose-invert prose-sm max-w-none whitespace-pre-wrap">
                                        {msg.content}
                                    </div>

                                    {/* Artifacts Display */}
                                    {msg.artifacts && msg.artifacts.length > 0 && (
                                        <div className="mt-4 space-y-2">
                                            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">References</p>
                                            {msg.artifacts.map((artifact, aIdx) => (
                                                <div key={aIdx} className="bg-slate-950/50 rounded p-3 text-xs border border-slate-800/50">
                                                    {/* Render artifact content safely */}
                                                    <pre className="overflow-x-auto text-slate-400">
                                                        {JSON.stringify(artifact, null, 2)}
                                                    </pre>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                        {loading && (
                            <div className="flex gap-4">
                                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                                    <Bot className="w-5 h-5" />
                                </div>
                                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl rounded-tl-none p-4 flex items-center gap-2">
                                    <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                                    <span className="text-sm text-slate-400">Thinking...</span>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Area */}
                    <div className="p-4 bg-slate-900/80 border-t border-slate-800">
                        <form onSubmit={handleSend} className="flex gap-3">
                            <Input
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder="Type your question..."
                                className="flex-1"
                                disabled={loading}
                            />
                            <Button type="submit" disabled={loading || !input.trim()} className="px-6">
                                <Send className="w-5 h-5" />
                            </Button>
                        </form>
                    </div>
                </div>

                {/* Context Sidebar */}
                <div className="w-72 hidden lg:flex flex-col gap-4">
                    <Card className="flex-1 flex flex-col p-4 bg-slate-900/30">
                        <h3 className="font-semibold text-slate-200 mb-4 flex items-center gap-2">
                            <FileText className="w-5 h-5 text-blue-400" />
                            Context
                        </h3>

                        <div className="space-y-2 overflow-y-auto flex-1 pr-2">
                            <button
                                onClick={() => setSelectedCollection(null)}
                                className={clsx(
                                    'w-full text-left px-3 py-2 rounded-lg text-sm transition-colors',
                                    selectedCollection === null
                                        ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30'
                                        : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                                )}
                            >
                                All Books (General)
                            </button>

                            {collections.map((col) => (
                                <button
                                    key={col.name}
                                    onClick={() => setSelectedCollection(col.name)}
                                    className={clsx(
                                        'w-full text-left px-3 py-2 rounded-lg text-sm transition-colors truncate',
                                        selectedCollection === col.name
                                            ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30'
                                            : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                                    )}
                                    title={col.name}
                                >
                                    {col.name}
                                </button>
                            ))}
                        </div>
                    </Card>
                </div>
            </div>
        </Layout>
    );
}
