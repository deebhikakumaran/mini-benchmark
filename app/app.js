const express = require('express');
const app = express();
app.use(express.json());

let todos = [];

app.post('/add', (req, res) => {
    const { item } = req.body;
    if (item && item.length > 3) {
        todos.push(item);
        res.status(201).json({ success: true, todos });
    } else {
        res.status(400).json({ success: false, message: "Item too short" });
    }
});

module.exports = app; 