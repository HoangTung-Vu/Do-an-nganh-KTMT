"""
API Endpoint for PDF Processing
"""
import shutil
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
from src.pdf_processing import PDFProcessor
from src.utils.logger import setup_logger
from src.utils.load_config import load_config
from src.utils.s3_client import S3Client

router = APIRouter(prefix="/pdf", tags=["PDF Processing"])
logger = setup_logger('pdf_api', 'pdf_api.log')

# Load config once
config = load_config()
s3_client = S3Client(config=config)


class ProcessPDFResponse(BaseModel):
    """Response model for PDF processing"""
    message: str
    book_name: str
    s3_prefix: str
    total_chapters: int
    total_images: int


@router.post("/upload", response_model=ProcessPDFResponse)
async def upload_and_process_pdf(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload and process a PDF file
    
    Args:
        file: PDF file to upload
        user_id: ID of the user uploading the file
        background_tasks: FastAPI background tasks
    
    Returns:
        ProcessPDFResponse with processing results
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Get temp directory from config
    temp_base = config.get('pdf_processing', {}).get('temp_dir', './temp')
    
    # Create temporary directory for uploaded file
    upload_dir = Path(temp_base) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded file
    pdf_path = upload_dir / file.filename
    try:
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"PDF uploaded: {file.filename}")
        
        # Process PDF with config
        processor = PDFProcessor(
            pdf_path=str(pdf_path),
            user_id=user_id,
            config=config
        )
        
        result = processor.process()
        
        # Clean up uploaded file
        if pdf_path.exists():
            pdf_path.unlink()
        
        logger.info(f"PDF processed successfully: {result['book_name']}")
        
        return ProcessPDFResponse(
            message="PDF processed successfully and uploaded to S3",
            book_name=result['book_name'],
            s3_prefix=processor.s3_prefix,
            total_chapters=result['total_chapters'],
            total_images=result['total_images']
        )
    
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        # Clean up on error
        if pdf_path.exists():
            pdf_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.get("/status/{book_name}")
async def get_processing_status(book_name: str, user_id: str):
    """
    Get processing status and metadata for a book from S3
    
    Args:
        book_name: Name of the book (PDF filename without extension)
        user_id: ID of the user who owns the book
    
    Returns:
        Book metadata and processing status
    """
    json_s3_key = f"{user_id}/{book_name}.json"
    
    if not s3_client.object_exists(json_s3_key):
        raise HTTPException(status_code=404, detail=f"Book '{book_name}' not found in S3")
    
    data = s3_client.read_json(json_s3_key)
    
    return {
        "status": "completed",
        "book_name": data["book_name"],
        "total_chapters": data["total_chapters"],
        "total_images": data["total_images"],
        "s3_prefix": f"{user_id}/{book_name}",
        "chapters": [
            {
                "chapter_id": ch["chapter_id"],
                "title": ch["title"],
                "image_count": ch["image_count"]
            }
            for ch in data["chapters"]
        ]
    }


@router.get("/chapter/{book_name}/{chapter_id}")
async def get_chapter_content(book_name: str, chapter_id: int, user_id: str):
    """
    Get full content of a specific chapter from S3
    
    Args:
        book_name: Name of the book
        chapter_id: Chapter ID (0-indexed)
        user_id: ID of the user who owns the book
    
    Returns:
        Chapter content with text and image references
    """
    json_s3_key = f"{user_id}/{book_name}.json"
    
    if not s3_client.object_exists(json_s3_key):
        raise HTTPException(status_code=404, detail=f"Book '{book_name}' not found in S3")
    
    data = s3_client.read_json(json_s3_key)
    
    # Find chapter
    chapter = next(
        (ch for ch in data["chapters"] if ch["chapter_id"] == chapter_id),
        None
    )
    
    if not chapter:
        raise HTTPException(
            status_code=404,
            detail=f"Chapter {chapter_id} not found in book '{book_name}'"
        )
    
    return chapter


@router.delete("/delete/{book_name}")
async def delete_processed_book(book_name: str, user_id: str):
    """
    Delete all processed data for a book from S3
    
    Args:
        book_name: Name of the book to delete
        user_id: ID of the user who owns the book
    
    Returns:
        Success message
    """
    # Check if book exists in S3
    json_s3_key = f"{user_id}/{book_name}.json"
    if not s3_client.object_exists(json_s3_key):
        raise HTTPException(status_code=404, detail=f"Book '{book_name}' not found in S3")
    
    try:
        # Delete JSON file
        s3_client.delete_object(json_s3_key)
        
        # Delete images (they are prefixed with book_name in user_id folder)
        # We need to list and delete files starting with user_id/book_name_image_
        
        # List objects in user_id folder
        objects_to_delete = []
        for obj_key in s3_client.list_objects(prefix=f"{user_id}/"):
            # Extract the filename part after the user_id/ prefix
            relative_filename = obj_key[len(f"{user_id}/"):]
            if relative_filename.startswith(f"{book_name}_image_"):
                objects_to_delete.append(obj_key)
        
        if objects_to_delete:
            for obj_key in objects_to_delete:
                s3_client.delete_object(obj_key)
            
        logger.info(f"Deleted book '{book_name}' and associated images from S3 for user '{user_id}'")
        return {"message": f"Book '{book_name}' deleted successfully from S3"}
    except Exception as e:
        logger.error(f"Error deleting book from S3: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting book: {str(e)}")
