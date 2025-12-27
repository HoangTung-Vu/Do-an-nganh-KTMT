import client from './client';

export const pdfService = {
    uploadPdf: async (file, userId) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('user_id', userId);

        const response = await client.post('/pdf/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    getStatus: async (bookName, userId) => {
        const response = await client.get(`/pdf/status/${bookName}`, {
            params: { user_id: userId },
        });
        return response.data;
    },

    getChapter: async (bookName, chapterId, userId) => {
        const response = await client.get(`/pdf/chapter/${bookName}/${chapterId}`, {
            params: { user_id: userId },
        });
        return response.data;
    },

    deleteProcessedBook: async (bookName, userId) => {
        const response = await client.delete(`/pdf/delete/${bookName}`, {
            params: { user_id: userId },
        });
        return response.data;
    },
};
