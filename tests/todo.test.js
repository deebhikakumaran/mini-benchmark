const request = require('supertest');
const app = require('../app/app');

console.log('DEBUG TYPE:', typeof app);
console.log('DEBUG KEYS:', Object.keys(app));

describe('POST /add', () => {
    test('should add a valid todo', async () => {
        const response = await request(app)
            .post('/add')
            .send({ item: 'hello' });
        expect(response.status).toBe(201);
        expect(response.body.todos).toContain('hello');
    });

    test('should add a short todo item', async () => {
        const response = await request(app)
            .post('/add')
            .send({ item: 'hi' });
        
        expect(response.status).toBe(201);
        expect(response.body.todos).toContain('hi');
    });
});