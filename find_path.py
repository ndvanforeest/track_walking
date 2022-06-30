#!/usr/bin/env python
from collections import defaultdict
import sqlite3
import numpy as np
from sklearn.neighbors import KDTree
import networkx as nx
import folium

import common as c

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

start = hengelo_station
finish = goor_station
# finish = delden_station
# start = noorderplantsoen
# finish = midlaren

via = [vorden, babberich]
via = []
# via = [haren_roeiclub, midlaren]
# via = [haren_roeiclub]
A_to_B = [start] + via + [finish]


def get_containg_rectangle(path, eps=0.1):
    north = max(p[0] for p in path) + eps
    south = min(p[0] for p in path) - eps
    west = min(p[1] for p in path) - eps
    east = max(p[1] for p in path) + eps
    return north, west, south, east


def find_node_nearby_gps(point):
    north, west, south, east = get_containg_rectangle([point], eps=0.005)
    sql = (
        "SELECT node_from FROM compressed "
        "WHERE node_from IN "
        "(SELECT node_id FROM nodes "
        f"WHERE latitude BETWEEN {south} AND {north} "
        f"AND longitude BETWEEN {west} AND {east}) "
    )
    cur.execute(sql)
    nearby = ",".join(str(n[0]) for n in cur.fetchall())
    sql = (
        "SELECT node_id, latitude, longitude FROM nodes "
        f"WHERE node_id IN ({nearby});"
    )
    cur.execute(sql)
    res = np.array([[n[0], n[1], n[2]] for n in cur.fetchall()])
    tree = KDTree(res[:, [1, 2]])
    p = np.array(point).reshape(1, -1)  # reshape required
    dist, ind = tree.query(p, k=1)
    return int(res[ind][0][0][0])  # lots of unpacking


def get_shortest_path():
    north, west, south, east = get_containg_rectangle(A_to_B)

    sql = (
        "SELECT  node_from, node_to, cost "
        "FROM compressed "
        "WHERE node_from IN "
        "(SELECT node_id FROM nodes "
        f"WHERE latitude BETWEEN {south} AND {north} "
        f"AND longitude BETWEEN {west} AND {east}); "
    )
    cur.execute(sql)
    C = nx.Graph()  # compressed graph
    for e in cur.fetchall():
        node_from, node_to, cost = e
        C.add_edge(node_from, node_to, cost=cost)

    path = [find_node_nearby_gps(p) for p in A_to_B]
    best = []
    for p, q in zip(path[:-1], path[1:]):
        best += nx.shortest_path(C, p, q, weight="cost")
    return C.subgraph(best), best


def re_engineer_path(B, path):
    north, west, south, east = get_containg_rectangle(A_to_B)

    trunk_tags = ",".join(str(t) for t in c.trunk_tags)
    sql = (
        "SELECT  node_from, node_to, length, cost, tag "
        "FROM highways "
        f"WHERE tag NOT IN ({trunk_tags}) "
        "AND node_from IN "
        "(SELECT node_id FROM nodes "
        f"WHERE latitude BETWEEN {south} AND {north} "
        f"AND longitude BETWEEN {west} AND {east}); "
    )
    cur.execute(sql)
    G = nx.Graph()
    for e in cur.fetchall():
        node_from, node_to, length, cost, tag = e
        G.add_edge(node_from, node_to, cost=cost, tag=tag, length=length)

    longer_path = []
    for p, q in zip(path[:-1], path[1:]):  # B.edges():
        longer_path += nx.shortest_path(G, p, q, weight="cost")
    return G.subgraph(longer_path), longer_path


def plot_path(G, fname):
    res = ",".join(str(n) for n in G.nodes())
    cur.execute(
        f'SELECT node_id, latitude, longitude FROM nodes WHERE node_id in ({res});'
    )
    nodes = {ID: (la, lo) for ID, la, lo in cur.fetchall()}

    # location for the map
    mean_lat = sum(v[0] for v in nodes.values()) / len(nodes)
    mean_lon = sum(v[1] for v in nodes.values()) / len(nodes)
    zoom = 12
    myMap = folium.Map(location=[mean_lat, mean_lon], zoom_start=zoom)

    colors = {
        i: c.tag_to_color[t]
        for i, t in enumerate(c.tags)
        if t in c.tag_to_color
    }
    for m, n, data in G.edges(data=True):
        p, q = nodes[m], nodes[n]
        color = colors[data["tag"]]
        folium.PolyLine([p, q], color=color, weight=3.5, opacity=1).add_to(
            myMap
        )
    myMap.save(fname)


def print_path_stats(G):
    dist = defaultdict(float)
    for m, n, data in G.edges(data=True):
        dist[data["tag"]] += data["length"]

    colors = {
        i: c.tag_to_color[t]
        for i, t in enumerate(c.tags)
        if t in c.tag_to_color
    }
    tot = sum(v for v in dist.values())
    for k, v in sorted(dist.items(), key=lambda x: -x[1]):
        v /= tot
        v = round(100 * v)
        if v > 0:
            print(f"{c.tags[k]:<13}{colors[k]:<10}{v:2d}%")

    tot = round(tot / 1000)
    print(f"total lenght: {tot} km")


def write_path_to_gpx(path, fname):
    res = ",".join(str(n) for n in path)
    cur.execute(
        f'SELECT node_id, latitude, longitude FROM nodes WHERE node_id in ({res});'
    )
    nodes = {ID: (la, lo) for ID, la, lo in cur.fetchall()}

    import gpxpy

    gpx = gpxpy.gpx.GPX()

    # Create first track in our GPX:
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)

    # Create first segment in our GPX track:
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    for n in path:
        p = nodes[n]
        gpx_segment.points.append(
            gpxpy.gpx.GPXTrackPoint(p[0], p[1])  # , elevation=1234)
        )
    with open(fname, "w") as fp:
        fp.write(gpx.to_xml())


def write_path_to_kml(path=[], fname=""):
    import simplekml

    res = ",".join(str(n) for n in path)
    cur.execute(
        f'SELECT node_id, latitude, longitude FROM nodes WHERE node_id in ({res});'
    )
    nodes = {ID: (la, lo) for ID, la, lo in cur.fetchall()}

    path_nodes = []
    for n in path:
        p = nodes[n]
        path_nodes.append((p[1], p[0]))  # lon, lat

    kml = simplekml.Kml()
    ls = kml.newlinestring(name='My walk')
    ls.description = "pieter zand pad app"
    ls.coords = path_nodes
    ls.style.linestyle.width = 5
    ls.style.linestyle.color = simplekml.Color.blue
    kml.save("my_walk.kml")


def main():
    B, path = get_shortest_path()
    B, path = re_engineer_path(B, path)
    plot_path(B, fname="map.html")
    print_path_stats(B)
    # write_path_to_gpx(path, fname="mypath.gpx")
    write_path_to_kml(path, fname="mypath.kml")


if __name__ == '__main__':
    conn = sqlite3.connect(c.db_name)
    cur = conn.cursor()
    main()
    conn.close()
