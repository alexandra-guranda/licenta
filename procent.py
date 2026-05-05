import json
import os

def audit_one_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        total = len(data)
        failed_cat = sum(1 for x in data if x.get('category') == "Necategorizat")
        generic_brand = sum(1 for x in data if x.get('brand') == "Generic")

        accuracy_cat = ((total - failed_cat) / total) * 100

        print(f"\n--- REZULTATE AUDIT: {os.path.basename(file_path)} ---")
        print(f"✅ Total produse: {total}")
        print(f"🎯 Categorisite corect: {total - failed_cat}")
        print(f"⚠️ Eșuate (Necategorizat): {failed_cat}")
        print(f"📊 Acuratețe Categorisire: {accuracy_cat:.2f}%")
        print(f"🏷️ Produse fără brand (Generic): {generic_brand}")
        print("-" * 40)

    except Exception as e:
        print(f"❌ Eroare: {e}")

# AICI APELĂM FUNCȚIA
if __name__ == "__main__":
    # Verifică dacă calea este corectă pe calculatorul tău
    cale_fisier = "outputs/refined/refined_data_profi.json"
    audit_one_file(cale_fisier)