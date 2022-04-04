data_dir = "/home/nicky/tmp/"
db_name = data_dir + "nodes_and_edges.db"

provinces = [
    "groningen",
    "drenthe",
    "overijssel",
    # "flevoland",
    # "friesland",
    "gelderland",
    "limburg",
    # "noord-holland",
    # "utrecht",
]

tags = [
    'track',
    'footway',
    'path',
    'cycleway',
    'living_street',
    'pedestrian',
    'bridleway',
    'residential',
    'steps',
    'service',
    'unclassified',
    'tertiary',
    'tertiary_link',
    'secondary',
    'secondary_link',
    "primary",
    "primary_link",
    "motorway",
    "motorway_link",
    "motorway_junction",
    "trunk",
    "trunk_link",
]

trunks = {
    "primary",
    "primary_link",
    "motorway",
    "motorway_link",
    "motorway_junction",
    "trunk",
    "trunk_link",
}

edge_tags = {t: i for i, t in enumerate(tags)}
trunk_tags = set(edge_tags[t] for t in trunks)

factor = 2
cost_factor = {
    'steps': 1,
    'track': 1,
    'path': 1.2,
    'bridleway': factor,
    'footway': factor,
    'cycleway': 1.5 * factor,
    'residential': 1.3 * factor,
    'unclassified': 1.2 * factor,
    'living_street': 1.2 * factor,
    'pedestrian': 1.2 * factor,
    'tertiary': 1.5 * factor,
    'tertiary_link': 1.5 * factor,
    'secondary': 1.5 * factor,
    'secondary_link': 1.5 * factor,
    'primary': 2 * factor,
    'primary_link': 2 * factor,
    'service': 2 * factor,
}

near_trunk_cost = 3

tag_to_color = {
    'path': "black",
    'steps': "green",
    'track': "green",
    'bridleway': "black",
    'footway': "blue",
    'cycleway': "purple",
    'living_street': "purple",
    'pedestrian': "yellow",
    'unclassified': "yellow",
    'residential': "yellow",
    'tertiary': "orange",
    'tertiary_link': "orange",
    'secondary': "red",
    'secondary_link': "red",
    'service': "black",
}
