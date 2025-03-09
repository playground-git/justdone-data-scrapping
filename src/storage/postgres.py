import json
import logging
from typing import Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from models.paper import PaperMetadata

logger = logging.getLogger(__name__)


class PostgresStorage:
    """PostgreSQL storage for research papers"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        dbname: str = "research_papers",
        user: str = "postgres",
        password: str = "postgres",
    ):
        """Initialize the PostgreSQL storage"""
        self.connection_params = {
            "host": host,
            "port": port,
            "dbname": dbname,
            "user": user,
            "password": password,
        }
        self.conn = None

    def __enter__(self):
        """Context manager entry"""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            logger.info("Connected to PostgreSQL database")
            return self
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL: {str(e)}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Closed PostgreSQL connection")
            except Exception as e:
                logger.error(f"Error closing PostgreSQL connection: {str(e)}")

    def store_papers(self, papers: list[PaperMetadata]) -> int:
        """Store papers metadata in the database"""
        if not papers:
            return 0

        stored_count = 0
        with self.conn.cursor() as cur:
            for paper in papers:
                try:
                    # Check if paper already exists
                    cur.execute("select id from papers where id = %s", (paper.id,))
                    if cur.fetchone():
                        continue

                    cur.execute(
                        """
                        insert into papers (
                            id, title, abstract, authors, categories, 
                            submission_date, update_date
                        ) values (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            paper.id,
                            paper.title,
                            paper.abstract,
                            json.dumps(paper.authors),
                            json.dumps(paper.categories),
                            paper.submission_date,
                            paper.update_date,
                        ),
                    )
                    stored_count += 1
                except Exception as e:
                    logger.error(f"Error storing paper {paper.id}: {str(e)}")

            if stored_count > 0:
                self.conn.commit()
                logger.info(f"Stored {stored_count} new papers")

        return stored_count

    def get_paper(self, paper_id: str) -> Optional[dict[str, Any]]:
        """Get a single paper by id"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("select * from papers where id = %s", (paper_id,))
                paper = cur.fetchone()

                if paper:
                    if isinstance(paper["authors"], str):
                        paper["authors"] = json.loads(paper["authors"])
                    if isinstance(paper["categories"], str):
                        paper["categories"] = json.loads(paper["categories"])

                return paper
        except Exception as e:
            logger.error(f"Error getting paper {paper_id}: {str(e)}")
            return None

    def get_papers_for_stage(self, stage: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get papers for specific processing stage (download, extraction, translation)"""
        queries = {
            "download": """
                select id
                from papers 
                where pdf_object_path is null 
                order by submission_date desc
                limit %s
            """,
            "extraction": """
                select id, pdf_object_path 
                from papers 
                where pdf_object_path is not null 
                and extracted_text is null 
                limit %s
            """,
            "translation": """
                select id, extracted_text 
                from papers 
                where extracted_text is not null 
                and translated_text is null 
                limit %s
            """,
        }

        if stage not in queries:
            logger.error(f"Invalid stage: {stage}")
            return []

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(queries[stage], (limit,))
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting papers for stage {stage}: {str(e)}")
            return []

    def update_paper(
        self,
        paper_id: str,
        stage: str,
        data: Optional[str] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Update paper processing data (PDF path, extracted text, translated text) for stages (download, extraction, translation)"""
        updates = {
            "download": {
                "success": """
                    update papers 
                    set pdf_object_path = %s, content_downloaded_at = now()
                    where id = %s
                """,
                "error": """
                    update papers 
                    set download_error = %s
                    where id = %s
                """,
            },
            "extraction": {
                "success": """
                    update papers 
                    set extracted_text = %s, text_extracted_at = now()
                    where id = %s
                """,
                "error": """
                    update papers 
                    set extraction_error = %s
                    where id = %s
                """,
            },
            "translation": {
                "success": """
                    update papers 
                    set translated_text = %s, translated_at = now()
                    where id = %s
                """,
                "error": """
                    update papers 
                    set translation_error = %s
                    where id = %s
                """,
            },
        }

        if stage not in updates:
            logger.error(f"Invalid stage: {stage}")
            return False

        try:
            with self.conn.cursor() as cur:
                if data is not None:
                    cur.execute(updates[stage]["success"], (data, paper_id))
                else:
                    cur.execute(updates[stage]["error"], (error, paper_id))
                self.conn.commit()
                return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error updating paper {paper_id} for stage {stage}: {str(e)}")
            return False
