"""Ecoregion-indexed Keystone Native Plant dataset.

Compiled from:
- Dr. Douglas Tallamy & Kimberley Shropshire (Univ. of Delaware / USFS) Lepidoptera Host-Plant Database
- National Wildlife Federation (NWF) Keystone Native Plants by Ecoregion
- USDA PLANTS & BONAP native flora distributions
"""

KEYSTONE_PLANT_DATASET = {
    "5": {  # Level I: 5 Northern Forests / 5.3 Atlantic Highlands (incl. 58h Reading Prong)
        "treesAndShrubs": [
            {
                "commonName": "Native Oaks",
                "genus": "Quercus",
                "exampleSpecies": "White Oak (Q. alba), Northern Red Oak (Q. rubra)",
                "lepidopteraCount": 445,
            },
            {
                "commonName": "Native Cherries & Plums",
                "genus": "Prunus",
                "exampleSpecies": "Black Cherry (P. serotina), Chokecherry (P. virginiana)",
                "lepidopteraCount": 409,
            },
            {
                "commonName": "Native Willows",
                "genus": "Salix",
                "exampleSpecies": "Black Willow (S. nigra), Pussy Willow (S. discolor)",
                "lepidopteraCount": 397,
            },
            {
                "commonName": "Native Birches",
                "genus": "Betula",
                "exampleSpecies": "Sweet Birch (B. lenta), Yellow Birch (B. alleghaniensis)",
                "lepidopteraCount": 385,
            },
            {
                "commonName": "Native Maples",
                "genus": "Acer",
                "exampleSpecies": "Sugar Maple (A. saccharum), Red Maple (A. rubrum)",
                "lepidopteraCount": 276,
            },
            {
                "commonName": "Native Blueberries",
                "genus": "Vaccinium",
                "exampleSpecies": "Highbush Blueberry (V. corymbosum), Lowbush Blueberry (V. angustifolium)",
                "lepidopteraCount": 258,
            },
        ],
        "flowersAndGrasses": [
            {
                "commonName": "Goldenrods",
                "genus": "Solidago",
                "exampleSpecies": "Wrinkleleaf Goldenrod (S. rugosa), Canada Goldenrod (S. canadensis)",
                "lepidopteraCount": 120,
            },
            {
                "commonName": "Native Asters",
                "genus": "Symphyotrichum",
                "exampleSpecies": "New England Aster (S. novae-angliae), Smooth Blue Aster (S. laeve)",
                "lepidopteraCount": 107,
            },
            {
                "commonName": "Woodland & Perennial Sunflowers",
                "genus": "Helianthus",
                "exampleSpecies": "Thinleaf Sunflower (H. decapetalus), Woodland Sunflower (H. divaricatus)",
                "lepidopteraCount": 58,
            },
            {
                "commonName": "Native Sedges",
                "genus": "Carex",
                "exampleSpecies": "Tussock Sedge (C. stricta), Pennsylvania Sedge (C. pensylvanica)",
                "lepidopteraCount": 36,
            },
            {
                "commonName": "Bluestem Grasses",
                "genus": "Schizachyrium",
                "exampleSpecies": "Little Bluestem (S. scoparium)",
                "lepidopteraCount": 28,
            },
        ],
    },
    "8": {  # Level I: 8 Eastern Temperate Forests (incl. 64 Piedmont & 67 Ridge and Valley)
        "treesAndShrubs": [
            {
                "commonName": "Native Oaks",
                "genus": "Quercus",
                "exampleSpecies": "White Oak (Q. alba), Pin Oak (Q. palustris), Red Oak (Q. rubra)",
                "lepidopteraCount": 534,
            },
            {
                "commonName": "Native Cherries & Plums",
                "genus": "Prunus",
                "exampleSpecies": "Black Cherry (P. serotina), American Plum (P. americana)",
                "lepidopteraCount": 456,
            },
            {
                "commonName": "Native Willows",
                "genus": "Salix",
                "exampleSpecies": "Black Willow (S. nigra), Silky Willow (S. sericea)",
                "lepidopteraCount": 355,
            },
            {
                "commonName": "Native Birches",
                "genus": "Betula",
                "exampleSpecies": "River Birch (B. nigra), Sweet Birch (B. lenta)",
                "lepidopteraCount": 332,
            },
            {
                "commonName": "Native Maples",
                "genus": "Acer",
                "exampleSpecies": "Red Maple (A. rubrum), Sugar Maple (A. saccharum)",
                "lepidopteraCount": 285,
            },
            {
                "commonName": "Native Blueberries",
                "genus": "Vaccinium",
                "exampleSpecies": "Highbush Blueberry (V. corymbosum), Deerberry (V. stamineum)",
                "lepidopteraCount": 248,
            },
        ],
        "flowersAndGrasses": [
            {
                "commonName": "Goldenrods",
                "genus": "Solidago",
                "exampleSpecies": "Showy Goldenrod (S. speciosa), Wrinkleleaf Goldenrod (S. rugosa)",
                "lepidopteraCount": 125,
            },
            {
                "commonName": "Native Asters",
                "genus": "Symphyotrichum",
                "exampleSpecies": "New England Aster (S. novae-angliae), Heart-leaved Aster (S. cordifolius)",
                "lepidopteraCount": 112,
            },
            {
                "commonName": "Perennial Sunflowers",
                "genus": "Helianthus",
                "exampleSpecies": "Woodland Sunflower (H. divaricatus), Thinleaf Sunflower (H. decapetalus)",
                "lepidopteraCount": 73,
            },
            {
                "commonName": "Joe-Pye Weeds & Bonesets",
                "genus": "Eutrochium",
                "exampleSpecies": "Hollow Joe-Pye Weed (E. fistulosum), Sweet Joe-Pye (E. purpureum)",
                "lepidopteraCount": 42,
            },
            {
                "commonName": "Native Sedges & Panicgrasses",
                "genus": "Carex",
                "exampleSpecies": "Tussock Sedge (C. stricta), Switchgrass (Panicum virgatum)",
                "lepidopteraCount": 36,
            },
        ],
    },
    "9": {  # Level I: 9 Great Plains
        "treesAndShrubs": [
            {
                "commonName": "Native Oaks",
                "genus": "Quercus",
                "exampleSpecies": "Bur Oak (Q. macrocarpa), Chinkapin Oak (Q. muehlenbergii)",
                "lepidopteraCount": 318,
            },
            {
                "commonName": "Native Willows",
                "genus": "Salix",
                "exampleSpecies": "Peachleaf Willow (S. amygdaloides), Sandbar Willow (S. exigua)",
                "lepidopteraCount": 296,
            },
            {
                "commonName": "Native Cherries & Plums",
                "genus": "Prunus",
                "exampleSpecies": "Chokecherry (P. virginiana), American Plum (P. americana)",
                "lepidopteraCount": 284,
            },
        ],
        "flowersAndGrasses": [
            {
                "commonName": "Perennial Sunflowers",
                "genus": "Helianthus",
                "exampleSpecies": "Maximilian Sunflower (H. maximiliani), Stiff Sunflower (H. pauciflorus)",
                "lepidopteraCount": 88,
            },
            {
                "commonName": "Goldenrods",
                "genus": "Solidago",
                "exampleSpecies": "Stiff Goldenrod (S. rigida), Missouri Goldenrod (S. missouriensis)",
                "lepidopteraCount": 82,
            },
            {
                "commonName": "Prairie Asters",
                "genus": "Symphyotrichum",
                "exampleSpecies": "Smooth Blue Aster (S. laeve), Heath Aster (S. ericoides)",
                "lepidopteraCount": 74,
            },
        ],
    },
}
