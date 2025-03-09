import logging
from io import BytesIO
from typing import Optional

import PyPDF2

logger = logging.getLogger(__name__)


def extract_text(pdf_content: bytes) -> Optional[str]:
    """Extract text from PDF content (basic version)"""
    try:
        pdf_file = BytesIO(pdf_content)
        reader = PyPDF2.PdfReader(pdf_file)

        text_parts = []
        for page_num in range(len(reader.pages)):
            try:
                page = reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num}: {str(e)}")
                continue

        full_text = "\n\n".join(text_parts)

        # NOTE: Basic cleaning. Of course it's not enough, but still it's just to show how the pipeline should look like
        full_text = full_text.strip()

        if not full_text:
            logger.warning("No text could be extracted from the PDF")
            return None

        logger.info(f"Successfully extracted {len(full_text)} characters from PDF")
        return full_text

    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {str(e)}")
        return None
