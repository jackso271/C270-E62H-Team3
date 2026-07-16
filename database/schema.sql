CREATE DATABASE IF NOT EXISTS rp_marketplace;

USE rp_marketplace;

CREATE TABLE IF NOT EXISTS notifications (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Info',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_notifications_created_at (created_at),
    INDEX idx_notifications_status (status)
);

CREATE TABLE IF NOT EXISTS reports (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    product_id BIGINT UNSIGNED NULL,
    product_title VARCHAR(150) NOT NULL,
    seller_identifier VARCHAR(255) NULL,
    reported_by VARCHAR(255) NULL,
    reason VARCHAR(255) NOT NULL,
    comments TEXT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME NULL,
    PRIMARY KEY (id),
    INDEX idx_reports_status (status),
    INDEX idx_reports_created_at (created_at),
    INDEX idx_reports_product_id (product_id)
);

CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    student_id VARCHAR(50) NULL,
    school VARCHAR(150) NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'student',
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME NULL,
    status_updated_at DATETIME NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_username (username),
    UNIQUE KEY uq_users_email (email),
    UNIQUE KEY uq_users_student_id (student_id),
    INDEX idx_users_role (role),
    INDEX idx_users_blocked (is_blocked)
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NULL,
    login_identifier VARCHAR(255) NOT NULL,
    was_successful BOOLEAN NOT NULL,
    failure_reason VARCHAR(255) NULL,
    attempted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_login_attempts_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE SET NULL,
    INDEX idx_login_attempts_user_time (user_id, attempted_at),
    INDEX idx_login_attempts_result_time (was_successful, attempted_at)
);

CREATE TABLE IF NOT EXISTS categories (
    id SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(80) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_categories_name (name)
);

CREATE TABLE IF NOT EXISTS products (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    seller_id BIGINT UNSIGNED NULL,
    seller_identifier VARCHAR(255) NOT NULL,
    legacy_seller_name VARCHAR(150) NULL,
    category_id SMALLINT UNSIGNED NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    image_url VARCHAR(500) NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Available',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_products_seller
        FOREIGN KEY (seller_id)
        REFERENCES users(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_products_category
        FOREIGN KEY (category_id)
        REFERENCES categories(id)
        ON DELETE SET NULL,
    INDEX idx_products_seller (seller_id),
    INDEX idx_products_seller_identifier (seller_identifier),
    INDEX idx_products_status (status),
    INDEX idx_products_category (category_id),
    CONSTRAINT chk_products_price CHECK (price >= 0)
);
