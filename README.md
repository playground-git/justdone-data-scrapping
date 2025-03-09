# Data Scraping for Research Papers

A data pipeline for scraping, processing, and translating research papers.

## Quick Setup

NOTE: This instruction is not comprehensive, but if you have any doubts - feel free to ask.
You need to have GCP account, python and pip installed, Terraform, Docker

1. **GCP Setup**
   - Create GCP project: `gcloud projects create <project-id>`
   - Enable APIs: Vertex AI, Cloud Storage
   - Create service account with Storage Admin and Storage Object Admin roles
   - Download key as `service-account.json` (or other name, doesn't matter)

2. **Environment Setup**
   ```bash
   # set environment variables
   export GCP_PROJECT_ID=<project-id>
   export GCS_BUCKET_NAME=<bucket-name>
   export GOOGLE_APPLICATION_CREDENTIALS=<path to service account key>
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Set correct Terraform variables and create infrastructure**
    ```bash
    cd terraform
    terraform apply
    ```

4. **Create and run database in Docker container**
    ```bash
    make db-up
    ```

5. **Run test pipeline**
    ```bash
    python3 src/pipeline.py
    ```

Hope I didn't forget anything from the config process😅

## Architecture
See [architecture documentation](./docs/architecture.md) for detailed design and component interactions.

## Customization
Edit src/pipeline.py to modify:
- Categories to scrape
- Date ranges
- Batch sizes
- Translation models
