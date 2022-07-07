import sqlite3
import common as common


class DB:
    def __init__(self):
        self.connection = sqlite3.connect(common.db_name)
        self.cursor = self.connection.cursor()

    def close_connection(self):
        self.connection.close()

    def commit(self):
        self.connection.commit()

    def execute(self, statement):
        self.cursor.execute(statement)

    def update_old(self, table, ID, **kwargs):
        sql = f'UPDATE edges SET'
        for k in kwargs.keys():
            sql += f" {k}=? "
        sql += f"WHERE ID=?"
        print(sql)
        quit()
        self.cursor.executemany(sql, zip(*kwargs.values(), ID))

    def update(self, sql, args):
        self.cursor.executemany(sql, args)

    def drop_edge_table(self):
        try:
            self.execute('''DROP TABLE edges;''')
            self.connection.commit()
        except Exception as e:
            print("ERROR : " + str(e))
            print("Cannot drop edge table")

    def make_edge_table(self):
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
        try:
            self.execute(sql)
            self.commit()
        except Exception as e:
            print("ERROR : " + str(e))
            print("Cannot make edge table")

    def drop_node_table(self):
        try:
            self.execute("DROP TABLE nodes;")
            self.commit()
        except Exception as e:
            print("ERROR : " + str(e))
            print("Cannot drop table")

    def make_node_table(self):
        sql = (
            "CREATE TABLE nodes "
            "(id INTEGER PRIMARY KEY, "
            "node_id int, "
            "latitude float, "
            "longitude float, "
            "UNIQUE(node_id));"
        )
        try:
            self.execute(sql)
            self.commit()
        except Exception as e:
            print("ERROR : " + str(e))
            print("Cannot make table")

    def add_edge(self, m, n, tag):
        sql = (
            "INSERT OR IGNORE INTO edges("
            " node_from, node_to, tag) VALUES"
            f" ({m}, {n}, {tag})"
        )
        self.cursor.execute(sql)

    def add_edges(self, left, right, tags):
        sql = (
            "INSERT OR IGNORE INTO edges(node_from, node_to, tag)"
            " VALUES (?, ?, ?)"
        )
        self.cursor.executemany(sql, zip(left, right, tags))

    def add_node(self, Id, lat, lon):
        sql = (
            "INSERT OR IGNORE INTO nodes "
            " (node_id, latitude, longitude)"
            f" VALUES ({Id}, {lat}, {lon})"
        )
        self.execute(sql)
        # self.cursor.executemany(sql, zip(*kwargs.values(), ID))

    def add_nodes(self, ID, lat, lon):
        sql = (
            "INSERT OR IGNORE INTO nodes "
            " (node_id, latitude, longitude)"
            f" VALUES (?, ?, ?)"
        )
        self.cursor.executemany(sql, zip(ID, lat, lon))

    def get_highway_nodes(self):
        # return the nodes ids of the edges
        self.execute('SELECT node_to, node_from FROM edges;')
        highway_nodes = set()
        for m in self.cursor.fetchall():
            highway_nodes.update(m)
        return highway_nodes

    def get_node_info(self, *args, where=""):
        sql = "SELECT " + ", ".join(a for a in args) + " FROM nodes"
        if where:
            sql += f" WHERE {where};"
        self.execute(sql)
        return self.cursor.fetchall()

    def get_edge_info(self, *args, where=""):
        sql = "SELECT " + ", ".join(a for a in args) + " FROM edges"
        if where:
            sql += f" WHERE {where};"
        self.execute(sql)
        return self.cursor.fetchall()

    def get_trunk_coordinates(self):
        trunk_tags = ",".join(str(t) for t in common.trunk_tags)
        sql = (
            "SELECT latitude, longitude "
            "FROM nodes "
            "WHERE node_id IN "
            "(SELECT  node_from "
            "FROM edges "
            f"WHERE tag IN ({trunk_tags}));"
        )
        self.execute(sql)
        return self.cursor.fetchall()
