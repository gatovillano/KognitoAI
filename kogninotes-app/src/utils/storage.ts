// src/utils/storage.ts
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

export const storage = {
    async getItem(key: string): Promise<string | null> {
        if (Platform.OS === 'web') {
            try {
                return localStorage.getItem(key);
            } catch {
                return null;
            }
        }
        return await SecureStore.getItemAsync(key);
    },

    async setItem(key: string, value: string): Promise<void> {
        if (Platform.OS === 'web') {
            try {
                localStorage.setItem(key, value);
            } catch (e) {
                console.error('Error saving to localStorage', e);
            }
            return;
        }
        await SecureStore.setItemAsync(key, value);
    },

    async deleteItem(key: string): Promise<void> {
        if (Platform.OS === 'web') {
            try {
                localStorage.removeItem(key);
            } catch (e) {
                console.error('Error deleting from localStorage', e);
            }
            return;
        }
        await SecureStore.deleteItemAsync(key);
    }
};
