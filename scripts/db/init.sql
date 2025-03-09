create table if not exists papers (
    id varchar(50) primary key,
    title text not null,
    abstract text not null,
    authors jsonb not null,
    categories jsonb not null,
    submission_date date not null,
    update_date date not null,
    metadata_fetched_at timestamp with time zone default now(),
    
    pdf_object_path text,
    content_downloaded_at timestamp with time zone,
    download_error text,
    
    extracted_text text,
    text_extracted_at timestamp with time zone,
    extraction_error text,
    
    translated_text text,
    translated_at timestamp with time zone,
    translation_error text
);

create index if not exists idx_papers_submission_date on papers(submission_date);
