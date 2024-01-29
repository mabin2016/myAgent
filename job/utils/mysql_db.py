import pymysql
from pymysql import Error

class MySQLDatabase:
    def __init__(self, host, user, password, db):
        self.host = host
        self.user = user
        self.password = password
        self.db = db
        self.connection = None
        self.cursor = None

    def connect(self):
        try:
            self.connection = pymysql.connect(host=self.host,
                                               user=self.user,
                                               password=self.password,
                                               db=self.db,
                                               charset='utf8mb4',
                                               cursorclass=pymysql.cursors.DictCursor)
            self.cursor = self.connection.cursor()
        except Error as e:
            print(f"Error connecting to MySQL: {e}")

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def execute_query(self, query, args=None):
        try:
            with self.cursor as cursor:
                if args:
                    cursor.execute(query, args)
                else:
                    cursor.execute(query)
                return cursor.fetchall()
        except Error as e:
            print(f"Error executing query: {e}")
            return None

    def insert_data(self, table, data):
        # 构建插入语句
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        try:
            self.execute_query(query, data.values())
            self.connection.commit()
            return True
        except Error as e:
            self.connection.rollback()
            print(f"Error inserting data: {e}")
            return False

    def select_data(self, table, conditions=None):
        query = f"SELECT * FROM {table}"
        if conditions:
            query += " WHERE " + " AND ".join([f"{key} = %s" for key in conditions.keys()])
            args = conditions.values()
        return self.execute_query(query, args)

    def update_data(self, table, data, conditions):
        # 构建更新语句
        set_clauses = ', '.join([f"{key} = %s" for key in data.keys()])
        query = f"UPDATE {table} SET {set_clauses}"
        if conditions:
            query += " WHERE " + " AND ".join([f"{key} = %s" for key in conditions.keys()])
            args = data.values() + conditions.values()
        return self.execute_query(query, args)

    def delete_data(self, table, conditions):
        query = f"DELETE FROM {table}"
        if conditions:
            query += " WHERE " + " AND ".join([f"{key} = %s" for key in conditions.keys()])
            args = conditions.values()
        return self.execute_query(query, args)

# 使用示例
# db = MySQLDatabase(host='localhost', user='your_username', password='your_password', db='your_database')
# db.connect()
# result = db.select_data('your_table', {'id': 1})
# db.close()