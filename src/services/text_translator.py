import logging
from abc import ABC, abstractmethod
from typing import List, Optional

logger = logging.getLogger(__name__)


class BaseTranslator(ABC):
    """Base class for text translation services"""

    def __init__(
        self,
        source_lang: str = "English",
        target_lang: str = "Ukrainian",
        chunk_size: int = 5000,
    ):
        """Initialize base translator"""
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.chunk_size = chunk_size

        logger.info(
            f"Initialized {self.__class__.__name__} "
            f"translating from {source_lang} to {target_lang}"
        )

    def _split_text(self, text: str) -> List[str]:
        """Split text into chunks for translation"""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        paragraphs = text.split("\n\n")
        current = ""

        for p in paragraphs:
            new_chunk = current + "\n\n" + p if current else p

            if len(new_chunk) <= self.chunk_size:
                current = new_chunk
            else:
                if current:
                    chunks.append(current)
                current = p

        if current:
            chunks.append(current)

        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks

    @abstractmethod
    def _translate_chunk(self, text: str) -> Optional[str]:
        """Translate single chunk of text"""
        pass

    def translate(self, text: str) -> Optional[str]:
        """Translate text from source language to target language"""
        if not text or not text.strip():
            logger.warning("Empty text provided for translation")
            return None

        chunks = self._split_text(text)

        translated_chunks = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Translating chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
            translated = self._translate_chunk(chunk)

            if translated:
                translated_chunks.append(translated)
            else:
                logger.error(f"Failed to translate chunk {i+1}/{len(chunks)}")
                return None

        full_translation = "\n\n".join(translated_chunks)
        logger.info(
            f"Successfully translated {len(text)} chars to {len(full_translation)} chars"
        )

        return full_translation


class VertexAITranslator(BaseTranslator):
    """Translator service using Google Cloud Vertex AI"""

    def __init__(
        self,
        project_id: str,
        location: str = "europe-central2",
        model_name: str = "gemini-1.5-pro",
        **kwargs,
    ):
        """Initialize the Vertex AI translator"""
        super().__init__(**kwargs)
        self.project_id = project_id
        self.location = location
        self.model_name = model_name

        # Initialize Vertex AI
        from google.cloud import aiplatform

        aiplatform.init(project=project_id, location=location)
        self.vertex_ai = aiplatform

        logger.info(f"Initialized VertexAITranslator with model {model_name}")

    def _translate_chunk(self, text: str) -> Optional[str]:
        """Translate single chunk of text using Vertex AI"""
        try:
            from vertexai.generative_models import GenerativeModel

            # Create the prompt for translation
            prompt = f"Translate following text from {self.source_lang} to {self.target_lang}. Preserve all formatting, including paragraphs, bullet points, and any special characters:\n\n{text}"

            model = GenerativeModel(self.model_name)
            response = model.generate_content(prompt)

            if response and response.text:
                return response.text
            else:
                logger.warning("Empty response from Vertex AI")
                return None

        except Exception as e:
            logger.error(f"Error translating with Vertex AI: {str(e)}")
            return None
