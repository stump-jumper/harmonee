/**
 * Map layer definitions, habitat object types, feeder food catalogs, and paint brush classes.
 */

export function createInitialMapLayers() {
  return [
    {
      id: 'satellite-base',
      name: 'Satellite Imagery',
      type: 'base',
      visible: true,
      toggleable: false,
      color: '#6ee7b7',
      mapLayerIds: ['satellite-layer'],
    },
    {
      id: 'property-boundary',
      name: 'Property Boundary',
      type: 'overlay',
      visible: true,
      toggleable: true,
      color: '#f2cc8f',
      mapLayerIds: ['parcel-boundary-fill', 'parcel-boundary-outline'],
    },
    {
      id: 'habitat-objects-layer',
      name: 'Habitat Objects',
      type: 'overlay',
      visible: true,
      toggleable: true,
      color: '#f59e0b',
      mapLayerIds: [],
    },
    {
      id: 'ebird-sightings-layer',
      name: 'eBird Sightings (1.0 mi)',
      type: 'overlay',
      visible: false,
      toggleable: true,
      color: '#38bdf8',
      mapLayerIds: ['ebird-radius-fill', 'ebird-radius-outline'],
    },
  ]
}

export const HABITAT_OBJECT_TYPES = [
  {
    id: 'bird_feeder',
    name: 'Bird Feeder',
    icon: '🥣',
    color: '#f59e0b',
    description: 'Supplemental food source for seed, suet, or nectar eating birds',
    defaultVariant: 'Tube / Seed Feeder',
    variants: [
      'Tube / Seed Feeder',
      'Suet Cage Feeder',
      'Hummingbird / Nectar Feeder',
      'Hopper Feeder',
      'Platform / Tray Feeder',
      'Thistle / Finch Feeder',
    ],
  },
  {
    id: 'bird_house',
    name: 'Bird House / Nest Box',
    icon: '🏠',
    color: '#0284c7',
    description: 'Sheltered nesting site for cavity-nesting birds',
    defaultVariant: 'Bluebird Nest Box',
    variants: [
      'Bluebird Nest Box',
      'Chickadee / Titmouse Box',
      'Wren Box',
      'Screech Owl / Kestrel Box',
      'Swallow Box',
      'Custom Nest Box',
    ],
  },
  {
    id: 'bird_bath',
    name: 'Bird Bath / Water Basin',
    icon: '💧',
    color: '#06b6d4',
    description: 'Fresh clean water source for drinking, preening, and bathing',
    defaultVariant: 'Pedestal Bird Bath',
    variants: [
      'Pedestal Bird Bath',
      'Ground Water Basin',
      'Dripper / Mister Feature',
      'Solar Fountain Bird Bath',
      'Heated Winter Bird Bath',
    ],
  },
]

export function getObjectTypeDef(typeId) {
  return HABITAT_OBJECT_TYPES.find((t) => t.id === typeId) || HABITAT_OBJECT_TYPES[0]
}

export const FEEDER_FOOD_OPTIONS = [
  {
    id: 'sunflower_black_oil',
    label: 'Black-Oil Sunflower Seed',
    icon: '🌻',
    desc: 'High oil & fat content; top favorite of cardinals, chickadees, finches, and nuthatches',
  },
  {
    id: 'sunflower_striped',
    label: 'Striped Sunflower Seed',
    icon: '🌻',
    desc: 'Thicker hull; great for grosbeaks, blue jays, and woodpeckers',
  },
  {
    id: 'sunflower_chips',
    label: 'Sunflower Hearts / Chips (No Shell)',
    icon: '🌻',
    desc: 'No-waste, 100% edible energy accessible to both small and large songbirds',
  },
  {
    id: 'nyjer',
    label: 'Nyjer / Thistle Seed',
    icon: '🌾',
    desc: 'Tiny oil-rich seeds favorite of American goldfinches, siskins, and redpolls',
  },
  {
    id: 'suet',
    label: 'Suet / Suet Cakes',
    icon: '🥩',
    desc: 'Rendered calorie-dense fat cakes; loved by woodpeckers, nuthatches, and wrens',
  },
  {
    id: 'nectar',
    label: 'Sugar Water / Nectar',
    icon: '🌺',
    desc: 'Boiled 4:1 water-to-sugar nectar for hummingbirds and orioles',
  },
  {
    id: 'peanuts_shelled',
    label: 'Peanuts (Shelled / Halves)',
    icon: '🥜',
    desc: 'High-fat protein nuts; beloved by jays, titmice, nuthatches, and woodpeckers',
  },
  {
    id: 'peanuts_in_shell',
    label: 'Peanuts in Shell',
    icon: '🥜',
    desc: 'Whole in-shell nuts; entertaining for jays, crows, and red-bellied woodpeckers',
  },
  {
    id: 'safflower',
    label: 'Safflower Seed',
    icon: '🌱',
    desc: 'Bitter-tasting white seed squirrels and blackbirds dislike; eaten by cardinals and chickadees',
  },
  {
    id: 'mealworms',
    label: 'Mealworms (Dried or Live)',
    icon: '🐛',
    desc: 'High-protein insect treat for bluebirds, wrens, robins, and kinglets',
  },
  {
    id: 'fruit_jelly',
    label: 'Fruit (Oranges/Apples) & Grape Jelly',
    icon: '🍊',
    desc: 'Sweet nectar substitutes for Baltimore orioles, catbirds, and tanagers',
  },
  {
    id: 'millet_white',
    label: 'White Proso Millet',
    icon: '🌾',
    desc: 'Favorite ground-feeding seed for juncos, native sparrows, and mourning doves',
  },
  {
    id: 'cracked_corn',
    label: 'Cracked Corn',
    icon: '🌽',
    desc: 'Hearty grain for mourning doves, towhees, and native ground sparrows',
  },
]

export function getFoodOption(id) {
  return FEEDER_FOOD_OPTIONS.find((f) => f.id === id) || { id, label: id, icon: '🥣', desc: '' }
}

export const BRUSH_CLASSES = [
  { id: 'tree_canopy', name: 'Tree Canopy', color: '#15803d', icon: '🌳' },
  { id: 'low_vegetation', name: 'Low Vegetation', color: '#4ade80', icon: '🌱' },
  { id: 'impervious_surfaces', name: 'Impervious Surfaces', color: '#94a3af', icon: '🏠' },
  { id: 'water', name: 'Water', color: '#38bdf8', icon: '💧' },
  { id: 'barren', name: 'Barren', color: '#d97706', icon: '🏜️' },
]

export const BRUSH_SIZES_METERS = [
  { label: 'S (3m)', value: 3.0 },
  { label: 'M (6m)', value: 6.0 },
  { label: 'L (12m)', value: 12.0 },
]
