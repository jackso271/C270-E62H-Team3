const express = require("express");
const app = express();
const authRoutes = require("./routes/auth");

app.use(express.json());

app.use("/api", authRoutes);

app.get("/", (req, res) => {
  res.send("API is running");
});

const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});