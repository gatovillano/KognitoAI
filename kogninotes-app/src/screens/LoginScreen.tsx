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
    TouchableOpacity,
    StatusBar
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
        <View style={[styles.container, { backgroundColor: theme.background }]}>
            <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />
            <LinearGradient
                colors={[theme.primary + '15', theme.background]}
                style={StyleSheet.absoluteFill}
            />
            
            <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                style={{ flex: 1 }}
            >
                <ScrollView 
                   contentContainerStyle={styles.scrollContent} 
                   showsVerticalScrollIndicator={false}
                   keyboardShouldPersistTaps="handled"
                >
                    <View style={styles.header}>
                        <View style={[styles.logoContainer, { borderColor: theme.border, backgroundColor: theme.surface }]}>
                           <Image
                               source={require('../../assets/logo-simple.png')}
                               style={styles.logo}
                               resizeMode="contain"
                           />
                        </View>
                        <View style={styles.titleRow}>
                           <Text style={[styles.title, { color: theme.text }]}>Kognito</Text>
                           <Text style={[styles.titleSuffix, { color: theme.primary }]}>.ai</Text>
                        </View>
                        <Text style={[styles.subtitle, { color: theme.textMuted }]}>Tu exocerebro digital de alta fidelidad</Text>
                    </View>

                    <View style={[styles.formCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
                        <Input
                            label="Identidad"
                            placeholder="usuario@kognito.ai"
                            value={email}
                            onChangeText={setEmail}
                            keyboardType="email-address"
                            autoCapitalize="none"
                        />
                        <Input
                            label="Llave de Acceso"
                            placeholder="••••••••"
                            value={password}
                            onChangeText={setPassword}
                            secureTextEntry
                        />

                        <TouchableOpacity activeOpacity={0.85} onPress={handleLogin} disabled={loading} style={styles.loginWrapper}>
                            <LinearGradient
                                colors={[colors.primaryLight, colors.primary]}
                                start={{ x: 0, y: 0 }}
                                end={{ x: 1, y: 0 }}
                                style={styles.loginButton}
                            >
                                <Text style={styles.loginButtonText}>
                                    {loading ? 'Sincronizando...' : 'Entrar al Sistema'}
                                </Text>
                            </LinearGradient>
                        </TouchableOpacity>

                        <View style={styles.divider}>
                            <View style={[styles.line, { backgroundColor: theme.border }]} />
                        </View>

                        <Button
                            title="Telegram Secure Login"
                            onPress={() => navigation.navigate('TelegramLogin')}
                            variant="outline"
                            style={{ ...styles.telegramButton, borderColor: theme.primary + '50' }}
                        />
                    </View>

                    <View style={styles.footer}>
                        <Text style={[styles.footerText, { color: theme.textMuted }]}>Soberanía Cognitiva Garantizada</Text>
                        <Text style={[styles.versionText, { color: theme.textMuted + '60' }]}>v1.2 • 2026</Text>
                    </View>
                </ScrollView>
            </KeyboardAvoidingView>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    scrollContent: {
        flexGrow: 1,
        padding: spacing.xl,
        justifyContent: 'center',
    },
    header: {
        alignItems: 'center',
        marginBottom: spacing.xl * 1.5,
    },
    logoContainer: {
       width: 80,
       height: 80,
       borderRadius: 24,
       borderWidth: 1,
       justifyContent: 'center',
       alignItems: 'center',
       marginBottom: 20,
       ...Platform.select({
          ios: {
             shadowColor: '#000',
             shadowOffset: { width: 0, height: 4 },
             shadowOpacity: 0.1,
             shadowRadius: 10,
          },
          android: {
             elevation: 4,
          }
       })
    },
    logo: {
        width: 50,
        height: 50,
    },
    titleRow: {
       flexDirection: 'row',
       alignItems: 'baseline',
    },
    title: {
        fontSize: 42,
        fontWeight: '900',
        textAlign: 'center',
        letterSpacing: -1.5,
    },
    titleSuffix: {
        fontSize: 32,
        fontWeight: '900',
        letterSpacing: -1,
        marginLeft: 2,
    },
    subtitle: {
        fontSize: 15,
        marginTop: 10,
        textAlign: 'center',
        fontWeight: '600',
        opacity: 0.8,
    },
    formCard: {
        borderRadius: 32,
        padding: spacing.xl,
        borderWidth: 1,
        width: '100%',
        ...Platform.select({
           ios: {
              shadowColor: '#000',
              shadowOffset: { width: 0, height: 12 },
              shadowOpacity: 0.15,
              shadowRadius: 25,
           },
           android: {
              elevation: 10,
           }
        })
    },
    loginWrapper: {
       marginTop: spacing.md,
    },
    loginButton: {
        height: 58,
        borderRadius: 18,
        justifyContent: 'center',
        alignItems: 'center',
    },
    loginButtonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '800',
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
        opacity: 0.5,
    },
    telegramButton: {
        borderRadius: 18,
        height: 50,
    },
    footer: {
        marginTop: spacing.xl * 1.5,
        alignItems: 'center',
    },
    footerText: {
        fontSize: 11,
        fontWeight: '700',
        textTransform: 'uppercase',
        letterSpacing: 2,
    },
    versionText: {
       fontSize: 10,
       marginTop: 8,
       fontWeight: '500',
    }
});

