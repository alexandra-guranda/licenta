import { Tabs } from 'expo-router';
import { Home, Search, MessageCircle } from 'lucide-react-native';

const NAVY = '#1e3a5f';
const GOLD = '#f0c040';
const GRAY = '#a1a1aa';

export default function TabLayout() {
    return (
        <Tabs
            screenOptions={{
                headerShown: false,
                tabBarActiveTintColor: NAVY,
                tabBarInactiveTintColor: GRAY,
                tabBarStyle: {
                    height: 76,
                    paddingBottom: 16,
                    paddingTop: 8,
                    backgroundColor: '#fff',
                    borderTopWidth: 0.5,
                    borderTopColor: '#e2e4ee',
                    elevation: 12,
                    shadowColor: '#000',
                    shadowOpacity: 0.06,
                    shadowRadius: 12,
                },
                tabBarLabelStyle: { fontSize: 10, fontWeight: '700' },
            }}
        >
            <Tabs.Screen
                name="index"
                options={{ title: 'Acasă', tabBarIcon: ({ color, size }) => <Home color={color} size={size - 2} /> }}
            />
            <Tabs.Screen
                name="search"
                options={{ title: 'Caută', tabBarIcon: ({ color, size }) => <Search color={color} size={size - 2} /> }}
            />
            <Tabs.Screen
                name="ai-chat"
                options={{ title: 'AI Chat', tabBarIcon: ({ color, size }) => <MessageCircle color={color} size={size - 2} /> }}
            />
            <Tabs.Screen name="products"        options={{ href: null }} />
            <Tabs.Screen name="product-details" options={{ href: null }} />
            <Tabs.Screen name="notify"          options={{ href: null }} />
        </Tabs>
    );
}
