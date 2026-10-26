"""Feeder bird visit likelihood calculator and ecoregion/season normalization."""

from datetime import datetime
from typing import Any, Optional
import urllib.parse

from backend.data.feeder_foods import FEEDER_FOODS, PRESET_FOOD_BLENDS
from backend.data.feeder_species import FEEDER_SPECIES
from backend.services.birds import match_audubon_species


def get_season_for_month(month: int) -> str:
    """Return season code: 'spring', 'summer', 'fall', or 'winter'."""
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "fall"
    return "winter"


def normalize_ecoregion_zone(
    ecoregions: Optional[dict] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> str:
    """Determine broad EPA Level I ecoregion zone key (e.g. '8_eastern_temperate_forests')."""
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

    if lon is not None and lat is not None:
        if lon < -120 and lat >= 35:
            return "7_marine_west_coast"
        if lon < -115 and lat < 38:
            return "11_mediterranean_california"
        if lon < -104 and lat >= 35:
            return "6_northwestern_forested_mountains"
        if lon < -100 and lat < 35:
            return "10_deserts"
        if -104 <= lon <= -95:
            return "9_great_plains"
        if lon > -95:
            if lat > 45:
                return "5_northern_forests"
            return "8_eastern_temperate_forests"

    return "8_eastern_temperate_forests"


def calculate_feeder_likelihood(
    foods: list[str],
    season: Optional[str] = None,
    month: Optional[int] = None,
    ecoregion_zone: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    min_probability: float = 0.02,
) -> list[dict[str, Any]]:
    """Compute a sorted likelihood list of birds visiting a feeder given foods, season, and location."""
    if not foods:
        return []

    if not season:
        m = month or datetime.now().month
        season = get_season_for_month(m)

    zone = ecoregion_zone or normalize_ecoregion_zone(lat=lat, lon=lon)
    results = []

    for sp in FEEDER_SPECIES:
        pres_dict = sp["presence"].get(zone, {})
        pres_score = pres_dict.get(season, 0.0)
        if pres_score <= 0.0:
            continue

        pref_map = sp["foodPreferences"]
        matched_scores = [pref_map.get(f, 0.0) for f in foods]
        food_score = max(matched_scores) if matched_scores else 0.0
        if food_score <= 0.0:
            continue

        feeder_propensity = sp.get("feederPropensity", 0.8)
        probability = pres_score * food_score * feeder_propensity
        if probability < min_probability:
            continue

        if probability >= 0.65:
            tier, tier_code = "Very Likely", "very_likely"
        elif probability >= 0.40:
            tier, tier_code = "Likely", "likely"
        elif probability >= 0.15:
            tier, tier_code = "Occasional", "occasional"
        else:
            tier, tier_code = "Uncommon / Rare", "uncommon"

        best_food_id = None
        best_food_score = -1.0
        for f in foods:
            score = pref_map.get(f, 0.0)
            if score > best_food_score:
                best_food_score = score
                best_food_id = f

        best_food_name = FEEDER_FOODS.get(best_food_id, {}).get("name", best_food_id)

        results.append(
            {
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
            }
        )

    results.sort(key=lambda x: x["probability"], reverse=True)
    return results


def build_feeder_likelihood_response(
    foods: list[str],
    season: Optional[str] = None,
    month: Optional[int] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    ecoregions: Optional[dict] = None,
) -> dict[str, Any]:
    """Build complete feeder likelihood response enriched with species photo & Audubon plate links."""
    zone = normalize_ecoregion_zone(ecoregions=ecoregions, lat=lat, lon=lon)
    resolved_season = season or get_season_for_month(month or datetime.now().month)

    visitors = calculate_feeder_likelihood(
        foods=foods,
        season=resolved_season,
        ecoregion_zone=zone,
        lat=lat,
        lon=lon,
    )

    for v in visitors:
        sci = v["scientificName"]
        v["imageUrl"] = f"/api/birds/photo?species={urllib.parse.quote(sci)}"
        sp_match = match_audubon_species(sci, v["commonName"])
        if sp_match:
            v["audubonImage"] = (
                f"/api/audubon-image?species={urllib.parse.quote(sp_match['scientificName'])}"
            )
            v["audubonPlate"] = sp_match.get("plate", "")
        else:
            v["audubonImage"] = v["imageUrl"]
            v["audubonPlate"] = None

    return {
        "season": resolved_season,
        "ecoregionZone": zone,
        "foods": foods,
        "totalSpecies": len(visitors),
        "visitors": visitors,
    }


def get_feeder_options_catalog() -> dict[str, list[dict]]:
    """Return available feeder food ingredients and preset seed blends."""
    return {
        "foods": list(FEEDER_FOODS.values()),
        "presets": list(PRESET_FOOD_BLENDS.values()),
    }
