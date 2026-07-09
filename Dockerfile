# 1. Use an official Node.js runtime as a parent image
FROM node:20-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy package files first to leverage Docker layer caching
COPY package*.json ./

# 4. Install dependencies
RUN npm install

# 5. Copy the rest of your application code
COPY . .

# 6. Define the command to run the tests
CMD ["npx", "jest"]