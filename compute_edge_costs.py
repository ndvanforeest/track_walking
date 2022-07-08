#!/usr/bin/env python
import sqlite3

import common


def compute_edge_cost():
    tag_to_idx = {tag_str: i for i, tag_str in enumerate(common.tags)}
    factor = {
        tag_to_idx[t]: common.cost_factor[t]
        for t in tag_to_idx
        if t not in common.trunks
    }
    trunk_tags = ",".join(str(t) for t in common.trunk_tags)
    sql = (
        "SELECT id, node_from, tag, length, near_trunk "
        "FROM edges "
        f"WHERE tag NOT IN ({trunk_tags});"
    )
    cur.execute(sql)
    for e in cur.fetchall():
        ID, node_from, tag, length, near_trunk = e
        cost = length * factor[tag]
        cost *= common.near_trunk_cost if near_trunk else 1
        cur.execute(f'UPDATE edges SET cost = {cost} WHERE ID = {ID}')
    conn.commit()


def main():
    compute_edge_cost()


if __name__ == '__main__':
    conn = sqlite3.connect(common.db_name)
    cur = conn.cursor()
    main()
    conn.close()
