import spacy
import pycountry
from demonyms import demonym
from rapidfuzz import process, fuzz

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


# ============================================================
# ✅ LOAD BEST AVAILABLE SPACY MODEL (LG PREFERRED)
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
# ✅ BUILD MASTER COUNTRY TOKEN TABLE (PROGRAMMATIC)
# ============================================================

def build_country_master_table():
    """
    Builds:
      - token_to_country: every alias -> canonical country name
      - all_tokens: flat searchable token list
    """
    token_to_country = {}
    all_tokens = set()

    for c in pycountry.countries:
        canonical = c.name

        # --- Names ---
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

        # --- Demonyms ---
        demonyms_list = []
        if hasattr(c, "alpha_2"):
            demonyms_list = demonym.get(c.alpha_2, [])

        # --- Consolidate ---
        for item in list(names) + list(codes) + demonyms_list:
            key = item.lower().strip()
            token_to_country[key] = canonical
            all_tokens.add(key)

    return token_to_country, all_tokens


COUNTRY_TOKEN_MAP, COUNTRY_ALL_TOKENS = build_country_master_table()


# ============================================================
# ✅ COUNTRY RESOLVER (CODES + DEMONYMS + FUZZY)
# ============================================================

def resolve_country_token(token: str, fuzzy_threshold=88):
    """
    Resolves:
      SG, SGP, Singapore, Singaporian, Singpore → Singapore
    """
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
# ✅ COUNTRY GUARDRAIL OPERATOR
#     - Detects location via NER
#     - Normalizes to canonical country
#     - Masks everything else
#     - Exposes ONLY <loc>{COUNTRY}
# ============================================================

def country_guardrail(text: str):
    """
    Input:
        690 W Camp Rd, #09-04 JTC Aviation Two, SG 797523
    Output:
        <loc>Singapore
    """

    # -------- 1️⃣ Resolve Country First --------
    doc = nlp(text)
    resolved_country = None

    # Prefer NER-based resolution
    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC", "NORP"):
            resolved_country = resolve_country_token(ent.text)
            if resolved_country:
                break

    # Fallback: token scan for SG / SGP cases
    if not resolved_country:
        for token in doc:
            resolved_country = resolve_country_token(token.text)
            if resolved_country:
                break

    # -------- 2️⃣ Presidio: Mask Location Entities --------
    results = analyzer.analyze(text=text, language="en")

    operators = {
        # Mask everything by default
        "DEFAULT": OperatorConfig("replace", {"new_value": ""}),

        # Mask only location-related entities
        "LOCATION": OperatorConfig("replace", {"new_value": ""}),
        "GPE": OperatorConfig("replace", {"new_value": ""}),
        "NORP": OperatorConfig("replace", {"new_value": ""}),
    }

    _ = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=operators
    ).text

    # -------- 3️⃣ Deterministic Final Output --------
    if resolved_country:
        return f"<loc>{resolved_country}"
    else:
        return "<loc>UNKNOWN"


# ============================================================
# ✅ ✅ ✅ FULL TEST SUITE
# ============================================================

if __name__ == "__main__":
    tests = [
        "690 W Camp Rd, #09-04 JTC Aviation Two, SG 797523",
        "221B Baker Street, London, UK",
        "Whitefield, Bangalore, India 560066",
        "Client is Singaporian",
        "User belongs to SGP",
        "Lives in Singpore",
        "American working in UAE",
        "User moved from Paris to Germany"
    ]

    for t in tests:
        print(t)
        print("→", country_guardrail(t))
        print()

