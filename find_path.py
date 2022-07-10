#!/usr/bin/env python
from collections import defaultdict
import numpy as np
from sklearn.neighbors import KDTree
import networkx as nx
import folium

from database import DB
import common

noorderplantsoen = 53.22448, 6.55563
haren_roeiclub = 53.17997, 6.57565
oranje_kanaal = 52.8416, 6.7428
boven_balloerveld = 53.0392, 6.6446
in_balloerveld = 53.0024, 6.6423
onder_balloerveld = 52.9906, 6.6528
balloo = 52.9959, 6.6315
midlaren = 53.1061, 6.6737
vriezeveen = 52.4131, 6.6284
vorden = 52.1038, 6.3126
babberich = 51.9061, 6.1143
pieterberg = 50.8265, 5.6869
almelo_van_der_valk = 52.35611, 6.66668
hengelo_station = 52.26227, 6.79504
delden_station = 52.2603, 6.71479
almelo_de_riet = 52.3407, 6.6783
goor_station = 52.23054, 6.58517
noordlaarderbos = 53.1007, 6.6576
tynaarlo_noord = 53.0787, 6.6204
noordlaarderbos_midden = 53.1073, 6.6435
westlaren_weg = 53.09177, 6.66185
westlaren_coop = 53.0861, 6.6678
okkerveen = 53.10346, 6.6291

walk_1 = [
    tynaarlo_noord,
    okkerveen,
    noordlaarderbos_midden,
    noordlaarderbos,
    westlaren_weg,
]
A_to_B = walk_1

roderwolde = 53.1678, 6.4690
zanddijk = 53.16590, 6.49986
eelderwolde = 53.1729, 6.5471
madijk = 53.16450, 6.54072
peizerwolde_albert_heijn = 53.14709, 6.56690
voetpad = 53.14446, 6.53776
walk_2 = [zanddijk, madijk, peizerwolde_albert_heijn, voetpad, zanddijk]

A_to_B = walk_2


# A_to_B = [start] + via + [finish]


def get_containg_rectangle(path, eps=0.1):
    north = max(p[0] for p in path) + eps
    south = min(p[0] for p in path) - eps
    west = min(p[1] for p in path) - eps
    east = max(p[1] for p in path) + eps
    return north, west, south, east


def find_node_nearby_gps(db, point):
    north, west, south, east = get_containg_rectangle([point], eps=0.05)
    sql = (
        "SELECT node_from FROM edges "
        "WHERE node_from IN "
        "(SELECT node_id FROM nodes "
        f"WHERE latitude BETWEEN {south} AND {north} "
        f"AND longitude BETWEEN {west} AND {east}) "
    )
    nearby = ",".join(str(n[0]) for n in db.execute(sql))
    sql = (
        "SELECT node_id, latitude, longitude FROM nodes "
        f"WHERE node_id IN ({nearby});"
    )
    res = np.array([[n[0], n[1], n[2]] for n in db.execute(sql)])
    tree = KDTree(res[:, [1, 2]])
    p = np.array(point).reshape(1, -1)  # reshape required
    dist, ind = tree.query(p, k=1)
    return int(res[ind][0][0][0])  # lots of unpacking


def get_shortest_path(db):
    north, west, south, east = get_containg_rectangle(A_to_B)

    G = nx.Graph()
    trunk_tags = ",".join(str(t) for t in common.trunk_tags)
    sql = (
        "SELECT  node_from, node_to, length, cost, tag, near_trunk, near_primary "
        "FROM edges "
        f"WHERE tag NOT IN ({trunk_tags}) "
        "AND node_from IN "
        "(SELECT node_id FROM nodes "
        f"WHERE latitude BETWEEN {south} AND {north} "
        f"AND longitude BETWEEN {west} AND {east}); "
    )
    for e in db.execute(sql):
        node_from, node_to, length, cost, tag, near_trunk, near_primary = e
        G.add_edge(
            node_from,
            node_to,
            cost=cost,
            tag=tag,
            length=length,
            near_trunk=near_trunk,
            near_primary=near_primary,
        )

    path = [find_node_nearby_gps(db, p) for p in A_to_B]
    best = []
    for p, q in zip(path[:-1], path[1:]):
        best += nx.shortest_path(G, p, q, weight="cost")
    return G.subgraph(best), best


def get_node_info_for_graph(db, nodes):
    res = ",".join(str(n) for n in nodes)
    sql = f'SELECT node_id, latitude, longitude FROM nodes WHERE node_id in ({res});'
    return {ID: (la, lo) for ID, la, lo in db.execute(sql)}


def plot_path(db, G, fname):
    nodes = get_node_info_for_graph(db, G.nodes())

    # location for the map
    mean_lat = sum(v[0] for v in nodes.values()) / len(nodes)
    mean_lon = sum(v[1] for v in nodes.values()) / len(nodes)
    zoom = 13
    myMap = folium.Map(location=[mean_lat, mean_lon], zoom_start=zoom)

    colors = {
        i: common.tag_to_color[t]
        for i, t in enumerate(common.tags)
        if t in common.tag_to_color
    }
    for m, n, data in G.edges(data=True):
        p, q = nodes[m], nodes[n]
        color = colors[data["tag"]]
        folium.PolyLine([p, q], color=color, weight=3.5, opacity=1).add_to(
            myMap
        )
    myMap.save(fname)


def print_path_stats(G):
    if not G:
        print("The graph is empty")
        quit()
    length = defaultdict(float)
    for m, n, data in G.edges(data=True):
        length[data["tag"]] += data["length"]
    tot_length = sum(length.values())

    cost = defaultdict(float)
    for m, n, data in G.edges(data=True):
        cost[data["tag"]] += data["cost"]
    tot_cost = sum(cost.values())

    colors = {
        i: common.tag_to_color[t]
        for i, t in enumerate(common.tags)
        if t in common.tag_to_color
    }

    for k, v in sorted(length.items(), key=lambda x: -x[1]):
        perc = round(100 * v / tot_length)
        Cost = round(100 * cost[k] / max(tot_cost, 1))
        if v > 0:
            print(
                f"{common.tags[k]:<13}{colors[k]:<10}{int(v):>4d}{perc:>4d}%{int(cost[k]):>7}{Cost:>4d}%"
            )

    print(
        f"total lenght: {int(tot_length):<6d} m, total cost: {int(tot_cost):<5d}"
    )
    primary = sum(
        data["length"]
        for m, n, data in G.edges(data=True)
        if data["near_primary"] == 1
    )
    print(f"Near primary: {int(primary)}")
    trunk = sum(
        data["length"]
        for m, n, data in G.edges(data=True)
        if data["near_trunk"] == 1
    )
    print(f"Near trunk: {int(trunk)}")


def write_path_to_gpx(db, path, fname):
    import gpxpy

    gpx = gpxpy.gpx.GPX()

    # Create first track in our GPX:
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)

    # Create first segment in our GPX track:
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    nodes = get_node_info_for_graph(db, path)
    for n in path:
        p = nodes[n]
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(p[0], p[1]))
    with open(fname, "w") as fp:
        fp.write(gpx.to_xml())


def write_path_to_kml(db, path=[], fname="my_walk.kml"):
    import simplekml

    nodes = get_node_info_for_graph(db, path)
    # longitute, latitute -> latitude, longitude
    la_lo_path = [[nodes[n][1], nodes[n][0]] for n in path]

    kml = simplekml.Kml()
    ls = kml.newlinestring(name='My walk')
    ls.description = "pieter zand pad app"
    ls.coords = la_lo_path
    ls.style.linestyle.width = 3
    ls.style.linestyle.color = simplekml.Color.blue
    kml.save(fname)


def main():
    db = DB()
    B, path = get_shortest_path(db)
    plot_path(db, B, fname="map.html")
    print_path_stats(B)
    # write_path_to_gpx(db, path, fname="mypath.gpx")
    write_path_to_kml(db, path, fname="my_walk.kml")

    db.close_connection()


if __name__ == '__main__':
    main()
