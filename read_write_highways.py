#!/usr/bin/env python
import sqlite3
import osmium

import common as c


def drop_table():
    cur.execute('''DROP TABLE edges;''')
    connection.commit()


def make_table():
    sql = (
        "CREATE TABLE edges ("
        "id INTEGER PRIMARY KEY,"
        "node_from int,"
        "node_to int,"
        "tag int,"
        "length real default 0.,"
        "near_trunk int default 0,"
        "cost real default 0.,"
        "UNIQUE(node_from, node_to)"
        ");"
    )

    cur.execute(sql)
    connection.commit()


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
            s = [w.nodes[i].ref for i in range(len(w.nodes))] + [
                self.tag_str_to_idx[tag]
            ]
            self.highways.append(s)


def read_write_highway_data(fname):
    h = Highway_Handler()
    h.apply_file(fname)
    print("reading done")

    for e in h.highways:
        tag = e[-1]
        for m, n in zip(e[:-2], e[1:-1]):
            sql = (
                "INSERT OR IGNORE INTO edges("
                " node_from, node_to, tag) VALUES"
                f" ({m}, {n}, {tag})"
            )
            cur.execute(sql)
    connection.commit()
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
    connection = sqlite3.connect(c.db_name)
    cur = connection.cursor()
    main()
    connection.close()
