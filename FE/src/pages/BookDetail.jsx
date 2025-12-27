import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, BookOpen, Image as ImageIcon } from 'lucide-react';
import { Layout } from '../components/Layout';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Modal } from '../components/Modal';
import { pdfService } from '../api/pdf';
import { useAuth } from '../hooks/useAuth';

export default function BookDetail() {
    const { bookName } = useParams();
    const navigate = useNavigate();
    const { userId } = useAuth();
    const [book, setBook] = useState(null);
    const [loading, setLoading] = useState(true);
    const [selectedChapter, setSelectedChapter] = useState(null);
    const [chapterContent, setChapterContent] = useState(null);
    const [loadingChapter, setLoadingChapter] = useState(false);

    useEffect(() => {
        const fetchBookDetails = async () => {
            if (!userId || !bookName) return;
            try {
                setLoading(true);
                const data = await pdfService.getStatus(bookName, userId);
                setBook(data);
            } catch (error) {
                console.error('Failed to fetch book details:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchBookDetails();
    }, [bookName, userId]);

    const handleChapterClick = async (chapterId) => {
        try {
            setLoadingChapter(true);
            const content = await pdfService.getChapter(bookName, chapterId, userId);
            setChapterContent(content);
            setSelectedChapter(chapterId);
        } catch (error) {
            console.error('Failed to fetch chapter content:', error);
        } finally {
            setLoadingChapter(false);
        }
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">
                    <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                </div>
            </Layout>
        );
    }

    if (!book) {
        return (
            <Layout>
                <div className="text-center py-20">
                    <h2 className="text-xl text-slate-400">Book not found</h2>
                    <Button onClick={() => navigate('/')} className="mt-4">
                        Go Back
                    </Button>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="mb-8">
                <Button variant="ghost" onClick={() => navigate('/')} className="mb-4 pl-0 hover:pl-2 transition-all">
                    <ArrowLeft className="w-5 h-5 mr-2" />
                    Back to Library
                </Button>

                <div className="flex items-start justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-white mb-2">{book.book_name}</h1>
                        <div className="flex items-center gap-6 text-slate-400">
                            <span className="flex items-center gap-2">
                                <BookOpen className="w-4 h-4" />
                                {book.total_chapters} Chapters
                            </span>
                            <span className="flex items-center gap-2">
                                <ImageIcon className="w-4 h-4" />
                                {book.total_images} Images
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {book.chapters.map((chapter) => (
                    <Card
                        key={chapter.chapter_id}
                        className="hover:border-blue-500/30 cursor-pointer transition-all group"
                        onClick={() => handleChapterClick(chapter.chapter_id)}
                    >
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-bold text-blue-400 bg-blue-500/10 px-2 py-1 rounded">
                                Chapter {chapter.chapter_id + 1}
                            </span>
                            <span className="text-xs text-slate-500 flex items-center gap-1">
                                <ImageIcon className="w-3 h-3" />
                                {chapter.image_count}
                            </span>
                        </div>
                        <h3 className="font-medium text-slate-200 group-hover:text-blue-400 transition-colors line-clamp-2">
                            {chapter.title || `Chapter ${chapter.chapter_id + 1}`}
                        </h3>
                    </Card>
                ))}
            </div>

            <Modal
                isOpen={selectedChapter !== null}
                onClose={() => setSelectedChapter(null)}
                title={chapterContent?.title || 'Chapter Content'}
            >
                <div className="max-h-[70vh] overflow-y-auto pr-2">
                    {loadingChapter ? (
                        <div className="flex justify-center py-10">
                            <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                        </div>
                    ) : chapterContent ? (
                        <div className="prose prose-invert prose-sm max-w-none">
                            {/* This is a simple text dump. In a real app, we'd parse this better. */}
                            <div className="whitespace-pre-wrap text-slate-300">
                                {/* 
                  The content might be complex object or string. 
                  Based on API, it returns "Chapter content with text and image references".
                  Let's assume it has a 'text' field or similar.
                  Checking backend: get_chapter_content returns the chapter dict from JSON.
                  It likely has 'content' or 'text'.
                */}
                                {chapterContent.content || chapterContent.text || JSON.stringify(chapterContent, null, 2)}
                            </div>
                        </div>
                    ) : (
                        <p className="text-red-400">Failed to load content.</p>
                    )}
                </div>
            </Modal>
        </Layout>
    );
}
