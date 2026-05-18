export const API_BASE = "http://192.168.1.134:8001";

export const fetchProducts = async (category = null, query = null, store = null) => {
    try {
        let url = `${API_BASE}/products?`;
        if (category) url += `category=${encodeURIComponent(category)}&`;
        if (query) url += `q=${encodeURIComponent(query)}&`;
        if (store) url += `store=${encodeURIComponent(store)}&`;

        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error("API Error Products:", error);
        return { products: [], count: 0 };
    }
};

export const fetchTopDeals = async (limit = 15) => {
    try {
        const response = await fetch(`${API_BASE}/top-deals?limit=${limit}`);
        if (!response.ok) return [];
        return await response.json();
    } catch (error) {
        console.error("API Error TopDeals:", error);
        return [];
    }
};

export const fetchCategories = async () => {
    try {
        const response = await fetch(`${API_BASE}/categories`);
        return await response.json();
    } catch (error) {
        console.error("API Error Categories:", error);
        return { categories: [] };
    }
};

export const fetchProduct = async (id) => {
    try {
        const response = await fetch(`${API_BASE}/products/${id}`);
        if (!response.ok) return null;
        return await response.json();
    } catch (error) {
        console.error("API Error Product:", error);
        return null;
    }
};

export const searchProducts = async (query) => {
    try {
        const response = await fetch(`${API_BASE}/products?q=${encodeURIComponent(query)}&limit=20`);
        const data = await response.json();
        return data.products || [];
    } catch (error) {
        console.error("API Error Search:", error);
        return [];
    }
};

// Funcția de Chat AI
export const askAI = async (message) => {
    try {
        const response = await fetch(`${API_BASE}/ai/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        return await response.json();
    } catch (error) {
        console.error("AI Chat Error:", error);
        return { reply: "Scuze, am o mică eroare tehnică. Reîncearcă imediat!" };
    }
};