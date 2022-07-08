data_dir = "/home/nicky/tmp/"
db_name = data_dir + "nodes_and_edges.db"

provinces = [
    "groningen",
    "drenthe",
    "overijssel",
    "gelderland",
    "limburg",
    # "flevoland",
    # "friesland",
    # "noord-holland",
    # "utrecht",
]

provinces = [
    "drenthe",
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
    "motorway",
    "motorway_link",
    "motorway_junction",
    "trunk",
    "trunk_link",
}

primary = {
    "primary",
    "primary_link",
}

edge_tags = {t: i for i, t in enumerate(tags)}
trunk_tags = set(edge_tags[t] for t in trunks)
primary_tags = set(edge_tags[t] for t in primary)

near_trunk_cost = 3
near_primary_cost = 20

cost_factor = {
    'steps': 1,
    'track': 1,
    'path': 1,
    'bridleway': 1,
    'footway': 1,
    'cycleway': 1.5,
    'residential': 1.2,
    'unclassified': 1.5,
    'living_street': 2,
    'pedestrian': 1.2,
    'tertiary': 2,
    'tertiary_link': 2,
    'secondary': 3,
    'secondary_link': 3,
    'primary': 100,
    'primary_link': 100,
    'service': 2,
}


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
    'primary': "red",
    'primary_link': "red",
    'service': "black",
}
