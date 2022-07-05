#!/usr/bin/env python
import sqlite3
import networkx as nx

import common as c


def compress():
    G = nx.Graph()
    trunk_tags = ",".join(str(t) for t in c.trunk_tags)
    sql = (
        "SELECT  node_from, node_to, cost "
        "FROM highways "
        f"WHERE tag NOT IN ({trunk_tags});"
    )
    cur.execute(sql)
    for e in cur.fetchall():
        node_from, node_to, cost = e
        G.add_edge(node_from, node_to, cost=cost)
    return G  # don't compress

    # dead ends can be removed straight away
    print(G.number_of_nodes())
    nodes = set(n for n in G.nodes() if G.degree(n) == 1)
    while nodes:
        m = nodes.pop()
        while G.degree(m) == 1:
            n = list(G.neighbors(m))[0]
            G.remove_node(m)
            m = n
    print(G.number_of_nodes())
    # contract highways
    nodes = set(n for n in G.nodes() if G.degree(n) <= 2)
    num_passes = 0
    while nodes and num_passes < 5:
        for node in nodes:
            if G.degree(node) <= 1:  # remove dead end
                G.remove_node(node)
                continue
            e1, e2 = G.edges(node)
            cost = G.get_edge_data(*e1)['cost'] + G.get_edge_data(*e2)['cost']
            if G.has_edge(e1[1], e2[1]):
                cost = min(cost, G.get_edge_data(e1[1], e2[1])['cost'])
            G.add_edge(e1[1], e2[1], cost=cost)
            G.remove_node(node)
        nodes = set(n for n in G.nodes() if G.degree(n) <= 2)
        num_passes += 1
        print(G.number_of_nodes())

    return G


def write_to_db(G):
    for e in G.edges:
        cost = G.get_edge_data(*e)['cost']
        sql = (
            "INSERT OR IGNORE INTO compressed("
            "node_from, node_to, cost) VALUES"
            f"({e[0]}, {e[1]}, {cost})"
        )
        cur.execute(sql)
    conn.commit()


def drop_table():
    cur.execute('''DROP TABLE compressed;''')
    conn.commit()


def make_table():
    sql = (
        "CREATE TABLE compressed ("
        "id INTEGER PRIMARY KEY,"
        "node_from int,"
        "node_to int,"
        "cost int default 0,"
        "UNIQUE(node_from, node_to)"
        ");"
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

    G = compress()
    write_to_db(G)


if __name__ == '__main__':
    conn = sqlite3.connect(c.db_name)
    cur = conn.cursor()
    main()
    conn.close()
