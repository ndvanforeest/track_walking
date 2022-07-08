#!/usr/bin/env python
from math import sqrt, cos, pi
import numpy as np
from sklearn.neighbors import KDTree
import osmium
import networkx as nx

import common
from database import DB

from pytictoc import TicToc

t = TicToc()


class Highway_Handler(osmium.SimpleHandler):
    # A highway is a sequence of nodes with a tag to indicate the type of highway.
    def __init__(self):
        osmium.SimpleHandler.__init__(self)
        self.highways = []
        self.tag_str_to_idx = {
            tag_str: i for i, tag_str in enumerate(common.tags)
        }

    def way(self, w):
        tag = w.tags.get("highway")
        if tag in self.tag_str_to_idx:
            s = [w.nodes[i].ref for i in range(len(w.nodes))] + [
                self.tag_str_to_idx[tag]
            ]
            self.highways.append(s)


def read_write_highway_data(fname, db):
    t.tic()
    h = Highway_Handler()
    h.apply_file(fname)
    print("reading done")
    t.toc()

    # Remove all highway nodes that are not connected
    # to the largest component of the highway graph
    # because such nodes can never appear in any sensible route.
    G = nx.Graph()
    for e in h.highways:
        G.add_edges_from(zip(e[:-2], e[1:-1]), tag=e[-1])
    largest = max(nx.connected_components(G), key=len)
    G.remove_nodes_from(G.nodes() - largest)
    print("largest component found")
    t.toc()

    in_nodes, out_nodes, tags = [], [], []
    for e in G.edges:
        in_nodes.append(e[0])
        out_nodes.append(e[1])
        tags.append(G.get_edge_data(*e)['tag'])
    db.add_edges(in_nodes, out_nodes, tags)
    print("writing done")
    t.toc()


class Node_Handler(osmium.SimpleHandler):
    def __init__(self, highway_nodes):
        osmium.SimpleHandler.__init__(self)
        self.highway_nodes = highway_nodes
        self.nodes = []

    def node(self, n):
        if n.id in self.highway_nodes:
            self.nodes.append([n.id, n.location.lat, n.location.lon])


def read_write_node_coordinates(fname, db):
    # We only need the  coordinates of nodes that at either side of a highway edge.
    t.tic()
    highway_nodes = db.get_highway_nodes()
    print("got nodes of edges")
    t.toc()

    nodes = Node_Handler(highway_nodes)
    nodes.apply_file(fname)
    ID, lon, lat = [], [], []
    print("got node coordinates")
    t.toc()

    for n in nodes.nodes:
        ID.append(n[0])
        lat.append(n[1])
        lon.append(n[2])

    db.add_nodes(ID, lat, lon)
    print("node coordinates to db")
    t.toc()


def compute_edge_length(db):
    C = pi / 180
    R = 6378137  # earth radius is meters
    CR = C * R
    latitude_utrecht_domkerk = 52.09
    factor = cos(latitude_utrecht_domkerk * pi / 180) ** 2

    def haversine(lat1, lon1, lat2, lon2):
        # good approximation for nearby points in the Netherlands
        d2 = (lat1 - lat2) ** 2 + factor * (lon1 - lon2) ** 2
        return sqrt(d2) * CR

    t.tic()
    edges = db.get_edge_info("id", "node_from", "node_to", where="length<=0")
    if not edges:
        return
    nodes = db.get_node_info("node_id", "latitude", "longitude")
    node_info = {ID: (la, lo) for ID, la, lo in nodes}

    ids, lengths = [], []
    for e in edges:
        ID, node_from, node_to = e
        lat1, lon1 = node_info[node_from]
        lat2, lon2 = node_info[node_to]
        length = haversine(lat1, lon1, lat2, lon2)
        ids.append(ID)
        lengths.append(length)

    sql = "UPDATE edges SET length=? WHERE ID=?"
    db.update(sql, zip(lengths, ids))
    t.toc()


def set_tags_on_egdes(db, Type="trunk", tags={}, eps=0.005):
    X = np.array(db.get_tagged_coordinates(tags))
    tree = KDTree(X)
    # Load the nodes and mark nodes near to a trunk
    nodes = np.array(db.get_node_info("node_id", "latitude", "longitude"))
    hit = tree.query_radius(nodes[:, [1, 2]], r=eps, count_only=True)
    near_nodes = nodes[hit > 0][:, 0].astype(int)
    ones = [1] * len(near_nodes)
    sql = f"UPDATE edges SET near_{Type}=? WHERE node_from=?"
    db.update(sql, zip(ones, near_nodes.tolist()))


def tag_ugly_edges(db):
    # Avoid walking in the neighborhood of trunks and primary highways
    # eps = 0.005  is about 500 meters from a trunk
    set_tags_on_egdes(db, "trunk", common.trunk_tags, eps=0.001)

    # stay clear about 20 meters from secondary
    set_tags_on_egdes(db, "primary", common.primary_tags, eps=0.0002)


def reset_tags_and_cost(db):
    sql = f"UPDATE edges SET near_trunk=0, near_primary=0, cost=0"
    db.execute(sql)
    db.commit()


def compute_edge_cost(db):
    tag_to_idx = {tag_str: i for i, tag_str in enumerate(common.tags)}
    factor = {
        tag_to_idx[t]: common.cost_factor[t]
        for t in tag_to_idx
        if t not in common.trunks
    }
    trunk_tags = ",".join(str(t) for t in common.trunk_tags)
    sql = (
        "SELECT id, tag, length, near_trunk, near_primary "
        "FROM edges "
        f"WHERE tag NOT IN ({trunk_tags});"
    )
    IDs, costs = [], []
    for e in db.execute(sql):
        ID, tag, length, near_trunk, near_primary = e
        cost = length * factor[tag]
        if near_trunk:
            cost *= common.near_trunk_cost
        elif near_primary:
            cost *= common.near_primary_cost
        IDs.append(ID)
        costs.append(cost)
    sql = 'UPDATE edges SET cost=? WHERE id=?'
    db.update(sql, zip(costs, IDs))


def basic_setup(db):
    for province in common.provinces:
        fname = common.data_dir + province + "-latest.osm.pbf"
        print(fname)
        read_write_highway_data(fname, db)
        read_write_node_coordinates(fname, db)
    compute_edge_length(db)


def compute_cost(db):
    reset_tags_and_cost(db)
    tag_ugly_edges(db)
    compute_edge_cost(db)


def main():
    db = DB()

    build_new_database_p = False
    if build_new_database_p:
        db.rebuild()

    fill_database_with_new_info_p = False
    if fill_database_with_new_info_p:
        basic_setup(db)

    compute_cost(db)

    db.close_connection()


if __name__ == '__main__':
    main()
