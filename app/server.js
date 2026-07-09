// docker build -t mini-benchmark .
// docker run --rm mini-benchmark

const http = require('http');
const app = require('./app');

const server = http.createServer(app);

module.exports = server; 