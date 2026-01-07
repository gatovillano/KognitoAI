// src/components/TelegramLoginModal.tsx
import React from 'react';
import { Modal, View, StyleSheet, TouchableOpacity, Text, SafeAreaView } from 'react-native';
import { WebView } from 'react-native-webview';
import { colors, spacing } from '../theme/colors';
import { X } from 'lucide-react-native';

interface TelegramLoginModalProps {
    visible: boolean;
    onClose: () => void;
    onSuccess: (userData: any) => void;
}

export const TelegramLoginModal = ({ visible, onClose, onSuccess }: TelegramLoginModalProps) => {
    // El HTML con etiqueta <base> para forzar el dominio
    const telegramWidgetHtml = `
    <!DOCTYPE html>
    <html>
      <head>
        <base href="https://bot.gatoslibres.art">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
          body { 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            height: 100vh; 
            margin: 0; 
            background-color: #0f172a; 
          }
        </style>
      </head>
      <body>
        <div id="telegram-widget-container"></div>
        <script 
          async 
          src="https://telegram.org/js/telegram-widget.js?22" 
          data-telegram-login="KognitoAIBot" 
          data-size="large" 
          data-onauth="onTelegramAuth(user)" 
          data-request-access="write"
        ></script>
        <script type="text/javascript">
          function onTelegramAuth(user) {
            window.ReactNativeWebView.postMessage(JSON.stringify(user));
          }
        </script>
      </body>
    </html>
  `;

    return (
        <Modal
            visible={visible}
            animationType="slide"
            transparent={false}
        >
            <SafeAreaView style={styles.container}>
                <View style={styles.header}>
                    <Text style={styles.title}>Acceder con Telegram</Text>
                    <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                        <X size={24} color={colors.text} />
                    </TouchableOpacity>
                </View>

                <WebView
                    originWhitelist={['*']}
                    source={{
                        html: telegramWidgetHtml,
                        baseUrl: 'https://bot.gatoslibres.art'
                    }}
                    style={styles.webview}
                    onMessage={(event) => {
                        try {
                            const userData = JSON.parse(event.nativeEvent.data);
                            onSuccess(userData);
                        } catch (e) {
                            console.error("Error parsing telegram data", e);
                        }
                    }}
                    javaScriptEnabled={true}
                    domStorageEnabled={true}
                    startInLoadingState={true}
                    scalesPageToFit={true}
                    // Usar un User Agent de Chrome real para evitar bloqueos
                    userAgent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
                />
            </SafeAreaView>
        </Modal>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.background,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: spacing.md,
        borderBottomWidth: 1,
        borderBottomColor: colors.border,
    },
    title: {
        color: colors.text,
        fontSize: 18,
        fontWeight: '600',
    },
    closeButton: {
        padding: spacing.xs,
    },
    webview: {
        flex: 1,
        backgroundColor: colors.background,
    },
});
