import json
import os
from thefuzz import fuzz

class PriceMatcher:
    def __init__(self, similarity_threshold=85):
        """
        similarity_threshold: Scor de la 0 la 100.
        Peste 85 înseamnă că produsele sunt probabil identice.
        """
        self.threshold = similarity_threshold

    def load_data(self, file_path):
        if not os.path.exists(file_path):
            print(f"❌ Error: File {file_path} not found.")
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def find_matches(self, products):
        print(f"🔍 Analyzing {len(products)} products for matches...")

        # Dictionary to store grouped products
        # Key: a "base name", Value: list of product offers
        grouped_deals = {}

        for item in products:
            # We create a search key using the clean name and brand from AI Refiner
            # If AI refiner hasn't run yet, we use raw_name
            name_to_match = item.get('nume_curat', item.get('raw_name', '')).lower()
            brand = item.get('brand', '').lower()

            full_search_string = f"{brand} {name_to_match}".strip()

            found_group = False

            # Compare current product with existing groups
            for group_key in grouped_deals.keys():
                # token_sort_ratio is best here because it ignores word order
                # e.g., "Ariel 10kg" vs "10kg Ariel" -> score 100
                score = fuzz.token_sort_ratio(full_search_string, group_key)

                if score >= self.threshold:
                    grouped_deals[group_key].append(item)
                    found_group = True
                    break

            if not found_group:
                grouped_deals[full_search_string] = [item]

        return grouped_deals

    def report_best_deals(self, grouped_data):
        print("\n" + "="*50)
        print("📊 PRICE COMPARISON REPORT")
        print("="*50)

        matches_found = 0
        for base_name, offers in grouped_data.items():
            # We only care if the product exists in more than one offer
            if len(offers) > 1:
                matches_found += 1
                print(f"\n📦 PRODUCT: {base_name.upper()}")

                # Sort offers by the newest price (cheapest first)
                sorted_offers = sorted(offers, key=lambda x: x['price_new'])

                for offer in sorted_offers:
                    store = offer.get('store', offer.get('magazin', 'Unknown'))
                    price = offer['price_new']
                    old_price = offer.get('price_old', offer.get('pret_vechi', 0))

                    print(f"   💰 {store:12} | Price: {price:6.2f} RON (Was: {old_price:6.2f})")

        if matches_found == 0:
            print("ℹ️ No identical products found across different stores with current threshold.")
        else:
            print(f"\n✨ Identification complete. Found {matches_found} matching product groups.")

if __name__ == "__main__":
    # Path to your processed data (the one coming out of AI Refiner)
    input_file = "data/processed/final_database_march.json"

    matcher = PriceMatcher(similarity_threshold=80) # Slightly lower for better matching
    data = matcher.load_data(input_file)

    if data:
        grouped_results = matcher.find_matches(data)
        matcher.report_best_deals(grouped_results)

        # Optional: Save the matched results to a new file
        output_path = "data/processed/matched_prices_final.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(grouped_results, f, indent=4, ensure_ascii=False)
        print(f"\n📂 Final unified database saved to: {output_path}")