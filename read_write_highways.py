import sqlite3
import osmium
import networkx as nx

import common as c


def drop_table():
    cur.execute('''DROP TABLE highways;''')
    conn.commit()


def make_table():
    sql_command = """CREATE TABLE highways (
    id INTEGER PRIMARY KEY,
    node_from int,
    node_to int,
    tag int,
    length int default 0,
    near_trunk int default 0,
    cost int default 0,
    UNIQUE(node_from, node_to)
    );"""

    cur.execute(sql_command)
    conn.commit()


class Highway_Handler(osmium.SimpleHandler):
    # Read highway nodes from pbf file.
    # A highway is a sequence of nodes with a tag to indicate the type of highway.
    def __init__(self):
        osmium.SimpleHandler.__init__(self)
        self.highways = []
        self.tag_str_to_idx = {tag_str: i for i, tag_str in enumerate(c.tags)}

    def way(self, w):
        tag = w.tags.get("highway")
        if tag in self.tag_str_to_idx:
            s = [w.nodes[i].ref for i in range(len(w.nodes))] + [self.tag_str_to_idx[tag]]
            self.highways.append(s)


def read_write_highway_data(fname):
    h = Highway_Handler()
    h.apply_file(fname)
    print("reading done")

    # Remove all highway nodes that are not connected
    # to the largest component of the highway graph
    # because such nodes can never appear in any sensible route.
    G = nx.Graph()
    for h in h.highways:
        G.add_edges_from(zip(h[:-2], h[1:-1]), tag=h[-1])
    largest = max(nx.connected_components(G), key=len)
    for n in set(G.nodes()) - largest:
        G.remove_node(n)
    print("pruning done")

    for e in G.edges:
        tag = G.get_edge_data(*e)['tag']
        sql_command = f"""INSERT OR IGNORE INTO highways(
        node_from, node_to, tag) VALUES
        ({e[0]}, {e[1]}, {tag})"""
        cur.execute(sql_command)
    conn.commit()
    print("writing done")


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
        read_write_highway_data(fname)


if __name__ == '__main__':
    conn = sqlite3.connect(c.db_name)
    cur = conn.cursor()
    main()
    conn.close()
