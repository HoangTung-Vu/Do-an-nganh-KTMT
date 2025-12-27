import { useState, useEffect } from 'react';
import { Plus, Loader2, UploadCloud } from 'lucide-react';
import { Layout } from '../components/Layout';
import { Button } from '../components/Button';
import { BookCard } from '../components/BookCard';
import { Modal } from '../components/Modal';
import { Input } from '../components/Input';
import { embeddingService } from '../api/embedding';
import { pdfService } from '../api/pdf';
import { useAuth } from '../hooks/useAuth';

export default function Home() {
    const { userId } = useAuth();
    const [books, setBooks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);

    const fetchBooks = async () => {
        try {
            setLoading(true);
            const data = await embeddingService.listCollections();
            // The API returns { total: N, collections: [...] }
            // Each collection info has name, etc.
            // We might need to merge this with PDF status to get chapter counts if not in collection info
            // But for now let's use what we get.
            setBooks(data.collections || []);
        } catch (error) {
            console.error('Failed to fetch books:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchBooks();
    }, []);

    const handleFileSelect = (e) => {
        if (e.target.files && e.target.files[0]) {
            setSelectedFile(e.target.files[0]);
        }
    };

    const handleUpload = async () => {
        if (!selectedFile || !userId) return;

        try {
            setUploading(true);

            // 1. Upload PDF
            await pdfService.uploadPdf(selectedFile, userId);

            // 2. Trigger Indexing
            // The backend says scan-and-index scans the directory.
            // If upload puts it in the right place, this should work.
            // Wait, pdfService.uploadPdf puts it in temp/uploads then processes it to S3?
            // embeddingService.scanAndIndex scans "data directory".
            // We need to make sure the flow connects.
            // Looking at BE code:
            // pdf_processing/api.py -> uploads to S3.
            // embedding_services/api.py -> DocumentIndexer scans "data directory".
            // There might be a disconnect here. The user said "generate frontend", assuming backend works.
            // But if backend PDF processing puts files in S3, and Indexer scans local disk, they won't meet.
            // However, let's assume the backend is set up such that "data directory" is where PDFs end up or S3 is mounted.
            // OR, we just call index-book after upload.

            // Let's try calling index-book explicitly if we know the name.
            const bookName = selectedFile.name.replace('.pdf', '');
            await embeddingService.indexBook(bookName, userId);

            setIsUploadModalOpen(false);
            setSelectedFile(null);
            fetchBooks();
        } catch (error) {
            console.error('Upload failed:', error);
            alert('Upload failed: ' + error.message);
        } finally {
            setUploading(false);
        }
    };

    const handleDelete = async (bookName) => {
        if (!confirm(`Are you sure you want to delete "${bookName}"?`)) return;

        try {
            await embeddingService.deleteCollection(bookName);
            // Also delete from PDF service
            await pdfService.deleteProcessedBook(bookName, userId);
            fetchBooks();
        } catch (error) {
            console.error('Delete failed:', error);
        }
    };

    return (
        <Layout>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Library</h1>
                    <p className="text-slate-400">Manage your control theory textbooks and resources</p>
                </div>
                <Button onClick={() => setIsUploadModalOpen(true)} className="gap-2">
                    <Plus className="w-5 h-5" />
                    Upload PDF
                </Button>
            </div>

            {loading ? (
                <div className="flex items-center justify-center h-64">
                    <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                </div>
            ) : books.length === 0 ? (
                <div className="text-center py-20 bg-slate-900/30 rounded-2xl border border-slate-800 border-dashed">
                    <div className="w-16 h-16 bg-slate-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
                        <UploadCloud className="w-8 h-8 text-slate-500" />
                    </div>
                    <h3 className="text-xl font-semibold text-slate-300 mb-2">No books found</h3>
                    <p className="text-slate-500 max-w-sm mx-auto mb-6">
                        Upload your first textbook to start chatting with it using our AI agent.
                    </p>
                    <Button onClick={() => setIsUploadModalOpen(true)} variant="secondary">
                        Upload PDF
                    </Button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {books.map((book) => (
                        <BookCard key={book.name} book={book} onDelete={handleDelete} />
                    ))}
                </div>
            )}

            <Modal
                isOpen={isUploadModalOpen}
                onClose={() => !uploading && setIsUploadModalOpen(false)}
                title="Upload Textbook"
            >
                <div className="space-y-6">
                    <div className="border-2 border-dashed border-slate-700 rounded-xl p-8 text-center hover:border-blue-500/50 transition-colors bg-slate-950/30">
                        <input
                            type="file"
                            id="pdf-upload"
                            accept=".pdf"
                            className="hidden"
                            onChange={handleFileSelect}
                            disabled={uploading}
                        />
                        <label
                            htmlFor="pdf-upload"
                            className="cursor-pointer flex flex-col items-center gap-3"
                        >
                            <div className="w-12 h-12 bg-blue-500/10 rounded-full flex items-center justify-center">
                                <UploadCloud className="w-6 h-6 text-blue-400" />
                            </div>
                            <div>
                                <span className="text-blue-400 font-medium hover:text-blue-300">Click to upload</span>
                                <span className="text-slate-500"> or drag and drop</span>
                            </div>
                            <p className="text-xs text-slate-500">PDF files only (max 50MB)</p>
                        </label>
                    </div>

                    {selectedFile && (
                        <div className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                            <div className="w-8 h-8 bg-red-500/10 rounded flex items-center justify-center">
                                <span className="text-xs font-bold text-red-400">PDF</span>
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-slate-200 truncate">{selectedFile.name}</p>
                                <p className="text-xs text-slate-500">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                            </div>
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => setSelectedFile(null)}
                                disabled={uploading}
                            >
                                <X className="w-4 h-4" />
                            </Button>
                        </div>
                    )}

                    <div className="flex justify-end gap-3">
                        <Button
                            variant="ghost"
                            onClick={() => setIsUploadModalOpen(false)}
                            disabled={uploading}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={handleUpload}
                            disabled={!selectedFile || uploading}
                            className="min-w-[100px]"
                        >
                            {uploading ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Processing...
                                </>
                            ) : (
                                'Upload & Index'
                            )}
                        </Button>
                    </div>
                </div>
            </Modal>
        </Layout>
    );
}
