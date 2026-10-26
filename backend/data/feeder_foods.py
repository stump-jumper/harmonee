"""Available bird feeder food categories and preset seed blends."""

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
