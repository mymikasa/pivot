CREATE TABLE IF NOT EXISTS documents (
    id           BIGINT       NOT NULL AUTO_INCREMENT,
    kb_id        BIGINT       NOT NULL,
    filename     VARCHAR(255) NOT NULL,
    object_key   VARCHAR(512) NOT NULL,
    content_type VARCHAR(128) NOT NULL,
    file_size    INT UNSIGNED NOT NULL,
    status       VARCHAR(32)  NOT NULL DEFAULT 'uploading',
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_object_key (object_key),
    INDEX idx_kb_id (kb_id),
    CONSTRAINT fk_doc_kb FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
);
