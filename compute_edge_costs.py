#!/usr/bin/env python
import sqlite3
import numpy as np
from sklearn.neighbors import KDTree

import common as c


def compute_near_trunk():
    trunk_tags = ",".join(str(t) for t in c.trunk_tags)
    sql = (
        "SELECT latitude, longitude "
        "FROM nodes "
        "WHERE node_id IN "
        "(SELECT  node_from "
        "FROM edges "
        f"WHERE tag IN ({trunk_tags}));"
    )
    cur.execute(sql)
    X = np.array(cur.fetchall())
    tree = KDTree(X)
    # Load the nodes and mark nodes near to a trunk
    cur.execute('SELECT node_id, latitude, longitude FROM nodes')
    nodes = np.array(cur.fetchall())  # , dtype=(int, float, float))
    eps = 0.005  # about 500 meters from a trunk
    hit = tree.query_radius(nodes[:, [1, 2]], r=eps, count_only=True)
    near_to_trunk = nodes[hit > 0]
    for node_id in near_to_trunk[:, 0]:
        sql = f"UPDATE edges SET near_trunk = 1 WHERE node_from = {node_id}"
        cur.execute(sql)
    conn.commit()


def compute_edge_cost():
    tag_to_idx = {tag_str: i for i, tag_str in enumerate(c.tags)}
    factor = {
        tag_to_idx[t]: c.cost_factor[t] for t in tag_to_idx if t not in c.trunks
    }
    trunk_tags = ",".join(str(t) for t in c.trunk_tags)
    sql = (
        "SELECT id, node_from, tag, length, near_trunk "
        "FROM edges "
        f"WHERE tag NOT IN ({trunk_tags});"
    )
    cur.execute(sql)
    for e in cur.fetchall():
        ID, node_from, tag, length, near_trunk = e
        cost = length * factor[tag]
        cost *= c.near_trunk_cost if near_trunk else 1
        cur.execute(f'UPDATE edges SET cost = {cost} WHERE ID = {ID}')
    conn.commit()


def main():
    compute_near_trunk()
    compute_edge_cost()


if __name__ == '__main__':
    conn = sqlite3.connect(c.db_name)
    cur = conn.cursor()
    main()
    conn.close()
