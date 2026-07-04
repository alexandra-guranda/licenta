import React, { useEffect, useState, useRef, useMemo } from 'react';
import {
    View, Text, ScrollView, TouchableOpacity, StyleSheet,
    Image, FlatList, ActivityIndicator, StatusBar,
    Dimensions, Animated,
} from 'react-native';
import {
    ChevronRight, Beef, Apple, Milk, Soup, Leaf,
    Snowflake, Beer, Store, Cookie, Sparkles,
    Baby, Bath, Home, Dog, Percent, Bell,
    Search, Zap,
} from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { fetchTopDeals, API_BASE } from '../src/services/api';

const COLORS = {
    navy:         '#1e3a5f',
    navyDark:     '#0d1b2e',
    navyLight:    '#eef2ff',
    navyBorder:   '#a5b4fc',
    gold:         '#f0c040',
    goldLight:    '#fef3c7',
    bg:           '#f0f2f8',
    surface:      '#f7f8fc',
    white:        '#fff',
    border:       '#e2e4ee',
    textDark:     '#0d1b2e',
    textMid:      '#334155',
    textLight:    '#71717a',
    red:          '#ef4444',
    redLight:     '#fef2f2',
};

const STORES = ['Toate', 'Lidl', 'Kaufland', 'Profi', 'Mega Image', 'Auchan'];

const CATEGORII = [
    { name: 'Brutărie & patiserie',   icon: <Store   color="#047857" size={20}/>, bg: '#fffbeb' },
    { name: 'Carne & pește',           icon: <Beef    color="#ef4444" size={20}/>, bg: '#fef2f2' },
    { name: 'Fructe & legume',         icon: <Apple   color="#16a34a" size={20}/>, bg: '#f0fdf4' },
    { name: 'Lactate & ouă',           icon: <Milk    color="#3b82f6" size={20}/>, bg: '#eff6ff' },
    { name: 'Mezeluri & ready meals',  icon: <Soup    color="#f97316" size={20}/>, bg: '#fff7ed' },
    { name: 'Băuturi',                 icon: <Beer    color="#8b5cf6" size={20}/>, bg: '#f5f3ff' },
    { name: 'Băcănie',                 icon: <Store   color="#1e3a5f" size={20}/>, bg: '#eef2ff' },
    { name: 'Dulciuri & mic dejun',    icon: <Cookie  color="#d946ef" size={20}/>, bg: '#fdf4ff' },
    { name: 'Detergenți & igienizare', icon: <Bath    color="#3b82f6" size={20}/>, bg: '#eff6ff' },
    { name: 'Pet Shop',                icon: <Dog     color="#f97316" size={20}/>, bg: '#fff7ed' },
    { name: 'Cosmetice',               icon: <Sparkles color="#ec4899" size={20}/>, bg: '#fdf2f8' },
    { name: 'Mama & copilul',          icon: <Baby    color="#06b6d4" size={20}/>, bg: '#ecfeff' },
    { name: 'Casă & agrement',         icon: <Home    color="#64748b" size={20}/>, bg: '#f8fafc' },
];

function AIQuickAsk({ onPress }) {
    const pulse = useRef(new Animated.Value(1)).current;
    useEffect(() => {
        Animated.loop(
            Animated.sequence([
                Animated.timing(pulse, { toValue: 1.02, duration: 1000, useNativeDriver: true }),
                Animated.timing(pulse, { toValue: 1,    duration: 1000, useNativeDriver: true }),
            ])
        ).start();
    }, []);

    return (
        <Animated.View style={{ transform: [{ scale: pulse }] }}>
            <TouchableOpacity style={styles.aiTip} onPress={onPress} activeOpacity={0.82}>
                <View style={styles.aiTipIcon}>
                    <Zap size={18} color={COLORS.gold} />
                </View>
                <View style={{ flex: 1 }}>
                    <Text style={styles.aiTipText}>Unde e cel mai ieftin detergent azi?</Text>
                    <Text style={styles.aiTipSub}>Întreabă asistentul AI →</Text>
                </View>
            </TouchableOpacity>
        </Animated.View>
    );
}

function DealCard({ item, index, onPress }) {
    const anim = useRef(new Animated.Value(0)).current;
    useEffect(() => {
        Animated.timing(anim, { toValue: 1, duration: 360, delay: index * 80, useNativeDriver: true }).start();
    }, []);
    const translateX = anim.interpolate({ inputRange: [0, 1], outputRange: [40, 0] });

    return (
        <Animated.View style={{ opacity: anim, transform: [{ translateX }] }}>
            <TouchableOpacity style={styles.dealCard} onPress={onPress} activeOpacity={0.88}>
                <View style={styles.dealBadge}>
                    <Text style={styles.dealBadgeText}>-{Math.round(item.discount * 100)}%</Text>
                </View>
                <View style={styles.dealImageWrap}>
                    <Image
                        source={{ uri: item.image_url }}
                        style={styles.dealImage}
                        resizeMode="contain"
                    />
                </View>
                <View style={styles.dealBody}>
                    <View style={styles.dealStorePill}><Text style={styles.dealStoreText}>{item.store}</Text></View>
                    <Text style={styles.dealName} numberOfLines={3}>{item.name}</Text>
                    <View style={styles.dealPriceRow}>
                        <Text style={styles.dealPriceNew}>{item.price_new.toFixed(2)} lei</Text>
                        {item.price_old && <Text style={styles.dealPriceOld}>{item.price_old.toFixed(2)} lei</Text>}
                    </View>
                </View>
            </TouchableOpacity>
        </Animated.View>
    );
}

function CatItem({ cat, index, onPress }) {
    const anim = useRef(new Animated.Value(0)).current;
    useEffect(() => {
        Animated.timing(anim, { toValue: 1, duration: 300, delay: 200 + Math.min(index * 35, 500), useNativeDriver: true }).start();
    }, []);
    const translateX = anim.interpolate({ inputRange: [0, 1], outputRange: [-16, 0] });

    return (
        <Animated.View style={{ opacity: anim, transform: [{ translateX }] }}>
            <TouchableOpacity style={styles.catItem} onPress={onPress} activeOpacity={0.75}>
                <View style={styles.catLeft}>
                    <View style={[styles.iconCircle, { backgroundColor: cat.bg }]}>{cat.icon}</View>
                    <Text style={styles.catText}>{cat.name}</Text>
                </View>
                <View style={styles.catChevronWrap}><ChevronRight size={14} color={COLORS.navy} /></View>
            </TouchableOpacity>
        </Animated.View>
    );
}

export default function HomeScreen() {
    const router = useRouter();
    const [topDeals, setTopDeals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedStore, setSelectedStore] = useState('Toate');
    const scrollY       = useRef(new Animated.Value(0)).current;
    const headerOpacity = useRef(new Animated.Value(0)).current;
    const headerSlide   = useRef(new Animated.Value(-10)).current;

    useEffect(() => {
        Animated.parallel([
            Animated.timing(headerOpacity, { toValue: 1, duration: 500, useNativeDriver: true }),
            Animated.timing(headerSlide,   { toValue: 0, duration: 500, useNativeDriver: true }),
        ]).start();
        fetchTopDeals().then(data => { setTopDeals(data); setLoading(false); }).catch(() => setLoading(false));
    }, []);

    const filteredDeals = useMemo(() => {
        if (selectedStore === 'Toate') return topDeals;
        return topDeals.filter(d => d.store === selectedStore);
    }, [selectedStore, topDeals]);

    const headerHeight = scrollY.interpolate({ inputRange: [0, 80], outputRange: [200, 130], extrapolate: 'clamp' });
    const logoScale    = scrollY.interpolate({ inputRange: [0, 80], outputRange: [1, 0.82],  extrapolate: 'clamp' });
    const subOpacity   = scrollY.interpolate({ inputRange: [0, 60], outputRange: [1, 0],      extrapolate: 'clamp' });

    const getGreeting = () => {
        const h = new Date().getHours();
        if (h < 12) return 'Bună dimineața! ☀️';
        if (h < 18) return 'Bună ziua! 👋';
        return 'Bună seara! 🌙';
    };

    const goToProducts = (category) => router.push({ pathname: '/products', params: { category } });
    const goToAIChat   = (prefill)   => router.push({ pathname: '/ai-chat',  params: { prefill } });

    return (
        <View style={styles.root}>
            <StatusBar barStyle="light-content" backgroundColor={COLORS.navy} />

            <Animated.View style={[styles.header, { height: headerHeight, opacity: headerOpacity, transform: [{ translateY: headerSlide }] }]}>
                <View style={styles.deco1} /><View style={styles.deco2} />
                <View style={styles.headerInner}>
                    <View style={styles.headerTopRow}>
                        <View>
                            <Animated.Text style={[styles.greeting, { opacity: subOpacity }]}>{getGreeting()}</Animated.Text>
                            <Animated.Text style={[styles.logoText, { transform: [{ scale: logoScale }] }]}>SmartPrice</Animated.Text>
                        </View>
                        <TouchableOpacity style={styles.notifBtn} activeOpacity={0.8} onPress={() => router.push('/notify')}>
                            <Bell size={20} color={COLORS.gold} />
                            <View style={styles.notifDot} />
                        </TouchableOpacity>
                    </View>
                    <Animated.View style={{ opacity: subOpacity }}>
                        <TouchableOpacity style={styles.searchBar} onPress={() => router.push('/search')} activeOpacity={0.8}>
                            <Search size={16} color="rgba(255,255,255,0.5)" />
                            <Text style={styles.searchPlaceholder}>Caută produse sau magazine...</Text>
                        </TouchableOpacity>
                    </Animated.View>
                </View>
            </Animated.View>

            <Animated.ScrollView
                style={styles.scroll}
                showsVerticalScrollIndicator={false}
                onScroll={Animated.event([{ nativeEvent: { contentOffset: { y: scrollY } } }], { useNativeDriver: false })}
                scrollEventThrottle={16}
            >
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.storesRow} style={{ marginTop: 20 }}>
                    {STORES.map(s => (
                        <TouchableOpacity key={s} style={[styles.storePill, selectedStore === s && styles.storePillActive]} onPress={() => setSelectedStore(s)} activeOpacity={0.75}>
                            <Text style={[styles.storePillText, selectedStore === s && styles.storePillTextActive]}>{s}</Text>
                        </TouchableOpacity>
                    ))}
                </ScrollView>

                <View style={{ paddingHorizontal: 20, marginTop: 10 }}>
                    <AIQuickAsk onPress={() => goToAIChat('Unde găsesc cel mai ieftin detergent azi?')} />
                </View>

                <View style={styles.sectionRow}>
                    <View style={styles.sectionIconWrap}><Percent size={14} color={COLORS.red} /></View>
                    <Text style={styles.sectionTitle}>Oferte de neratat</Text>
                    <View style={styles.sectionBadge}><Text style={styles.sectionBadgeText}>HOT</Text></View>
                    <TouchableOpacity style={styles.seeAllBtn} onPress={() => goToProducts('__deals__')}><Text style={styles.seeAllText}>Vezi toate</Text></TouchableOpacity>
                </View>

                {loading ? (
                    <View style={styles.loaderWrap}><ActivityIndicator size="large" color={COLORS.navy} /><Text style={styles.loaderText}>Se încarcă ofertele...</Text></View>
                ) : (
                    <FlatList
                        horizontal data={filteredDeals} keyExtractor={(_, i) => i.toString()}
                        showsHorizontalScrollIndicator={false} contentContainerStyle={styles.dealsList}
                        renderItem={({ item, index }) => <DealCard item={item} index={index} onPress={() => goToProducts(item.category)} />}
                    />
                )}

                <View style={[styles.sectionRow, { marginTop: 24 }]}>
                    <View style={[styles.sectionIconWrap, { backgroundColor: COLORS.navyLight }]}><Leaf size={14} color={COLORS.navy} /></View>
                    <Text style={styles.sectionTitle}>Categorii</Text>
                </View>

                <View style={styles.catCard}>
                    {CATEGORII.map((cat, index) => <CatItem key={index} cat={cat} index={index} onPress={() => goToProducts(cat.name)} />)}
                </View>
                <View style={{ height: 90 }} />
            </Animated.ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    root:   { flex: 1, backgroundColor: COLORS.bg },
    scroll: { flex: 1, marginTop: -28 },
    header: { backgroundColor: COLORS.navy, paddingTop: 52, paddingHorizontal: 20, borderBottomLeftRadius: 36, borderBottomRightRadius: 36, overflow: 'hidden', elevation: 14, shadowColor: COLORS.navy, shadowOpacity: 0.4, shadowRadius: 20, zIndex: 10 },
    headerInner:   { flex: 1, justifyContent: 'flex-start' },
    headerTopRow:  { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 },
    greeting:      { fontSize: 13, color: 'rgba(255,255,255,0.65)', fontWeight: '500', marginBottom: 2 },
    logoText:      { fontSize: 34, fontWeight: '900', color: COLORS.gold, letterSpacing: -1.5, lineHeight: 36 },
    notifBtn:      { width: 40, height: 40, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.1)', justifyContent: 'center', alignItems: 'center', marginTop: 16, position: 'relative' },
    notifDot:      { position: 'absolute', top: 9, right: 9, width: 8, height: 8, borderRadius: 4, backgroundColor: COLORS.red, borderWidth: 1.5, borderColor: COLORS.navy },
    searchBar:     { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 16, paddingHorizontal: 14, paddingVertical: 11, gap: 10, marginBottom: 6, borderWidth: 1, borderColor: 'rgba(240,192,64,0.2)' },
    searchPlaceholder: { fontSize: 13, color: 'rgba(255,255,255,0.45)', fontWeight: '500' },
    deco1: { position: 'absolute', width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.04)', top: -50, right: -40 },
    deco2: { position: 'absolute', width: 110, height: 110, borderRadius: 55, backgroundColor: 'rgba(240,192,64,0.06)', bottom: 10, right: 90 },
    storesRow:           { paddingHorizontal: 20, gap: 8 },
    storePill:           { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 20, backgroundColor: COLORS.white, borderWidth: 0.5, borderColor: COLORS.border },
    storePillActive:     { backgroundColor: COLORS.navy, borderColor: COLORS.navy },
    storePillText:       { fontSize: 12, fontWeight: '700', color: COLORS.textMid },
    storePillTextActive: { color: COLORS.gold },
    aiTip:     { backgroundColor: COLORS.navyLight, borderWidth: 1, borderColor: COLORS.navyBorder, borderRadius: 16, padding: 12, flexDirection: 'row', alignItems: 'center', gap: 12 },
    aiTipIcon: { width: 38, height: 38, borderRadius: 12, backgroundColor: COLORS.navy, justifyContent: 'center', alignItems: 'center', flexShrink: 0 },
    aiTipText: { fontSize: 13, fontWeight: '700', color: COLORS.navyDark, lineHeight: 18 },
    aiTipSub:  { fontSize: 11, fontWeight: '500', color: COLORS.navy, marginTop: 2 },
    sectionRow:       { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, marginTop: 20, marginBottom: 12, gap: 8 },
    sectionIconWrap:  { width: 28, height: 28, borderRadius: 9, backgroundColor: COLORS.redLight, justifyContent: 'center', alignItems: 'center' },
    sectionTitle:     { fontSize: 17, fontWeight: '800', color: COLORS.textDark, flex: 1, letterSpacing: -0.3 },
    sectionBadge:     { backgroundColor: COLORS.red, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 7 },
    sectionBadgeText: { color: COLORS.white, fontSize: 10, fontWeight: '800' },
    seeAllBtn:        { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10, borderWidth: 1.5, borderColor: COLORS.navy },
    seeAllText:       { fontSize: 11, fontWeight: '700', color: COLORS.navy },
    dealsList:     { paddingLeft: 20, paddingRight: 8, paddingBottom: 8 },
    dealCard:      { backgroundColor: COLORS.white, width: 160, borderRadius: 22, marginRight: 12, overflow: 'hidden', elevation: 4, shadowColor: '#000', shadowOpacity: 0.07, shadowRadius: 10, borderWidth: 0.5, borderColor: COLORS.border },
    dealBadge:     { position: 'absolute', top: 10, left: 10, zIndex: 2, backgroundColor: COLORS.red, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 10 },
    dealBadgeText: { color: COLORS.white, fontSize: 11, fontWeight: '900' },
    dealImageWrap: { width: '100%', height: 110, backgroundColor: COLORS.surface, justifyContent: 'center', alignItems: 'center', padding: 10 },
    dealImage:     { width: '100%', height: '100%' },
    dealBody:      { padding: 10 },
    dealStorePill: { alignSelf: 'flex-start', backgroundColor: COLORS.navyLight, paddingHorizontal: 7, paddingVertical: 2, borderRadius: 6, marginBottom: 5 },
    dealStoreText: { fontSize: 9, fontWeight: '800', color: COLORS.navy, textTransform: 'uppercase', letterSpacing: 0.5 },
    dealName:      { fontSize: 13, fontWeight: '600', color: COLORS.textMid, marginBottom: 6, lineHeight: 18, minHeight: 36 },
    dealPriceRow:  { flexDirection: 'row', alignItems: 'flex-end', gap: 6 },
    dealPriceNew:  { fontSize: 17, fontWeight: '900', color: COLORS.red },
    dealPriceOld:  { fontSize: 11, color: COLORS.textLight, textDecorationLine: 'line-through', marginBottom: 1 },
    catCard:        { backgroundColor: COLORS.white, marginHorizontal: 20, borderRadius: 22, elevation: 3, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10, overflow: 'hidden', borderWidth: 0.5, borderColor: COLORS.border },
    catItem:        { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 13, borderBottomWidth: 0.5, borderBottomColor: COLORS.border },
    catLeft:        { flexDirection: 'row', alignItems: 'center', flex: 1 },
    iconCircle:     { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
    catText:        { marginLeft: 13, fontSize: 14, fontWeight: '700', color: COLORS.textDark, flex: 1 },
    catChevronWrap: { width: 24, height: 24, borderRadius: 7, backgroundColor: COLORS.navyLight, justifyContent: 'center', alignItems: 'center' },
    loaderWrap: { paddingVertical: 36, alignItems: 'center', gap: 10 },
    loaderText: { fontSize: 13, color: COLORS.textLight, fontWeight: '500' },
});
