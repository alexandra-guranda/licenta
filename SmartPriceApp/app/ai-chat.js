import React, { useState, useRef, useEffect } from 'react';
import {
    View, Text, StyleSheet, FlatList, TextInput,
    TouchableOpacity, KeyboardAvoidingView, Platform,
    ActivityIndicator, ScrollView,
} from 'react-native';
import { Send, Bot, Zap, ArrowLeft, X } from 'lucide-react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { askAI } from '../src/services/api';

const COLORS = {
    navy:         '#1e3a5f',
    navyDark:     '#0d1b2e',
    navyLight:    '#eef2ff',
    navyBorder:   '#a5b4fc',
    gold:         '#f0c040',
    bg:           '#f0f2f8',
    white:        '#fff',
    border:       '#e2e4ee',
    textDark:     '#0d1b2e',
    textLight:    '#71717a',
};

const QUICK_ASKS = [
    { emoji: '🧴', label: 'Cel mai ieftin detergent azi',   q: 'Unde găsesc cel mai ieftin detergent azi?' },
    { emoji: '🥩', label: 'Oferta zilei la carne',          q: 'Care e oferta zilei la carne?' },
    { emoji: '🥛', label: 'Lapte — Lidl vs Kaufland',       q: 'Compară prețul laptelui la Lidl vs Kaufland' },
    { emoji: '🍎', label: 'Fructe în ofertă azi',           q: 'Ce fructe sunt în ofertă azi?' },
];

export default function AIChatScreen() {
    const router = useRouter();
    const { prefill } = useLocalSearchParams();

    const [messages, setMessages] = useState([
        { id: '1', text: 'Bună! Sunt asistentul tău SmartPrice. Întreabă-mă orice despre oferte și prețuri! 💛', isAi: true },
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [showQuickAsks, setShowQuickAsks] = useState(true);
    const flatListRef = useRef();

    useEffect(() => {
        if (prefill) sendMessage(prefill);
    }, []);

    const sendMessage = async (text) => {
        const msgText = (text || input).trim();
        if (!msgText) return;

        setShowQuickAsks(false);
        setMessages(prev => [...prev, { id: Date.now().toString(), text: msgText, isAi: false }]);
        setInput('');
        setLoading(true);

        try {
            const data = await askAI(msgText);
            setMessages(prev => [...prev, { id: (Date.now() + 1).toString(), text: data.reply, isAi: true }]);
        } catch {
            setMessages(prev => [...prev, { id: 'err-' + Date.now(), text: 'Ups! A apărut o eroare. Reîncearcă?', isAi: true }]);
        } finally {
            setLoading(false);
        }
    };

    const renderMessage = ({ item }) => (
        <View style={[styles.bubbleWrap, item.isAi ? styles.aiBubbleWrap : styles.userBubbleWrap]}>
            {item.isAi && (
                <View style={styles.botAvatar}>
                    <Bot size={14} color={COLORS.gold} />
                </View>
            )}
            <View style={[styles.bubble, item.isAi ? styles.aiBubble : styles.userBubble]}>
                <Text style={[styles.messageText, { color: item.isAi ? COLORS.textDark : COLORS.white }]}>
                    {item.text}
                </Text>
            </View>
        </View>
    );

    return (
        <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            style={styles.container}
            keyboardVerticalOffset={90}
        >
            <View style={styles.header}>
                <TouchableOpacity style={styles.iconBtn} onPress={() => router.back()} activeOpacity={0.8}>
                    <ArrowLeft size={20} color={COLORS.navyDark} />
                </TouchableOpacity>
                <View style={styles.headerCenter}>
                    <View style={styles.headerIcon}>
                        <Zap size={16} color={COLORS.gold} />
                    </View>
                    <View>
                        <Text style={styles.headerTitle}>Asistent SmartPrice</Text>
                        <Text style={styles.headerStatus}>● Online acum</Text>
                    </View>
                </View>
                <TouchableOpacity style={styles.iconBtn} onPress={() => router.back()} activeOpacity={0.8}>
                    <X size={18} color={COLORS.textLight} />
                </TouchableOpacity>
            </View>

            <FlatList
                ref={flatListRef}
                data={messages}
                renderItem={renderMessage}
                keyExtractor={item => item.id}
                contentContainerStyle={styles.chatList}
                onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
                showsVerticalScrollIndicator={false}
            />

            {/* Typing indicator */}
            {loading && (
                <View style={[styles.bubbleWrap, styles.aiBubbleWrap, { paddingHorizontal: 16, paddingBottom: 6 }]}>
                    <View style={styles.botAvatar}>
                        <Bot size={14} color={COLORS.gold} />
                    </View>
                    <View style={[styles.bubble, styles.aiBubble]}>
                        <ActivityIndicator size="small" color={COLORS.navy} />
                    </View>
                </View>
            )}

            {/* Quick asks */}
            {showQuickAsks && (
                <ScrollView
                    horizontal
                    showsHorizontalScrollIndicator={false}
                    contentContainerStyle={styles.quickAskRow}
                    style={styles.quickAskScroll}
                >
                    {QUICK_ASKS.map((item, i) => (
                        <TouchableOpacity
                            key={i}
                            style={styles.quickAskBtn}
                            onPress={() => sendMessage(item.q)}
                            activeOpacity={0.75}
                        >
                            <Text style={styles.quickAskText}>{item.emoji} {item.label}</Text>
                        </TouchableOpacity>
                    ))}
                </ScrollView>
            )}

            {/* Input */}
            <View style={styles.inputArea}>
                <TextInput
                    style={styles.input}
                    placeholder="Întreabă-mă despre oferte..."
                    placeholderTextColor={COLORS.textLight}
                    value={input}
                    onChangeText={setInput}
                    multiline
                />
                <TouchableOpacity
                    onPress={() => sendMessage()}
                    style={[styles.sendBtn, (!input.trim() || loading) && styles.sendBtnDisabled]}
                    disabled={!input.trim() || loading}
                    activeOpacity={0.8}
                >
                    <Send color={COLORS.gold} size={18} />
                </TouchableOpacity>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: COLORS.bg },

    header: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingTop: 56,
        paddingBottom: 14,
        paddingHorizontal: 14,
        backgroundColor: COLORS.white,
        borderBottomWidth: 0.5,
        borderBottomColor: COLORS.border,
        elevation: 2,
        gap: 10,
    },
    iconBtn:      { width: 36, height: 36, borderRadius: 11, backgroundColor: COLORS.bg, justifyContent: 'center', alignItems: 'center' },
    headerCenter: { flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 },
    headerIcon:   { width: 36, height: 36, borderRadius: 11, backgroundColor: COLORS.navy, justifyContent: 'center', alignItems: 'center' },
    headerTitle:  { fontSize: 15, fontWeight: '800', color: COLORS.navyDark },
    headerStatus: { fontSize: 11, color: COLORS.navy, fontWeight: '600', marginTop: 1 },

    chatList: { padding: 16, gap: 10 },

    bubbleWrap:     { flexDirection: 'row', alignItems: 'flex-end', gap: 8, marginBottom: 2 },
    aiBubbleWrap:   { alignSelf: 'flex-start', maxWidth: '85%' },
    userBubbleWrap: { alignSelf: 'flex-end',   maxWidth: '85%', flexDirection: 'row-reverse' },

    botAvatar: {
        width: 28, height: 28,
        borderRadius: 9,
        backgroundColor: COLORS.navy,
        justifyContent: 'center',
        alignItems: 'center',
        flexShrink: 0,
        marginBottom: 2,
    },
    bubble:     { padding: 11, borderRadius: 16, flexShrink: 1 },
    aiBubble:   { backgroundColor: COLORS.white, borderTopLeftRadius: 4, borderWidth: 0.5, borderColor: COLORS.border },
    userBubble: { backgroundColor: COLORS.navy, borderTopRightRadius: 4 },
    messageText:{ fontSize: 14, lineHeight: 20, fontWeight: '500' },

    quickAskScroll: { flexGrow: 0 },
    quickAskRow:    { paddingHorizontal: 14, paddingBottom: 10, gap: 8 },
    quickAskBtn:    { backgroundColor: COLORS.navyLight, borderWidth: 1, borderColor: COLORS.navyBorder, borderRadius: 20, paddingHorizontal: 12, paddingVertical: 7 },
    quickAskText:   { fontSize: 12, fontWeight: '700', color: COLORS.navy },

    inputArea: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 12,
        backgroundColor: COLORS.white,
        borderTopWidth: 0.5,
        borderTopColor: COLORS.border,
        gap: 10,
    },
    input: {
        flex: 1,
        backgroundColor: COLORS.bg,
        borderRadius: 18,
        paddingHorizontal: 15,
        paddingVertical: 10,
        maxHeight: 100,
        fontSize: 14,
        color: COLORS.textDark,
        fontWeight: '500',
        borderWidth: 0.5,
        borderColor: COLORS.border,
    },
    sendBtn:         { backgroundColor: COLORS.navy, width: 42, height: 42, borderRadius: 21, justifyContent: 'center', alignItems: 'center' },
    sendBtnDisabled: { backgroundColor: COLORS.navyLight },
});