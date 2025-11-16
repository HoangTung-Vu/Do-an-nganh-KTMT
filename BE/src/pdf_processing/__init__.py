"""
PDF Processing Package - Extract and process PDF documents
Includes:
- PDF text extraction: Extract text using PyMuPDF
- PDF figure extraction: Detect and extract formulas, tables, and figures using YOLO-DocLayNet
- Chapter segmentation: Automatically split content into chapters
"""
from .pdf_processor import PDFProcessor

__all__ = ["PDFProcessor"]