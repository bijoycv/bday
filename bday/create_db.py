import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database():
    dbname = os.getenv('DB_NAME')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT', '5432')

    try:
        # Connect to default 'postgres' database to create the new one
        con = psycopg2.connect(dbname='postgres', user=user, host=host, password=password, port=port)
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = con.cursor()
        
        # Check if exists
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{dbname}'")
        exists = cur.fetchone()
        
        if not exists:
            print(f"Database {dbname} does not exist. Creating...")
            cur.execute(f"CREATE DATABASE {dbname}")
            print(f"Database {dbname} created successfully.")
        else:
            print(f"Database {dbname} already exists.")
            
        cur.close()
        con.close()
    except Exception as e:
        print(f"Error checking/creating database: {e}")

if __name__ == "__main__":
    create_database()
