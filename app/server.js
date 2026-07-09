// docker build -t mini-benchmark .
// docker run --rm mini-benchmark


const app = require('./app');
const PORT = 3000;

app.listen(PORT);