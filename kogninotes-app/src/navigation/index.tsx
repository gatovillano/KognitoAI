// src/navigation/index.tsx
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { useAuth } from '../context/AuthContext';
import { LoginScreen } from '../screens/LoginScreen';
import { TelegramLoginScreen } from '../screens/TelegramLoginScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { CalendarScreen } from '../screens/CalendarScreen';
import { NoteDetailScreen } from '../screens/NoteDetailScreen';
import { CreateNoteScreen } from '../screens/CreateNoteScreen';
import { ChatScreen } from '../screens/ChatScreen';
import { ActivityIndicator, View } from 'react-native';
import { colors } from '../theme/colors';

const Stack = createStackNavigator();

export const Navigation = () => {
    const { signed, loading } = useAuth();

    if (loading) {
        return (
            <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.background }}>
                <ActivityIndicator size="large" color={colors.primary} />
            </View>
        );
    }

    return (
        <NavigationContainer>
            <Stack.Navigator id="root" screenOptions={{ headerShown: false }}>
                {!signed ? (
                    <>
                        <Stack.Screen name="Login" component={LoginScreen} />
                        <Stack.Screen name="TelegramLogin" component={TelegramLoginScreen} />
                    </>
                ) : (
                    <>
                        <Stack.Screen name="Chat" component={ChatScreen} />
                        <Stack.Screen name="Home" component={HomeScreen} />
                        <Stack.Screen name="Calendar" component={CalendarScreen} />
                        <Stack.Screen name="NoteDetail" component={NoteDetailScreen} />
                        <Stack.Screen name="CreateNote" component={CreateNoteScreen} />
                    </>
                )}
            </Stack.Navigator>
        </NavigationContainer>
    );
};
