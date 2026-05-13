ALTER TABLE documents
    ADD COLUMN parse_status VARCHAR(32) NOT NULL DEFAULT 'not_parsed',
    ADD COLUMN parse_task_id BIGINT NULL,
    ADD COLUMN parse_progress TINYINT UNSIGNED NOT NULL DEFAULT 0,
    ADD COLUMN parse_error TEXT NULL,
    ADD COLUMN parsed_at DATETIME NULL,
    ADD INDEX idx_documents_parse_status (parse_status),
    ADD INDEX idx_documents_parse_task_id (parse_task_id);
