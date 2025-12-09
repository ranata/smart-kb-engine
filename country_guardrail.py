import spacy
import pycountry
import csv
from rapidfuzz import process, fuzz

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


# ============================================================
# ✅ LOAD BEST AVAILABLE SPACY MODEL
# ============================================================

def load_best_spacy_model():
    for model in ["en_core_web_lg", "en_core_web_sm_abd", "en_core_web_sm"]:
        try:
            return spacy.load(model)
        except Exception:
            continue
    raise RuntimeError("No usable spaCy model found.")

nlp = load_best_spacy_model()


# ============================================================
# ✅ LOAD DEMONYMS FROM CSV (COMPLIANCE-SAFE)
# File format:
# country,demonym
# United States,American
# Singapore,Singaporean
# ============================================================

def load_demonym_map_from_csv(path="country_demonyms.csv"):
    demonym_map = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            demonym = row["demonym"].strip().lower()
            country = row["country"].strip()
            demonym_map[demonym] = country
    return demonym_map


# ============================================================
# ✅ BUILD MASTER COUNTRY TOKEN TABLE
# (ISO names + ISO codes + Demonyms)
# ============================================================

def build_country_master_table():
    token_to_country = {}
    all_tokens = set()

    DEMONYM_MAP = load_demonym_map_from_csv("country_demonyms.csv")

    for c in pycountry.countries:
        canonical = c.name

        # --- Country Names ---
        names = {c.name}
        if hasattr(c, "official_name"):
            names.add(c.official_name)
        if hasattr(c, "common_name"):
            names.add(c.common_name)

        # --- ISO Codes ---
        codes = set()
        if hasattr(c, "alpha_2"):
            codes.add(c.alpha_2)
        if hasattr(c, "alpha_3"):
            codes.add(c.alpha_3)

        for item in list(names) + list(codes):
            key = item.lower().strip()
            token_to_country[key] = canonical
            all_tokens.add(key)

    # ✅ Add demonyms from CSV
    for dem, country in DEMONYM_MAP.items():
        token_to_country[dem] = country
        all_tokens.add(dem)

    return token_to_country, all_tokens


COUNTRY_TOKEN_MAP, COUNTRY_ALL_TOKENS = build_country_master_table()


# ============================================================
# ✅ COUNTRY RESOLVER (NAMES + CODES + DEMONYMS + FUZZY)
# ============================================================

def resolve_country_token(token: str, fuzzy_threshold=88):
    t = token.lower().strip()

    # 1️⃣ Exact match
    if t in COUNTRY_TOKEN_MAP:
        return COUNTRY_TOKEN_MAP[t]

    # 2️⃣ Fuzzy match for typos
    match = process.extractOne(
        t,
        COUNTRY_ALL_TOKENS,
        scorer=fuzz.ratio
    )

    if match and match[1] >= fuzzy_threshold:
        return COUNTRY_TOKEN_MAP[match[0]]

    return None


# ============================================================
# ✅ PRESIDIO INITIALIZATION
# ============================================================

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()


# ============================================================
# ✅ ADDRESS HEURISTIC (TO DECIDE WHEN TO MASK)
# ============================================================

ADDRESS_HINTS = {
    "road", "rd", "street", "st", "avenue", "ave", "blvd", "lane",
    "floor", "flat", "apt", "apartment", "suite", "unit",
    "tower", "block", "#"
}

def looks_like_address(text: str) -> bool:
    text_l = text.lower()

    # Any digits usually indicate address
    if any(ch.isdigit() for ch in text_l):
        return True

    # Address keywords
    for hint in ADDRESS_HINTS:
        if hint in text_l:
            return True

    return False


# ============================================================
# ✅ FINAL COUNTRY GUARDRAIL FUNCTION
# ============================================================

def country_guardrail(text: str):
    """
    Rules:
    - If address-like content exists → return <loc>CanonicalCountry
    - If only a country/demonym/code exists → return original text as-is
    """

    doc = nlp(text)
    found_countries = []

    # ---- 1️⃣ Collect countries from NER ----
    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC", "NORP"):
            resolved = resolve_country_token(ent.text)
            if resolved and resolved not in found_countries:
                found_countries.append(resolved)

    # ---- 2️⃣ Token-level fallback (SG, SGP, UAE, etc.) ----
    for token in doc:
        resolved = resolve_country_token(token.text)
        if resolved and resolved not in found_countries:
            found_countries.append(resolved)

    # ---- 3️⃣ If no country → return text unchanged ----
    if not found_countries:
        return text

    # ---- 4️⃣ Decide if this is an address ----
    is_address = looks_like_address(text)

    # ✅ CASE A: Address present → mask everything & expose canonical country
    if is_address:
        country = found_countries[0]  # Primary jurisdiction

        results = analyzer.analyze(text=text, language="en")

        operators = {
            "DEFAULT": OperatorConfig("replace", {"new_value": ""}),
            "LOCATION": OperatorConfig("replace", {"new_value": ""}),
            "GPE": OperatorConfig("replace", {"new_value": ""}),
            "NORP": OperatorConfig("replace", {"new_value": ""}),
        }

        _ = anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators
        ).text

        return f"<loc>{country}"

    # ✅ CASE B: Only country mention → return as-is (no masking, no normalization)
    else:
        return text


# ============================================================
# ✅ ✅ ✅ TEST CASES
# ============================================================

if __name__ == "__main__":
    tests = [
        "690 W Camp Rd, #09-04 JTC Aviation Two, SG 797523",
        "221B Baker Street, London, UK",
        "Whitefield, Bangalore, India 560066",
        "Singapore",
        "UAE",
        "American",
        "User is from Singapore",
        "Client lives in Dubai UAE 45021",
        "Lives in Singpore"
    ]

    for t in tests:
        print(t)
        print("→", country_guardrail(t))
        print()
