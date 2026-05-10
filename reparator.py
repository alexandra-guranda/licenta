import json
import re
import logging
import ollama
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

INPUT_DIR  = Path("outputs/raw_web")
OUTPUT_DIR = Path("outputs/refined_llama")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AI_MODEL      = "llama3.2:3b"
AI_BATCH_SIZE = 1

AI_CATEGORIES = [
    "Panificatie & Dulciuri", "Carne & Mezeluri", "Lactate & Oua",
    "Legume & Fructe", "Bauturi", "Bacanie & Alimente de baza",
    "Ingrijire & Curatenie", "Casa & Diverse",
]

RAW_NAME_UNRELIABLE_STORES = {"Penny", "Auchan"}
FALLBACK_CATEGORY = "Necategorizat"

# Minimum word-overlap ratio between AI-extracted name and raw_name to trust AI name
_MIN_NAME_OVERLAP = 0.5

VALID_CATEGORIES = {
    "Ingrijire & Curatenie", "Carne & Mezeluri", "Lactate & Oua",
    "Panificatie & Dulciuri", "Bauturi", "Legume & Fructe",
    "Bacanie & Alimente de baza", "Casa & Diverse", "Necategorizat",
}

EXTERNAL_CATEGORY_MAP: dict[str, str] = {
    "lactate & ouă": "Lactate & Oua", "lactate & oua": "Lactate & Oua",
    "băuturi": "Bauturi", "băuturi alcoolice": "Bauturi",
    "băcănie": "Bacanie & Alimente de baza", "bacanie": "Bacanie & Alimente de baza",
    "brutărie & patiserie": "Panificatie & Dulciuri", "brutarie & patiserie": "Panificatie & Dulciuri",
    "dulciuri & mic dejun": "Panificatie & Dulciuri",
    "înghețată & congelate": "Panificatie & Dulciuri", "inghetata & congelate": "Panificatie & Dulciuri",
    "carne & pește": "Carne & Mezeluri", "carne & peste": "Carne & Mezeluri",
    "mezeluri & ready meals": "Carne & Mezeluri",
    "fructe & legume": "Legume & Fructe",
    "detergenți & igienizare": "Ingrijire & Curatenie", "detergenti & igienizare": "Ingrijire & Curatenie",
    "cosmetice": "Ingrijire & Curatenie", "îngrijire & curățenie": "Ingrijire & Curatenie",
    "casă & agrement": "Casa & Diverse", "casa & agrement": "Casa & Diverse",
    "pet shop": "Casa & Diverse",
    "produse vegetale": "Necategorizat",
    "dietetic, eco & internațional": "Necategorizat", "dietetic, eco & international": "Necategorizat",
}

BRAND_TO_CATEGORY: dict[str, str] = {
    "Branza": "Lactate & Oua", "Cascaval": "Lactate & Oua", "Telemea": "Lactate & Oua",
    "Smantana": "Lactate & Oua", "Iaurt": "Lactate & Oua", "Lapte": "Lactate & Oua",
    "Unt": "Lactate & Oua", "Mozzarella": "Lactate & Oua", "Mascarpone": "Lactate & Oua",
    "Urda": "Lactate & Oua", "Cas": "Lactate & Oua", "Kefir": "Lactate & Oua",
    "Budinca": "Lactate & Oua", "Frisca": "Lactate & Oua", "Crema": "Lactate & Oua",
    "Salam": "Carne & Mezeluri", "Carnati": "Carne & Mezeluri", "Sunca": "Carne & Mezeluri",
    "Mici": "Carne & Mezeluri", "Ceafa": "Carne & Mezeluri", "Pulpe": "Carne & Mezeluri",
    "Piept": "Carne & Mezeluri", "Muschi": "Carne & Mezeluri", "Parizer": "Carne & Mezeluri",
    "Slanina": "Carne & Mezeluri", "Scaricica": "Carne & Mezeluri", "Carcasa": "Carne & Mezeluri",
    "Obrajori": "Carne & Mezeluri", "Kaizer": "Carne & Mezeluri", "Cabanos": "Carne & Mezeluri",
    "Mere": "Legume & Fructe", "Pere": "Legume & Fructe", "Telina": "Legume & Fructe",
    "Dovleac": "Legume & Fructe", "Ciuperci": "Legume & Fructe", "Zmeura": "Legume & Fructe",
    "Cartofi": "Legume & Fructe", "Fasole": "Legume & Fructe", "Mazare": "Legume & Fructe",
    "Gogosari": "Legume & Fructe", "Castraveti": "Legume & Fructe", "Masline": "Legume & Fructe",
    "Ardei": "Legume & Fructe", "Ananas": "Legume & Fructe",
    "Migdale": "Bacanie & Alimente de baza", "Stafide": "Legume & Fructe",
    "Arahide": "Bacanie & Alimente de baza", "Alune": "Bacanie & Alimente de baza",
    "Faina": "Bacanie & Alimente de baza", "Zahar": "Bacanie & Alimente de baza",
    "Orez": "Bacanie & Alimente de baza", "Paste": "Bacanie & Alimente de baza",
    "Ulei": "Bacanie & Alimente de baza", "Ketchup": "Bacanie & Alimente de baza",
    "Mustar": "Bacanie & Alimente de baza", "Otet": "Bacanie & Alimente de baza",
    "Sare": "Bacanie & Alimente de baza", "Margarina": "Bacanie & Alimente de baza",
    "Miere": "Bacanie & Alimente de baza", "Sirop": "Bacanie & Alimente de baza",
    "Drojdie": "Bacanie & Alimente de baza", "Malai": "Bacanie & Alimente de baza",
    "Ton": "Bacanie & Alimente de baza",
    "Vin": "Bauturi", "Bere": "Bauturi", "Cafea": "Bacanie & Alimente de baza", "Capsule": "Bacanie & Alimente de baza",
    "Suc": "Bauturi", "Nectar": "Bauturi", "Apa": "Bauturi", "Bautura": "Bauturi",
    "Rom": "Bauturi", "Gin": "Bauturi", "Vodca": "Bauturi", "Vodka": "Bauturi",
    "Whisky": "Bauturi", "Whiskey": "Bauturi", "Lichior": "Bauturi", "Cidru": "Bauturi",
    "Prosecco": "Bauturi", "Rachiu": "Bauturi", "Palinca": "Bauturi", "Vinars": "Bauturi",
    "Cocktail": "Bauturi", "Aperitiv": "Bauturi", "Ceai": "Bacanie & Alimente de baza", "Vermut": "Bauturi",
}

# All categories are overridable — keyword rules always beat AI when they match.
OVERRIDABLE_CATEGORIES = set(VALID_CATEGORIES)

KEYWORD_CATEGORIES: dict[str, list[str]] = {
    "Ingrijire & Curatenie": [
        "detergent automat", "detergent vase", "detergent lichid", "detergent pudra",
        "detergent pardoseala", "detergent manual", "balsam rufe", "balsam par",
        "pasta dinti", "periuta dinti", "apa de gura",
        "gel de dus", "gel de baie", "gel ras", "sampon",
        "pampers", "scutece", "absorbante", "tampoane", "servetele umede",
        "hartie igienica", "prosop hartie", "servetele cosmetice", "servetele masa",
        "sapun lichid", "sapun solid", "sapun antibacterian",
        "protex", "colgate", "ariel", "persil", "dero", "domestos", "lenor",
        "perwoll", "vanish", "bref ", "cif ", "ajax", "fairy", "clin ",
        "sano ", "mr. proper", "mr proper", "torre detergent",
        "deodorant", "deo spray", "antiperspirant", "vopsea par", "vopsea de oua",
        "odorizant", "dezinfectant", "igienizant", "spray forte",
        "nivea", "garnier", "loreal", "elmiplant", "gerovital", "borotalco",
        "palmolive", "apa micelara", "solutie suprafete", "solutie curatat",
        "lichid parbriz", "aleze", "seni ",
        "lacalut", "aquafresh", "parodontax",
        "spuma de ras", "gel de ras", "after shave",
        "crema depilatoare", "epilator",
        "detartrant", "bureți", "bureti pentru", "pentru vase",
        "blush", "fond de ten", "ruj ", "oja ", "fard ", "mascara",
        "creion de ochi", "creion contur", "rimel ", "tus de ochi",
        "loțiune", "lotiune", "crema de maini", "crema de corp", "crema hidratanta",
        "servetele demachiante", "dischete demachiante",
        "dischete ", "dischete baby", "dischete cosmetice",
        "lac unghii", "oja de unghii",
        "vopsea permanenta", "vopsea pentru par", "vopsea de par",
        "balsam de par", "spray pentru par", "spray par ",
        "inalbitor rufe", "inalbitor ",
        "servetele captatoare", "k2r ",
        "rezerva mop", "cap mop", "mop ",
        "tinctura de",
    ],
    "Carne & Mezeluri": [
        "piept de pui", "piept pui", "pulpa pui", "pulpe pui", "pulpe de pui",
        "aripi de pui", "aripi pui", "pui intreg", "pui proaspat", "pui pane",
        "cotlet de porc", "cotlet porc", "muschi de porc", "scarita",
        "coaste porc", "fleica", "ceafa porc", "ceafa de porc", "antricot",
        "slanina", "scaricica",
        "salam ", "parizer", "cremwursti", "crenvursti", "sunca",
        "mici ", "carnati", "cabanos", "kaiser",
        "mezeluri", "bacon", "muschi file", "salata icre", "hering picant",
        "obrajori", "carcasa de", "iepure",
        "vita tocata", "carne tocata", "carne de porc", "carne de vita",
        "somon ", "file de somon", "pastrav ", "pastrav afumat",
        "prosciutto", "jambon ", "jambon copt",
        "chiftele", "tochitura",
    ],
    "Lactate & Oua": [
        "iaurt", "lapte batut", "lapte uht", "lapte de vaca", "lapte integral",
        "lapte semidegresat", "lapte ", "kefir", "sana ", "frappe",
        "smantana", "branza de vaci", "branza dulce", "branza telemea",
        "branza cremoasa", "branza cottage", "branza feta", "branza burduf",
        "branza graviera", "branza halloumi", "branza burrata",
        "branza edam", "branza olandeza", "branza cheddar", "branza maturata",
        "branza topita", "branza afumata", "branza cu mucegai",
        "cascaval", "telemea", "crema de branza",
        "unt ", "frisca", "mascarpone", "burduf", "cas de oaie", "cas dulce",
        "grana padano", "br.rasa",
        "danonino", "danone", "albalact", "napolact", "zuzu", "activia",
        "oua ", "oua de", "budinca", "urda ",
        "mozzarella", "ricotta", "gorgonzola",
        "branzeturi", "mix de branza", "formaggio",
        "ayran",
    ],
    "Panificatie & Dulciuri": [
        "paine alba", "paine neagra", "paine graham", "paine toast",
        "paine durum", "paine multicereale", "paine ", "painici",
        "minibagheta", "demibagheta", "bagheta", "chifla", "croissant",
        "gogoasa", "cozonac", "ecler", "prajitura", "tort ", "placinta",
        "pernuta", "pernita", "foietaj", "aluat", "foi de placinta", "rulada",
        "ciocolata", "biscuiti", "biscuit", "napolitane", "wafer", "eugenia",
        "milka", "oreo", "kinder", "snickers", "twix", "bounty", "kitkat",
        "roshen", "bomboane", "caramele", "praline", "drajeuri", "halva",
        "inghetata", "cereale ", "cereale mic dejun", "brezel", "cracker",
        "panettone", "baigli", "strudel",
        "lindt", "ferrero", "raffaello",
        "acadea", "dropsuri",
        "cantuccini", "amaretti",
    ],
    "Bauturi": [
        "bere ", "whiskey", "whisky", "vodca", "vodka", "brandy", "gin ",
        "rom ", "tequila", "lichior", "sampanie", "prosecco", "bautura spirtoasa",
        "vin rosu", "vin alb", "vin rose", "vin sec", "vin demisec",
        "vin dulce", "vin merlot", "vin feteasca", "vin sauvignon", "vin ",
        "suc ", "suc de", "nectar", "apa plata", "apa minerala", "apa izvorul",
        "apa carpatica", "aqua carpatica",
        "pepsi", "fanta", "sprite", "mirinda", "cola",
        "santal", "prigat", "nestea", "energizant", "monster energy", "burn ",
        "red bull", "limonada", "bautura racoritoare", "bautura energizanta",
        "bautura carbo", "bautura necarbogazoasa", "bautura carbogazoasa",
        "bautura vitaminizata",
        "tymbark", "hell ", "coca-cola", "coca cola",
        "cidru", "rachiu", "palinca", "vinars", "aperitiv ",
        "cocktail", "vermut", "schweppes", "tonic",
        "coniac", "cognac", "hennessy", "martell", "courvoisier",
        "bautura tare",
    ],
    # Bacanie ÎNAINTE de Legume — legumele conservate/murate câștigă față de cele proaspete
    "Bacanie & Alimente de baza": [
        "ulei de masline", "ulei floarea soarelui", "ulei de", "ulei ",
        "faina alba", "faina de grau", "faina graham", "faina ", "malai",
        "zahar tos", "zahar pudra", "zahar brun", "zahar cristal", "zahar ",
        "orez bob", "orez ", "paste fainoase", "paste ", "macaroane",
        "spaghete", "spaghetti", "penne ", "farfalle", "tagliatelle",
        "pasta de tomate", "sos de rosii", "bulion", "ketchup", "mustar ",
        "maioneza", "sos de", "otet", "sare ", "piper ",
        "condimente", "boia", "curry", "cub de supa", "legume baza",
        "drojdie", "praf de copt", "bicarbonat",
        "gem ", "dulceata", "miere", "sirop de agave", "sirop de artar",
        "conserva", "fasole boabe", "fasole alba", "fasole rosie",
        "fasole in sos", "fasole cu", "linte", "naut", "mazare boabe", "mazare la conserva",
        "ton ", "sardine", "macrou", "hering", "icre",
        "hrean", "capere", "supa instant", "fidea", "margarina",
        "pasta vegetala", "salata humus",
        "migdale crude", "migdale prajite", "arahide", "alune prajite",
        "seminte dovleac", "seminte floarea soarelui vrac",
        "nuci ", "nuci caju", "nuci pecan",
        "cafea boabe", "cafea macinata", "cafea solubila", "capsule cafea",
        "nescafe", "jacobs", "3 in 1", "cafea instant", "cafea ",
        "ceai de munte", "ceai rece", "ceai instant", "ceai verde", "ceai negru", "ceai ",
        "chips cartofi", "chipsuri cartofi", "chips cascaval", "chipsuri cascaval",
        "chips", "chipsuri", "stickletti", "tortilla chips", "spirale",
        "seminte floarea", "snack ", "covrigei", "covrig ", "stick sarate", "grisine",
        # legume murate/conservate — mai specific decât keyword-urile din Legume
        "castraveti in otet", "castraveti cornichon",
        "ardei capia in otet", "ardei in otet",
        "rosii decojite", "rosii in suc", "rosii la conserva",
        "vinete coapte", "vinete in otet",
        # pate si pateu — conserve, nu carne proaspata
        "pate ", "pateu",
    ],
    "Legume & Fructe": [
        "ceapa", "usturoi", "cartofi vrac", "cartofi albi", "cartofi in coaja",
        "morcovi", "patrunjel", "telina radacina",
        "ardei capia", "ardei ", "rosii vrac", "rosii ", "vinete",
        "dovlecel", "varza murata", "varza ", "salata verde", "spanac",
        "broccoli", "conopida", "fasole verde pastai", "mazare verde boabe",
        "castraveti intregi", "castraveti ",
        "ciuperci taiate", "ciuperci champignon",
        "mere ", "pere vrac", "banane", "portocale", "mandarine", "lamai",
        "grapefruit", "kiwi", "mango", "avocado", "ananas rondele",
        "capsuni", "zmeura ", "afine", "visine", "cirese",
        "piersici", "caise", "prune", "struguri", "pepene", "pepeni",
        "masline ", "dovleac placintar", "sparanghel",
        "stafide",
    ],
    "Casa & Diverse": [
        "jucarie", "figurine", "excavator", "sosete", "ciorapi",
        "pungi alimentare", "folie aluminiu", "hartie copt",
        "hrana caini", "hrana pisici", "hrana animale", "hrana uscata", "hrana umeda",
        "pentru pisici", "pentru caini", "nisip pisici",
        "lumanare", "baterie ", "bec ", "prelungitor",
        "trotineta", "bicicleta copii", "leagan", "tobogan",
        "troler", "valiza", "lego ", "puzzle",
        "cantar de", "cantar electronic", "cantar bucatarie",
        "robot de bucatarie", "robot bucatarie",
        "creioane colorate", "creioane cerate",
        "buchet de flori", "buchet flori",
        "cartuse filtrante", "filtrante",
        "perna scaun", "husa scaun", "scaun ",
        "mixer vertical", "mixer de", "blender ",
        "tava ", "tava detasabila", "tava copt",
        "ibric ", "ceainic ", "cana ", "caserola ",
        "platou ", "bol ", "farfurie ",
        "papusa ", "papusi", "joc de masa", "joc de societate",
        "marker ", "stilou ", "pix ",
        "pungi ", "saci menajeri", "saci gunoi",
        "parfum de camera", "odorizant camera",
        "proiector led", "bec led", "spot led",
        "hartie pentru copt", "folie pentru copt",
        "ciocan snitel", "ciocan de bucatarie",
        "panza ", "laveta ", "lavet",
    ],
}

KNOWN_MULTI_WORD_BRANDS: list[tuple[str, str]] = [
    ("marca neidentificabila", "Generic"), ("marca necunoscuta", "Generic"),
    ("pentru tine de la penny", "Penny"),
    ("margaritar zahar cristal alb", "Margaritar"),
    ("hugo dog food", "Hugo"), ("nutline intersnack", "Nutline"),
    ("theoni olive oils", "Theoni"), ("eugenia dobrogea", "Eugenia"),
    ("monster energy", "Monster Energy"), ("aqua carpatica", "Aqua Carpatica"),
    ("perla harghitei", "Perla Harghitei"), ("cassa profi", "Cassa"),
    ("alex dr. oetker", "Dr. Oetker"), ("alex dr oetker", "Dr. Oetker"),
    ("chengyu toys", "Chengyu Toys"), ("gradina bunicii", "Gradina Bunicii"),
    ("ferma din deal", "Ferma din Deal"), ("ferma noua", "Ferma Noua"),
    ("hanul boieresc", "Hanul Boieresc"), ("casa antonie", "Casa Antonie"),
    ("gran mare", "Gran Mare"), ("boni de tot", "Boni De Tot"),
    ("san fabio", "San Fabio"), ("rio mare", "Rio Mare"),
    ("gerovital h3", "Gerovital H3"), ("laptaria amu", "Laptaria Amu"),
    ("brutaria veche", "Brutaria Veche"), ("masa boiereasca", "Masa Boiereasca"),
    ("diamant zahar", "Diamant Zahar"), ("muller milch", "Muller Milch"),
    ("de albalact", "De Albalact"), ("home garden", "Home Garden"),
    ("home kitchen", "Home Kitchen"), ("milka total", "Milka"),
    ("lay's total", "Lay's"), ("ciuc premium", "Ciuc"),
    ("neumarkt bere", "Neumarkt"), ("ciao tymbark", "Ciao"),
    ("riso scotti", "Riso Scotti"), ("premia elit", "Premia Elit"),
    ("casa buna", "Casa Buna"), ("la minut", "La minut"),
    ("el capitan", "El Capitan"), ("mr. proper", "Mr. Proper"),
    ("mr proper", "Mr. Proper"), ("fry me", "Fry Me"), ("7 days", "7 Days"),
    ("cris-tim", "Cris-Tim"), ("majorette", "Majorette"),
    ("scandia sibiu", "Scandia Sibiu"), ("matache macelaru", "Matache Macelaru"),
    ("birra moretti", "Birra Moretti"), ("la dorna", "La Dorna"),
    ("wg sampon", "WG"), ("5 to go", "5 To Go"), ("dr. oetker", "Dr. Oetker"),
    ("la provincia", "La Provincia"), ("puiul fermierului", "Puiul Fermierului"),
    ("deliciosul de vaslui", "Deliciosul de Vaslui"),
]

BRAND_OVERRIDES: list[tuple[str, str]] = [
    ("caroli ", "Caroli"),
]

NON_BRAND_PREFIXES = [
    "marca neidentificabila", "marca necunoscuta", "marca ", "fără", "fara",
]

NOISE_SUFFIXES = re.compile(
    r"\b(vrac|ambalat[ae]?|proaspet[ae]?|congelat[ae]?|feliat[ae]?|"
    r"dezosat[ae]?|fara piele|pane|diverse sortimente?|div sort)\b",
    re.IGNORECASE,
)
GRAMAJ_RE = re.compile(
    r"\s*\b\d+\s*(g|kg|ml|l|gr|buc|x\s*\d+|straturi|sp|spalari|"
    r"%\s*(grasime|alc\.?|vol\.?)?)\b\s*"
    r"|\s*\+\/\-?\s*",  # strip +/- (variable weight marker)
    re.IGNORECASE,
)

SINGLE_WORD_OK = {
    "bere", "vodca", "cafea", "mazare", "ketchup", "otet",
    "margarina", "malai", "miere", "sana", "kiwi","portocale"
}


_FEW_SHOT = """Exemple:
INPUT: "Piept de pui dezosat fara piele Ferma Noua, +/- 1kg"
OUTPUT: {"nume_curat": "Piept de pui dezosat fara piele Ferma Noua 1 kg", "brand": "Ferma Noua", "categorie": "Carne & Mezeluri"}

INPUT: "Lapte UHT integral ZuZu, 3.5% grasime, 1L"
OUTPUT: {"nume_curat": "Lapte ZuZu UHT ", "brand": "ZuZu", "categorie": "Lactate & Oua"}

INPUT: "Cafea macinata Jacobs Kronung, 500g"
OUTPUT: {"nume_curat": "Cafea macinata Kronung 500g", "brand": "Jacobs", "categorie": "Bacanie & Alimente de baza"}

INPUT: "Vin rosu sec Beciul Domnesc Cabernet Sauvignon, 0.75L"
OUTPUT: {"nume_curat": "Vin rosu sec Cabernet Sauvignon", "brand": "Beciul Domnesc", "categorie": "Bauturi"}

INPUT: "Detergent automat Ariel Pods Color, 30 capsule"
OUTPUT: {"nume_curat": "Detergent automat Airel Pods Color 30 capsule", "brand": "Ariel", "categorie": "Ingrijire & Curatenie"}

INPUT: "Branza cheddar felii Auchan, 150g"
OUTPUT: {"nume_curat": "Branza cheddar felii 150g", "brand": "Auchan", "categorie": "Lactate & Oua"}

INPUT: "Ton bucati in ulei Rio Mare, 160g"
OUTPUT: {"nume_curat": "Ton bucati in ulei Rio Mare 160g", "brand": "Rio Mare", "categorie": "Bacanie & Alimente de baza"}

INPUT: "Mere Golden, +/- 1kg"
OUTPUT: {"nume_curat": "Mere Golden", "brand": "Generic", "categorie": "Legume & Fructe"}
"""

_CATEGORY_GUIDE = """Ghid categorii (alege EXACT una):
- Carne & Mezeluri: carne proaspata (pui, porc, vita, miel), mezeluri (salam, sunca, carnati), peste proaspat/congelat
- Lactate & Oua: lapte, iaurt, branza (orice tip), smantana, unt, oua, kefir, crema, 
- Legume & Fructe: legume si fructe proaspete, congelate sau uscate (mere, cartofi, rosii, stafide)
- Bacanie & Alimente de baza: conserve (ton, macrou, sardine, fasole, mazare, rosii decojite, castraveti in otet), paste, orez, faina, ulei, sos, gem, miere, nuci prajite, snacks sarate, migdale crude, cafea (boabe/macinata/capsule/solubila), ceai, pate, pasta vegetala
- Bauturi: apa, sucuri, bere, vin, spirtoase, bauturi energizante (NU ceai)
- Panificatie & Dulciuri: paine, croissant, cozonac, prajituri, ciocolata, biscuiti, inghetata, cereale mic dejun
- Ingrijire & Curatenie: detergenti, sapunuri, sampoane, cosmetice, hartie igienica, scutece, gel de dus, sapun, absorbante
- Casa & Diverse: jucarii, electrocasnice, hrana animale, articole menaj, imbracaminte
"""


_RAW_PREFIXES_TO_STRIP = re.compile(
    r"^(pentru\s+tine\s+de\s+la\s+penny|marca\s+neidentificabil[ae]|marca\s+neidentificata)\s*",
    re.IGNORECASE,
)


def ai_refine_batch(batch: list[dict]) -> list[dict]:
    results = []
    for item in batch:
        raw = item.get("raw_name", "").strip()
        # Strip retail noise prefixes before sending to AI
        raw_clean = _RAW_PREFIXES_TO_STRIP.sub("", raw).strip()
        # Strip +/- (variable weight marker)
        raw_clean = re.sub(r"\s*\+/-?\s*", " ", raw_clean).strip()
        prompt = (
            f"Esti un expert in retail romanesc. Analizeaza numele de produs si returneaza DOAR JSON.\n\n"
            f"{_CATEGORY_GUIDE}\n"
            f"{_FEW_SHOT}\n"
            f"REGULI STRICTE:\n"
            f"- nume_curat: numele produsului cu brand, cu gramaj (g/kg/ml/L), fara +/-\n"
            f"- brand: primul nume propriu din input (ex: Milka, Jacobs, Ferma Noua). De obicei e in partea din mijloc sau spre final, si e scris cu litere mari. Daca nu exista brand clar, pune \"Generic\". De exemplu Detergent automat Ariel 5, Ariel este brandul. \n"
            f"- categorie: EXACT una din cele 8 categorii de mai sus, fara modificari. De obicei primele 1-2 cuvinte indica categoria. \n"
            f"- Raspunde DOAR cu JSON, fara text suplimentar\n\n"
            f"INPUT: \"{raw_clean}\"\n"
            f"OUTPUT:"
        )
        try:
            response = ollama.generate(
                model=AI_MODEL,
                prompt=prompt,
                format="json",
                options={"temperature": 0.0, "num_predict": 200},
            )
            parsed = json.loads(response["response"])
            # Normalize key names (model may vary capitalization)
            normalized = {k.lower(): v for k, v in parsed.items()}
            results.append({
                "nume_curat": normalized.get("nume_curat") or normalized.get("name") or "",
                "brand":      normalized.get("brand") or "Generic",
                "categorie":  normalized.get("categorie") or normalized.get("category") or FALLBACK_CATEGORY,
            })
        except Exception as e:
            log.warning("Eroare Llama [%s]: %s", raw[:40], e)
            results.append({})
    return results


def resolve_category(source: str) -> str | None:
    if not source:
        return None
    s = source.lower() + " "  # trailing space so keywords match end-of-string too
    for cat, keywords in KEYWORD_CATEGORIES.items():
        if any(kw in s for kw in keywords):
            return cat
    return None


def resolve_category_from_brand(brand: str, current_cat: str) -> str | None:
    if current_cat not in OVERRIDABLE_CATEGORIES:
        return None
    return BRAND_TO_CATEGORY.get(brand)


def remap_external_category(category: str) -> str | None:
    if category in VALID_CATEGORIES:
        return None
    return EXTERNAL_CATEGORY_MAP.get(category.lower().strip())


def extract_brand(source: str) -> str:
    s_lower = source.lower().strip()
    for prefix_lower, brand_correct in KNOWN_MULTI_WORD_BRANDS:
        if s_lower.startswith(prefix_lower):
            return brand_correct
    for prefix_lower, brand_correct in BRAND_OVERRIDES:
        if s_lower.startswith(prefix_lower):
            return brand_correct
    for prefix in NON_BRAND_PREFIXES:
        if s_lower.startswith(prefix):
            return "Generic"
    words = source.split()
    if words:
        first = words[0].rstrip(".,;:()")
        if first.islower() and len(first) < 4:
            return "Generic"
        return first
    return "Generic"


def extract_name(source: str, brand: str) -> str:
    s = source.strip()
    brand_lower = brand.lower()
    if brand_lower != "generic" and s.lower().startswith(brand_lower):
        s = s[len(brand):].strip(" -,")
    else:
        for prefix_lower, _ in KNOWN_MULTI_WORD_BRANDS:
            if s.lower().startswith(prefix_lower):
                s = s[len(prefix_lower):].strip(" -,")
                break
    s = GRAMAJ_RE.sub(" ", s).strip()
    s = NOISE_SUFFIXES.sub(" ", s).strip(" -,.")
    s = re.sub(r"\s{2,}", " ", s)
    return s if s else source


_STOP = {"de", "si", "și", "cu", "la", "pe", "a", "o", "al", "ale", "pentru",
         "din", "fara", "fără", "sau", "ori", "ca", "dar", "ci", "nici"}


def _significant_words(text: str) -> list[str]:
    return [w for w in re.findall(r"\w+", text.lower())
            if w not in _STOP and len(w) > 2]


def is_name_corrupt(name: str, source: str) -> bool:
    if not name:
        return True
    stripped = name.strip()
    if re.match(r"^[\d\+\-\.,%/\\]+$", stripped):  # only digits/symbols
        return True
    if stripped.lower() == source.strip().lower():
        return True
    words = stripped.split()
    if len(words) == 1 and len(stripped) <= 8 and stripped.lower() not in SINGLE_WORD_OK:
        return True
    if stripped and stripped[0].islower():
        return True
    if stripped.lower() in ("fără", "fara", "fără", "-", "n/a"):
        return True
    return False


def name_overlaps_raw(name: str, raw_name: str) -> bool:
    """Return True if AI-extracted name has sufficient word overlap with raw_name."""
    if not raw_name:
        return True
    name_words = _significant_words(name)
    raw_words   = set(_significant_words(raw_name))
    if not name_words:
        return False
    matched = sum(1 for w in name_words if w in raw_words)
    return (matched / len(name_words)) >= _MIN_NAME_OVERLAP


def capitalize_name(name: str) -> str:
    if not name:
        return name
    return name[0].upper() + name[1:]


def fix_brand_casing(brand: str) -> str:
    if brand in ("Generic", "N/A", ""):
        return brand
    if brand.islower() or brand.isupper():
        return brand.title()
    return brand


def fix_item(item: dict) -> dict:
    raw_name  = item.get("raw_name", "")
    cur_name  = item.get("name", "")
    store     = item.get("store", "")
    cur_brand = item.get("brand", "")

    raw_reliable = store not in RAW_NAME_UNRELIABLE_STORES
    truth_source = raw_name if (raw_reliable and raw_name) else cur_name

    if not truth_source and not raw_name:
        return item

    fixed = dict(item)
    cur_cat = fixed.get("category", "")

    # Always try raw_name first for category keywords — it preserves the product
    # type ("Vin rosu sec", "Bere blonda") even when cur_name lost that prefix.
    correct_cat = resolve_category(raw_name)
    if not correct_cat:
        correct_cat = resolve_category(truth_source)
    if not correct_cat and cur_name and cur_name != truth_source:
        correct_cat = resolve_category(cur_name)
    if not correct_cat:
        correct_cat = resolve_category_from_brand(cur_brand, cur_cat)
    if not correct_cat:
        correct_cat = remap_external_category(cur_cat)
    if correct_cat and correct_cat != cur_cat:
        fixed["category"] = correct_cat
    elif not correct_cat and cur_cat not in VALID_CATEGORIES:
        fixed["category"] = FALLBACK_CATEGORY

    # Corecții de context: keyword-urile Carne prind și preparate conservate
    raw_low = raw_name.lower()
    if fixed.get("category") == "Carne & Mezeluri":
        # Fasole cu carnati = conserva → Bacanie
        if raw_low.startswith("fasole cu") or raw_low.startswith("fasole in"):
            fixed["category"] = "Bacanie & Alimente de baza"
    # Snack-uri cu gust de cascaval nu sunt Lactate
    if fixed.get("category") == "Lactate & Oua":
        if any(kw in raw_low for kw in ["chips", "sticks cu", "chio ", "lay", "popcorn"]):
            fixed["category"] = "Bacanie & Alimente de baza"

    correct_brand = extract_brand(truth_source)
    current_brand = fixed.get("brand") or "Generic"
    should_fix = (
        current_brand[0].islower()
        or (
            correct_brand != "Generic"
            and current_brand.lower() != correct_brand.lower()
            and not current_brand.lower().startswith(correct_brand.lower()[:4])
        )
    )
    fixed["brand"] = correct_brand if should_fix else fix_brand_casing(current_brand)

    # Treat AI name as corrupt if it has low word-overlap with raw_name
    # (cross-contamination from adjacent products in the same batch).
    name_corrupt = is_name_corrupt(cur_name, truth_source) or (
        raw_name and not name_overlaps_raw(cur_name, raw_name)
    )
    if name_corrupt:
        # For unreliable stores cur_name is truth_source but may be garbled;
        # always try raw_name as a second-chance source when it looks richer.
        recover_source = truth_source
        if raw_name and (len(raw_name) > len(truth_source) + 3 or name_corrupt):
            recover_source = raw_name
        fixed["name"] = capitalize_name(extract_name(recover_source, fixed["brand"]))
    else:
        brand_lower = fixed["brand"].lower()
        if brand_lower != "generic" and cur_name.lower().startswith(brand_lower):
            stripped = cur_name[len(fixed["brand"]):].strip(" -,")
            if stripped:
                fixed["name"] = capitalize_name(stripped)
        else:
            fixed["name"] = capitalize_name(cur_name)

    # Prepend brand to name for reliable stores only — Auchan/Penny have poor
    # brand extraction so we avoid polluting names with wrong first-word guesses.
    final_brand = fixed.get("brand", "Generic")
    final_name  = fixed.get("name", "")
    if (
        raw_reliable
        and final_brand and final_brand != "Generic"
        and final_name
        and final_brand.lower() not in final_name.lower()
    ):
        fixed["name"] = f"{final_brand} {final_name}"

    return fixed


def process_file(path: Path) -> None:
    with open(path, "r", encoding="utf-8") as f:
        raw_data: list[dict] = json.load(f)

    log.info("Procesare %s (%d produse)...", path.name, len(raw_data))

    interim: list[dict] = []
    for i in range(0, len(raw_data), AI_BATCH_SIZE):
        batch = raw_data[i : i + AI_BATCH_SIZE]
        ai_results = ai_refine_batch(batch)
        for j, raw_item in enumerate(batch):
            ai = ai_results[j] if j < len(ai_results) else {}
            interim.append({
                "store":         raw_item.get("store", ""),
                "raw_name":      raw_item.get("raw_name", ""),
                "name":          ai.get("nume_curat") or raw_item.get("raw_name", ""),
                "brand":         ai.get("brand") or "Generic",
                "category":      ai.get("categorie") or FALLBACK_CATEGORY,
                "price_new":     raw_item.get("price_new"),
                "price_old":     raw_item.get("price_old"),
                "discount":      raw_item.get("discount"),
                "image_url":     raw_item.get("image_url"),
                "image_local":   raw_item.get("local_image_path") or raw_item.get("image_local"),
                "requires_card": raw_item.get("requires_card", False),
            })
        print(f"  AI: {min(i + AI_BATCH_SIZE, len(raw_data))}/{len(raw_data)}", end="\r")

    print()
    fixed_data = [fix_item(item) for item in interim]

    cat_fixes   = sum(1 for a, b in zip(interim, fixed_data) if a.get("category") != b.get("category"))
    brand_fixes = sum(1 for a, b in zip(interim, fixed_data) if a.get("brand")    != b.get("brand"))
    name_fixes  = sum(1 for a, b in zip(interim, fixed_data) if a.get("name")     != b.get("name"))

    store_slug = path.name.replace("data_", "")
    out_path = OUTPUT_DIR / f"refined_data_{store_slug}"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fixed_data, f, indent=4, ensure_ascii=False)

    log.info("%s → cat:%d brand:%d name:%d | salvat → %s",
             path.name, cat_fixes, brand_fixes, name_fixes, out_path)


if __name__ == "__main__":
    files = list(INPUT_DIR.glob("data_*.json"))
    if not files:
        log.warning("Niciun fisier data_*.json gasit in %s", INPUT_DIR)
    for f in sorted(files):
        process_file(f)