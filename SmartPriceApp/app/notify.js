import React, { useState } from 'react';
import {
    View, Text, TextInput, TouchableOpacity,
    StyleSheet, StatusBar, KeyboardAvoidingView,
    Platform, ActivityIndicator,
} from 'react-native';
import { ArrowLeft, Bell, CheckCircle, Mail } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { API_BASE } from '../src/services/api';

const COLORS = {
    navy:      '#1e3a5f',
    navyDark:  '#0d1b2e',
    navyLight: '#eef2ff',
    gold:      '#f0c040',
    bg:        '#f0f2f8',
    white:     '#fff',
    border:    '#e2e4ee',
    textDark:  '#0d1b2e',
    textLight: '#71717a',
    red:       '#ef4444',
    green:     '#16a34a',
    greenLight:'#f0fdf4',
};

export default function NotifyScreen() {
    const router = useRouter();
    const [email, setEmail]       = useState('');
    const [loading, setLoading]   = useState(false);
    const [success, setSuccess]   = useState(false);
    const [error, setError]       = useState('');

    const isValidEmail = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);

    const handleSubscribe = async () => {
        if (!isValidEmail(email)) {
            setError('Introdu un email valid.');
            return;
        }
        setError('');
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/subscribe`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
            if (res.ok) {
                setSuccess(true);
            } else {
                setError('A apărut o eroare. Încearcă din nou.');
            }
        } catch {
            setError('Nu s-a putut conecta la server.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <KeyboardAvoidingView
            style={styles.root}
            behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
            <StatusBar barStyle="light-content" backgroundColor={COLORS.navy} />

            <View style={styles.header}>
                <TouchableOpacity style={styles.backBtn} onPress={() => router.back()} activeOpacity={0.8}>
                    <ArrowLeft size={20} color={COLORS.white} />
                </TouchableOpacity>
                <Text style={styles.headerTitle}>Notificări oferte</Text>
                <View style={{ width: 40 }} />
            </View>

            <View style={styles.body}>
                {success ? (
                    <View style={styles.successCard}>
                        <View style={styles.successIcon}>
                            <CheckCircle size={48} color={COLORS.green} />
                        </View>
                        <Text style={styles.successTitle}>Ești abonat!</Text>
                        <Text style={styles.successSub}>
                            Vei primi un email la <Text style={{ fontWeight: '700' }}>{email}</Text> când
                            apar oferte noi cu reducere ≥ 35%.
                        </Text>
                        <TouchableOpacity style={styles.backHomeBtn} onPress={() => router.back()} activeOpacity={0.85}>
                            <Text style={styles.backHomeBtnText}>Înapoi la oferte</Text>
                        </TouchableOpacity>
                    </View>
                ) : (
                    <>
                        <View style={styles.iconWrap}>
                            <Bell size={36} color={COLORS.gold} />
                        </View>
                        <Text style={styles.title}>Fii primul care află</Text>
                        <Text style={styles.subtitle}>
                            Introdu emailul tău și îți trimitem o notificare de fiecare dată când
                            apar oferte noi cu reducere de cel puțin 35%.
                        </Text>

                        <View style={[styles.inputWrap, error ? styles.inputWrapError : null]}>
                            <Mail size={18} color={COLORS.textLight} style={{ marginRight: 10 }} />
                            <TextInput
                                style={styles.input}
                                placeholder="exemplu@email.com"
                                placeholderTextColor={COLORS.textLight}
                                keyboardType="email-address"
                                autoCapitalize="none"
                                autoCorrect={false}
                                value={email}
                                onChangeText={(t) => { setEmail(t); setError(''); }}
                            />
                        </View>

                        {error ? <Text style={styles.errorText}>{error}</Text> : null}

                        <TouchableOpacity
                            style={[styles.btn, (!email || loading) && styles.btnDisabled]}
                            onPress={handleSubscribe}
                            activeOpacity={0.85}
                            disabled={!email || loading}
                        >
                            {loading
                                ? <ActivityIndicator color={COLORS.navyDark} />
                                : <Text style={styles.btnText}>Abonează-mă</Text>
                            }
                        </TouchableOpacity>

                        <Text style={styles.disclaimer}>
                            Nu trimitem spam. Te poți dezabona oricând.
                        </Text>
                    </>
                )}
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    root:   { flex: 1, backgroundColor: COLORS.bg },
    header: { backgroundColor: COLORS.navy, paddingTop: 52, paddingBottom: 16, paddingHorizontal: 20, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
    backBtn:      { width: 40, height: 40, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.15)', justifyContent: 'center', alignItems: 'center' },
    headerTitle:  { fontSize: 17, fontWeight: '800', color: COLORS.white },

    body: { flex: 1, paddingHorizontal: 28, paddingTop: 48, alignItems: 'center' },

    iconWrap:  { width: 80, height: 80, borderRadius: 24, backgroundColor: COLORS.navy, justifyContent: 'center', alignItems: 'center', marginBottom: 24 },
    title:     { fontSize: 24, fontWeight: '900', color: COLORS.navyDark, textAlign: 'center', marginBottom: 12, letterSpacing: -0.5 },
    subtitle:  { fontSize: 14, color: COLORS.textLight, textAlign: 'center', lineHeight: 22, marginBottom: 32 },

    inputWrap:      { flexDirection: 'row', alignItems: 'center', backgroundColor: COLORS.white, borderRadius: 16, paddingHorizontal: 16, paddingVertical: 14, borderWidth: 1.5, borderColor: COLORS.border, width: '100%', marginBottom: 8 },
    inputWrapError: { borderColor: COLORS.red },
    input:          { flex: 1, fontSize: 15, color: COLORS.textDark, fontWeight: '500' },
    errorText:      { color: COLORS.red, fontSize: 12, fontWeight: '600', alignSelf: 'flex-start', marginBottom: 12 },

    btn:         { backgroundColor: COLORS.gold, borderRadius: 16, paddingVertical: 16, width: '100%', alignItems: 'center', marginTop: 8, elevation: 4, shadowColor: COLORS.gold, shadowOpacity: 0.35, shadowRadius: 8 },
    btnDisabled: { opacity: 0.5, elevation: 0 },
    btnText:     { fontSize: 16, fontWeight: '900', color: COLORS.navyDark },

    disclaimer: { fontSize: 11, color: COLORS.textLight, marginTop: 16, textAlign: 'center' },

    successCard:  { alignItems: 'center', paddingTop: 20 },
    successIcon:  { width: 96, height: 96, borderRadius: 30, backgroundColor: COLORS.greenLight, justifyContent: 'center', alignItems: 'center', marginBottom: 24 },
    successTitle: { fontSize: 26, fontWeight: '900', color: COLORS.navyDark, marginBottom: 12 },
    successSub:   { fontSize: 14, color: COLORS.textLight, textAlign: 'center', lineHeight: 22, marginBottom: 32 },
    backHomeBtn:      { backgroundColor: COLORS.navy, borderRadius: 16, paddingVertical: 14, paddingHorizontal: 40, alignItems: 'center' },
    backHomeBtnText:  { fontSize: 15, fontWeight: '800', color: COLORS.white },
});