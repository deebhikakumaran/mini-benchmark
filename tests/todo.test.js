const request = require('supertest');
const { app, server } = require('../app/app');

describe('POST /add', () => {
    test('should add a valid todo', async () => {
        const response = await request(server)
            .post('/add')
            .send({ item: 'hello' });
        expect(response.status).toBe(201);
        expect(response.body.todos).toContain('hello');
    });

    test('should add a short todo item', async () => {
        const response = await request(server)
            .post('/add')
            .send({ item: 'hi' });
        
        expect(response.status).toBe(201);
        expect(response.body.todos).toContain('hi');
    });
});