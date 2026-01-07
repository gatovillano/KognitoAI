// src/screens/TelegramLoginScreen.tsx
import React, { useState } from 'react';
import { View, Text, StyleSheet, KeyboardAvoidingView, Platform, ScrollView, Alert, TouchableOpacity } from 'react-native';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { colors, spacing, borderRadius } from '../theme/colors';
import { Send, CheckCircle2, ChevronLeft } from 'lucide-react-native';

export const TelegramLoginScreen = ({ navigation }: any) => {
    const [identifier, setIdentifier] = useState('');
    const [code, setCode] = useState('');
    const [step, setStep] = useState<'identifier' | 'code'>('identifier');
    const [loading, setLoading] = useState(false);
    const { requestCode, verifyCode } = useAuth();

    const handleRequestCode = async () => {
        if (!identifier) {
            Alert.alert('Error', 'Por favor introduce tu alias o ID de Telegram');
            return;
        }

        setLoading(true);
        try {
            await requestCode(identifier);
            setStep('code');
        } catch (error) {
            Alert.alert('Error', 'No se pudo enviar el código. Asegúrate de haber iniciado el bot de Kognito en Telegram.');
        } finally {
            setLoading(false);
        }
    };

    const handleVerifyCode = async () => {
        if (!code) {
            Alert.alert('Error', 'Por favor introduce el código de verificación');
            return;
        }

        setLoading(true);
        try {
            await verifyCode(identifier, code);
            // El AuthContext actualizará el estado 'signed' y la navegación cambiará automáticamente
        } catch (error) {
            Alert.alert('Error', 'Código incorrecto o expirado.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            style={styles.container}
        >
            <View style={styles.headerNav}>
                <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
                    <ChevronLeft size={28} color={colors.text} />
                </TouchableOpacity>
            </View>

            <ScrollView contentContainerStyle={styles.scrollContent}>
                <View style={styles.header}>
                    <View style={styles.iconContainer}>
                        <Send size={40} color={colors.primary} />
                    </View>
                    <Text style={styles.title}>Acceso vía Telegram</Text>
                    <Text style={styles.subtitle}>
                        {step === 'identifier'
                            ? 'Introduce tu alias de Telegram para recibir un código de acceso.'
                            : `Introduce el código que te hemos enviado al chat de Telegram.`}
                    </Text>
                </View>

                <View style={styles.form}>
                    {step === 'identifier' ? (
                        <>
                            <Input
                                label="Alias o ID de Telegram"
                                placeholder="@usuario o 12345678"
                                value={identifier}
                                onChangeText={setIdentifier}
                                autoCapitalize="none"
                            />
                            <Button
                                title="Enviar Código"
                                onPress={handleRequestCode}
                                loading={loading}
                                style={styles.button}
                            />
                        </>
                    ) : (
                        <>
                            <Input
                                label="Código de Verificación"
                                placeholder="123456"
                                value={code}
                                onChangeText={setCode}
                                keyboardType="number-pad"
                                maxLength={6}
                            />
                            <Button
                                title="Verificar e Iniciar Sesión"
                                onPress={handleVerifyCode}
                                loading={loading}
                                style={styles.button}
                            />
                            <TouchableOpacity
                                onPress={() => setStep('identifier')}
                                style={styles.resendButton}
                                disabled={loading}
                            >
                                <Text style={styles.resendText}>¿No recibiste el código? Reintentar</Text>
                            </TouchableOpacity>
                        </>
                    )}
                </View>

                <View style={styles.footer}>
                    <Text style={styles.footerText}>
                        ¿Aún no has activado el bot?
                        <Text style={styles.linkText}> Busca @KognitoAIBot</Text>
                    </Text>
                </View>
            </ScrollView>
        </KeyboardAvoidingView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.background,
    },
    headerNav: {
        paddingTop: spacing.xl * 2,
        paddingHorizontal: spacing.md,
    },
    backButton: {
        padding: spacing.sm,
    },
    scrollContent: {
        flexGrow: 1,
        padding: spacing.lg,
        paddingTop: spacing.md,
    },
    header: {
        alignItems: 'center',
        marginBottom: spacing.xl * 2,
    },
    iconContainer: {
        width: 80,
        height: 80,
        borderRadius: 40,
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: spacing.lg,
    },
    title: {
        fontSize: 28,
        fontWeight: 'bold',
        color: colors.text,
        textAlign: 'center',
    },
    subtitle: {
        fontSize: 16,
        color: colors.textMuted,
        marginTop: spacing.sm,
        textAlign: 'center',
        paddingHorizontal: spacing.md,
    },
    form: {
        width: '100%',
    },
    button: {
        marginTop: spacing.md,
    },
    resendButton: {
        marginTop: spacing.lg,
        alignItems: 'center',
    },
    resendText: {
        color: colors.primary,
        fontSize: 14,
        fontWeight: '500',
    },
    footer: {
        marginTop: 'auto',
        paddingVertical: spacing.xl,
        alignItems: 'center',
    },
    footerText: {
        color: colors.textMuted,
        fontSize: 14,
    },
    linkText: {
        color: colors.primary,
        fontWeight: 'bold',
    },
});
