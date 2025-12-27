import client from './client';

export const agentService = {
    chat: async (userId, sessionId, query, dbName = null) => {
        const response = await client.post('/agent/chat', {
            user_id: userId,
            session_id: sessionId,
            query,
            db_name: dbName,
        });
        return response.data;
    },

    deleteSession: async (userId, sessionId) => {
        const response = await client.delete(`/agent/session/${userId}/${sessionId}`);
        return response.data;
    },
};
