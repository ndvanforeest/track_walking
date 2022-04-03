import sqlite3
import osmium
import networkx as nx

import common as c


def drop_table():
    cur.execute('''DROP TABLE nodes;''')
    conn.commit()


def make_table():
    sql = (
        "CREATE TABLE nodes "
        "(id INTEGER PRIMARY KEY, "
        "node_id int, "
        "latitude float, "
        "longitude float, "
        "UNIQUE(node_id));"
    )
    cur.execute(sql)
    conn.commit()


class Node_Handler(osmium.SimpleHandler):
    def __init__(self, nodes):
        osmium.SimpleHandler.__init__(self)
        self.nodes = nodes
        self.output = []

    def node(self, n):
        if n.id in self.nodes:
            self.output.append([n.id, n.location.lat, n.location.lon])


def read_write_node_coordinates(fname):
    # We only need the  coordinates of nodes that at either side of a highway edge.
    cur.execute('SELECT node_to FROM highways')
    nodes = set(n[0] for n in cur.fetchall())
    cur.execute('SELECT node_from FROM highways')
    nodes.update(set(n[0] for n in cur.fetchall()))

    nodes = Node_Handler(nodes)
    nodes.apply_file(fname)

    for n in nodes.output:
        sql = (
            "INSERT OR IGNORE INTO nodes "
            " (node_id, latitude, longitude)"
            f" VALUES ({n[0]}, {n[1]}, {n[2]})"
        )
        cur.execute(sql)
    conn.commit()


def main():
    try:
        drop_table()
    except Exception as e:
        print("ERROR : " + str(e))
        print("Cannot drop table")
    try:
        make_table()
    except Exception as e:
        print("ERROR : " + str(e))
        print("Cannot make table")

    for province in c.provinces:
        fname = c.data_dir + province + "-latest.osm.pbf"
        print(fname)
        read_write_node_coordinates(fname)


if __name__ == '__main__':
    conn = sqlite3.connect(c.db_name)
    cur = conn.cursor()
    main()
    conn.close()
