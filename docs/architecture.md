# Architecture Overview

## System Components

This project implements modular data pipeline for research papers processing with these components:

1. **Source** - Fetches metadata from different sources (for example arXiv)
2. **Downloader** - Downloads PDF files
3. **Text Extractor** - Extracts text from PDFs
4. **Translator** - Translates text
5. **Storage** - Stores data in PostgreSQL and PDF files in GCS

## Architecture Decisions

### Modular Design
I choosed modular approach with abstract base classes for (almost) all components. This makes system flexible - we can easy replace any component (for example, switch from arXiv to Scopus) without changing pipeline logic.
Note: this is in theory, because I needed to simplify the pipeline to finish faster. I suppose that these papers on each source is in PDF format and have similar metadata information (which is not always the case for different sources).

### Asynchronous Processing
For Source and Downloader components I implemented async processing with aiohttp. This improves performance when making many HTTP requests to external APIs. Rate limiting also implemented to avoid being blocked.

### Storage Strategy
I used two storage types:
- **PostgreSQL** - For structured metadata and processing state
- **Google Cloud Storage** - For PDF files

This separation is good practice because:
1. Database not overloaded with binary data
2. GCS provides better scaling for file storage
3. We can access files directly from other services

### Error Handling
Each component has detailed error handling with multiple retry logic and exponentail backoff. Most errors are logged and some stored in database, so we can see which papers failed in processing.
Note: of course I can do better, add more error handling, better logging, etc. But it takes time, so I simplified the solution.

### State Management
The database schema designed to track state of each paper through pipeline:
- Metadata fetched
- PDF downloaded
- Text extracted
- Text translated

This allows to resume processing from any stage if pipeline fails.
Note: it's not perfect solution now, but I hope you got my idea)

## Limitations and Future Improvements

Current implementation has some limitations:
- Text extraction from PDF is pretty basic on purpose, because I think it's crucial part of the pipeline and it could be improved with more advanced algorithms. And it's the weakest part of my code( Scientific papers could have different structure with lot of formulas, graphs, images. I'm not gonna focus on that right now.
- Translation using Vertex AI could be expensive for large volumes, we can use other translation services.
- No monitoring or alerting system

For production system, I would add:
- Better monitoring
- Implement Apache Airflow for scheduling and DAG management
- Add more robust error recovery
- Implement data quality checks
- Add unit and integration tests
- There are different versions of paper; think about how to handle it.

## Data Flow

1. Fetch metadata (eg from arXiv)
2. Store metadata in PostgreSQL
3. Download PDF files for papers
4. Store PDFs in Google Cloud Storage
5. Extract text from PDFs
6. Translate text (eg using Vertex AI)
7. Store translate  text in database

And the coordinator for all these components - `src/pipeline.py`.
Code in pipeline is far from perfect, I didn't have enough time to design and implement it properly, with best practices in mind. I needed to proceed to the next task)

In general I think this architecture provides good balance between complexity and functionality for test task, while showing understanding of data engineering principles.
