import client from './client';

export const embeddingService = {
    scanAndIndex: async () => {
        const response = await client.post('/embedding/scan-and-index');
        return response.data;
    },

    indexBook: async (bookName, userId, forceReindex = false) => {
        const response = await client.post('/embedding/index-book', {
            book_name: bookName,
            user_id: userId,
            force_reindex: forceReindex,
        });
        return response.data;
    },

    listCollections: async () => {
        const response = await client.get('/embedding/collections');
        return response.data;
    },

    getCollection: async (collectionName) => {
        const response = await client.get(`/embedding/collection/${collectionName}`);
        return response.data;
    },

    search: async (collectionName, query, limit = 10, scoreThreshold = null) => {
        const response = await client.post('/embedding/search', {
            collection_name: collectionName,
            query,
            limit,
            score_threshold: scoreThreshold,
        });
        return response.data;
    },

    deleteCollection: async (collectionName) => {
        const response = await client.delete(`/embedding/collection/${collectionName}`);
        return response.data;
    },

    health: async () => {
        const response = await client.get('/embedding/health');
        return response.data;
    },
};
