#!/usr/bin/env python
from math import sqrt, cos, pi
import sqlite3
import numpy as np

import common as c


C = pi / 180
R = 6378137  # earth radius is meters
CR = C * R
latitude_utrecht_domkerk = 52.09
factor = cos(pi * latitude_utrecht_domkerk / 180) ** 2


def haversine(lat1, lon1, lat2, lon2):  # good approximation for nearby points
    d2 = (lat1 - lat2) ** 2 + (lon1 - lon2) ** 2 * factor
    return sqrt(d2) * CR


def compute_edge_length():
    # we only need the  coordinates of highway nodes
    cur.execute('SELECT node_id, latitude, longitude FROM nodes')
    nodes = {ID: (la, lo) for ID, la, lo in cur.fetchall()}

    cur.execute('SELECT id, node_from, node_to FROM edges')
    for e in cur.fetchall():
        ID, node_from, node_to = e
        lat1, lon1 = nodes[node_from]
        lat2, lon2 = nodes[node_to]
        length = haversine(lat1, lon1, lat2, lon2)
        cur.execute(f'UPDATE edges SET length = {length} WHERE ID = {ID}')
    conn.commit()


def main():
    compute_edge_length()


if __name__ == '__main__':
    conn = sqlite3.connect(c.db_name)
    cur = conn.cursor()
    main()
    conn.close()
