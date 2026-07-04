import React, { useEffect, useState, useRef } from 'react';
import {
    View, Text, FlatList, Image, StyleSheet,
    ActivityIndicator, TouchableOpacity, StatusBar,
    Animated, ScrollView, useWindowDimensions,
} from 'react-native';
import { ChevronLeft, SlidersHorizontal, Tag, CreditCard } from 'lucide-react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { fetchProducts, fetchTopDeals, API_BASE } from '../src/services/api';

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
    border:    '#e2e4ee',
};

const ALL_STORES   = ['Auchan', 'Kaufland', 'Penny', 'Profi', 'Carrefour', 'Mega Image', 'Lidl'];
const SORT_OPTIONS = ['Relevanță', 'Preț ↑', 'Preț ↓', 'Reducere'];

function ProductCard({ item, index, onPress, cardWidth }) {
    const anim = useRef(new Animated.Value(0)).current;
    useEffect(() => {
        Animated.timing(anim, { toValue: 1, duration: 320, delay: Math.min(index * 60, 400), useNativeDriver: true }).start();
    }, []);
    const translateY  = anim.interpolate({ inputRange: [0, 1], outputRange: [24, 0] });
    const hasDiscount = item.price_old && item.price_old > item.price_new;
    const discountPct = hasDiscount
        ? Math.round(((item.price_old - item.price_new) / item.price_old) * 100)
        : null;
    return (
        <Animated.View style={[styles.card, { width: cardWidth }, { opacity: anim, transform: [{ translateY }] }]}>
            <TouchableOpacity onPress={onPress} activeOpacity={0.88} style={{ flex: 1 }}>
                {discountPct && (
                    <View style={styles.discountBadge}>
                        <Tag size={10} color={COLORS.white} />
                        <Text style={styles.discountBadgeText}>-{discountPct}%</Text>
                    </View>
                )}
                {item.requires_card && (
                    <View style={styles.cardBadge}><CreditCard size={10} color={COLORS.white} /></View>
                )}
                <View style={styles.imageWrapper}>
                    <Image source={{ uri: item.image_url }} style={[styles.image, { width: cardWidth - 24 }]} resizeMode="contain" />
                </View>
                <View style={styles.cardBody}>
                    <View style={styles.storePill}><Text style={styles.storeText}>{item.store}</Text></View>
                    <Text style={styles.productName} numberOfLines={3}>{item.name}</Text>
                    <View style={styles.priceRow}>
                        <Text style={styles.priceNew}>{item.price_new.toFixed(2)} lei</Text>
                        {hasDiscount && <Text style={styles.priceOld}>{item.price_old.toFixed(2)} lei</Text>}
                    </View>
                </View>
            </TouchableOpacity>
        </Animated.View>
    );
}

export default function ProductsScreen() {
    const { width } = useWindowDimensions();
    const cardWidth = (width - 48) / 2;
    const router = useRouter();
    const { category, store, deals } = useLocalSearchParams();
    const isDeals = deals === 'true';

    const [data, setData]           = useState({ products: [], count: 0 });
    const [loading, setLoading]     = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [activeSort, setActiveSort] = useState(0);
    const [storeFilter, setStoreFilter] = useState(store || null);
    const pageRef = useRef(0);
    const PAGE_SIZE = 100;

    const headerOpacity = useRef(new Animated.Value(0)).current;
    const headerSlide   = useRef(new Animated.Value(-20)).current;

    useEffect(() => {
        Animated.parallel([
            Animated.timing(headerOpacity, { toValue: 1, duration: 400, useNativeDriver: true }),
            Animated.timing(headerSlide,   { toValue: 0, duration: 400, useNativeDriver: true }),
        ]).start();
        pageRef.current = 0;
        setLoading(true);
        const loader = isDeals
            ? fetchTopDeals(500).then((products) => ({ products: products || [], count: (products || []).length }))
            : fetchProducts(category, null, null, 0, PAGE_SIZE);
        loader
            .then((res) => { setData(res); setLoading(false); })
            .catch(() => setLoading(false));
    }, [category, isDeals]);

    const loadMore = () => {
        if (loadingMore || isDeals || loading) return;
        if (data.products.length >= data.count) return;
        setLoadingMore(true);
        const nextSkip = (pageRef.current + 1) * PAGE_SIZE;
        fetchProducts(category, null, null, nextSkip, PAGE_SIZE).then((res) => {
            pageRef.current += 1;
            setData((prev) => ({ count: res.count, products: [...prev.products, ...(res.products || [])] }));
            setLoadingMore(false);
        }).catch(() => setLoadingMore(false));
    };

    const storesInCategory = React.useMemo(() => {
        const present = new Set((data.products || []).map(p => p.store));
        return ALL_STORES.filter(s => present.has(s));
    }, [data.products]);

    const sortedProducts = React.useMemo(() => {
        const list = [...(data.products || [])];
        if (activeSort === 1) return list.sort((a, b) => a.price_new - b.price_new);
        if (activeSort === 2) return list.sort((a, b) => b.price_new - a.price_new);
        if (activeSort === 3) return list.sort((a, b) => {
            const da = a.price_old ? (a.price_old - a.price_new) / a.price_old : 0;
            const db = b.price_old ? (b.price_old - b.price_new) / b.price_old : 0;
            return db - da;
        });
        return list;
    }, [data.products, activeSort]);

    const displayedProducts = React.useMemo(() => {
        if (!storeFilter) return sortedProducts;
        return sortedProducts.filter(p => p.store === storeFilter);
    }, [sortedProducts, storeFilter]);

    return (
        <View style={styles.container}>
            <StatusBar barStyle="light-content" backgroundColor={COLORS.navy} />

            <Animated.View style={[styles.header, { opacity: headerOpacity, transform: [{ translateY: headerSlide }] }]}>
                <View style={styles.headerTop}>
                    <TouchableOpacity style={styles.backBtn} onPress={() => router.back()} activeOpacity={0.8}>
                        <ChevronLeft size={22} color={COLORS.white} />
                    </TouchableOpacity>
                    <View style={styles.headerTitleWrap}>
                        <Text style={styles.headerTitle} numberOfLines={1}>{isDeals ? 'Oferte de Neratat' : category}</Text>
                        {!loading && (
                            <Text style={styles.headerCount}>{displayedProducts.length} produse</Text>
                        )}
                    </View>
                    <TouchableOpacity style={styles.filterBtn} activeOpacity={0.8}>
                        <SlidersHorizontal size={18} color={COLORS.white} />
                    </TouchableOpacity>
                </View>

                <View style={styles.sortRow}>
                    {SORT_OPTIONS.map((opt, i) => (
                        <TouchableOpacity
                            key={i}
                            style={[styles.sortChip, activeSort === i && styles.sortChipActive]}
                            onPress={() => setActiveSort(i)}
                            activeOpacity={0.8}
                        >
                            <Text style={[styles.sortChipText, activeSort === i && styles.sortChipTextActive]}>{opt}</Text>
                        </TouchableOpacity>
                    ))}
                </View>

                {!loading && storesInCategory.length > 1 && (
                    <ScrollView
                        horizontal
                        showsHorizontalScrollIndicator={false}
                        contentContainerStyle={styles.storeFilterList}
                    >
                        {storesInCategory.map(s => {
                            const active = storeFilter === s;
                            return (
                                <TouchableOpacity
                                    key={s}
                                    style={[styles.storeChip, active && styles.storeChipActive]}
                                    onPress={() => setStoreFilter(active ? null : s)}
                                    activeOpacity={0.8}
                                >
                                    <Text style={[styles.storeChipText, active && styles.storeChipTextActive]}>{s}</Text>
                                </TouchableOpacity>
                            );
                        })}
                    </ScrollView>
                )}
            </Animated.View>

            {loading ? (
                <View style={styles.loaderWrap}>
                    <ActivityIndicator size="large" color={COLORS.navy} />
                    <Text style={styles.loaderText}>Se încarcă produsele...</Text>
                </View>
            ) : displayedProducts.length === 0 ? (
                <View style={styles.emptyWrap}>
                    <Text style={styles.emptyEmoji}>🛒</Text>
                    <Text style={styles.emptyTitle}>Niciun produs găsit</Text>
                    <Text style={styles.emptySub}>
                        {storeFilter ? `${storeFilter} nu are produse în această categorie` : 'Încearcă altă categorie'}
                    </Text>
                </View>
            ) : (
                <FlatList
                    data={displayedProducts}
                    keyExtractor={(_, i) => i.toString()}
                    numColumns={2}
                    columnWrapperStyle={styles.row}
                    contentContainerStyle={styles.listContent}
                    showsVerticalScrollIndicator={false}
                    onEndReached={loadMore}
                    onEndReachedThreshold={0.3}
                    ListFooterComponent={loadingMore ? <ActivityIndicator color={COLORS.navy} style={{ marginVertical: 16 }} /> : null}
                    renderItem={({ item, index }) => (
                        <ProductCard
                            item={item}
                            index={index}
                            cardWidth={cardWidth}
                            onPress={() => router.push({ pathname: '/product-details', params: { id: item.id } })}
                        />
                    )}
                />
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: COLORS.bg },

    header: {
        backgroundColor: COLORS.navy,
        paddingTop: 56, paddingHorizontal: 16,
        borderBottomLeftRadius: 32, borderBottomRightRadius: 32,
        elevation: 12, shadowColor: COLORS.navy, shadowOpacity: 0.35, shadowRadius: 16, zIndex: 10,
    },
    headerTop:       { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
    backBtn:         { width: 40, height: 40, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.18)', justifyContent: 'center', alignItems: 'center' },
    headerTitleWrap: { flex: 1, paddingHorizontal: 12 },
    headerTitle:     { fontSize: 20, fontWeight: '900', color: COLORS.white, letterSpacing: -0.5 },
    headerCount:     { fontSize: 13, color: 'rgba(255,255,255,0.75)', fontWeight: '500', marginTop: 1 },
    filterBtn:       { width: 40, height: 40, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.18)', justifyContent: 'center', alignItems: 'center' },

    sortRow:            { flexDirection: 'row', paddingBottom: 12, gap: 8 },
    sortChip:           { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.15)' },
    sortChipActive:     { backgroundColor: COLORS.white },
    sortChipText:       { fontSize: 13, fontWeight: '600', color: 'rgba(255,255,255,0.85)' },
    sortChipTextActive: { color: COLORS.navyDark },

    storeFilterList: { paddingBottom: 16, gap: 8, paddingRight: 8 },
    storeChip:       { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 16, backgroundColor: 'rgba(255,255,255,0.15)', borderWidth: 1, borderColor: 'rgba(255,255,255,0.3)' },
    storeChipActive: { backgroundColor: COLORS.white, borderColor: COLORS.white },
    storeChipText:   { fontSize: 12, fontWeight: '700', color: 'rgba(255,255,255,0.9)' },
    storeChipTextActive: { color: COLORS.navyDark },

    listContent: { padding: 16, paddingTop: 20, paddingBottom: 40 },
    row: { gap: 16, marginBottom: 16 },

    card: {
        backgroundColor: COLORS.white, borderRadius: 24,
        overflow: 'hidden', elevation: 5,
        shadowColor: '#000', shadowOpacity: 0.08, shadowRadius: 12,
        borderWidth: 1, borderColor: COLORS.border,
    },
    discountBadge:     { position: 'absolute', top: 12, left: 12, zIndex: 2, flexDirection: 'row', alignItems: 'center', backgroundColor: COLORS.red, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 10, gap: 3 },
    discountBadgeText: { color: COLORS.white, fontSize: 11, fontWeight: '900' },
    imageWrapper:      { width: '100%', height: 130, backgroundColor: '#fafafa', justifyContent: 'center', alignItems: 'center' },
    image:             { height: 106 },
    cardBody:          { padding: 12 },
    storePill:         { alignSelf: 'flex-start', backgroundColor: COLORS.navyLight, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8, marginBottom: 6 },
    storeText:         { fontSize: 10, fontWeight: '800', color: COLORS.navyDark, textTransform: 'uppercase', letterSpacing: 0.5 },
    cardBadge:         { position: 'absolute', top: 12, right: 12, zIndex: 2, backgroundColor: COLORS.navy, width: 22, height: 22, borderRadius: 6, justifyContent: 'center', alignItems: 'center' },
    productName:       { fontSize: 13, fontWeight: '600', color: COLORS.textMid, lineHeight: 18, marginBottom: 8, minHeight: 54 },
    priceRow:          { flexDirection: 'row', alignItems: 'flex-end', gap: 6, marginBottom: 10 },
    priceNew:          { fontSize: 17, fontWeight: '900', color: COLORS.red },
    priceOld:          { fontSize: 12, color: COLORS.textLight, textDecorationLine: 'line-through', marginBottom: 1 },

    loaderWrap: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 },
    loaderText: { fontSize: 15, color: COLORS.textLight, fontWeight: '500' },
    emptyWrap:  { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 8 },
    emptyEmoji: { fontSize: 52, marginBottom: 8 },
    emptyTitle: { fontSize: 20, fontWeight: '800', color: COLORS.textDark },
    emptySub:   { fontSize: 15, color: COLORS.textLight, textAlign: 'center', paddingHorizontal: 32 },
});
