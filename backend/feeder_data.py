"""
Harmonee Feeder Birds Database & Likelihood Calculator.

Self-contained dataset mapping North American backyard birds to:
- Seasonal presence across Level 1 Ecoregions (or broad geographic zones)
- Feeder propensity (how readily the species visits artificial feeders)
- Food preference scores (0.0 = never/rare, 1.0 = highly preferred staple)
"""

from typing import List, Dict, Optional, Any
from datetime import datetime

# Common feeder food categories
FEEDER_FOODS = {
    "sunflower_black_oil": {
        "id": "sunflower_black_oil",
        "name": "Black-Oil Sunflower Seeds",
        "description": "High oil content, thin shells. Universal favorite for cardinals, chickadees, finches, nuthatches.",
    },
    "sunflower_striped": {
        "id": "sunflower_striped",
        "name": "Striped Sunflower Seeds",
        "description": "Thicker shell. Favored by larger beaks: Blue Jays, Cardinals, Grosbeaks.",
    },
    "sunflower_chips": {
        "id": "sunflower_chips",
        "name": "Sunflower Hearts / Chips (No Shell)",
        "description": "No mess, universally accessible to both small and large songbirds.",
    },
    "millet_white": {
        "id": "millet_white",
        "name": "White Proso Millet",
        "description": "Ground and platform seed favored by juncos, native sparrows, doves, towhees.",
    },
    "nyjer": {
        "id": "nyjer",
        "name": "Nyjer / Thistle Seed",
        "description": "Tiny black seed loved by American Goldfinches, Pine Siskins, redpolls.",
    },
    "safflower": {
        "id": "safflower",
        "name": "Safflower Seeds",
        "description": "Bitter taste to squirrels & grackles; favorite of Cardinals, Nuthatches, Chickadees.",
    },
    "peanuts_shelled": {
        "id": "peanuts_shelled",
        "name": "Peanuts (Shelled / Halves)",
        "description": "High fat & protein. Woodpeckers, jays, nuthatches, chickadees, titmice.",
    },
    "peanuts_in_shell": {
        "id": "peanuts_in_shell",
        "name": "Peanuts in Shell",
        "description": "Loved by Blue Jays, Scrub Jays, larger woodpeckers, and nuthatches.",
    },
    "suet": {
        "id": "suet",
        "name": "Suet / Fat Cake",
        "description": "Rendered beef fat / seed cake. Woodpeckers, nuthatches, chickadees, wrens, starlings.",
    },
    "cracked_corn": {
        "id": "cracked_corn",
        "name": "Cracked Corn",
        "description": "Affordable grain for mourning doves, quails, turkeys, jays, ducks.",
    },
    "nectar": {
        "id": "nectar",
        "name": "Nectar (Sugar Water)",
        "description": "4:1 water to white cane sugar. Hummingbirds and Orioles.",
    },
    "mealworms": {
        "id": "mealworms",
        "name": "Mealworms (Dried or Live)",
        "description": "Protein-rich favorite of Eastern & Western Bluebirds, robins, wrens, thrushes.",
    },
    "fruit_jelly": {
        "id": "fruit_jelly",
        "name": "Fruit, Oranges & Grape Jelly",
        "description": "Spring and summer favorite for Baltimore and Bullock's Orioles, catbirds, tanagers.",
    },
}

# Pre-set seed blends for quick convenience
PRESET_FOOD_BLENDS = {
    "wild_bird_basic": {
        "id": "wild_bird_basic",
        "name": "Classic Mixed Wild Bird Seed",
        "foods": ["millet_white", "cracked_corn", "sunflower_striped"],
    },
    "premium_songbird": {
        "id": "premium_songbird",
        "name": "Premium Songbird Blend",
        "foods": ["sunflower_black_oil", "millet_white", "safflower", "peanuts_shelled"],
    },
    "no_mess_patio": {
        "id": "no_mess_patio",
        "name": "No-Mess / Patio Blend",
        "foods": ["sunflower_chips", "peanuts_shelled"],
    },
    "finch_special": {
        "id": "finch_special",
        "name": "Finch Blend",
        "foods": ["nyjer", "sunflower_chips"],
    },
    "cardinal_blend": {
        "id": "cardinal_blend",
        "name": "Cardinal & Songbird Blend",
        "foods": ["sunflower_black_oil", "safflower", "sunflower_striped"],
    },
    "woodpecker_treat": {
        "id": "woodpecker_treat",
        "name": "Woodpecker & Nuthatch Blend",
        "foods": ["peanuts_shelled", "sunflower_chips", "suet"],
    },
    "hummingbird_nectar": {
        "id": "hummingbird_nectar",
        "name": "Hummingbird Nectar",
        "foods": ["nectar"],
    },
    "suet_cake": {
        "id": "suet_cake",
        "name": "Pure Suet Cake",
        "foods": ["suet"],
    },
}

# Season helper
def get_season_for_month(month: int) -> str:
    """Return season code: 'spring', 'summer', 'fall', or 'winter'."""
    if month in (3, 4, 5):
        return "spring"
    elif month in (6, 7, 8):
        return "summer"
    elif month in (9, 10, 11):
        return "fall"
    else:
        return "winter"

# EPA Level 1 Ecoregion / Geographic Zone mapping helper
# Ecoregion codes:
# 5: Northern Forests
# 6: Northwestern Forested Mountains
# 7: Marine West Coast Forest
# 8: Eastern Temperate Forests
# 9: Great Plains
# 10: North American Deserts
# 11: Mediterranean California
# 12: Southern Semi-Arid Highlands
# 13: Temperate Sierras
def normalize_ecoregion_zone(ecoregions: Optional[dict] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> str:
    """Determine broad ecoregion zone key (e.g. '8_eastern_temperate_forests')."""
    if ecoregions and isinstance(ecoregions, dict):
        l1 = str(ecoregions.get("level1", "")).lower()
        if "8" in l1 or "eastern temperate" in l1:
            return "8_eastern_temperate_forests"
        if "5" in l1 or "northern forest" in l1:
            return "5_northern_forests"
        if "9" in l1 or "great plains" in l1:
            return "9_great_plains"
        if "6" in l1 or "northwestern forested" in l1:
            return "6_northwestern_forested_mountains"
        if "7" in l1 or "marine west coast" in l1:
            return "7_marine_west_coast"
        if "10" in l1 or "desert" in l1:
            return "10_deserts"
        if "11" in l1 or "mediterranean" in l1:
            return "11_mediterranean_california"

    # Fallback by latitude / longitude if ecoregion string isn't supplied
    if lon is not None and lat is not None:
        if lon < -120 and lat >= 35:
            return "7_marine_west_coast"
        elif lon < -115 and lat < 38:
            return "11_mediterranean_california"
        elif lon < -104 and lat >= 35:
            return "6_northwestern_forested_mountains"
        elif lon < -100 and lat < 35:
            return "10_deserts"
        elif -104 <= lon <= -95:
            return "9_great_plains"
        elif lon > -95:
            if lat > 45:
                return "5_northern_forests"
            return "8_eastern_temperate_forests"

    # Default to Eastern Temperate Forests if unknown
    return "8_eastern_temperate_forests"


# Curated catalog of backyard birds with seasonal presence and food affinities
FEEDER_SPECIES = [
    {
        "id": "northern_cardinal",
        "commonName": "Northern Cardinal",
        "scientificName": "Cardinalis cardinalis",
        "feederPropensity": 0.95,
        "description": "Brilliant red songbird with a crest and sturdy cone beak built for seeds.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.95, "summer": 0.95, "fall": 0.95, "winter": 0.95},
            "9_great_plains": {"spring": 0.70, "summer": 0.70, "fall": 0.70, "winter": 0.70},
            "10_deserts": {"spring": 0.45, "summer": 0.40, "fall": 0.40, "winter": 0.45},
            "5_northern_forests": {"spring": 0.30, "summer": 0.30, "fall": 0.30, "winter": 0.25},
            "6_northwestern_forested_mountains": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "7_marine_west_coast": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "11_mediterranean_california": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
        },
        "foodPreferences": {
            "sunflower_black_oil": 1.0,
            "safflower": 0.95,
            "sunflower_chips": 0.95,
            "sunflower_striped": 0.85,
            "peanuts_shelled": 0.65,
            "millet_white": 0.55,
            "cracked_corn": 0.45,
            "suet": 0.20,
            "nyjer": 0.0,
            "nectar": 0.0,
            "mealworms": 0.30,
            "fruit_jelly": 0.10,
        },
    },
    {
        "id": "blue_jay",
        "commonName": "Blue Jay",
        "scientificName": "Cyanocitta cristata",
        "feederPropensity": 0.90,
        "description": "Intelligent, vocal crested jay known for caching acorns and peanuts.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.95, "summer": 0.95, "fall": 0.95, "winter": 0.90},
            "9_great_plains": {"spring": 0.80, "summer": 0.75, "fall": 0.80, "winter": 0.75},
            "5_northern_forests": {"spring": 0.75, "summer": 0.80, "fall": 0.70, "winter": 0.50},
            "6_northwestern_forested_mountains": {"spring": 0.05, "summer": 0.05, "fall": 0.05, "winter": 0.05},
            "7_marine_west_coast": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "10_deserts": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "11_mediterranean_california": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
        },
        "foodPreferences": {
            "peanuts_in_shell": 1.0,
            "peanuts_shelled": 0.95,
            "sunflower_black_oil": 0.90,
            "sunflower_striped": 0.90,
            "sunflower_chips": 0.85,
            "suet": 0.70,
            "cracked_corn": 0.60,
            "millet_white": 0.20,
            "safflower": 0.20,
            "nyjer": 0.0,
            "nectar": 0.0,
            "mealworms": 0.50,
            "fruit_jelly": 0.20,
        },
    },
    {
        "id": "black_capped_chickadee",
        "commonName": "Black-capped Chickadee",
        "scientificName": "Poecile atricapillus",
        "feederPropensity": 0.95,
        "description": "Curious, agile acrobat that grabs seeds one at a time to open on nearby twigs.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.85, "summer": 0.80, "fall": 0.85, "winter": 0.90},
            "5_northern_forests": {"spring": 0.95, "summer": 0.95, "fall": 0.95, "winter": 0.95},
            "6_northwestern_forested_mountains": {"spring": 0.90, "summer": 0.90, "fall": 0.90, "winter": 0.90},
            "7_marine_west_coast": {"spring": 0.85, "summer": 0.85, "fall": 0.85, "winter": 0.85},
            "9_great_plains": {"spring": 0.60, "summer": 0.50, "fall": 0.60, "winter": 0.70},
            "10_deserts": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "11_mediterranean_california": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
        },
        "foodPreferences": {
            "sunflower_black_oil": 1.0,
            "sunflower_chips": 1.0,
            "peanuts_shelled": 0.90,
            "suet": 0.85,
            "safflower": 0.75,
            "mealworms": 0.70,
            "nyjer": 0.30,
            "sunflower_striped": 0.40,
            "millet_white": 0.15,
            "cracked_corn": 0.05,
            "nectar": 0.0,
            "fruit_jelly": 0.0,
        },
    },
    {
        "id": "tufted_titmouse",
        "commonName": "Tufted Titmouse",
        "scientificName": "Baeolophus bicolor",
        "feederPropensity": 0.90,
        "description": "Silvery gray bird with an expressive crest and big black eyes.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.90, "summer": 0.90, "fall": 0.90, "winter": 0.90},
            "9_great_plains": {"spring": 0.35, "summer": 0.35, "fall": 0.35, "winter": 0.35},
            "5_northern_forests": {"spring": 0.20, "summer": 0.20, "fall": 0.20, "winter": 0.15},
            "6_northwestern_forested_mountains": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "7_marine_west_coast": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "10_deserts": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "11_mediterranean_california": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
        },
        "foodPreferences": {
            "sunflower_black_oil": 1.0,
            "sunflower_chips": 0.95,
            "peanuts_shelled": 0.90,
            "suet": 0.75,
            "safflower": 0.70,
            "mealworms": 0.65,
            "sunflower_striped": 0.50,
            "millet_white": 0.20,
            "cracked_corn": 0.10,
            "nyjer": 0.05,
            "nectar": 0.0,
            "fruit_jelly": 0.0,
        },
    },
    {
        "id": "white_breasted_nuthatch",
        "commonName": "White-breasted Nuthatch",
        "scientificName": "Sitta carolinensis",
        "feederPropensity": 0.90,
        "description": "Tree-trunk acrobat that walks headfirst down tree trunks.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.85, "summer": 0.85, "fall": 0.85, "winter": 0.90},
            "5_northern_forests": {"spring": 0.70, "summer": 0.70, "fall": 0.70, "winter": 0.70},
            "6_northwestern_forested_mountains": {"spring": 0.65, "summer": 0.65, "fall": 0.65, "winter": 0.65},
            "7_marine_west_coast": {"spring": 0.40, "summer": 0.40, "fall": 0.40, "winter": 0.40},
            "9_great_plains": {"spring": 0.45, "summer": 0.45, "fall": 0.45, "winter": 0.50},
            "10_deserts": {"spring": 0.30, "summer": 0.30, "fall": 0.30, "winter": 0.30},
            "11_mediterranean_california": {"spring": 0.40, "summer": 0.40, "fall": 0.40, "winter": 0.40},
        },
        "foodPreferences": {
            "peanuts_shelled": 1.0,
            "sunflower_black_oil": 0.95,
            "suet": 0.90,
            "sunflower_chips": 0.90,
            "safflower": 0.65,
            "mealworms": 0.60,
            "sunflower_striped": 0.50,
            "millet_white": 0.10,
            "cracked_corn": 0.10,
            "nyjer": 0.0,
            "nectar": 0.0,
            "fruit_jelly": 0.0,
        },
    },
    {
        "id": "downy_woodpecker",
        "commonName": "Downy Woodpecker",
        "scientificName": "Dryobates pubescens",
        "feederPropensity": 0.90,
        "description": "The smallest North American woodpecker, frequent visitor to backyard suet and peanut feeders.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.90, "summer": 0.90, "fall": 0.90, "winter": 0.95},
            "5_northern_forests": {"spring": 0.85, "summer": 0.85, "fall": 0.85, "winter": 0.90},
            "6_northwestern_forested_mountains": {"spring": 0.75, "summer": 0.75, "fall": 0.75, "winter": 0.80},
            "7_marine_west_coast": {"spring": 0.75, "summer": 0.75, "fall": 0.75, "winter": 0.80},
            "9_great_plains": {"spring": 0.65, "summer": 0.60, "fall": 0.65, "winter": 0.70},
            "10_deserts": {"spring": 0.10, "summer": 0.10, "fall": 0.10, "winter": 0.15},
            "11_mediterranean_california": {"spring": 0.65, "summer": 0.65, "fall": 0.65, "winter": 0.70},
        },
        "foodPreferences": {
            "suet": 1.0,
            "peanuts_shelled": 0.90,
            "sunflower_black_oil": 0.80,
            "sunflower_chips": 0.85,
            "mealworms": 0.75,
            "peanuts_in_shell": 0.50,
            "millet_white": 0.10,
            "cracked_corn": 0.10,
            "safflower": 0.10,
            "nyjer": 0.0,
            "nectar": 0.0,
            "fruit_jelly": 0.0,
        },
    },
    {
        "id": "american_goldfinch",
        "commonName": "American Goldfinch",
        "scientificName": "Spinus tristis",
        "feederPropensity": 0.95,
        "description": "Lemony yellow acrobat in summer that feeds strictly on seeds, molting olive-brown in winter.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.85, "summer": 0.90, "fall": 0.85, "winter": 0.80},
            "5_northern_forests": {"spring": 0.80, "summer": 0.90, "fall": 0.75, "winter": 0.40},
            "6_northwestern_forested_mountains": {"spring": 0.75, "summer": 0.85, "fall": 0.70, "winter": 0.40},
            "7_marine_west_coast": {"spring": 0.80, "summer": 0.90, "fall": 0.80, "winter": 0.60},
            "9_great_plains": {"spring": 0.70, "summer": 0.75, "fall": 0.70, "winter": 0.60},
            "10_deserts": {"spring": 0.20, "summer": 0.10, "fall": 0.20, "winter": 0.35},
            "11_mediterranean_california": {"spring": 0.75, "summer": 0.75, "fall": 0.75, "winter": 0.75},
        },
        "foodPreferences": {
            "nyjer": 1.0,
            "sunflower_chips": 0.95,
            "sunflower_black_oil": 0.65,
            "millet_white": 0.10,
            "safflower": 0.05,
            "peanuts_shelled": 0.0,
            "suet": 0.0,
            "cracked_corn": 0.0,
            "nectar": 0.0,
            "mealworms": 0.0,
            "fruit_jelly": 0.0,
        },
    },
    {
        "id": "mourning_dove",
        "commonName": "Mourning Dove",
        "scientificName": "Zenaida macroura",
        "feederPropensity": 0.85,
        "description": "Gentle, soft-calling dove that sweeps fallen grain beneath trays and platforms.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.90, "summer": 0.95, "fall": 0.90, "winter": 0.80},
            "9_great_plains": {"spring": 0.95, "summer": 0.95, "fall": 0.90, "winter": 0.70},
            "10_deserts": {"spring": 0.90, "summer": 0.90, "fall": 0.90, "winter": 0.85},
            "11_mediterranean_california": {"spring": 0.90, "summer": 0.90, "fall": 0.90, "winter": 0.85},
            "6_northwestern_forested_mountains": {"spring": 0.70, "summer": 0.80, "fall": 0.65, "winter": 0.35},
            "7_marine_west_coast": {"spring": 0.60, "summer": 0.70, "fall": 0.60, "winter": 0.40},
            "5_northern_forests": {"spring": 0.70, "summer": 0.80, "fall": 0.65, "winter": 0.20},
        },
        "foodPreferences": {
            "millet_white": 1.0,
            "cracked_corn": 0.90,
            "sunflower_chips": 0.85,
            "sunflower_black_oil": 0.80,
            "safflower": 0.70,
            "sunflower_striped": 0.40,
            "peanuts_shelled": 0.30,
            "nyjer": 0.20,
            "suet": 0.0,
            "nectar": 0.0,
            "mealworms": 0.0,
            "fruit_jelly": 0.0,
        },
    },
    {
        "id": "dark_eyed_junco",
        "commonName": "Dark-eyed Junco",
        "scientificName": "Junco hyemalis",
        "feederPropensity": 0.85,
        "description": "Known as the 'snowbird' across the southern and eastern US, visiting ground and tray feeders in winter.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.50, "summer": 0.05, "fall": 0.70, "winter": 0.95},
            "9_great_plains": {"spring": 0.40, "summer": 0.05, "fall": 0.65, "winter": 0.90},
            "5_northern_forests": {"spring": 0.90, "summer": 0.95, "fall": 0.90, "winter": 0.40},
            "6_northwestern_forested_mountains": {"spring": 0.90, "summer": 0.90, "fall": 0.90, "winter": 0.80},
            "7_marine_west_coast": {"spring": 0.75, "summer": 0.60, "fall": 0.85, "winter": 0.95},
            "10_deserts": {"spring": 0.30, "summer": 0.05, "fall": 0.40, "winter": 0.65},
            "11_mediterranean_california": {"spring": 0.60, "summer": 0.40, "fall": 0.75, "winter": 0.90},
        },
        "foodPreferences": {
            "millet_white": 1.0,
            "sunflower_chips": 0.95,
            "cracked_corn": 0.75,
            "sunflower_black_oil": 0.60,
            "nyjer": 0.40,
            "peanuts_shelled": 0.30,
            "safflower": 0.20,
            "suet": 0.15,
            "mealworms": 0.15,
            "sunflower_striped": 0.05,
            "nectar": 0.0,
            "fruit_jelly": 0.0,
        },
    },
    {
        "id": "ruby_throated_hummingbird",
        "commonName": "Ruby-throated Hummingbird",
        "scientificName": "Archilochus colubris",
        "feederPropensity": 0.95,
        "description": "Sole breeding hummingbird across eastern North America; voracious feeder of flower nectar and sugar water.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.85, "summer": 0.95, "fall": 0.70, "winter": 0.0},
            "9_great_plains": {"spring": 0.60, "summer": 0.60, "fall": 0.45, "winter": 0.0},
            "5_northern_forests": {"spring": 0.70, "summer": 0.80, "fall": 0.30, "winter": 0.0},
            "6_northwestern_forested_mountains": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "7_marine_west_coast": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "10_deserts": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "11_mediterranean_california": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
        },
        "foodPreferences": {
            "nectar": 1.0,
            "sunflower_black_oil": 0.0,
            "sunflower_chips": 0.0,
            "sunflower_striped": 0.0,
            "millet_white": 0.0,
            "nyjer": 0.0,
            "safflower": 0.0,
            "peanuts_shelled": 0.0,
            "suet": 0.0,
            "cracked_corn": 0.0,
            "mealworms": 0.0,
            "fruit_jelly": 0.0,
        },
    },
    {
        "id": "eastern_bluebird",
        "commonName": "Eastern Bluebird",
        "scientificName": "Sialia sialis",
        "feederPropensity": 0.70,
        "description": "Gentle songbird of open woods and fields that readily takes live/dried mealworms and suet.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.85, "summer": 0.85, "fall": 0.80, "winter": 0.65},
            "9_great_plains": {"spring": 0.65, "summer": 0.65, "fall": 0.55, "winter": 0.35},
            "5_northern_forests": {"spring": 0.50, "summer": 0.60, "fall": 0.30, "winter": 0.05},
            "6_northwestern_forested_mountains": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "7_marine_west_coast": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "10_deserts": {"spring": 0.05, "summer": 0.05, "fall": 0.05, "winter": 0.05},
            "11_mediterranean_california": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
        },
        "foodPreferences": {
            "mealworms": 1.0,
            "suet": 0.75,
            "sunflower_chips": 0.40,
            "fruit_jelly": 0.35,
            "peanuts_shelled": 0.30,
            "sunflower_black_oil": 0.15,
            "millet_white": 0.05,
            "cracked_corn": 0.0,
            "nyjer": 0.0,
            "safflower": 0.0,
            "nectar": 0.0,
        },
    },
    {
        "id": "baltimore_oriole",
        "commonName": "Baltimore Oriole",
        "scientificName": "Icterus galbula",
        "feederPropensity": 0.80,
        "description": "Vibrant orange flame in spring trees, readily attracted to halved oranges and sweet grape jelly.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.80, "summer": 0.80, "fall": 0.30, "winter": 0.0},
            "9_great_plains": {"spring": 0.65, "summer": 0.65, "fall": 0.20, "winter": 0.0},
            "5_northern_forests": {"spring": 0.55, "summer": 0.60, "fall": 0.15, "winter": 0.0},
            "6_northwestern_forested_mountains": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "7_marine_west_coast": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "10_deserts": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "11_mediterranean_california": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
        },
        "foodPreferences": {
            "fruit_jelly": 1.0,
            "nectar": 0.90,
            "mealworms": 0.50,
            "suet": 0.40,
            "sunflower_chips": 0.15,
            "sunflower_black_oil": 0.05,
            "millet_white": 0.0,
            "nyjer": 0.0,
            "cracked_corn": 0.0,
            "safflower": 0.0,
            "peanuts_shelled": 0.0,
        },
    },
    {
        "id": "white_throated_sparrow",
        "commonName": "White-throated Sparrow",
        "scientificName": "Zonotrichia albicollis",
        "feederPropensity": 0.85,
        "description": "Beloved winter visitor in the east, famous for its crisp 'Poor Sam Peabody' whistle.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.70, "summer": 0.05, "fall": 0.80, "winter": 0.90},
            "5_northern_forests": {"spring": 0.90, "summer": 0.95, "fall": 0.85, "winter": 0.20},
            "9_great_plains": {"spring": 0.50, "summer": 0.05, "fall": 0.50, "winter": 0.40},
            "6_northwestern_forested_mountains": {"spring": 0.05, "summer": 0.05, "fall": 0.05, "winter": 0.05},
            "7_marine_west_coast": {"spring": 0.05, "summer": 0.0, "fall": 0.05, "winter": 0.05},
            "10_deserts": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "11_mediterranean_california": {"spring": 0.05, "summer": 0.0, "fall": 0.05, "winter": 0.05},
        },
        "foodPreferences": {
            "millet_white": 0.95,
            "sunflower_chips": 0.90,
            "sunflower_black_oil": 0.80,
            "cracked_corn": 0.65,
            "safflower": 0.40,
            "nyjer": 0.35,
            "peanuts_shelled": 0.30,
            "suet": 0.20,
            "mealworms": 0.20,
            "sunflower_striped": 0.15,
            "nectar": 0.0,
            "fruit_jelly": 0.0,
        },
    },
    {
        "id": "house_finch",
        "commonName": "House Finch",
        "scientificName": "Haemorhous mexicanus",
        "feederPropensity": 0.95,
        "description": "Cheerful red-crowned songbird found throughout backyards across all of North America.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.90, "summer": 0.90, "fall": 0.90, "winter": 0.90},
            "9_great_plains": {"spring": 0.85, "summer": 0.85, "fall": 0.85, "winter": 0.85},
            "10_deserts": {"spring": 0.95, "summer": 0.95, "fall": 0.95, "winter": 0.95},
            "11_mediterranean_california": {"spring": 0.95, "summer": 0.95, "fall": 0.95, "winter": 0.95},
            "6_northwestern_forested_mountains": {"spring": 0.80, "summer": 0.80, "fall": 0.80, "winter": 0.80},
            "7_marine_west_coast": {"spring": 0.90, "summer": 0.90, "fall": 0.90, "winter": 0.90},
            "5_northern_forests": {"spring": 0.60, "summer": 0.60, "fall": 0.60, "winter": 0.50},
        },
        "foodPreferences": {
            "sunflower_black_oil": 1.0,
            "sunflower_chips": 0.95,
            "nyjer": 0.80,
            "safflower": 0.70,
            "millet_white": 0.50,
            "sunflower_striped": 0.40,
            "cracked_corn": 0.15,
            "peanuts_shelled": 0.10,
            "suet": 0.10,
            "nectar": 0.0,
            "mealworms": 0.0,
            "fruit_jelly": 0.0,
        },
    },
    {
        "id": "red_bellied_woodpecker",
        "commonName": "Red-bellied Woodpecker",
        "scientificName": "Melanerpes carolinus",
        "feederPropensity": 0.85,
        "description": "Medium-sized woodpecker with zebra-striped back and brilliant scarlet cap.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.90, "summer": 0.90, "fall": 0.90, "winter": 0.90},
            "9_great_plains": {"spring": 0.55, "summer": 0.55, "fall": 0.55, "winter": 0.55},
            "5_northern_forests": {"spring": 0.25, "summer": 0.25, "fall": 0.25, "winter": 0.20},
            "6_northwestern_forested_mountains": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "7_marine_west_coast": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "10_deserts": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "11_mediterranean_california": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
        },
        "foodPreferences": {
            "suet": 1.0,
            "peanuts_shelled": 0.95,
            "peanuts_in_shell": 0.90,
            "sunflower_black_oil": 0.85,
            "sunflower_chips": 0.85,
            "sunflower_striped": 0.70,
            "mealworms": 0.60,
            "fruit_jelly": 0.40,
            "cracked_corn": 0.35,
            "safflower": 0.30,
            "millet_white": 0.10,
            "nyjer": 0.0,
            "nectar": 0.0,
        },
    },
    {
        "id": "carolina_wren",
        "commonName": "Carolina Wren",
        "scientificName": "Thryothorus ludovicianus",
        "feederPropensity": 0.75,
        "description": "Chunky, expressive rust-brown songbird with a loud 'teakettle-teakettle' song.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.85, "summer": 0.85, "fall": 0.85, "winter": 0.80},
            "9_great_plains": {"spring": 0.40, "summer": 0.40, "fall": 0.40, "winter": 0.30},
            "5_northern_forests": {"spring": 0.10, "summer": 0.10, "fall": 0.10, "winter": 0.05},
            "6_northwestern_forested_mountains": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "7_marine_west_coast": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "10_deserts": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "11_mediterranean_california": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
        },
        "foodPreferences": {
            "suet": 0.95,
            "mealworms": 0.95,
            "peanuts_shelled": 0.85,
            "sunflower_chips": 0.75,
            "sunflower_black_oil": 0.40,
            "millet_white": 0.15,
            "cracked_corn": 0.05,
            "safflower": 0.05,
            "nyjer": 0.0,
            "nectar": 0.0,
            "fruit_jelly": 0.10,
        },
    },
    {
        "id": "rose_breasted_grosbeak",
        "commonName": "Rose-breasted Grosbeak",
        "scientificName": "Pheucticus ludovicianus",
        "feederPropensity": 0.85,
        "description": "Striking black and white migrant with a ruby-rose triangle chest patch, loves sunflower seeds.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.75, "summer": 0.70, "fall": 0.50, "winter": 0.0},
            "5_northern_forests": {"spring": 0.80, "summer": 0.85, "fall": 0.45, "winter": 0.0},
            "9_great_plains": {"spring": 0.50, "summer": 0.40, "fall": 0.30, "winter": 0.0},
            "6_northwestern_forested_mountains": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "7_marine_west_coast": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "10_deserts": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "11_mediterranean_california": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
        },
        "foodPreferences": {
            "sunflower_black_oil": 1.0,
            "sunflower_striped": 0.95,
            "sunflower_chips": 0.90,
            "safflower": 0.85,
            "peanuts_shelled": 0.60,
            "suet": 0.30,
            "millet_white": 0.20,
            "mealworms": 0.20,
            "fruit_jelly": 0.25,
            "cracked_corn": 0.10,
            "nyjer": 0.0,
            "nectar": 0.0,
        },
    },
    {
        "id": "pileated_woodpecker",
        "commonName": "Pileated Woodpecker",
        "scientificName": "Dryocopus pileatus",
        "feederPropensity": 0.50,
        "description": "Crow-sized giant woodpecker with a flaming red crest; an occasional dramatic visitor to suet cages.",
        "presence": {
            "8_eastern_temperate_forests": {"spring": 0.65, "summer": 0.65, "fall": 0.65, "winter": 0.65},
            "5_northern_forests": {"spring": 0.60, "summer": 0.60, "fall": 0.60, "winter": 0.60},
            "6_northwestern_forested_mountains": {"spring": 0.55, "summer": 0.55, "fall": 0.55, "winter": 0.55},
            "7_marine_west_coast": {"spring": 0.50, "summer": 0.50, "fall": 0.50, "winter": 0.50},
            "9_great_plains": {"spring": 0.10, "summer": 0.10, "fall": 0.10, "winter": 0.10},
            "10_deserts": {"spring": 0.0, "summer": 0.0, "fall": 0.0, "winter": 0.0},
            "11_mediterranean_california": {"spring": 0.25, "summer": 0.25, "fall": 0.25, "winter": 0.25},
        },
        "foodPreferences": {
            "suet": 1.0,
            "peanuts_shelled": 0.70,
            "peanuts_in_shell": 0.60,
            "sunflower_black_oil": 0.30,
            "sunflower_chips": 0.30,
            "mealworms": 0.30,
            "millet_white": 0.0,
            "cracked_corn": 0.0,
            "safflower": 0.0,
            "nyjer": 0.0,
            "nectar": 0.0,
            "fruit_jelly": 0.05,
        },
    },
]


def calculate_feeder_likelihood(
    foods: List[str],
    season: Optional[str] = None,
    month: Optional[int] = None,
    ecoregion_zone: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    min_probability: float = 0.02,
) -> List[Dict[str, Any]]:
    """
    Given a feeder's contents, location, and season/date:
    Computes a sorted likelihood list of birds visiting the feeder.
    """
    if not season:
        m = month or datetime.now().month
        season = get_season_for_month(m)

    zone = ecoregion_zone or normalize_ecoregion_zone(lat=lat, lon=lon)

    results = []

    # If no foods are specified, return empty
    if not foods:
        return []

    for sp in FEEDER_SPECIES:
        # 1. Regional & seasonal presence probability
        pres_dict = sp["presence"].get(zone, {})
        pres_score = pres_dict.get(season, 0.0)

        if pres_score <= 0.0:
            continue

        # 2. Food affinity score
        # The bird looks for the food in the feeder that it likes the best
        pref_map = sp["foodPreferences"]
        matched_scores = [pref_map.get(f, 0.0) for f in foods]
        food_score = max(matched_scores) if matched_scores else 0.0

        if food_score <= 0.0:
            continue

        # 3. Overall visit likelihood probability
        feeder_propensity = sp.get("feederPropensity", 0.8)
        probability = pres_score * food_score * feeder_propensity

        if probability < min_probability:
            continue

        # Likelihood classification tier
        if probability >= 0.65:
            tier = "Very Likely"
            tier_code = "very_likely"
        elif probability >= 0.40:
            tier = "Likely"
            tier_code = "likely"
        elif probability >= 0.15:
            tier = "Occasional"
            tier_code = "occasional"
        else:
            tier = "Uncommon / Rare"
            tier_code = "uncommon"

        # Determine favorite food match in this feeder
        best_food_id = None
        best_food_score = -1.0
        for f in foods:
            score = pref_map.get(f, 0.0)
            if score > best_food_score:
                best_food_score = score
                best_food_id = f

        best_food_name = FEEDER_FOODS.get(best_food_id, {}).get("name", best_food_id)

        results.append({
            "id": sp["id"],
            "commonName": sp["commonName"],
            "scientificName": sp["scientificName"],
            "description": sp["description"],
            "probability": round(probability, 3),
            "tier": tier,
            "tierCode": tier_code,
            "presenceScore": round(pres_score, 2),
            "foodMatchScore": round(food_score, 2),
            "primaryTargetFood": best_food_name,
        })

    # Sort descending by probability
    results.sort(key=lambda x: x["probability"], reverse=True)
    return results
