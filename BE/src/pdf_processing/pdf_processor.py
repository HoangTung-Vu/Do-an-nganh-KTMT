"""
PDF Processing Module - Extract chapters, formulas, tables, and figures from PDF documents
"""
import json
import re
import shutil
import cv2
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from tqdm import tqdm
import pypdfium2 as pdfium
from ultralytics import YOLO
from ..utils.logger import setup_logger
from ..utils.load_config import load_config
from ..utils.s3_client import S3Client

logger = setup_logger('pdf_processor', 'pdf_processing.log')


class PDFProcessor:
    """Main class for processing PDF documents with chapter detection and image extraction"""
    
    # DocLayNet class labels
    DOCLAYNET_CLASSES = [
        "Text", "Picture", "Caption", "Section-header", "Footnote",
        "Formula", "Table", "List-item", "Page-header", "Page-footer", "Title"
    ]
    
    # Classes to extract as images
    IMAGE_CLASSES = {"Formula", "Picture", "Table"}
    
    # Regex patterns for chapter detection
    CHAPTER_PATTERNS = {
        'page_mark': re.compile(r"^\[--- PAGE\s+(\d+)\s+---\]$"),
        'chapter_only': re.compile(r"^\s*(?:CHƯƠNG|Chương|CHAPTER|Chapter)\s+([IVXLCDM]+|\d+)\s*$"),
        'chapter_inline': re.compile(r"^\s*(?:CHƯƠNG|Chương|CHAPTER|Chapter)\s+([IVXLCDM]+|\d+)\s*[\.\-–:]?\s+(.+?)\s*$"),
        'appendix_only': re.compile(r"^\s*(?:PHỤ LỤC|Phụ lục|APPENDIX|Appendix)\s+([A-Z]+)\s*$"),
        'appendix_inline': re.compile(r"^\s*(?:PHỤ LỤC|Phụ lục|APPENDIX|Appendix)\s+([A-Z]+)\s*[\.\-–:]?\s+(.+?)\s*$"),
    }
    
    def __init__(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        model_path: Optional[str] = None,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
        scale: Optional[float] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize PDF Processor
        
        Args:
            pdf_path: Path to input PDF file
            output_dir: Directory to save processed outputs
            model_path: Path to YOLO model weights
            conf_threshold: Confidence threshold for object detection
            iou_threshold: IoU threshold for NMS
            scale: Scale factor for PDF rendering
            config: Configuration dict (if None, loads from config.yaml)
        """
        # Load config if not provided
        if config is None:
            config = load_config()
        
        pdf_config = config.get('pdf_processing', {})
        indexing_config = config.get('indexing', {})
        
        self.pdf_path = Path(pdf_path)
        self.book_name = self.pdf_path.stem
        
        # Setup temporary local directory for processing
        temp_base = pdf_config.get('temp_dir', './temp')
        self.temp_dir = Path(temp_base) / self.book_name
        self.images_dir = self.temp_dir / "images"
        self.pages_dir = self.temp_dir / "pdf_pages"
        self.pred_dir = self.temp_dir / "predictions"
        
        # Create temporary directories
        for directory in [self.temp_dir, self.images_dir, self.pages_dir, self.pred_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize S3 client
        self.s3_client = S3Client(config=config)
        self.s3_prefix = self.book_name  # S3 folder prefix for this book
        
        # Model parameters from config
        self.model_path = model_path or pdf_config.get('model_path', './models/yolo-doclaynet.pt')
        self.conf_threshold = conf_threshold or pdf_config.get('conf_threshold', 0.25)
        self.iou_threshold = iou_threshold or pdf_config.get('iou_threshold', 0.50)
        self.scale = scale or pdf_config.get('scale', 2.0)
        
        # Load YOLO model
        self.model = YOLO(model_path)
        self.id2name = (
            self.model.names if isinstance(self.model.names, dict) 
            else {i: n for i, n in enumerate(self.model.names)}
        )
        
        # Global image counter
        self.image_counter = 0
        
    def process(self) -> Dict[str, Any]:
        """
        Main processing pipeline
        
        Returns:
            Dictionary containing book metadata and chapters
        """
        logger.info(f"Starting PDF processing: {self.pdf_path}")
        logger.info(f"Output directory: {self.output_dir}")
        
        # Step 1: Convert PDF pages to images
        logger.info("[Step 1/5] Converting PDF to images...")
        page_images = self._pdf_to_images()
        
        # Step 2: Detect objects (formulas, tables, pictures)
        logger.info("[Step 2/5] Detecting objects with YOLO...")
        detections = self._detect_objects(page_images)
        
        # Step 3: Extract images and build linear text
        logger.info("[Step 3/5] Extracting images and text...")
        linear_text = self._extract_content(page_images, detections)
        
        # Step 4: Split into chapters
        logger.info("[Step 4/5] Splitting into chapters...")
        chapters = self._split_chapters(linear_text)
        
        # Step 5: Save results
        logger.info("[Step 5/5] Saving results to S3...")
        result = self._save_results(chapters)
        
        # Step 6: Cleanup temporary files
        logger.info("[Step 6/6] Cleaning up temporary files...")
        self._cleanup_temp_files()
        
        logger.info(f"Processing complete! Chapters: {len(chapters)}, Images: {self.image_counter}")
        logger.info(f"Results saved to S3: s3://{self.s3_client.bucket_name}/{self.s3_prefix}/")
        
        return result
    
    def _pdf_to_images(self) -> List[Path]:
        """Convert PDF pages to PNG images"""
        logger.debug(f"Rendering PDF with scale={self.scale}")
        pdf = pdfium.PdfDocument(str(self.pdf_path))
        page_images = []
        
        for i in tqdm(range(len(pdf)), desc="Rendering pages"):
            page = pdf.get_page(i)
            pil = page.render(scale=self.scale).to_pil()
            img_path = self.pages_dir / f"page_{i+1:04d}.png"
            pil.save(img_path)
            page_images.append(img_path)
            page.close()
        
        logger.info(f"Rendered {len(page_images)} pages")
        return page_images
    
    def _detect_objects(self, page_images: List[Path]) -> Dict[str, List[Dict]]:
        """Run YOLO detection on all pages"""
        # Run prediction
        pred_run_dir = self.pred_dir / "predict"
        labels_dir = pred_run_dir / "labels"
        
        if pred_run_dir.exists():
            shutil.rmtree(pred_run_dir)
        
        logger.info(f"Running YOLO prediction on {len(page_images)} pages")
        _ = self.model.predict(
            [str(p) for p in page_images],
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            save=True,
            save_txt=True,
            save_conf=True,
            project=str(self.pred_dir),
            name="predict",
            exist_ok=False,
            verbose=False
        )
        
        # Parse detection results
        detections = {}
        total_detections = 0
        
        for img_path in page_images:
            stem = img_path.stem
            img = cv2.imread(str(img_path))
            if img is None:
                logger.warning(f"Could not read image: {img_path}")
                detections[stem] = []
                continue
            
            h, w = img.shape[:2]
            page_dets = self._parse_labels(labels_dir / f"{stem}.txt", w, h)
            page_dets = self._dedup_detections(page_dets)
            detections[stem] = page_dets
            total_detections += len(page_dets)
        
        logger.info(f"Detected {total_detections} objects across {len(page_images)} pages")
        return detections
    
    def _parse_labels(self, label_path: Path, img_w: int, img_h: int) -> List[Dict]:
        """Parse YOLO label file to detection dictionaries"""
        dets = []
        if not label_path.exists():
            return dets
        
        with open(label_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                
                cls_id = int(float(parts[0]))
                cls_name = self.id2name.get(cls_id, str(cls_id))
                
                if cls_name not in self.IMAGE_CLASSES:
                    continue
                
                # Convert from YOLO format (normalized cx, cy, w, h)
                cx = float(parts[1]) * img_w
                cy = float(parts[2]) * img_h
                bw = float(parts[3]) * img_w
                bh = float(parts[4]) * img_h
                conf = float(parts[5]) if len(parts) >= 6 else 1.0
                
                x1 = int(round(cx - bw/2))
                y1 = int(round(cy - bh/2))
                x2 = int(round(cx + bw/2))
                y2 = int(round(cy + bh/2))
                
                # Clip to image bounds
                x1 = max(0, min(x1, img_w - 1))
                x2 = max(0, min(x2, img_w - 1))
                y1 = max(0, min(y1, img_h - 1))
                y2 = max(0, min(y2, img_h - 1))
                
                if x2 <= x1 or y2 <= y1:
                    continue
                
                dets.append({
                    "cls_name": cls_name,
                    "conf": conf,
                    "bbox_xyxy": [x1, y1, x2, y2],
                    "y0": y1,
                    "h": y2 - y1
                })
        
        return dets
    
    def _dedup_detections(self, dets: List[Dict], iou_thresh: float = 0.90) -> List[Dict]:
        """Remove duplicate detections, prioritizing Formula over Table/Picture"""
        if not dets:
            return []
        
        kept = []
        used = [False] * len(dets)
        
        for i in range(len(dets)):
            if used[i]:
                continue
            
            a = dets[i]
            group = [i]
            
            # Find overlapping boxes
            for j in range(i + 1, len(dets)):
                if used[j]:
                    continue
                b = dets[j]
                if self._calculate_iou(a["bbox_xyxy"], b["bbox_xyxy"]) >= iou_thresh:
                    group.append(j)
            
            # Select best detection in group
            candidates = [dets[k] for k in group]
            
            # Prioritize Formula
            formulas = [c for c in candidates if c["cls_name"] == "Formula"]
            if formulas:
                best = max(formulas, key=lambda x: x["conf"])
            else:
                best = max(candidates, key=lambda x: x["conf"])
            
            kept.append(best)
            for k in group:
                used[k] = True
        
        return kept
    
    @staticmethod
    def _calculate_iou(box_a: List[int], box_b: List[int]) -> float:
        """Calculate IoU between two bounding boxes"""
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b
        
        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)
        
        iw = max(0, ix2 - ix1)
        ih = max(0, iy2 - iy1)
        inter = iw * ih
        
        if inter <= 0:
            return 0.0
        
        area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
        area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
        union = area_a + area_b - inter
        
        return inter / (union + 1e-6)
    
    def _extract_content(
        self, 
        page_images: List[Path], 
        detections: Dict[str, List[Dict]]
    ) -> List[str]:
        """Extract text and images from PDF pages"""
        doc = fitz.open(str(self.pdf_path))
        linear_text = []
        
        for i in tqdm(range(len(doc)), desc="Extracting content"):
            page_num = i + 1
            stem = f"page_{page_num:04d}"
            linear_text.append(f"[--- PAGE {page_num} ---]")
            
            img_path = page_images[i]
            img = cv2.imread(str(img_path))
            
            if img is None:
                # Fallback to full text extraction
                full_text = doc[i].get_text("text") or ""
                linear_text.extend(full_text.splitlines())
                linear_text.append("")
                continue
            
            img_h, img_w = img.shape[:2]
            page_dets = detections.get(stem, [])
            
            if not page_dets:
                full_text = doc[i].get_text("text") or ""
                linear_text.extend(full_text.splitlines())
                linear_text.append("")
                continue
            
            # Sort detections by Y position and height
            sorted_dets = self._sort_blocks(page_dets)
            
            # Extract text and images
            page_text = []
            pdf_page = doc[i]
            
            for det in sorted_dets:
                if det["cls_name"] in self.IMAGE_CLASSES:
                    # Save image and add placeholder
                    image_id = self._save_image(img, det, stem)
                    page_text.append(f"<image_{image_id}>")
                else:
                    # Extract text from bbox
                    text = self._extract_text_from_bbox(
                        pdf_page, det["bbox_xyxy"], img_w, img_h
                    )
                    if text:
                        page_text.append(text)
            
            linear_text.extend(page_text)
            linear_text.append("")
        
        doc.close()
        return linear_text
    
    def _sort_blocks(self, blocks: List[Dict], eps_y: int = 5) -> List[Dict]:
        """Sort blocks by Y position, then by height"""
        blocks = sorted(blocks, key=lambda d: (d["y0"], -d["h"]))
        
        result = []
        i = 0
        n = len(blocks)
        
        while i < n:
            j = i + 1
            group = [blocks[i]]
            
            # Group blocks at similar Y position
            while j < n and abs(blocks[j]["y0"] - blocks[i]["y0"]) <= eps_y:
                group.append(blocks[j])
                j += 1
            
            # Sort group by height (taller first), then X position
            group.sort(key=lambda d: (-d["h"], d["bbox_xyxy"][0]))
            result.extend(group)
            i = j
        
        return result
    
    def _save_image(self, img: Any, det: Dict, page_stem: str) -> int:
        """Crop and save image region, return image ID"""
        x1, y1, x2, y2 = det["bbox_xyxy"]
        crop = img[y1:y2, x1:x2]
        
        if crop.size == 0:
            logger.warning(f"Empty crop region on {page_stem}: {det['bbox_xyxy']}")
            return -1
        
        image_id = self.image_counter
        
        # Save locally first
        img_filename = f"{image_id}.png"
        local_img_path = self.images_dir / img_filename
        cv2.imwrite(str(local_img_path), crop)
        
        self.image_counter += 1
        logger.debug(f"Saved image {image_id}: {img_filename}")
        
        return image_id
    
    def _extract_text_from_bbox(
        self, 
        pdf_page: Any, 
        bbox_xyxy: List[int], 
        img_w: int, 
        img_h: int
    ) -> str:
        """Extract text from PDF page within bounding box"""
        x1, y1, x2, y2 = bbox_xyxy
        
        # Convert image coordinates to PDF coordinates
        pdf_w = pdf_page.rect.width
        pdf_h = pdf_page.rect.height
        sx = pdf_w / img_w
        sy = pdf_h / img_h
        
        rect = fitz.Rect(x1 * sx, y1 * sy, x2 * sx, y2 * sy)
        text = pdf_page.get_text("text", clip=rect) or ""
        
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines).strip()
    
    def _split_chapters(self, linear_text: List[str]) -> List[Dict[str, Any]]:
        """Split linear text into chapters based on headings"""
        chapters = []
        current = {"title": "Chương 0. Mở đầu", "content": []}
        
        i = 0
        n = len(linear_text)
        
        while i < n:
            line = linear_text[i]
            stripped = (line or "").strip()
            
            # Check if this is a page marker
            if self.CHAPTER_PATTERNS['page_mark'].match(stripped):
                # Look ahead for chapter/appendix heading
                new_chapter = self._detect_chapter_heading(linear_text, i)
                
                if new_chapter:
                    # Save current chapter
                    if current["content"] or chapters:
                        chapters.append(current.copy())
                    # Start new chapter
                    current = new_chapter
                    i += 1
                    continue
            
            # Add line to current chapter
            current["content"].append(line)
            i += 1
        
        # Save last chapter
        if current["content"] or not chapters:
            chapters.append(current)
        
        # Handle single chapter case
        if len(chapters) == 1 and chapters[0]["title"] == "Chương 0. Mở đầu":
            chapters[0]["title"] = "Chương 0. Toàn văn"
        
        return chapters
    
    def _detect_chapter_heading(
        self, 
        lines: List[str], 
        page_idx: int, 
        lookahead: int = 8
    ) -> Optional[Dict[str, Any]]:
        """Detect chapter or appendix heading after page marker"""
        # Find next non-empty line
        next_idx = self._find_next_non_empty(lines, page_idx, lookahead)
        if next_idx is None:
            return None
        
        candidate = (lines[next_idx] or "").strip()
        
        # Try appendix patterns first
        m = self.CHAPTER_PATTERNS['appendix_inline'].match(candidate)
        if m:
            app_id = m.group(1)
            title = m.group(2).strip()
            return {
                "title": f"Phụ lục {app_id}. {title}" if title else f"Phụ lục {app_id}",
                "content": []
            }
        
        m = self.CHAPTER_PATTERNS['appendix_only'].match(candidate)
        if m:
            # Look for title on next line
            title_idx = self._find_next_non_empty(lines, next_idx, 6)
            if title_idx:
                title_line = (lines[title_idx] or "").strip()
                if not self._is_heading_marker(title_line):
                    app_id = m.group(1)
                    return {
                        "title": f"Phụ lục {app_id}. {title_line}",
                        "content": []
                    }
        
        # Try chapter patterns
        m = self.CHAPTER_PATTERNS['chapter_inline'].match(candidate)
        if m:
            ch_num = m.group(1)
            title = m.group(2).strip()
            return {
                "title": f"Chương {ch_num}. {title}" if title else f"Chương {ch_num}",
                "content": []
            }
        
        m = self.CHAPTER_PATTERNS['chapter_only'].match(candidate)
        if m:
            # Look for title on next line
            title_idx = self._find_next_non_empty(lines, next_idx, 6)
            if title_idx:
                title_line = (lines[title_idx] or "").strip()
                if not self._is_heading_marker(title_line):
                    ch_num = m.group(1)
                    return {
                        "title": f"Chương {ch_num}. {title_line}",
                        "content": []
                    }
        
        return None
    
    def _find_next_non_empty(
        self, 
        lines: List[str], 
        start_idx: int, 
        max_steps: int = 8
    ) -> Optional[int]:
        """Find index of next non-empty line"""
        i = start_idx + 1
        steps = 0
        while i < len(lines) and steps < max_steps:
            if (lines[i] or "").strip():
                return i
            i += 1
            steps += 1
        return None
    
    def _is_heading_marker(self, line: str) -> bool:
        """Check if line is a heading marker (page, chapter, appendix)"""
        patterns = [
            self.CHAPTER_PATTERNS['page_mark'],
            self.CHAPTER_PATTERNS['chapter_only'],
            self.CHAPTER_PATTERNS['appendix_only'],
        ]
        return any(p.match(line) for p in patterns)
    
    def _save_results(self, chapters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Save processing results to S3"""
        result = {
            "book_name": self.book_name,
            "pdf_path": str(self.pdf_path),
            "total_chapters": len(chapters),
            "total_images": self.image_counter,
            "chapters": []
        }
        
        for idx, chapter in enumerate(chapters):
            # Extract image IDs from content
            content_text = "\n".join(chapter["content"])
            image_ids = self._extract_image_ids(content_text)
            
            result["chapters"].append({
                "chapter_id": idx,
                "title": chapter["title"],
                "content": content_text,
                "image_count": len(image_ids),
                "image_ids": image_ids
            })
        
        # Upload JSON to S3
        json_s3_key = f"{self.s3_prefix}/{self.book_name}.json"
        self.s3_client.write_json(json_s3_key, result)
        logger.info(f"Uploaded JSON to s3://{self.s3_client.bucket_name}/{json_s3_key}")
        
        # Upload all images to S3
        logger.info(f"Uploading {self.image_counter} images to S3...")
        for img_file in tqdm(list(self.images_dir.glob("*.png")), desc="Uploading images"):
            s3_key = f"{self.s3_prefix}/images/{img_file.name}"
            self.s3_client.upload_file(str(img_file), s3_key)
        
        logger.info(f"All files uploaded to S3: s3://{self.s3_client.bucket_name}/{self.s3_prefix}/")
        return result
    
    def _cleanup_temp_files(self):
        """Clean up temporary processing files"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Error cleaning up temp files: {str(e)}")
    
    @staticmethod
    def _extract_image_ids(text: str) -> List[int]:
        """Extract all image IDs from text"""
        pattern = re.compile(r"<image_(\d+)>")
        matches = pattern.findall(text)
        return [int(m) for m in matches]
