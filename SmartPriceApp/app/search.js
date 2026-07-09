import React, { useState, useEffect, useRef } from 'react';
import {
    View, Text, TextInput, FlatList, TouchableOpacity,
    StyleSheet, Image, ActivityIndicator, Keyboard
} from 'react-native';
import { Search, X, ArrowLeft, Clock, ShoppingBag } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { searchProducts } from '../src/services/api';

const COLORS = {
    navy:      '#1e3a5f',
    gold:      '#f0c040',
    bg:        '#f0f2f8',
    textDark:  '#0d1b2e',
    textLight: '#71717a',
    white:     '#fff',
    border:    '#e2e4ee',
    red:       '#ef4444',
};

export default function SearchScreen() {
    const router = useRouter();
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [recentSearches, setRecentSearches] = useState(['Lapte', 'Pui', 'Ulei floarea soarelui']);
    const inputRef = useRef(null);

    useEffect(() => {
        setTimeout(() => inputRef.current?.focus(), 100);
    }, []);

    useEffect(() => {
        if (query.length > 2) {
            const delayDebounceFn = setTimeout(() => {
                performSearch(query);
            }, 300);
            return () => clearTimeout(delayDebounceFn);
        } else {
            setResults([]);
        }
    }, [query]);

    const performSearch = async (txt) => {
        setLoading(true);
        const data = await searchProducts(txt);
        setResults(data);
        setLoading(false);
    };

    const renderProduct = ({ item }) => (
        <TouchableOpacity
            style={styles.productItem}
            onPress={() => router.push({ pathname: '/product-details', params: { id: item.id } })}
        >
            <Image
                source={{ uri: item.image_url }}
                style={styles.productImg}
                resizeMode="contain"
            />
            <View style={styles.productInfo}>
                <Text style={styles.storeTag}>{item.store}</Text>
                <Text style={styles.productName} numberOfLines={3}>{item.name}</Text>
                <View style={styles.priceRow}>
                    <Text style={styles.priceText}>{item.price_new.toFixed(2)} lei</Text>
                    {item.discount > 0 && <Text style={styles.discountText}>-{Math.round(item.discount * 100)}%</Text>}
                </View>
            </View>
        </TouchableOpacity>
    );

    return (
        <View style={styles.container}>
            <View style={styles.searchHeader}>
                <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
                    <ArrowLeft color={COLORS.textDark} size={24} />
                </TouchableOpacity>
                <View style={styles.inputWrapper}>
                    <Search size={18} color={COLORS.navy} />
                    <TextInput
                        ref={inputRef}
                        style={styles.input}
                        placeholder="Caută produse..."
                        value={query}
                        onChangeText={setQuery}
                        returnKeyType="search"
                    />
                    {query.length > 0 && (
                        <TouchableOpacity onPress={() => setQuery('')}>
                            <X size={18} color={COLORS.textLight} />
                        </TouchableOpacity>
                    )}
                </View>
            </View>

            {loading ? (
                <View style={styles.center}>
                    <ActivityIndicator size="large" color={COLORS.navy} />
                </View>
            ) : query.length === 0 ? (

                <View style={styles.historyContainer}>
                    <Text style={styles.sectionTitle}>Căutări recente</Text>
                    {recentSearches.map((item, index) => (
                        <TouchableOpacity
                            key={index}
                            style={styles.historyItem}
                            onPress={() => setQuery(item)}
                        >
                            <Clock size={16} color={COLORS.textLight} />
                            <Text style={styles.historyText}>{item}</Text>
                        </TouchableOpacity>
                    ))}
                </View>
            ) : (

                <FlatList
                    data={results}
                    renderItem={renderProduct}
                    keyExtractor={item => item.id.toString()}
                    contentContainerStyle={styles.list}
                    ListEmptyComponent={
                        <View style={styles.center}>
                            <ShoppingBag size={48} color={COLORS.border} />
                            <Text style={styles.noResults}>Nu am găsit niciun produs.</Text>
                        </View>
                    }
                />
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: COLORS.bg },
    searchHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingTop: 50,
        paddingBottom: 15,
        paddingHorizontal: 20,
        backgroundColor: COLORS.white,
        borderBottomWidth: 1,
        borderBottomColor: COLORS.border,
    },
    backBtn: { marginRight: 15 },
    inputWrapper: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#F1F5F9',
        borderRadius: 12,
        paddingHorizontal: 12,
        height: 45,
    },
    input: {
        flex: 1,
        marginLeft: 8,
        fontSize: 15,
        color: COLORS.textDark,
        fontWeight: '500',
    },
    center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 40 },
    historyContainer: { padding: 20 },
    sectionTitle: { fontSize: 16, fontWeight: '800', color: COLORS.textDark, marginBottom: 15 },
    historyItem: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: COLORS.border },
    historyText: { marginLeft: 12, fontSize: 14, color: COLORS.textLight, fontWeight: '500' },
    list: { padding: 20 },
    productItem: {
        flexDirection: 'row',
        backgroundColor: COLORS.white,
        borderRadius: 16,
        padding: 12,
        marginBottom: 12,
        elevation: 2,
    },
    productImg: { width: 70, height: 70 },
    productInfo: { flex: 1, marginLeft: 15, justifyContent: 'center' },
    storeTag: { fontSize: 10, fontWeight: '800', color: COLORS.navy, textTransform: 'uppercase' },
    productName: { fontSize: 14, fontWeight: '600', color: COLORS.textDark, marginVertical: 2 },
    priceRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    priceText: { fontSize: 16, fontWeight: '800', color: COLORS.red },
    discountText: { fontSize: 12, fontWeight: '700', color: COLORS.gold },
    noResults: { marginTop: 15, color: COLORS.textLight, fontSize: 14, textAlign: 'center' },
});
