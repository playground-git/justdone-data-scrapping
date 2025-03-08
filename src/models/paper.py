from datetime import date

from pydantic import BaseModel


class PaperMetadata(BaseModel):
    """Data model for paper metadata"""

    id: str
    authors: list[str]
    title: str
    abstract: str
    categories: list[str]
    submission_date: date
    update_date: date

    class Config:
        json_encoders = {date: lambda d: d.isoformat()}
