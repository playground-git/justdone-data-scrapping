import asyncio
import logging
from datetime import date
from typing import Optional

from config.logging import setup_logging
from downloaders.base import BaseDownloader
from services.text_extractor import extract_text
from services.text_translator import BaseTranslator
from sources.base import BaseSource
from storage.gcs import GCSStorage
from storage.postgres import PostgresStorage

logger = logging.getLogger(__name__)


class Pipeline:
    """Coordinator for research paper processing pipeline"""

    def __init__(
        self,
        db_storage: PostgresStorage,
        gcs_storage: GCSStorage,
        source: BaseSource,
        downloader: BaseDownloader,
        translator: BaseTranslator,
        batch_size: int = 10,
    ):
        """Initialize the pipeline with required components"""
        self.db_storage = db_storage
        self.gcs_storage = gcs_storage
        self.source = source
        self.downloader = downloader
        self.translator = translator
        self.batch_size = batch_size

        logger.info(
            f"Pipeline initialized with {source.__class__.__name__} source, "
            f"{downloader.__class__.__name__} downloader, and "
            f"{translator.__class__.__name__} translator"
        )

    async def fetch_metadata(
        self,
        category: str,
        start_date: date,
        end_date: date,
        limit: Optional[int] = None,
    ) -> int:
        """Fetch paper metadata from source and store in database"""
        logger.info(
            f"Fetching metadata for category '{category}' from {start_date} to {end_date}"
        )

        papers = await self.source.fetch_papers(
            category=category, start_date=start_date, end_date=end_date, limit=limit
        )

        if not papers:
            logger.warning("No papers found matching criteria")
            return 0

        stored_count = self.db_storage.store_papers(papers)
        logger.info(f"Stored {stored_count} new papers in database")
        return stored_count

    async def process_downloads(self, limit: Optional[int] = None) -> int:
        """Download PDFs for papers and store in GCS"""
        # Get papers that need downloading
        papers = self.db_storage.get_papers_for_stage(
            "download", limit or self.batch_size
        )
        if not papers:
            logger.info("No papers found for download")
            return 0

        logger.info(f"Processing downloads for {len(papers)} papers")
        success_count = 0

        for paper in papers:
            paper_id = paper["id"]
            logger.info(f"Downloading paper {paper_id}")

            try:
                pdf_content = await self.downloader.download_paper(paper_id)
                if not pdf_content:
                    self.db_storage.update_paper(
                        paper_id, "download", error="Failed to download PDF"
                    )
                    continue

                # Upload to GCS
                source_name = self.source.__class__.__name__.lower().replace(
                    "source", ""
                )
                object_path = f"papers/{source_name}/{paper_id}.pdf"
                gcs_path = self.gcs_storage.upload_file(
                    content=pdf_content, object_path=object_path
                )

                if gcs_path:
                    # Update database with object path
                    self.db_storage.update_paper(paper_id, "download", data=object_path)
                    success_count += 1
                else:
                    self.db_storage.update_paper(
                        paper_id, "download", error="Failed to upload to GCS"
                    )
            except Exception as e:
                logger.error(
                    f"Error processing download for paper {paper_id}: {str(e)}"
                )
                self.db_storage.update_paper(paper_id, "download", error=str(e))

        logger.info(f"Successfully downloaded {success_count}/{len(papers)} papers")
        return success_count

    def process_extractions(self, limit: Optional[int] = None) -> int:
        """Extract text from PDFs"""
        # Get papers with PDFs but no extracted text
        papers = self.db_storage.get_papers_for_stage(
            "extraction", limit or self.batch_size
        )
        if not papers:
            logger.info("No papers found for text extraction")
            return 0

        logger.info(f"Processing text extraction for {len(papers)} papers")
        success_count = 0

        for paper in papers:
            paper_id = paper["id"]
            object_path = paper["pdf_object_path"]
            logger.info(f"Extracting text from paper {paper_id}")

            try:
                # Download PDF from GCS
                pdf_content = self.gcs_storage.download_file(object_path)
                if not pdf_content:
                    self.db_storage.update_paper(
                        paper_id, "extraction", error="Failed to download PDF from GCS"
                    )
                    continue

                # Extract text
                extracted_text = extract_text(pdf_content)
                if not extracted_text:
                    self.db_storage.update_paper(
                        paper_id, "extraction", error="No text could be extracted"
                    )
                    continue

                # Update database with extracted text
                self.db_storage.update_paper(
                    paper_id, "extraction", data=extracted_text
                )
                success_count += 1

            except Exception as e:
                logger.error(f"Error extracting text for paper {paper_id}: {str(e)}")
                self.db_storage.update_paper(paper_id, "extraction", error=str(e))

        logger.info(
            f"Successfully extracted text from {success_count}/{len(papers)} papers"
        )
        return success_count

    def process_translations(self, limit: Optional[int] = None) -> int:
        """Translate extracted text"""
        # Get papers with extracted text but no translation
        papers = self.db_storage.get_papers_for_stage(
            "translation", limit or self.batch_size
        )
        if not papers:
            logger.info("No papers found for translation")
            return 0

        logger.info(f"Processing translations for {len(papers)} papers")
        success_count = 0

        for paper in papers:
            paper_id = paper["id"]
            extracted_text = paper["extracted_text"]
            logger.info(f"Translating paper {paper_id}")

            try:
                # Translate text
                translated_text = self.translator.translate(extracted_text)
                if not translated_text:
                    self.db_storage.update_paper(
                        paper_id, "translation", error="Translation failed"
                    )
                    continue

                # Update database with translated text
                self.db_storage.update_paper(
                    paper_id, "translation", data=translated_text
                )
                success_count += 1

            except Exception as e:
                logger.error(f"Error translating paper {paper_id}: {str(e)}")
                self.db_storage.update_paper(paper_id, "translation", error=str(e))

        logger.info(f"Successfully translated {success_count}/{len(papers)} papers")
        return success_count

    # NOTE: this pipeline function is not perfect - it's just for testing; to make it better we need separate these components as well
    # maybe we don't want to download PDFs for all the files but for specific category. etc. I don't provide this functionality in current version of the pipeline
    async def run_full_pipeline(
        self,
        category: str,
        start_date: date,
        end_date: date,
        fetch_limit: Optional[int] = None,
        process_limit: Optional[int] = None,
    ) -> dict:
        """Run the complete pipeline"""
        logger.info(f"Starting full pipeline for category '{category}'")
        results = {
            "metadata_count": 0,
            "download_count": 0,
            "extraction_count": 0,
            "translation_count": 0,
        }

        # Step 1: Fetch metadata
        results["metadata_count"] = await self.fetch_metadata(
            category=category,
            start_date=start_date,
            end_date=end_date,
            limit=fetch_limit,
        )

        # Step 2: Download PDFs
        results["download_count"] = await self.process_downloads(limit=process_limit)

        # Step 3: Extract text
        results["extraction_count"] = self.process_extractions(limit=process_limit)

        # Step 4: Translate text
        results["translation_count"] = self.process_translations(limit=process_limit)

        logger.info(
            f"Pipeline completed: {results['metadata_count']} papers fetched, "
            f"{results['download_count']} downloaded, "
            f"{results['extraction_count']} extracted, "
            f"{results['translation_count']} translated"
        )

        return results


# ----------------------------------------------------------------------------------------------------
# TESTING
# ----------------------------------------------------------------------------------------------------


async def run_pipeline(
    category: str,
    start_date: date,
    end_date: date,
    project_id: str,
    bucket_name: str,
    limit: Optional[int] = 10,
    batch_size: int = 10,
):
    """Run the pipeline with default parameters"""
    setup_logging()

    with PostgresStorage() as db_storage:
        # NOTE: Here we use concrete implementations, but the pipeline accepts any implementation
        # that inherits from the base classes
        from downloaders.arxiv import ArxivDownloader
        from services.text_translator import VertexAITranslator
        from sources.arxiv import ArxivSource

        gcs_storage = GCSStorage(bucket_name=bucket_name)
        source = ArxivSource()
        downloader = ArxivDownloader()
        translator = VertexAITranslator(project_id=project_id)

        # Create and run pipeline
        pipeline = Pipeline(
            db_storage=db_storage,
            gcs_storage=gcs_storage,
            source=source,
            downloader=downloader,
            translator=translator,
            batch_size=batch_size,
        )

        results = await pipeline.run_full_pipeline(
            category=category,
            start_date=start_date,
            end_date=end_date,
            fetch_limit=limit,
            process_limit=batch_size,
        )

        return results


# Simple script to run the pipeline
if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()

    # Get configuration from environment or use some hard-coded values
    category = "physics.geo-ph"
    start_date = date(2025, 3, 1)
    end_date = date(2025, 3, 2)
    limit = 10
    batch_size = 10
    project_id = os.getenv("GCP_PROJECT_ID")
    bucket_name = os.getenv("GCS_BUCKET_NAME")

    results = asyncio.run(
        run_pipeline(
            category=category,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            batch_size=batch_size,
            project_id=project_id,
            bucket_name=bucket_name,
        )
    )

    print(f"Pipeline results: {results}")
