CREATE TABLE IF NOT EXISTS knowledge_bases (
    id          BIGINT       NOT NULL AUTO_INCREMENT,
    name        VARCHAR(128) NOT NULL,
    description TEXT,
    owner_id    INT          NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_name (name),
    INDEX idx_owner_id (owner_id),
    CONSTRAINT fk_kb_owner FOREIGN KEY (owner_id) REFERENCES users(id)
);
