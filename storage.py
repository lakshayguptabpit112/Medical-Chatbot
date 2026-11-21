import os
import io
import uuid
from datetime import datetime
from PIL import Image, ImageOps
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "medical-attachments")

# Local storage directory
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def preprocess_medical_image(image_bytes: bytes, max_dimension: int = 1600, quality: int = 85) -> bytes:
    """
    Compresses mobile camera photos by ~90-95% while keeping clinical text and lab tables crisp.
    - Fixes EXIF phone camera rotation.
    - Converts RGBA/transparency to RGB for clean JPEG output.
    - Proportionally resizes to max_dimension (1600px) using high-quality Lanczos filter.
    - Saves optimized JPEG in memory (~240KB).
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # 1. Auto-rotate based on phone camera EXIF tags (portrait vs landscape)
            img = ImageOps.exif_transpose(img)

            # 2. Normalize palette / RGBA to RGB to avoid JPEG save errors
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # 3. Proportional downscaling
            w, h = img.size
            if max(w, h) > max_dimension:
                scale = max_dimension / max(w, h)
                new_size = (int(w * scale), int(h * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # 4. Save optimized JPEG into RAM buffer
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            return output.getvalue()
    except Exception as e:
        print(f"[STORAGE WARNING]: Image preprocessing notice: {e}")
        return image_bytes  # Safely fall back to original bytes


def generate_pdf_thumbnail(pdf_input: bytes | str, output_path: str = None) -> bytes | bool | None:
    """
    Renders Page 1 of a PDF document into a high-resolution PNG thumbnail (~108 DPI).
    Accepts either raw bytes or a string file path.
    If output_path is provided, saves to disk and returns True/False.
    If output_path is None, returns PNG bytes directly.
    """
    try:
        import pypdfium2 as pdfium
        
        pdf = pdfium.PdfDocument(pdf_input)
        if len(pdf) == 0:
            return False if output_path else None
            
        page = pdf[0]
        # Render at 1.5x resolution for a clean, sharp thumbnail
        image = page.render(scale=1.5).to_pil()
        
        if output_path:
            image.save(output_path, format="PNG", optimize=True)
            return True
        else:
            out = io.BytesIO()
            image.save(out, format="PNG", optimize=True)
            return out.getvalue()
    except Exception as e:
        print(f"[STORAGE WARNING]: Could not generate PDF thumbnail: {e}")
        return False if output_path else None


def upload_medical_file(file_bytes: bytes, filename: str, mime_type: str) -> str:
    """
    Saves file to Supabase Cloud Storage (primary for persistence across host sleeps/restarts)
    with seamless local /uploads fallback if Supabase is not configured or temporarily unreachable.
    """
    safe_filename = f"{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:8]}_{filename}"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    local_path = os.path.join(UPLOAD_DIR, safe_filename)
    try:
        with open(local_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        print(f"[STORAGE LOCAL CACHE NOTICE]: {e}")

    # 1. Upload to Supabase Storage if configured (permanent cloud URLs survive Render container sleeps)
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{safe_filename}"
            headers = {
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": mime_type,
                "x-upsert": "true"
            }
            res = requests.post(upload_url, headers=headers, data=file_bytes, timeout=4)
            if res.status_code in (200, 201):
                return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{safe_filename}"
            else:
                print(f"[SUPABASE UPLOAD HTTP {res.status_code}]: {res.text}")
        except Exception as e:
            print(f"[SUPABASE UPLOAD NOTICE]: {e}")

    # 2. Local fallback
    return f"/uploads/{safe_filename}"


def delete_medical_file(file_url: str):
    """
    Deletes physical file from Supabase Storage or local disk when quota is reached.
    """
    if not file_url:
        return

    # Case 1: Supabase Storage
    if SUPABASE_URL and SUPABASE_URL in file_url:
        try:
            filename = file_url.split(f"/{SUPABASE_BUCKET}/")[-1]
            delete_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}"
            headers = {"Authorization": f"Bearer {SUPABASE_KEY}"}
            requests.delete(delete_url, headers=headers, timeout=5)
        except Exception as e:
            print(f"[SUPABASE DELETE ERROR]: {e}")
        return

    # Case 2: Local Disk
    if "/uploads/" in file_url:
        local_filename = file_url.split("/uploads/")[-1]
        local_path = os.path.join(UPLOAD_DIR, local_filename)
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception as e:
                print(f"[LOCAL FILE DELETE ERROR]: {e}")
