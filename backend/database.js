// backend/database.js
// SQLite setup and seed data
// This file is shared by all routes

const Database = require('better-sqlite3');
const db = new Database('app.db');

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role  TEXT DEFAULT 'buyer'
  );

  CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id   INTEGER NOT NULL,
    name        TEXT NOT NULL,
    description TEXT,
    price       REAL NOT NULL,
    status      TEXT DEFAULT 'Available',
    FOREIGN KEY (seller_id) REFERENCES users(id)
  );
`);

// Seed test data on first run
const userCount = db.prepare('SELECT COUNT(*) as count FROM users').get();
if (userCount.count === 0) {
  db.prepare("INSERT INTO users (name, email, role) VALUES (?, ?, ?)").run('Oliver', 'oliver@test.com', 'seller');
  db.prepare("INSERT INTO users (name, email, role) VALUES (?, ?, ?)").run('Alice', 'alice@test.com', 'buyer');

  const insert = db.prepare(
    "INSERT INTO products (seller_id, name, description, price, status) VALUES (?, ?, ?, ?, ?)"
  );
  insert.run(1, 'Calculus Textbook', 'Good condition, minor highlights', 25.00, 'Available');
  insert.run(1, 'Laptop Stand', 'Adjustable aluminium stand', 40.00, 'Sold');
  insert.run(1, 'Scientific Calculator', 'Casio FX-991, barely used', 15.00, 'Available');
}

module.exports = db;
