import axios from 'axios';

const API_URL = 'http://localhost:8000'; // Adjust if backend runs on different port

const client = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export default client;
