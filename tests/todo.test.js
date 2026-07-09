const request = require('supertest');
const http = require('http');
const app = require('../app/app');

describe('POST /add', () => {
    test('should add a valid todo', async () => {
        const server = http.createServer(app);
        const response = await request(server)
            .post('/add')
            .send({ item: 'hello' });
        expect(response.status).toBe(201);
        expect(response.body.todos).toContain('hello');
    });

    test('should add a short todo item', async () => {
        const server = http.createServer(app);
        const response = await request(server)
            .post('/add')
            .send({ item: 'hi' });
        
        expect(response.status).toBe(201);
        expect(response.body.todos).toContain('hi');
    });
});