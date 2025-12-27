import { Book, Trash2, FileText, Image as ImageIcon } from 'lucide-react';
import { Card } from './Card';
import { Button } from './Button';
import { Link } from 'react-router-dom';

export function BookCard({ book, onDelete }) {
    return (
        <Card className="group hover:border-blue-500/30 transition-all duration-300 hover:shadow-blue-500/10 hover:-translate-y-1">
            <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-lg bg-blue-500/10 flex items-center justify-center group-hover:bg-blue-500/20 transition-colors">
                    <Book className="w-6 h-6 text-blue-400" />
                </div>
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onDelete(book.name)}
                    className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 hover:bg-red-500/10"
                >
                    <Trash2 className="w-4 h-4" />
                </Button>
            </div>

            <h3 className="font-semibold text-lg text-slate-200 mb-2 line-clamp-1" title={book.name}>
                {book.name}
            </h3>

            <div className="flex items-center gap-4 text-sm text-slate-400 mb-4">
                <div className="flex items-center gap-1.5">
                    <FileText className="w-4 h-4" />
                    <span>{book.total_chapters || 0} Chapters</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <ImageIcon className="w-4 h-4" />
                    <span>{book.total_images || 0} Images</span>
                </div>
            </div>

            <Link to={`/book/${book.name}`}>
                <Button className="w-full bg-slate-800 hover:bg-slate-700 border-slate-700">
                    View Details
                </Button>
            </Link>
        </Card>
    );
}
