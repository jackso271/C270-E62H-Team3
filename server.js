const express = require("express");
const sqlite3 = require("sqlite3").verbose();
const jwt = require("jsonwebtoken");
const cors = require("cors");

const app = express();

// ======================
// CORS
// ======================
app.use(cors({
    origin: ["http://127.0.0.1:5500", "http://localhost:5500"],
    methods: ["GET", "POST", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"]
}));

app.use(express.json());

// ======================
// CONFIG
// ======================
const JWT_SECRET = "secretkey";

// ======================
// DATABASE
// ======================
const db = new sqlite3.Database("./database.db");

db.serialize(() => {

    db.run(`
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    `);

    db.run(`
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    `);

});

// ======================
// AUTH MIDDLEWARE
// ======================
function verifyToken(req, res, next) {

    const authHeader = req.headers["authorization"];

    const token = authHeader && authHeader.split(" ")[1];

    if (!token) {
        return res.status(401).send("No token provided");
    }

    jwt.verify(token, JWT_SECRET, (err, user) => {

        if (err) {
            return res.status(403).send("Invalid token");
        }

        req.user = user;

        next();
    });
}

// ======================
// REGISTER
// ======================
app.post("/register", (req, res) => {

    const { name, email, password } = req.body;

    const rpEmailRegex = /^\d{8}@myrp\.edu\.sg$/;

    if (!name || !email || !password) {
        return res.status(400).send("All fields required");
    }

    if (!rpEmailRegex.test(email)) {
        return res.status(403).send("Use RP email format");
    }

    db.run(
        `INSERT INTO users (name, email, password)
         VALUES (?, ?, ?)`,
        [name, email, password],

        function (err) {

            if (err) {
                return res.status(400).send("User already exists");
            }

            res.send("User registered successfully");
        }
    );
});

// ======================
// LOGIN
// ======================
app.post("/login", (req, res) => {

    const { email, password } = req.body;

    db.get(
        `SELECT * FROM users
         WHERE email = ? AND password = ?`,
        [email, password],

        (err, user) => {

            if (err) {
                return res.status(500).send("Server error");
            }

            if (!user) {
                return res.status(401).send("Invalid credentials");
            }

            const token = jwt.sign(
                {
                    id: user.id,
                    name: user.name
                },
                JWT_SECRET
            );

            res.json({
                token,
                user
            });
        }
    );
});

// ======================
// GET USERS
// ======================
app.get("/users", verifyToken, (req, res) => {

    db.all(
        `SELECT id, name, email FROM users`,
        [],

        (err, rows) => {

            if (err) {
                return res.status(500).send("Error fetching users");
            }

            res.json(rows);
        }
    );
});

// ======================
// SEND MESSAGE
// ======================
app.post("/send", verifyToken, (req, res) => {

    const { receiver_id, message } = req.body;

    if (!receiver_id || !message) {
        return res.status(400).send("Message required");
    }

    db.run(
        `INSERT INTO messages
        (sender_id, receiver_id, message)
        VALUES (?, ?, ?)`,
        [req.user.id, receiver_id, message],

        function (err) {

            if (err) {
                return res.status(500).send("Error sending message");
            }

            res.send("Message sent");
        }
    );
});

// ======================
// CHAT LIST
// ======================
app.get("/chat-list", verifyToken, (req, res) => {

    const sql = `
        SELECT DISTINCT users.id,
        users.name,
        users.email

        FROM users

        JOIN messages
        ON (
            users.id = messages.sender_id
            OR users.id = messages.receiver_id
        )

        WHERE (
            messages.sender_id = ?
            OR messages.receiver_id = ?
        )

        AND users.id != ?
    `;

    db.all(
        sql,
        [req.user.id, req.user.id, req.user.id],

        (err, rows) => {

            if (err) {
                return res.status(500).send("Error loading chats");
            }

            res.json(rows);
        }
    );
});

// ======================
// GET CONVERSATION
// ======================
app.get("/conversation/:userId", verifyToken, (req, res) => {

    const sql = `
        SELECT messages.*,
        users.name AS sender_name

        FROM messages

        JOIN users
        ON messages.sender_id = users.id

        WHERE
        (sender_id = ? AND receiver_id = ?)

        OR

        (sender_id = ? AND receiver_id = ?)

        ORDER BY timestamp ASC
    `;

    db.all(
        sql,
        [
            req.user.id,
            req.params.userId,

            req.params.userId,
            req.user.id
        ],

        (err, rows) => {

            if (err) {
                return res.status(500).send("Error fetching messages");
            }

            res.json(rows);
        }
    );
});

// ======================
// START SERVER
// ======================
app.listen(3000, () => {

    console.log("Server running on port 3000");

});