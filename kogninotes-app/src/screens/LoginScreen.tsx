// src/screens/LoginScreen.tsx
import React, { useState } from 'react';
import {
    View,
    Text,
    StyleSheet,
    KeyboardAvoidingView,
    Platform,
    ScrollView,
    Alert,
    Image,
    TouchableOpacity
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { colors, lightColors, spacing, borderRadius } from '../theme/colors';
import { LinearGradient } from 'expo-linear-gradient';

export const LoginScreen = ({ navigation }: any) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const { signIn, isDarkMode } = useAuth();

    const theme = isDarkMode ? colors : lightColors;

    const handleLogin = async () => {
        if (!email || !password) {
            Alert.alert('Error', 'Por favor completa todos los campos');
            return;
        }

        setLoading(true);
        try {
            await signIn(email, password);
        } catch (error) {
            Alert.alert('Error de acceso', 'Credenciales incorrectas o problema de conexión');
        } finally {
            setLoading(false);
        }
    };

    return (
        <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            style={[styles.container, { backgroundColor: theme.background }]}
        >
            <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
                <View style={styles.header}>
                    <Image
                        source={require('../../assets/logo-simple.png')}
                        style={styles.logo}
                        resizeMode="contain"
                    />
                    <Text style={[styles.title, { color: theme.text }]}>Kognito</Text>
                    <Text style={styles.titleSuffix}>Notes</Text>
                    <Text style={[styles.subtitle, { color: theme.textMuted }]}>Tu exocerebro digital, ahora móvil.</Text>
                </View>

                <View style={[styles.formCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
                    <Input
                        label="Correo Electrónico"
                        placeholder="ejemplo@kognito.ai"
                        value={email}
                        onChangeText={setEmail}
                        keyboardType="email-address"
                        autoCapitalize="none"
                    />
                    <Input
                        label="Contraseña"
                        placeholder="••••••••"
                        value={password}
                        onChangeText={setPassword}
                        secureTextEntry
                    />

                    <TouchableOpacity activeOpacity={0.8} onPress={handleLogin} disabled={loading}>
                        <LinearGradient
                            colors={[theme.primary, theme.primaryLight]}
                            start={{ x: 0, y: 0 }}
                            end={{ x: 1, y: 0 }}
                            style={styles.loginButton}
                        >
                            <Text style={styles.loginButtonText}>
                                {loading ? 'Iniciando sesión...' : 'Entrar al Sistema'}
                            </Text>
                        </LinearGradient>
                    </TouchableOpacity>

                    <View style={styles.divider}>
                        <View style={[styles.line, { backgroundColor: theme.border }]} />
                        <Text style={[styles.dividerText, { color: theme.textMuted }]}>o también</Text>
                        <View style={[styles.line, { backgroundColor: theme.border }]} />
                    </View>

                    <Button
                        title="Acceder con Telegram"
                        onPress={() => navigation.navigate('TelegramLogin')}
                        variant="outline"
                        style={{ ...styles.telegramButton, borderColor: theme.primary }}
                    />
                </View>

                <View style={styles.footer}>
                    <Text style={[styles.footerText, { color: theme.textMuted }]}>© 2026 Kognito AI • Soberanía Cognitiva</Text>
                </View>
            </ScrollView>
        </KeyboardAvoidingView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    scrollContent: {
        flexGrow: 1,
        padding: spacing.lg,
        justifyContent: 'center',
    },
    header: {
        alignItems: 'center',
        marginBottom: spacing.xl * 1.5,
    },
    logo: {
        width: 100,
        height: 100,
        marginBottom: spacing.md,
    },
    title: {
        fontSize: 48,
        fontWeight: '900',
        textAlign: 'center',
        lineHeight: 48,
    },
    titleSuffix: {
        fontSize: 48,
        fontWeight: '900',
        color: '#6366f1',
        textAlign: 'center',
        lineHeight: 48,
        marginTop: -5,
    },
    subtitle: {
        fontSize: 16,
        marginTop: spacing.md,
        textAlign: 'center',
        fontWeight: '500',
    },
    formCard: {
        borderRadius: borderRadius.xl,
        padding: spacing.lg,
        borderWidth: 1,
        width: '100%',
        elevation: 10,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 10 },
        shadowOpacity: 0.3,
        shadowRadius: 20,
    },
    loginButton: {
        height: 56,
        borderRadius: borderRadius.md,
        justifyContent: 'center',
        alignItems: 'center',
        marginTop: spacing.md,
    },
    loginButtonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: 'bold',
        letterSpacing: 0.5,
    },
    divider: {
        flexDirection: 'row',
        alignItems: 'center',
        marginVertical: spacing.xl,
    },
    line: {
        flex: 1,
        height: 1,
    },
    dividerText: {
        paddingHorizontal: spacing.md,
        fontSize: 14,
        fontWeight: '600',
    },
    telegramButton: {
        marginTop: 0,
    },
    footer: {
        marginTop: spacing.xl,
        alignItems: 'center',
    },
    footerText: {
        fontSize: 12,
        fontWeight: '500',
    },
});
