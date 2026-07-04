import React, { useEffect, useState } from 'react';
import {
    View, Text, StyleSheet, ScrollView, Image,
    TouchableOpacity, ActivityIndicator, StatusBar, FlatList,
} from 'react-native';
import { ArrowLeft, Tag, CreditCard, Store } from 'lucide-react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { fetchProduct, fetchProducts, compareProduct } from '../src/services/api';

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

function SimilarCard({ item, onPress }) {
    const discount = item.price_old && item.price_old > item.price_new
        ? Math.round(((item.price_old - item.price_new) / item.price_old) * 100)
        : null;

    return (
        <TouchableOpacity style={styles.simCard} onPress={onPress} activeOpacity={0.85}>
            {discount && (
                <View style={styles.simBadge}>
                    <Text style={styles.simBadgeText}>-{discount}%</Text>
                </View>
            )}
            <Image
                source={{ uri: item.image_url }}
                style={styles.simImage}
                resizeMode="contain"
            />
            <Text style={styles.simStore}>{item.store}</Text>
            <Text style={styles.simName} numberOfLines={3}>{item.name}</Text>
            <Text style={styles.simPrice}>{item.price_new.toFixed(2)} lei</Text>
        </TouchableOpacity>
    );
}

export default function ProductDetailsScreen() {
    const router = useRouter();
    const { id } = useLocalSearchParams();

    const [product, setProduct] = useState(null);
    const [similar, setSimilar] = useState([]);
    const [compareResults, setCompareResults] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!id) return;
        fetchProduct(id).then((p) => {
            setProduct(p);
            setLoading(false);
            if (p?.name) {
                compareProduct(p.name).then((res) => {
                    setCompareResults(res.filter((x) => x.id !== p.id));
                });
            }
            if (p?.category) {
                fetchProducts(p.category).then((res) => {
                    const others = (res.products || []).filter(
                        (x) => x.id !== p.id && x.store !== p.store
                    );
                    setSimilar(others.slice(0, 10));
                });
            }
        });
    }, [id]);

    if (loading) {
        return (
            <View style={styles.center}>
                <ActivityIndicator size="large" color={COLORS.navy} />
            </View>
        );
    }

    if (!product) {
        return (
            <View style={styles.center}>
                <Text style={styles.errorText}>Produsul nu a fost găsit.</Text>
                <TouchableOpacity style={styles.backBtnCenter} onPress={() => router.back()}>
                    <Text style={styles.backBtnCenterText}>Înapoi</Text>
                </TouchableOpacity>
            </View>
        );
    }

    const hasDiscount = product.price_old && product.price_old > product.price_new;
    const discountPct = hasDiscount
        ? Math.round(((product.price_old - product.price_new) / product.price_old) * 100)
        : null;

    return (
        <View style={styles.root}>
            <StatusBar barStyle="light-content" backgroundColor={COLORS.navy} />

            <View style={styles.header}>
                <TouchableOpacity style={styles.backBtn} onPress={() => router.back()} activeOpacity={0.8}>
                    <ArrowLeft size={20} color={COLORS.white} />
                </TouchableOpacity>
                <Text style={styles.headerTitle} numberOfLines={1}>{product.name}</Text>
                <View style={{ width: 40 }} />
            </View>

            <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>

                <View style={styles.imageCard}>
                    {discountPct && (
                        <View style={styles.discountBadge}>
                            <Tag size={11} color={COLORS.navyDark} />
                            <Text style={styles.discountBadgeText}>-{discountPct}%</Text>
                        </View>
                    )}
                    <Image
                        source={{ uri: product.image_url }}
                        style={styles.image}
                        resizeMode="contain"
                    />
                </View>

                <View style={styles.infoCard}>
                    <View style={styles.pillRow}>
                        <View style={styles.storePill}>
                            <Store size={11} color={COLORS.navyDark} />
                            <Text style={styles.storePillText}>{product.store}</Text>
                        </View>
                        <View style={styles.catPill}>
                            <Text style={styles.catPillText}>{product.category}</Text>
                        </View>
                        {product.requires_card && (
                            <View style={styles.cardPill}>
                                <CreditCard size={11} color={COLORS.white} />
                                <Text style={styles.cardPillText}>Card necesar</Text>
                            </View>
                        )}
                    </View>

                    <Text style={styles.productName}>{product.name}</Text>

                    {product.brand && product.brand !== 'Generic' && (
                        <Text style={styles.brand}>{product.brand}</Text>
                    )}

                    <View style={styles.priceSection}>
                        <Text style={styles.priceNew}>{product.price_new.toFixed(2)} lei</Text>
                        {hasDiscount && (
                            <View style={styles.priceOldWrap}>
                                <Text style={styles.priceOld}>{product.price_old.toFixed(2)} lei</Text>
                                <View style={styles.savingsBadge}>
                                    <Text style={styles.savingsText}>
                                        Economisești {(product.price_old - product.price_new).toFixed(2)} lei
                                    </Text>
                                </View>
                            </View>
                        )}
                    </View>

                </View>

                {compareResults.length > 0 && (
                    <View style={styles.compareSection}>
                        <Text style={styles.sectionTitle}>Prețuri la alte magazine</Text>
                        {compareResults.map((item, i) => {
                            const isCheaper = item.price_new < product.price_new;
                            const isExpensive = item.price_new > product.price_new;
                            return (
                                <TouchableOpacity
                                    key={i}
                                    style={styles.compareRow}
                                    onPress={() => router.push({ pathname: '/product-details', params: { id: item.id } })}
                                    activeOpacity={0.8}
                                >
                                    <Image source={{ uri: item.image_url }} style={styles.compareImg} resizeMode="contain" />
                                    <View style={styles.compareInfo}>
                                        <Text style={styles.compareStore}>{item.store}</Text>
                                        <Text style={styles.compareName} numberOfLines={1}>{item.name}</Text>
                                    </View>
                                    <View style={styles.comparePriceWrap}>
                                        <Text style={[styles.comparePrice, isCheaper && styles.cheaperPrice, isExpensive && styles.expensivePrice]}>
                                            {item.price_new.toFixed(2)} lei
                                        </Text>
                                        {isCheaper && (
                                            <Text style={styles.savingTag}>-{(product.price_new - item.price_new).toFixed(2)} lei</Text>
                                        )}
                                    </View>
                                </TouchableOpacity>
                            );
                        })}
                    </View>
                )}

                {similar.length > 0 && (
                    <View style={styles.similarSection}>
                        <Text style={styles.sectionTitle}>Aceeași categorie, alte magazine</Text>
                        <FlatList
                            horizontal
                            data={similar}
                            keyExtractor={(_, i) => i.toString()}
                            showsHorizontalScrollIndicator={false}
                            contentContainerStyle={styles.simList}
                            renderItem={({ item }) => (
                                <SimilarCard
                                    item={item}
                                    onPress={() => router.push({ pathname: '/product-details', params: { id: item.id } })}
                                />
                            )}
                        />
                    </View>
                )}

                <View style={{ height: 40 }} />
            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    root:   { flex: 1, backgroundColor: COLORS.bg },
    center: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 16, backgroundColor: COLORS.bg },
    errorText:        { fontSize: 16, color: COLORS.textLight, fontWeight: '600' },
    backBtnCenter:    { backgroundColor: COLORS.navy, paddingHorizontal: 24, paddingVertical: 10, borderRadius: 14 },
    backBtnCenterText:{ color: COLORS.white, fontWeight: '700', fontSize: 14 },

    header: {
        backgroundColor: COLORS.navy,
        flexDirection: 'row', alignItems: 'center',
        paddingTop: 56, paddingBottom: 16, paddingHorizontal: 16,
        elevation: 10, shadowColor: COLORS.navy, shadowOpacity: 0.35, shadowRadius: 14,
    },
    backBtn:     { width: 40, height: 40, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.15)', justifyContent: 'center', alignItems: 'center' },
    headerTitle: { flex: 1, fontSize: 17, fontWeight: '800', color: COLORS.white, textAlign: 'center', paddingHorizontal: 8 },

    scroll: { paddingTop: 20 },

    imageCard: {
        marginHorizontal: 20, backgroundColor: COLORS.white,
        borderRadius: 28, padding: 24, alignItems: 'center',
        elevation: 4, shadowColor: '#000', shadowOpacity: 0.07, shadowRadius: 12,
        borderWidth: 1, borderColor: COLORS.border, marginBottom: 16,
    },
    discountBadge:     { position: 'absolute', top: 14, left: 14, flexDirection: 'row', alignItems: 'center', backgroundColor: COLORS.gold, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 12, gap: 4 },
    discountBadgeText: { fontSize: 13, fontWeight: '900', color: COLORS.navyDark },
    image:             { width: 220, height: 220 },

    infoCard: {
        marginHorizontal: 20, backgroundColor: COLORS.white,
        borderRadius: 28, padding: 20,
        elevation: 4, shadowColor: '#000', shadowOpacity: 0.07, shadowRadius: 12,
        borderWidth: 1, borderColor: COLORS.border, marginBottom: 16,
    },
    pillRow:      { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 14 },
    storePill:    { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: COLORS.navyLight, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 10 },
    storePillText:{ fontSize: 11, fontWeight: '800', color: COLORS.navyDark },
    catPill:      { backgroundColor: '#f1f5f9', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 10 },
    catPillText:  { fontSize: 11, fontWeight: '600', color: COLORS.textMid },
    cardPill:     { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: COLORS.navy, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 10 },
    cardPillText: { fontSize: 11, fontWeight: '700', color: COLORS.white },

    productName: { fontSize: 22, fontWeight: '900', color: COLORS.textDark, lineHeight: 28, marginBottom: 4 },
    brand:       { fontSize: 14, fontWeight: '600', color: COLORS.textLight, marginBottom: 16 },

    priceSection:  { marginBottom: 20 },
    priceNew:      { fontSize: 36, fontWeight: '900', color: COLORS.red, lineHeight: 40 },
    priceOldWrap:  { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 4 },
    priceOld:      { fontSize: 16, color: COLORS.textLight, textDecorationLine: 'line-through' },
    savingsBadge:  { backgroundColor: '#fef9e7', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8, borderWidth: 1, borderColor: COLORS.gold },
    savingsText:   { fontSize: 12, fontWeight: '700', color: COLORS.navyDark },

    compareSection:    { marginHorizontal: 20, marginBottom: 16 },
    compareRow:        { flexDirection: 'row', alignItems: 'center', backgroundColor: COLORS.white, borderRadius: 16, padding: 12, marginBottom: 10, elevation: 2, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 8, borderWidth: 1, borderColor: COLORS.border },
    compareImg:        { width: 52, height: 52, borderRadius: 10 },
    compareInfo:       { flex: 1, marginHorizontal: 12 },
    compareStore:      { fontSize: 10, fontWeight: '800', color: COLORS.navyDark, textTransform: 'uppercase', marginBottom: 2 },
    compareName:       { fontSize: 12, fontWeight: '600', color: COLORS.textMid },
    comparePriceWrap:  { alignItems: 'flex-end' },
    comparePrice:      { fontSize: 16, fontWeight: '900', color: COLORS.textDark },
    cheaperPrice:      { color: '#16a34a' },
    expensivePrice:    { color: COLORS.red },
    savingTag:         { fontSize: 10, fontWeight: '700', color: '#16a34a', backgroundColor: '#f0fdf4', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, marginTop: 2 },

    similarSection: { marginHorizontal: 20 },
    sectionTitle:   { fontSize: 18, fontWeight: '800', color: COLORS.textDark, marginBottom: 14 },
    simList:        { paddingBottom: 4 },
    simCard: {
        width: 140, backgroundColor: COLORS.white, borderRadius: 20, marginRight: 12,
        padding: 10, elevation: 3, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8,
        borderWidth: 1, borderColor: COLORS.border,
    },
    simBadge:     { alignSelf: 'flex-start', backgroundColor: COLORS.gold, paddingHorizontal: 7, paddingVertical: 3, borderRadius: 8, marginBottom: 6 },
    simBadgeText: { fontSize: 10, fontWeight: '900', color: COLORS.navyDark },
    simImage:     { width: '100%', height: 80, marginBottom: 8 },
    simStore:     { fontSize: 9, fontWeight: '800', color: COLORS.navyDark, textTransform: 'uppercase', marginBottom: 2 },
    simName:      { fontSize: 12, fontWeight: '600', color: COLORS.textMid, lineHeight: 16, marginBottom: 4, minHeight: 48 },
    simPrice:     { fontSize: 15, fontWeight: '900', color: COLORS.red },
});
