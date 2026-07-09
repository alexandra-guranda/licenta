import React, { useEffect, useState, useRef } from 'react';
import {
    View, Text, ScrollView, TouchableOpacity, StyleSheet,
    Image, FlatList, ActivityIndicator, StatusBar,
    Animated, useWindowDimensions,
} from 'react-native';
import {
    ChevronRight, Beef, Apple, Milk, Leaf,
    Beer, Store, Cookie,
    Bath, Home, Percent, Bell, Search, Tag,
} from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { fetchTopDeals, fetchProducts, fetchCategories } from '../src/services/api';

const COLORS = {
    navy:      '#1e3a5f',
    navyDark:  '#0d1b2e',
    navyLight: '#eef2ff',
    gold:      '#f0c040',
    bg:        '#f0f2f8',
    textDark:  '#0d1b2e',
    textMid:   '#334155',
    textLight: '#71717a',
    white:     '#fff',
    red:       '#ef4444',
    redLight:  '#fef2f2',
    border:    '#e2e4ee',
};

const CATEGORII = [
    { name: 'Panificatie & Dulciuri',    icon: <Cookie  color="#d946ef"       size={20}/>, bg: '#fdf4ff', border: '#f5d0fe' },
    { name: 'Carne & Mezeluri',          icon: <Beef    color="#ef4444"       size={20}/>, bg: '#fef2f2', border: '#fecaca' },
    { name: 'Lactate & Oua',             icon: <Milk    color="#3b82f6"       size={20}/>, bg: '#eff6ff', border: '#bfdbfe' },
    { name: 'Legume & Fructe',           icon: <Apple   color={COLORS.gold}   size={20}/>, bg: COLORS.navyLight, border: '#c7d2fe' },
    { name: 'Bauturi',                   icon: <Beer    color="#8b5cf6"       size={20}/>, bg: '#f5f3ff', border: '#ddd6fe' },
    { name: 'Bacanie & Alimente de baza',icon: <Store   color="#6366f1"       size={20}/>, bg: '#eef2ff', border: '#c7d2fe' },
    { name: 'Ingrijire & Curatenie',     icon: <Bath    color="#06b6d4"       size={20}/>, bg: '#ecfeff', border: '#a5f3fc' },
    { name: 'Casa & Diverse',            icon: <Home    color="#64748b"       size={20}/>, bg: '#f8fafc', border: '#e2e8f0' },
];

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
                    <Image source={{ uri: item.image_url }} style={styles.dealImage} resizeMode="contain" />
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

function SmallProductCard({ item, onPress, cardW }) {
    const hasDiscount = item.price_old && item.price_old > item.price_new;
    const discountPct = hasDiscount
        ? Math.round(((item.price_old - item.price_new) / item.price_old) * 100)
        : null;
    return (
        <TouchableOpacity style={[styles.smallCard, { width: cardW }]} onPress={onPress} activeOpacity={0.88}>
            {discountPct && (
                <View style={styles.smallBadge}>
                    <Tag size={9} color={COLORS.white} />
                    <Text style={styles.smallBadgeText}>-{discountPct}%</Text>
                </View>
            )}
            <View style={styles.smallImageWrap}>
                <Image source={{ uri: item.image_url }} style={styles.smallImage} resizeMode="contain" />
            </View>
            <View style={styles.smallBody}>
                <Text style={styles.smallName} numberOfLines={3}>{item.name}</Text>
                <Text style={styles.smallPrice}>{item.price_new.toFixed(2)} lei</Text>
                {hasDiscount && <Text style={styles.smallPriceOld}>{item.price_old.toFixed(2)} lei</Text>}
            </View>
        </TouchableOpacity>
    );
}

function CatItem({ cat, index, onPress, count }) {
    const anim = useRef(new Animated.Value(0)).current;
    useEffect(() => {
        Animated.timing(anim, { toValue: 1, duration: 300, delay: 200 + Math.min(index * 35, 500), useNativeDriver: true }).start();
    }, []);
    const translateX = anim.interpolate({ inputRange: [0, 1], outputRange: [-16, 0] });
    return (
        <Animated.View style={{ opacity: anim, transform: [{ translateX }] }}>
            <TouchableOpacity style={styles.catItem} onPress={onPress} activeOpacity={0.75}>
                <View style={styles.catLeft}>
                    <View style={[styles.iconCircle, { backgroundColor: cat.bg, borderColor: cat.border }]}>
                        {cat.icon}
                    </View>
                    <View style={{ flex: 1, marginLeft: 14 }}>
                        <Text style={styles.catText}>{cat.name}</Text>
                        {count !== undefined && (
                            <Text style={styles.catCount}>{count} produse</Text>
                        )}
                    </View>
                </View>
                <View style={styles.catChevronWrap}>
                    <ChevronRight size={16} color={COLORS.navyDark} />
                </View>
            </TouchableOpacity>
        </Animated.View>
    );
}

export default function HomeScreen() {
    const { width } = useWindowDimensions();
    const cardW = (width - 52) / 2;
    const router = useRouter();
    const [topDeals, setTopDeals]             = useState([]);
    const [loading, setLoading]               = useState(true);
    const [selectedStores, setSelectedStores] = useState([]);
    const [selectedCategories, setSelectedCategories] = useState([]);
    const [inlineProducts, setInlineProducts] = useState([]);
    const [inlineLoading, setInlineLoading]   = useState(false);
    const [categoryCounts, setCategoryCounts] = useState({});
    const scrollY       = useRef(new Animated.Value(0)).current;
    const headerOpacity = useRef(new Animated.Value(0)).current;
    const headerSlide   = useRef(new Animated.Value(-10)).current;

    useEffect(() => {
        Animated.parallel([
            Animated.timing(headerOpacity, { toValue: 1, duration: 500, useNativeDriver: true }),
            Animated.timing(headerSlide,   { toValue: 0, duration: 500, useNativeDriver: true }),
        ]).start();
        fetchTopDeals(20)
            .then(data => { setTopDeals([...data].sort((a, b) => (b.discount || 0) - (a.discount || 0))); setLoading(false); })
            .catch(() => setLoading(false));
        fetchCategories().then(res => {
            const map = {};
            (res.categories || []).forEach(c => { map[c.name] = c.count; });
            setCategoryCounts(map);
        });
    }, []);

    useEffect(() => {
        if (selectedStores.length > 0) {
            setInlineLoading(true);
            fetchProducts(null, null, null, 0, 300)
                .then(res => {
                    let filtered = (res.products || []).filter(p => selectedStores.includes(p.store));
                    if (selectedCategories.length > 0) {
                        filtered = filtered.filter(p => selectedCategories.includes(p.category));
                    }
                    setInlineProducts(filtered);
                    setInlineLoading(false);
                })
                .catch(() => { setInlineProducts([]); setInlineLoading(false); });
        } else {
            setInlineProducts([]);
        }
    }, [selectedStores, selectedCategories]);

    const handleStoreSelect = (store) => {
        setSelectedStores(prev => {
            const next = prev.includes(store) ? prev.filter(s => s !== store) : [...prev, store];
            if (next.length === 0) setSelectedCategories([]);
            return next;
        });
    };

    const handleCategorySelect = (categoryName) => {
        if (selectedStores.length > 0) {
            setSelectedCategories(prev => prev.includes(categoryName) ? prev.filter(c => c !== categoryName) : [...prev, categoryName]);
        } else {
            router.push({ pathname: '/products', params: { category: categoryName, store: '' } });
        }
    };

    const headerHeight = scrollY.interpolate({ inputRange: [0, 80], outputRange: [190, 130], extrapolate: 'clamp' });
    const logoScale    = scrollY.interpolate({ inputRange: [0, 80], outputRange: [1, 0.82],  extrapolate: 'clamp' });
    const subOpacity   = scrollY.interpolate({ inputRange: [0, 60], outputRange: [1, 0],     extrapolate: 'clamp' });

    const getGreeting = () => {
        const h = new Date().getHours();
        if (h < 12) return 'Bună dimineața! ☀️';
        if (h < 18) return 'Bună ziua! 👋';
        return 'Bună seara! 🌙';
    };

    const filteredDeals = selectedStores.length > 0 ? topDeals.filter(p => selectedStores.includes(p.store)) : topDeals;

    return (
        <View style={styles.root}>
            <StatusBar barStyle="light-content" backgroundColor={COLORS.navy} />

            <Animated.View style={[styles.header, { height: headerHeight, opacity: headerOpacity, transform: [{ translateY: headerSlide }] }]}>
                <View style={styles.deco1} />
                <View style={styles.deco2} />
                <View style={styles.headerInner}>
                    <View style={styles.headerTopRow}>
                        <View>
                            <Animated.Text style={[styles.greeting, { opacity: subOpacity }]}>{getGreeting()}</Animated.Text>
                            <Animated.Text style={[styles.logoText, { transform: [{ scale: logoScale }] }]}>SmartPrice</Animated.Text>
                        </View>
                        <TouchableOpacity style={styles.notifBtn} activeOpacity={0.8} onPress={() => router.push('/notify')}>
                            <Bell size={20} color={COLORS.white} />
                            <View style={styles.notifDot} />
                        </TouchableOpacity>
                    </View>
                    <TouchableOpacity activeOpacity={0.85} onPress={() => router.push('/search')}>
                        <Animated.View style={[styles.searchBar, { opacity: subOpacity }]}>
                            <Search size={16} color={COLORS.textLight} />
                            <Text style={styles.searchPlaceholder}>Caută produse sau magazine...</Text>
                        </Animated.View>
                    </TouchableOpacity>
                </View>
            </Animated.View>

            <Animated.ScrollView
                style={styles.scroll}
                showsVerticalScrollIndicator={false}
                onScroll={Animated.event([{ nativeEvent: { contentOffset: { y: scrollY } } }], { useNativeDriver: false })}
                scrollEventThrottle={16}
            >
                <View style={{ height: 44 }} />

                <View style={styles.sectionRow}>
                    <View style={styles.sectionIconWrap}><Percent size={16} color={COLORS.red} /></View>
                    <Text style={styles.sectionTitle}>Oferte de Neratat</Text>
                    <View style={styles.sectionBadge}><Text style={styles.sectionBadgeText}>≥ 35%</Text></View>
                    <TouchableOpacity style={styles.seeAllBtn} onPress={() => router.push({ pathname: '/products', params: { deals: 'true' } })}><Text style={styles.seeAllText}>Vezi toate</Text></TouchableOpacity>
                </View>

                {loading ? (
                    <View style={styles.loaderWrap}>
                        <ActivityIndicator size="large" color={COLORS.navy} />
                        <Text style={styles.loaderText}>Se încarcă ofertele...</Text>
                    </View>
                ) : (
                    <FlatList
                        horizontal
                        data={filteredDeals}
                        keyExtractor={(_, i) => i.toString()}
                        showsHorizontalScrollIndicator={false}
                        contentContainerStyle={styles.dealsList}
                        renderItem={({ item, index }) => (
                            <DealCard
                                item={item}
                                index={index}
                                onPress={() => router.push({ pathname: '/product-details', params: { id: item.id } })}
                            />
                        )}
                    />
                )}

                <View style={[styles.sectionRow, { marginTop: 28 }]}>
                    <View style={[styles.sectionIconWrap, { backgroundColor: COLORS.navyLight }]}><Store size={16} color={COLORS.navy} /></View>
                    <Text style={styles.sectionTitle}>Magazine</Text>
                    {selectedStores.length > 0 && (
                        <TouchableOpacity
                            style={styles.seeAllBtn}
                            onPress={() => { setSelectedStores([]); setSelectedCategories([]); }}
                        >
                            <Text style={styles.seeAllText}>Șterge tot</Text>
                        </TouchableOpacity>
                    )}
                </View>
                <FlatList
                    horizontal
                    data={['Auchan', 'Kaufland', 'Penny', 'Profi', 'Carrefour', 'Mega Image', 'Lidl']}
                    keyExtractor={item => item}
                    showsHorizontalScrollIndicator={false}
                    contentContainerStyle={styles.storeFilterList}
                    renderItem={({ item }) => {
                        const active = selectedStores.includes(item);
                        return (
                            <TouchableOpacity
                                style={[styles.storeChip, active && styles.storeChipActive]}
                                onPress={() => handleStoreSelect(item)}
                                activeOpacity={0.8}
                            >
                                <Text style={[styles.storeChipText, active && styles.storeChipTextActive]}>{item}</Text>
                            </TouchableOpacity>
                        );
                    }}
                />

                <View style={[styles.sectionRow, { marginTop: 28 }]}>
                    <View style={[styles.sectionIconWrap, { backgroundColor: COLORS.navyLight }]}><Leaf size={16} color={COLORS.navy} /></View>
                    <Text style={styles.sectionTitle}>Categorii</Text>
                    {selectedStores.length > 0 && <Text style={styles.storeHint}>{selectedStores.join(', ')}</Text>}
                </View>

                {selectedStores.length > 0 ? (
                    <FlatList
                        horizontal
                        data={CATEGORII}
                        keyExtractor={item => item.name}
                        showsHorizontalScrollIndicator={false}
                        contentContainerStyle={styles.storeFilterList}
                        renderItem={({ item: cat }) => {
                            const catActive = selectedCategories.includes(cat.name);
                            return (
                                <TouchableOpacity
                                    style={[styles.storeChip, catActive && styles.storeChipActive]}
                                    onPress={() => handleCategorySelect(cat.name)}
                                    activeOpacity={0.8}
                                >
                                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                                        {React.cloneElement(cat.icon, { color: catActive ? COLORS.white : undefined })}
                                        <Text style={[styles.storeChipText, catActive && styles.storeChipTextActive]}>{cat.name}</Text>
                                    </View>
                                </TouchableOpacity>
                            );
                        }}
                    />
                ) : (
                    <View style={styles.catCard}>
                        {CATEGORII.map((cat, index) => (
                            <CatItem key={index} cat={cat} index={index} count={categoryCounts[cat.name]} onPress={() => handleCategorySelect(cat.name)} />
                        ))}
                    </View>
                )}

                {selectedStores.length > 0 && (
                    <View style={styles.inlineSection}>
                        <View style={styles.inlineHeader}>
                            <Text style={styles.inlineTitle} numberOfLines={1}>
                                {selectedCategories.length > 0 ? selectedCategories.join(', ') : 'Toate produsele'}
                            </Text>
                            <TouchableOpacity
                                style={styles.seeAllBtn}
                                onPress={() => router.push({ pathname: '/products', params: { category: selectedCategories.length === 1 ? selectedCategories[0] : '', store: selectedStores.join(',') } })}
                            >
                                <Text style={styles.seeAllText}>Vezi toate</Text>
                            </TouchableOpacity>
                        </View>

                        {inlineLoading ? (
                            <View style={[styles.loaderWrap, { paddingVertical: 24 }]}>
                                <ActivityIndicator size="small" color={COLORS.navy} />
                                <Text style={styles.loaderText}>Se încarcă...</Text>
                            </View>
                        ) : inlineProducts.length === 0 ? (
                            <View style={styles.emptyInline}>
                                <Text style={styles.emptyInlineText}>Niciun produs găsit</Text>
                            </View>
                        ) : (
                            <View style={styles.inlineGrid}>
                                {inlineProducts.slice(0, 20).map((item, i) => (
                                    <SmallProductCard
                                        key={i}
                                        item={item}
                                        cardW={cardW}
                                        onPress={() => router.push({ pathname: '/product-details', params: { id: item.id } })}
                                    />
                                ))}
                            </View>
                        )}
                    </View>
                )}

                <View style={{ height: 80 }} />
            </Animated.ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    root:   { flex: 1, backgroundColor: COLORS.bg },
    scroll: { flex: 1, marginTop: -28 },

    header: {
        backgroundColor: COLORS.navy,
        paddingTop: 52, paddingHorizontal: 20,
        borderBottomLeftRadius: 36, borderBottomRightRadius: 36,
        overflow: 'hidden', elevation: 14,
        shadowColor: COLORS.navy, shadowOpacity: 0.4, shadowRadius: 20, zIndex: 10,
    },
    headerInner:   { flex: 1, justifyContent: 'flex-start' },
    headerTopRow:  { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 },
    greeting:      { fontSize: 14, color: 'rgba(255,255,255,0.8)', fontWeight: '500', marginBottom: 2 },
    logoText:      { fontSize: 36, fontWeight: '900', color: COLORS.white, letterSpacing: -1.5, lineHeight: 38 },
    notifBtn:      { width: 42, height: 42, borderRadius: 15, backgroundColor: 'rgba(255,255,255,0.18)', justifyContent: 'center', alignItems: 'center', marginTop: 18 },
    notifDot:      { position: 'absolute', top: 9, right: 9, width: 8, height: 8, borderRadius: 4, backgroundColor: COLORS.red, borderWidth: 1.5, borderColor: COLORS.navy },
    searchBar:     { flexDirection: 'row', alignItems: 'center', backgroundColor: COLORS.white, borderRadius: 16, paddingHorizontal: 14, paddingVertical: 11, gap: 10, marginBottom: 6 },
    searchPlaceholder: { fontSize: 14, color: COLORS.textLight, fontWeight: '500' },
    deco1: { position: 'absolute', width: 160, height: 160, borderRadius: 80, backgroundColor: 'rgba(255,255,255,0.07)', top: -40, right: -30 },
    deco2: { position: 'absolute', width: 100, height: 100, borderRadius: 50,  backgroundColor: 'rgba(255,255,255,0.06)', bottom: 10, right: 80 },

    sectionRow:       { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, marginBottom: 16, gap: 8 },
    sectionIconWrap:  { width: 30, height: 30, borderRadius: 10, backgroundColor: COLORS.redLight, justifyContent: 'center', alignItems: 'center' },
    sectionTitle:     { fontSize: 20, fontWeight: '800', color: COLORS.textDark, flex: 1, letterSpacing: -0.3 },
    sectionBadge:     { backgroundColor: COLORS.gold, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
    sectionBadgeText: { color: COLORS.navyDark, fontSize: 11, fontWeight: '800' },
    seeAllBtn:        { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10, borderWidth: 1.5, borderColor: COLORS.navy },
    seeAllText:       { fontSize: 12, fontWeight: '700', color: COLORS.navyDark },
    storeHint:        { fontSize: 12, fontWeight: '700', color: COLORS.navy, backgroundColor: COLORS.navyLight, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },

    dealsList:     { paddingLeft: 20, paddingRight: 8, paddingBottom: 8 },
    dealCard:      { backgroundColor: COLORS.white, width: 176, borderRadius: 28, marginRight: 14, overflow: 'hidden', elevation: 7, shadowColor: '#000', shadowOpacity: 0.09, shadowRadius: 14, borderWidth: 1, borderColor: COLORS.border },
    dealBadge:     { position: 'absolute', top: 12, left: 12, zIndex: 2, backgroundColor: COLORS.red, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 12 },
    dealBadgeText: { color: COLORS.white, fontSize: 12, fontWeight: '900' },
    dealImageWrap: { width: '100%', height: 120, backgroundColor: '#fafafa', justifyContent: 'center', alignItems: 'center' },
    dealImage:     { width: 150, height: 100 },
    dealBody:      { padding: 12 },
    dealStorePill: { alignSelf: 'flex-start', backgroundColor: COLORS.navyLight, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8, marginBottom: 6 },
    dealStoreText: { fontSize: 10, fontWeight: '800', color: COLORS.navyDark, textTransform: 'uppercase', letterSpacing: 0.5 },
    dealName:      { fontSize: 14, fontWeight: '600', color: COLORS.textMid, marginBottom: 8, lineHeight: 19, minHeight: 38 },
    dealPriceRow:  { flexDirection: 'row', alignItems: 'flex-end', gap: 6 },
    dealPriceNew:  { fontSize: 18, fontWeight: '900', color: COLORS.red },
    dealPriceOld:  { fontSize: 12, color: COLORS.textLight, textDecorationLine: 'line-through', marginBottom: 2 },

    catCard:        { backgroundColor: COLORS.white, marginHorizontal: 20, borderRadius: 28, elevation: 4, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 12, overflow: 'hidden', borderWidth: 1, borderColor: COLORS.border },
    catItem:        { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 18, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
    catLeft:        { flexDirection: 'row', alignItems: 'center', flex: 1 },
    iconCircle:     { width: 44, height: 44, borderRadius: 14, justifyContent: 'center', alignItems: 'center', borderWidth: 1 },
    catText:        { fontSize: 15, fontWeight: '700', color: COLORS.textDark },
    catCount:       { fontSize: 12, fontWeight: '500', color: COLORS.textLight, marginTop: 1 },
    catChevronWrap: { width: 28, height: 28, borderRadius: 9, backgroundColor: COLORS.navyLight, justifyContent: 'center', alignItems: 'center' },

    loaderWrap: { paddingVertical: 36, alignItems: 'center', gap: 10 },
    loaderText: { fontSize: 14, color: COLORS.textLight, fontWeight: '500' },

    storeFilterList:     { paddingHorizontal: 20, paddingBottom: 4, gap: 8 },
    storeChip:           { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20, backgroundColor: COLORS.white, borderWidth: 1.5, borderColor: COLORS.border },
    storeChipActive:     { backgroundColor: COLORS.navy, borderColor: COLORS.navy },
    storeChipText:       { fontSize: 13, fontWeight: '700', color: COLORS.textMid },
    storeChipTextActive: { color: COLORS.white },

    inlineSection: { marginTop: 28, paddingHorizontal: 20 },
    inlineHeader:  { flexDirection: 'row', alignItems: 'center', marginBottom: 14, gap: 8 },
    inlineTitle:   { fontSize: 17, fontWeight: '800', color: COLORS.textDark, flex: 1, letterSpacing: -0.3 },
    inlineGrid:    { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },

    smallCard:      { backgroundColor: COLORS.white, borderRadius: 20, overflow: 'hidden', elevation: 4, shadowColor: '#000', shadowOpacity: 0.07, shadowRadius: 10, borderWidth: 1, borderColor: COLORS.border },
    smallBadge:     { position: 'absolute', top: 8, left: 8, zIndex: 2, flexDirection: 'row', alignItems: 'center', backgroundColor: COLORS.red, paddingHorizontal: 6, paddingVertical: 3, borderRadius: 8, gap: 2 },
    smallBadgeText: { color: COLORS.white, fontSize: 10, fontWeight: '900' },
    smallImageWrap: { width: '100%', height: 110, backgroundColor: '#fafafa', justifyContent: 'center', alignItems: 'center', padding: 10 },
    smallImage:     { width: '100%', height: '100%' },
    smallBody:      { padding: 10 },
    smallName:      { fontSize: 12, fontWeight: '600', color: COLORS.textMid, lineHeight: 16, marginBottom: 6, minHeight: 32 },
    smallPrice:     { fontSize: 15, fontWeight: '900', color: COLORS.red },
    smallPriceOld:  { fontSize: 11, color: COLORS.textLight, textDecorationLine: 'line-through', marginTop: 2 },
    emptyInline:    { paddingVertical: 24, alignItems: 'center' },
    emptyInlineText:{ fontSize: 14, color: COLORS.textLight, fontWeight: '500' },
});
