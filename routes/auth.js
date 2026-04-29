const express = require("express");
const router = express.Router();
const users = require("../data/users.json");

router.post("/login", (req, res) => {
  const { email, studentId, password } = req.body;

  if (!email && !studentId) {
    return res.status(400).json({
      message: "Please enter your RP student email or student ID"
    });
  }

  const isRpEmail = email && email.endsWith("@myrp.edu.sg");

  const user = users.find((u) => {
    return (
      (u.email === email || u.studentId === studentId) &&
      u.password === password
    );
  });

  if (!isRpEmail && !studentId) {
    return res.status(403).json({
      message: "Only RP students are allowed to log in"
    });
  }

  if (!user) {
    return res.status(401).json({
      message: "Invalid RP student login details"
    });
  }

  res.status(200).json({
    message: "Login successful",
    studentId: user.studentId,
    email: user.email
  });
});

module.exports = router;