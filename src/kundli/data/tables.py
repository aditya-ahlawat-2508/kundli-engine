"""Classical constants. Every table is cited in docs/sources.md; uncertain values carry `# VERIFY`
and are listed in docs/open_questions.md. Nothing here is computed."""

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORDS = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars",
              "Jupiter", "Saturn", "Saturn", "Jupiter"]
PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
SEVEN = PLANETS[:7]
WEEKDAY_LORDS = SEVEN  # Sunday..Saturday: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn
CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]  # hora order

# BPHS ch.3: exaltation sign index + degree. Debilitation = opposite sign, same degree.
EXALTATION = {"Sun": (0, 10.0), "Moon": (1, 3.0), "Mars": (9, 28.0), "Mercury": (5, 15.0),
              "Jupiter": (3, 5.0), "Venus": (11, 27.0), "Saturn": (6, 20.0),
              "Rahu": (1, 20.0), "Ketu": (7, 20.0)}  # VERIFY nodes (schools differ: Taurus/Gemini)
# BPHS ch.3: moolatrikona (sign, from_deg, to_deg)
MOOLATRIKONA = {"Sun": (4, 0, 20), "Moon": (1, 3, 30), "Mars": (0, 0, 12), "Mercury": (5, 15, 20),
                "Jupiter": (8, 0, 10), "Venus": (6, 0, 15), "Saturn": (10, 0, 20)}  # VERIFY Moon 3-30 vs 4-30
OWN_SIGNS = {"Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5], "Jupiter": [8, 11],
             "Venus": [1, 6], "Saturn": [9, 10], "Rahu": [], "Ketu": []}

# BPHS ch.3 natural friendship (naisargika maitri)
FRIENDS = {
    "Sun": ["Moon", "Mars", "Jupiter"], "Moon": ["Sun", "Mercury"],
    "Mars": ["Sun", "Moon", "Jupiter"], "Mercury": ["Sun", "Venus"],
    "Jupiter": ["Sun", "Moon", "Mars"], "Venus": ["Mercury", "Saturn"],
    "Saturn": ["Mercury", "Venus"], "Rahu": ["Mercury", "Venus", "Saturn"],  # VERIFY nodes
    "Ketu": ["Mars", "Venus", "Saturn"],  # VERIFY
}
ENEMIES = {
    "Sun": ["Venus", "Saturn"], "Moon": [], "Mars": ["Mercury"], "Mercury": ["Moon"],
    "Jupiter": ["Mercury", "Venus"], "Venus": ["Sun", "Moon"], "Saturn": ["Sun", "Moon", "Mars"],
    "Rahu": ["Sun", "Moon", "Mars"], "Ketu": ["Sun", "Moon"],  # VERIFY nodes
}

# Vimshottari
VIM_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
VIM_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16,
             "Saturn": 19, "Mercury": 17}
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya",
              "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
              "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
              "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
NAK_SPAN = 360.0 / 27
ABHIJIT = (276 + 40 / 60, 280 + 53 / 60 + 20 / 3600)  # last 4'13.33" of Uttara Ashadha + first 1/15 Shravana

# Yogini dasha: (name, lord, years). Start index = (nakshatra_no(1..27) + 3) mod 8 (BPHS / Yogini dasha texts)
YOGINI = [("Mangala", "Moon", 1), ("Pingala", "Sun", 2), ("Dhanya", "Jupiter", 3), ("Bhramari", "Mars", 4),
          ("Bhadrika", "Mercury", 5), ("Ulka", "Saturn", 6), ("Siddha", "Venus", 7), ("Sankata", "Rahu", 8)]

# Combustion orbs (degrees from Sun). docs/conventions.md. VERIFY (schools differ)
COMBUST_ORBS = {"Moon": 12.0, "Mars": 17.0, "Mercury": 14.0, "Jupiter": 11.0, "Venus": 10.0, "Saturn": 15.0}
COMBUST_ORBS_RETRO = {"Mercury": 12.0, "Venus": 8.0}

# Panchang
TITHI_NAMES = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami", "Ashtami",
               "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi"]
YOGA_NAMES = ["Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda", "Sukarma", "Dhriti",
              "Shula", "Ganda", "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata",
              "Variyana", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra",
              "Vaidhriti"]
KARANA_MOVABLE = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]
KARANA_FIXED = {0: "Kimstughna", 57: "Shakuni", 58: "Chatushpada", 59: "Naga"}
CHOGHADIYA_CYCLE = ["Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog"]
CHOGHADIYA_START = [0, 3, 6, 2, 5, 1, 4]  # index into cycle for Sun..Sat day start VERIFY
CHOGHADIYA_QUALITY = {"Udveg": "bad", "Chal": "neutral", "Labh": "good", "Amrit": "good",
                      "Kaal": "bad", "Shubh": "good", "Rog": "bad"}

# Indu lagna kalas
INDU_KALAS = {"Sun": 30, "Moon": 16, "Mars": 6, "Mercury": 8, "Jupiter": 10, "Venus": 12, "Saturn": 1}

# Shadbala (BPHS ch.27)
NAISARGIKA = {"Sun": 60.0, "Moon": 51.43, "Venus": 42.85, "Jupiter": 34.28, "Mercury": 25.71,
              "Mars": 17.14, "Saturn": 8.57}
SHADBALA_REQUIRED = {"Sun": 390, "Moon": 360, "Mars": 300, "Mercury": 420, "Jupiter": 390, "Venus": 330,
                     "Saturn": 300}  # virupas
SAPTAVARGA = ["D1", "D2", "D3", "D7", "D9", "D12", "D30"]
SAPTAVARGAJA_POINTS = {"moolatrikona": 45.0, "own": 30.0, "great_friend": 22.5, "friend": 15.0,
                       "neutral": 7.5, "enemy": 3.75, "great_enemy": 1.875}
# Dig bala: house in which the planet is strongest
DIG_STRONG_HOUSE = {"Jupiter": 1, "Mercury": 1, "Sun": 10, "Mars": 10, "Saturn": 7, "Moon": 4, "Venus": 4}
# Vimshopaka (shodashavarga weights, total 20) and dignity scores (of 20)
SHODASHAVARGA_WEIGHTS = {"D1": 3.5, "D2": 1.0, "D3": 1.0, "D4": 0.5, "D7": 0.5, "D9": 3.0, "D10": 0.5,
                         "D12": 0.5, "D16": 2.0, "D20": 0.5, "D24": 0.5, "D27": 0.5, "D30": 1.0,
                         "D40": 0.5, "D45": 0.5, "D60": 4.0}
VIMSHOPAKA_SCORE = {"own": 20.0, "moolatrikona": 20.0, "exalted": 20.0, "great_friend": 18.0, "friend": 15.0,
                    "neutral": 10.0, "enemy": 7.0, "debilitated": 5.0, "great_enemy": 5.0}

# Ashtakavarga (BPHS ch.66-72): benefic houses counted from each contributor. Row totals checked in tests.
BAV_CONTRIB = {
    "Sun": {"Sun": [1, 2, 4, 7, 8, 9, 10, 11], "Moon": [3, 6, 10, 11], "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
            "Mercury": [3, 5, 6, 9, 10, 11, 12], "Jupiter": [5, 6, 9, 11], "Venus": [6, 7, 12],
            "Saturn": [1, 2, 4, 7, 8, 9, 10, 11], "Lagna": [3, 4, 6, 10, 11, 12]},
    "Moon": {"Sun": [3, 6, 7, 8, 10, 11], "Moon": [1, 3, 6, 7, 10, 11], "Mars": [2, 3, 5, 6, 9, 10, 11],
             "Mercury": [1, 3, 4, 5, 7, 8, 10, 11], "Jupiter": [1, 4, 7, 8, 10, 11, 12],
             "Venus": [3, 4, 5, 7, 9, 10, 11], "Saturn": [3, 5, 6, 11], "Lagna": [3, 6, 10, 11]},
    "Mars": {"Sun": [3, 5, 6, 10, 11], "Moon": [3, 6, 11], "Mars": [1, 2, 4, 7, 8, 10, 11],
             "Mercury": [3, 5, 6, 11], "Jupiter": [6, 10, 11, 12], "Venus": [6, 8, 11, 12],
             "Saturn": [1, 4, 7, 8, 9, 10, 11], "Lagna": [1, 3, 6, 10, 11]},
    "Mercury": {"Sun": [5, 6, 9, 11, 12], "Moon": [2, 4, 6, 8, 10, 11], "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
                "Mercury": [1, 3, 5, 6, 9, 10, 11, 12], "Jupiter": [6, 8, 11, 12],
                "Venus": [1, 2, 3, 4, 5, 8, 9, 11], "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
                "Lagna": [1, 2, 4, 6, 8, 10, 11]},
    "Jupiter": {"Sun": [1, 2, 3, 4, 7, 8, 9, 10, 11], "Moon": [2, 5, 7, 9, 11],
                "Mars": [1, 2, 4, 7, 8, 10, 11], "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
                "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11], "Venus": [2, 5, 6, 9, 10, 11],
                "Saturn": [3, 5, 6, 12], "Lagna": [1, 2, 4, 5, 6, 7, 9, 10, 11]},
    "Venus": {"Sun": [8, 11, 12], "Moon": [1, 2, 3, 4, 5, 8, 9, 11, 12], "Mars": [3, 5, 6, 9, 11, 12],
              "Mercury": [3, 5, 6, 9, 11], "Jupiter": [5, 8, 9, 10, 11],
              "Venus": [1, 2, 3, 4, 5, 8, 9, 10, 11], "Saturn": [3, 4, 5, 8, 9, 10, 11],
              "Lagna": [1, 2, 3, 4, 5, 8, 9, 11]},
    "Saturn": {"Sun": [1, 2, 4, 7, 8, 10, 11], "Moon": [3, 6, 11], "Mars": [3, 5, 6, 10, 11, 12],
               "Mercury": [6, 8, 9, 10, 11, 12], "Jupiter": [5, 6, 11, 12], "Venus": [6, 11, 12],
               "Saturn": [3, 5, 6, 11], "Lagna": [1, 3, 4, 6, 10, 11]},
}
BAV_TOTALS = {"Sun": 48, "Moon": 49, "Mars": 39, "Mercury": 54, "Jupiter": 56, "Venus": 52, "Saturn": 39}
SAV_TOTAL = 337
# Shodhya pinda multipliers (BPHS ch.72). VERIFY
RASI_GUNAKARA = [7, 10, 8, 4, 10, 5, 7, 8, 9, 5, 11, 12]
GRAHA_GUNAKARA = {"Sun": 5, "Moon": 5, "Mars": 8, "Mercury": 5, "Jupiter": 10, "Venus": 7, "Saturn": 5}
# Ekadhipatya pairs (planet -> its two signs)
EKADHIPATYA = {"Mars": (0, 7), "Mercury": (2, 5), "Jupiter": (8, 11), "Venus": (1, 6), "Saturn": (9, 10)}

BENEFICS = ["Jupiter", "Venus", "Mercury", "Moon"]
MALEFICS = ["Sun", "Mars", "Saturn", "Rahu", "Ketu"]
# Graha drishti: aspected houses counted from the planet (BPHS ch.26) ; nodes 5/7/9 VERIFY
ASPECT_HOUSES = {"Sun": [7], "Moon": [7], "Mercury": [7], "Venus": [7], "Mars": [4, 7, 8],
                 "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10], "Rahu": [5, 7, 9], "Ketu": [5, 7, 9]}

# Ashtakavarga of the Lagna itself (Lagna as the target). Houses counted from each contributor; total 49.
# Derived from, and checked against, an external reference report (tests/reference).
LAGNA_BAV_CONTRIB = {
    "Sun": [3, 4, 6, 10, 11, 12], "Moon": [3, 6, 10, 11, 12], "Mars": [1, 3, 6, 10, 11],
    "Mercury": [1, 2, 4, 6, 8, 10, 11], "Jupiter": [1, 2, 4, 5, 6, 7, 9, 10, 11],
    "Venus": [1, 2, 3, 4, 5, 8, 9], "Saturn": [1, 3, 4, 6, 10, 11], "Lagna": [3, 6, 10, 11],
}
LAGNA_BAV_TOTAL = 49

# Avakahada (nakshatra / rashi lookups). Indices: nakshatra 0..26, sign 0..11.
# VERIFY: entered from the standard avakahada scheme from memory; cross-checked on ONE chart only (Pisces / Uttara
# Bhadrapada Moon). Needs a source line and a second-person review of all 27 / 12 entries (docs/open_questions.md).
VARNA_BY_SIGN = ["Kshatriya", "Vaishya", "Shudra", "Vipra", "Kshatriya", "Vaishya", "Shudra", "Vipra",
                 "Kshatriya", "Vaishya", "Shudra", "Vipra"]  # Vipra = Brahmin
YONI_BY_NAK = ["Ashwa", "Gaja", "Mesha", "Sarpa", "Sarpa", "Shwan", "Marjar", "Mesha", "Marjar", "Mushak",
               "Mushak", "Gau", "Mahisha", "Vyaghra", "Mahisha", "Vyaghra", "Mriga", "Mriga", "Shwan", "Vanar",
               "Nakul", "Vanar", "Simha", "Ashwa", "Simha", "Gau", "Gaja"]
GANA_BY_NAK = ["Deva", "Manushya", "Rakshasa", "Manushya", "Deva", "Manushya", "Deva", "Deva", "Rakshasa",
               "Rakshasa", "Manushya", "Manushya", "Deva", "Rakshasa", "Deva", "Rakshasa", "Deva", "Rakshasa",
               "Rakshasa", "Manushya", "Manushya", "Deva", "Rakshasa", "Rakshasa", "Manushya", "Manushya", "Deva"]
NADI_CYCLE = ["Adi", "Madhya", "Antya", "Antya", "Madhya", "Adi"]  # repeats 0..5 over the 27 nakshatras
TATVA_BY_SIGN = ["Fire", "Earth", "Air", "Water"]  # sign % 4
# Name syllables (avakahada akshara): 4 padas per nakshatra. VERIFY: Shravana and a few others vary by school.
NAME_SYLLABLES = [
    "Chu Che Cho La", "Li Lu Le Lo", "A I U E", "O Va Vi Vu", "Ve Vo Ka Ki", "Ku Gha Ng Chha", "Ke Ko Ha Hi",
    "Hu He Ho Da", "Di Du De Do", "Ma Mi Mu Me", "Mo Ta Ti Tu", "Te To Pa Pi", "Pu Sha Na Tha", "Pe Po Ra Ri",
    "Ru Re Ro Ta", "Ti Tu Te To", "Na Ni Nu Ne", "No Ya Yi Yu", "Ye Yo Bha Bhi", "Bhu Dha Pha Dha",
    "Bhe Bho Ja Ji", "Ju Je Jo Gha", "Ga Gi Gu Ge", "Go Sa Si Su", "Se So Da Di", "Du Tha Jha Na",
    "De Do Cha Chi",
]
# Paya (by Moon's house from Lagna) and Kaal Sarpa types (by Rahu's house from Lagna). VERIFY (one chart checked).
PAYA_BY_HOUSE = {1: "Gold", 6: "Gold", 11: "Gold", 2: "Silver", 5: "Silver", 9: "Silver",
                 3: "Copper", 7: "Copper", 10: "Copper", 4: "Iron", 8: "Iron", 12: "Iron"}
KAAL_SARPA_TYPES = ["Anant", "Kulik", "Vasuki", "Shankhpal", "Padma", "Mahapadma", "Takshak", "Karkotak",
                    "Shankhchoor", "Ghatak", "Vishdhar", "Sheshnaag"]

# VERIFY: gem, finger, metal and substitutes differ by tradition; checked only for Saturn/Venus/Mercury.
# Navagraha gemstones (traditional): gem, substitutes, weekday, finger of the right hand, metal, deity, beeja mantra.
GEMS = {
    "Sun": ("Ruby", ["Garnet", "Red Spinel"], "Sunday", "Ring", "Gold", "Surya", "ॐ ह्रां ह्रीं ह्रौं सः सूर्याय नमः"),
    "Moon": ("Pearl", ["Moonstone"], "Monday", "Little", "Silver", "Chandra", "ॐ श्रां श्रीं श्रौं सः चन्द्रमसे नमः"),
    "Mars": ("Red Coral", ["Carnelian"], "Tuesday", "Ring", "Gold or copper", "Mangal",
             "ॐ क्रां क्रीं क्रौं सः भौमाय नमः"),
    "Mercury": ("Emerald", ["Peridot", "Green Onyx"], "Wednesday", "Little", "Gold", "Budha",
                "ॐ ब्रां ब्रीं ब्रौं सः बुधाय नमः"),
    "Jupiter": ("Yellow Sapphire", ["Yellow Topaz", "Citrine"], "Thursday", "Index", "Gold", "Guru",
                "ॐ ग्रां ग्रीं ग्रौं सः गुरवे नमः"),
    "Venus": ("Diamond", ["White Sapphire", "White Zircon"], "Friday", "Little", "Silver or platinum", "Shukra",
              "ॐ द्रां द्रीं द्रौं सः शुक्राय नमः"),
    "Saturn": ("Blue Sapphire", ["Amethyst", "Lapis Lazuli"], "Saturday", "Middle", "Silver or iron (ashtadhatu)",
               "Shani", "ॐ प्रां प्रीं प्रौं सः शनैश्चराय नमः"),
    "Rahu": ("Hessonite (Gomed)", ["Orange Zircon"], "Saturday", "Middle", "Silver or ashtadhatu", "Rahu",
             "ॐ भ्रां भ्रीं भ्रौं सः राहवे नमः"),
    "Ketu": ("Cat's Eye", ["Tiger's Eye"], "Tuesday", "Little", "Silver or ashtadhatu", "Ketu",
             "ॐ स्रां स्रीं स्रौं सः केतवे नमः"),
}
