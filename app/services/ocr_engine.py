"""OCR Engine service using PaddleOCR with CPU optimization."""
import os
import re
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from app.core.config import get_settings

settings = get_settings()

# Lazy-load PaddleOCR to avoid import overhead
_ocr_engine = None


def get_ocr_engine():
    """Get or initialize the PaddleOCR engine (singleton)."""
    global _ocr_engine
    if _ocr_engine is None:
        from paddleocr import PaddleOCR
        _ocr_engine = PaddleOCR(
            use_angle_cls=True,
            lang=settings.OCR_LANG,
            use_gpu=settings.OCR_USE_GPU,
            show_log=False,
            enable_mkldnn=True,      # Intel MKL-DNN acceleration for CPU
            cpu_threads=4,           # Limit threads for consumer hardware
            # NOTE: Do NOT specify model dirs unless you have manually 
            # downloaded and extracted models. Let PaddleOCR auto-download.
        )
    return _ocr_engine


def convert_pdf_to_images(pdf_path: str, dpi: int = 200) -> List[str]:
    """Convert PDF pages to images for OCR processing."""
    image_paths = []
    doc = fitz.open(pdf_path)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page.get_pixmap(matrix=mat)
        
        img_path = f"{pdf_path}_page_{page_num}.png"
        pix.save(img_path)
        image_paths.append(img_path)
    
    doc.close()
    return image_paths


def preprocess_image(image_path: str) -> str:
    """Preprocess image for better OCR accuracy."""
    img = Image.open(image_path)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Resize if too large
    max_dimension = 3000
    if max(img.size) > max_dimension:
        ratio = max_dimension / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    
    # Enhance contrast
    from PIL import ImageEnhance
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.2)
    
    processed_path = image_path.replace(".png", "_processed.png")
    img.save(processed_path, 'PNG')
    return processed_path


def extract_text_from_image(image_path: str) -> Tuple[List[Any], float]:
    """Run OCR on a single image."""
    ocr = get_ocr_engine()
    start_time = time.time()
    
    result = ocr.ocr(image_path, cls=True)
    processing_time = (time.time() - start_time) * 1000
    
    return result, processing_time


def parse_invoice_text(ocr_results: List[Any], raw_text: str) -> Dict[str, Any]:
    """Parse OCR text into structured invoice data."""
    invoice_data = {
        "invoice_id": None,
        "vendor_name": None,
        "vendor_address": None,
        "vendor_email": None,
        "vendor_phone": None,
        "date": None,
        "due_date": None,
        "customer_name": None,
        "customer_address": None,
        "line_items": [],
        "subtotal": None,
        "tax": None,
        "tax_rate": None,
        "discount": None,
        "total_amount": None,
        "currency": None,
        "payment_terms": None,
        "notes": None
    }
    
    if not ocr_results or not ocr_results[0]:
        return invoice_data
    
    text_lines = []
    for line in ocr_results[0]:
        if line:
            bbox = line[0]
            text_info = line[1]
            text = text_info[0]
            confidence = text_info[1]
            text_lines.append({"text": text, "confidence": confidence, "bbox": bbox})
    
    full_text = " ".join([line["text"] for line in text_lines])
    
    # Invoice ID
    for pattern in [
        r'(?:Invoice|Inv|Bill)\s*(?:#|No|Number|Num|ID)?[:\s#]*([A-Z0-9\-]{3,20})',
        r'(?:Invoice|Inv)\s*(?:#|No)?[:\s#]*([0-9]{3,10})',
        r'INV[\-\s]?([0-9]{3,10})',
    ]:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            invoice_data["invoice_id"] = match.group(1).strip()
            break
    
    # Date
    for pattern in [
        r'(?:Date|Invoice Date|Issued)[:\s]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})',
        r'(?:Date|Invoice Date)[:\s]*([A-Za-z]{3,9}\s+[0-9]{1,2},?\s+[0-9]{4})',
    ]:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            invoice_data["date"] = match.group(1).strip()
            break
    
    # Due date
    for pattern in [
        r'(?:Due Date|Payment Due|Due By)[:\s]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})',
        r'(?:Due Date)[:\s]*([A-Za-z]{3,9}\s+[0-9]{1,2},?\s+[0-9]{4})',
    ]:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            invoice_data["due_date"] = match.group(1).strip()
            break
    
    # Amounts
    for pattern, field in [
        (r'(?:Total|Amount Due|Grand Total|Balance Due)[:\s]*[$\u20ac\u00a3\u00a5]?\s*([0-9,]+\.?[0-9]{0,2})', "total_amount"),
        (r'(?:Subtotal|Sub-Total)[:\s]*[$\u20ac\u00a3\u00a5]?\s*([0-9,]+\.?[0-9]{0,2})', "subtotal"),
        (r'(?:Tax|VAT|GST|Sales Tax)[:\s]*[$\u20ac\u00a3\u00a5]?\s*([0-9,]+\.?[0-9]{0,2})', "tax"),
        (r'(?:Discount|Disc)[:\s]*[$\u20ac\u00a3\u00a5]?\s*([0-9,]+\.?[0-9]{0,2})', "discount"),
    ]:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            try:
                invoice_data[field] = float(match.group(1).replace(",", ""))
            except ValueError:
                pass
    
    # Tax rate
    match = re.search(r'(?:Tax Rate|VAT Rate)[:\s]*([0-9]{1,2}\.?[0-9]{0,2})\s*%', full_text, re.IGNORECASE)
    if match:
        try:
            invoice_data["tax_rate"] = float(match.group(1))
        except ValueError:
            pass
    
    # Currency
    for symbol, code in {'$': 'USD', '\u20ac': 'EUR', '\u00a3': 'GBP', '\u00a5': 'JPY'}.items():
        if symbol in full_text:
            invoice_data["currency"] = code
            break
    
    # Vendor name
    for pattern in [
        r'^([A-Z][A-Za-z0-9\s&.,]+(?:Inc|LLC|Ltd|Limited|Corp|Corporation|Company|Co\.?|GmbH|BV|PLC))',
        r'(?:From|Seller|Vendor|Billed By)[:\s]*([A-Za-z0-9\s&.,]+)',
    ]:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            invoice_data["vendor_name"] = match.group(1).strip()
            break
    
    if not invoice_data["vendor_name"] and text_lines:
        invoice_data["vendor_name"] = text_lines[0]["text"]
    
    # Customer name
    match = re.search(r'(?:To|Bill To|Customer|Client)[:\s]*([A-Za-z0-9\s&.,]+)', full_text, re.IGNORECASE)
    if match:
        invoice_data["customer_name"] = match.group(1).strip()
    
    # Email
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', full_text)
    if emails:
        invoice_data["vendor_email"] = emails[0]
    
    # Phone
    match = re.search(r'(?:Tel|Phone)[:\s]*([0-9\-\(\)\s\.+]{7,20})', full_text, re.IGNORECASE)
    if match:
        invoice_data["vendor_phone"] = match.group(1).strip()
    
    # Line items
    seen = set()
    for pattern in [
        r'([A-Za-z0-9\s\-\.]+)\s+(\d+)\s+[$\u20ac\u00a3\u00a5]?\s*([0-9,]+\.?[0-9]{0,2})\s+[$\u20ac\u00a3\u00a5]?\s*([0-9,]+\.?[0-9]{0,2})',
        r'([A-Za-z0-9\s\-\.]{3,50})\s+(\d+(?:\.\d{1,2})?)\s+x\s+[$\u20ac\u00a3\u00a5]?\s*([0-9,]+\.?[0-9]{0,2})',
    ]:
        for m in re.finditer(pattern, full_text, re.IGNORECASE):
            desc = m.group(1).strip()
            if desc not in seen and len(desc) > 3:
                seen.add(desc)
                try:
                    invoice_data["line_items"].append({
                        "description": desc,
                        "quantity": float(m.group(2)),
                        "unit_price": float(m.group(3).replace(",", "")),
                        "total": float(m.group(4).replace(",", "")) if len(m.groups()) > 3 else None
                    })
                except (ValueError, IndexError):
                    pass
    
    # Payment terms
    match = re.search(r'(?:Payment Terms|Terms)[:\s]*([A-Za-z0-9\s]+)', full_text, re.IGNORECASE)
    if match:
        invoice_data["payment_terms"] = match.group(1).strip()
    
    # Notes
    match = re.search(r'(?:Notes|Memo|Description)[:\s]*(.{10,200})', full_text, re.IGNORECASE)
    if match:
        invoice_data["notes"] = match.group(1).strip()
    
    return invoice_data


async def process_document(file_path: str, progress_callback=None) -> Dict[str, Any]:
    """Process a document through OCR and return structured data."""
    start_time = time.time()
    file_ext = Path(file_path).suffix.lower()
    
    if progress_callback:
        await progress_callback(5, "Initializing OCR engine...")
    
    get_ocr_engine()
    
    if progress_callback:
        await progress_callback(10, "Analyzing document...")
    
    if file_ext == '.pdf':
        if progress_callback:
            await progress_callback(15, "Converting PDF to images...")
        image_paths = convert_pdf_to_images(file_path)
    else:
        image_paths = [file_path]
    
    total_pages = len(image_paths)
    all_results = []
    all_raw_text = []
    total_processing_time = 0
    
    for i, img_path in enumerate(image_paths):
        page_progress = 20 + (60 * (i / total_pages))
        if progress_callback:
            await progress_callback(int(page_progress), f"Processing page {i+1} of {total_pages}...")
        
        processed_path = preprocess_image(img_path)
        result, proc_time = extract_text_from_image(processed_path)
        total_processing_time += proc_time
        
        if result and result[0]:
            all_results.extend(result[0])
            page_text = "\n".join([line[1][0] for line in result[0] if line])
            all_raw_text.append(f"--- Page {i+1} ---\n{page_text}")
        
        if processed_path != img_path and os.path.exists(processed_path):
            os.remove(processed_path)
    
    if progress_callback:
        await progress_callback(85, "Parsing invoice data...")
    
    full_raw_text = "\n\n".join(all_raw_text)
    structured_data = parse_invoice_text(all_results, full_raw_text)
    
    if progress_callback:
        await progress_callback(95, "Finalizing results...")
    
    total_time = int((time.time() - start_time) * 1000)
    
    if progress_callback:
        await progress_callback(100, "Complete!")
    
    return {
        "structured_data": structured_data,
        "raw_text": full_raw_text,
        "processing_time_ms": total_time,
        "pages_processed": total_pages,
        "text_blocks_detected": len(all_results)
    }