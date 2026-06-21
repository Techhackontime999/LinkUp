import os
import logging
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False
    fitz = None


def extract_pdf_pages(attachment):
    """Extract each page of a PDF as a thumbnail image and create DocumentPage records.

    Returns the number of pages extracted, or 0 if processing is skipped.
    """
    if not HAS_FITZ:
        logger.warning("PyMuPDF not installed — skipping PDF page extraction")
        return 0

    ext = os.path.splitext(attachment.file.name)[1].lower()
    if ext != '.pdf':
        return 0

    try:
        attachment.file.seek(0)
        pdf_bytes = attachment.file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.error("Failed to open PDF %s: %s", attachment.file.name, e)
        return 0

    from .models import DocumentPage

    pages_created = 0
    for page_num in range(len(doc)):
        try:
            page = doc.load_page(page_num)

            render_params = {"matrix": fitz.Matrix(2, 2), "dpi": 144}
            pix = page.get_pixmap(**render_params)

            img_bytes = pix.tobytes("png")
            filename = f"page_{attachment.id}_{page_num + 1:03d}.png"

            page_record = DocumentPage(
                attachment=attachment,
                page_number=page_num + 1,
                width=pix.width,
                height=pix.height,
            )
            page_record.image.save(filename, ContentFile(img_bytes), save=False)
            page_record.save()
            pages_created += 1

        except Exception as e:
            logger.error("Failed to extract page %d of %s: %s", page_num + 1, attachment.file.name, e)
            continue

    doc.close()
    logger.info("Extracted %d pages from %s", pages_created, attachment.file.name)
    return pages_created
