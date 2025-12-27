import { useState, useEffect } from 'react';

export const useAuth = () => {
    const [userId, setUserId] = useState('');

    useEffect(() => {
        let storedUserId = localStorage.getItem('user_id');
        if (!storedUserId) {
            storedUserId = 'user_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('user_id', storedUserId);
        }
        setUserId(storedUserId);
    }, []);

    return { userId };
};
