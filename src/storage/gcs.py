import logging
from typing import Optional

from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

logger = logging.getLogger(__name__)


class GCSStorage:
    """Google Cloud Storage for research papers"""

    def __init__(self, bucket_name: str):
        """Initialize the GCS storage"""
        self.bucket_name = bucket_name

        try:
            self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
            logger.info(f"Connected to GCS bucket: {bucket_name}")
        except Exception as e:
            logger.error(f"Error connecting to GCS: {str(e)}")
            raise

    def upload_file(
        self, content: bytes, object_path: str, content_type: str = "application/pdf"
    ) -> Optional[str]:
        """Upload content to GCS bucket"""
        try:
            blob = self.bucket.blob(object_path)
            blob.upload_from_string(content, content_type=content_type)

            logger.info(f"Successfully uploaded {object_path} to {self.bucket_name}")
            return object_path
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error uploading {object_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading {object_path}: {str(e)}")
            return None

    def download_file(self, object_path: str) -> Optional[bytes]:
        """Download file content from GCS"""
        try:
            blob = self.bucket.blob(object_path)

            if not blob.exists():
                logger.error(f"Object does not exist: {object_path}")
                return None

            content = blob.download_as_bytes()
            logger.info(
                f"Successfully downloaded {len(content)} bytes from {object_path}"
            )
            return content
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error downloading {object_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading {object_path}: {str(e)}")
            return None
