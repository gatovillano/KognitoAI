import { MongoClient } from 'mongodb';

const uri = process.env.MONGODB_URI || 'mongodb://localhost:27017';
const client = new MongoClient(uri);

async function connectToDatabase() {
  try {
    await client.connect();
    console.log('Connected to MongoDB');
    return client.db(); // Return the default database
  } catch (error) {
    console.error('Failed to connect to MongoDB', error);
    throw error;
  }
}

export { client, connectToDatabase };
