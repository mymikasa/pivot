CREATE TABLE IF NOT EXISTS users (
    id              BIGINT       NOT NULL AUTO_INCREMENT,
    username        VARCHAR(64)  NOT NULL,
    email           VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role_id         BIGINT       NOT NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email)
);
