#!/usr/bin/env python
from collections import defaultdict
from functools import cache
from itertools import chain
import numpy as np
import os.path
from sklearn.neighbors import KDTree
import networkx as nx
import folium
import simplekml
from pytictoc import TicToc

from database import DB
import common
from my_walks import A_to_B

t = TicToc()


class Coordinates:
    def __init__(self, db):
        self._coordinates = {}
        self.db = db

    @classmethod
    def get_containing_rectangle(self, path, eps=0.1):
        north = max(p[0] for p in path) + eps
        south = min(p[0] for p in path) - eps
        west = min(p[1] for p in path) - eps
        east = max(p[1] for p in path) + eps
        return north, west, south, east

    def coordinate(self, node):
        return self._coordinates[node]

    def update(self, nodes):
        to_update = set(n for n in nodes if n not in self._coordinates)
        res = ",".join(str(n) for n in to_update)
        sql = f'SELECT node_id, latitude, longitude FROM nodes WHERE node_id in ({res});'
        self._coordinates.update(
            {ID: (la, lo) for ID, la, lo in self.db.execute(sql)}
        )

    def find_node_nearby_gps(self, point):
        north, west, south, east = self.get_containing_rectangle(
            [point], eps=0.05
        )
        sql = (
            "SELECT node_from FROM edges "
            "WHERE node_from IN "
            "(SELECT node_id FROM nodes "
            f"WHERE latitude BETWEEN {south} AND {north} "
            f"AND longitude BETWEEN {west} AND {east}) "
        )
        nodes = [n[0] for n in self.db.execute(sql)]
        self.update(nodes)
        res = np.array([[n, *self.coordinate(n)] for n in nodes])
        tree = KDTree(res[:, [1, 2]])
        p = np.array(point).reshape(1, -1)  # reshape required
        dist, ind = tree.query(p, k=1)
        return int(res[ind][0][0][0])  # lots of unpacking


class Segment:
    def __init__(self, m, n, G):
        self._nodes = [m, n]
        self.G = G
        self.tag = self.G[m][n]["tag"]

    def nodes(self):
        return self._nodes

    def last_node(self):
        return self._nodes[-1]

    def append_node(self, n):
        self._nodes.append(n)

    @cache
    def length(self, condition=""):
        length = 0
        for m, n in zip(self._nodes[:-1], self._nodes[1:]):
            if condition == "" or self.G[m][n][condition]:
                length += self.G[m][n]["length"]
        return length

    @cache
    def cost(self):
        cost = 0
        for m, n in zip(self._nodes[:-1], self._nodes[1:]):
            cost += self.G[m][n]["cost"]
        return cost

    @cache
    def near_trunk(self):
        return self.length("near_trunk")

    @cache
    def near_primary(self):
        return self.length("near_primary")

    def color(self):
        return common.tag_color[self.tag]


class Path:
    def __init__(self, db, coordinates):
        self.db = db
        self.coordinates = coordinates
        self._segments = []
        self.G = nx.Graph()

    def append(self, segment):
        self._segments.append(segment)

    @cache
    def length(self):
        return sum(s.length() for s in self._segments)

    @cache
    def cost(self):
        return sum(s.cost() for s in self._segments)

    @cache
    def near_trunk(self):
        return sum(s.near_trunk() for s in self._segments)

    @cache
    def near_primary(self):
        return sum(s.near_primary() for s in self._segments)

    @cache
    def nodes(self):
        return list(chain.from_iterable(s.nodes() for s in self._segments))

    def segments(self):
        return self._segments

    def get_graph_data(self):
        north, west, south, east = self.coordinates.get_containing_rectangle(
            A_to_B.coordinates
        )

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
        data = []
        for e in self.db.execute(sql):
            node_from, node_to, length, cost, tag, near_trunk, near_primary = e
            d = {
                "length": length,
                "cost": cost,
                "tag": tag,
                "near_trunk": near_trunk,
                "near_primary": near_primary,
            }
            data.append([node_from, node_to, d])
        self.G.add_edges_from(data)

    def compute_shortest_path(self):
        self.get_graph_data()
        if A_to_B.node_ids:
            route = A_to_B.node_ids
        else:
            route = [
                self.coordinates.find_node_nearby_gps(p)
                for p in A_to_B.coordinates
            ]
            print(f"Node ids of path sketch: {route}")
        best = []
        for p, q in zip(route[:-1], route[1:]):
            best += nx.shortest_path(self.G, p, q, weight="cost")[:-1]
        # :-1 because end points are the same
        best.append(route[-1])

        segment = Segment(best[0], best[1], self.G)
        self.append(segment)
        for n in best[2:]:
            tag = self.G[segment.last_node()][n]["tag"]
            if tag == segment.tag:
                segment.append_node(n)
            else:
                segment = Segment(segment.last_node(), n, self.G)
                self.append(segment)

    def plot(self):
        self.coordinates.update(self.nodes())

        res = np.array([self.coordinates.coordinate(n) for n in self.nodes()])
        mean_lat, mean_lon = res.mean(axis=0)
        zoom = 12
        myMap = folium.Map(location=[mean_lat, mean_lon], zoom_start=zoom)

        for segment in self._segments:
            folium.PolyLine(
                [self.coordinates.coordinate(n) for n in segment.nodes()],
                color=segment.color(),
                weight=3.5,
                opacity=1,
            ).add_to(myMap)
        myMap.save(A_to_B.name + ".html")

    def print_stats(self):
        length = defaultdict(float)
        for segment in self._segments:
            length[segment.tag] += segment.length()
        cost = defaultdict(float)
        for segment in self._segments:
            cost[segment.tag] += segment.cost()

        for k, v in sorted(length.items(), key=lambda x: -x[1]):
            perc = round(100 * v / self.length())
            # Cost = round(100 * cost[k] / max(self.cost(), 1))
            Cost = round(100 * cost[k] / self.cost())
            if v > 0:
                print(
                    f"{common.tags[k]:<13}{common.tag_color[k]:<10}{int(v):>4d}{perc:>4d}%{int(cost[k]):>7}{Cost:>4d}%"
                )

        print(
            f"total length: {int(self.length()):<6d} m, total cost: {int(self.cost()):<5d}"
        )
        print(f"Near primary: {int(self.near_primary())} m")
        print(f"Near trunk: {int(self.near_trunk())} m")

    def write_path_to_kml(self):
        kml_color_mapper = {
            "black": simplekml.Color.black,
            "blue": simplekml.Color.blue,
            "green": simplekml.Color.green,
            "purple": simplekml.Color.purple,
            "red": simplekml.Color.blue,
            "yellow": simplekml.Color.yellow,
            "orange": simplekml.Color.orange,
        }

        km_lenght = int(self.length() / 1000 + 0.5)  # round to km
        name = f"{A_to_B.name}_{km_lenght}"

        self.coordinates.update(self.nodes())
        kml = simplekml.Kml(name=A_to_B.name)
        for segment in self._segments:
            ls = kml.newlinestring()
            ls.coords = [
                [
                    self.coordinates.coordinate(n)[1],
                    self.coordinates.coordinate(n)[0],
                ]
                for n in segment.nodes()
            ]
            ls.style.linestyle.width = 3
            ls.style.linestyle.color = kml_color_mapper[segment.color()]

        kml.save(name + ".kml")


def write_path_to_gpx(db, path):
    "this needs to be updated"
    import gpxpy

    gpx = gpxpy.gpx.GPX()

    # Create first track in our GPX:
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)

    # Create first segment in our GPX track:
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    nodes = get_node_coordinates(db, path)
    for n in path:
        p = nodes[n]
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(p[0], p[1]))
    with open(A_to_B.name, "w") as fp:
        fp.write(gpx.to_xml())


def main():
    db = DB()
    coordinates = Coordinates(db)
    path = Path(db, coordinates)
    path.compute_shortest_path()
    path.plot()
    path.print_stats()
    path.write_path_to_kml()

    db.close_connection()


if __name__ == '__main__':
    main()
