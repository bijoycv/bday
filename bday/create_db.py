import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database():
    # Use SERVER_ prefixed vars (production/Docker), fall back to DB_ vars
    dbname = os.getenv('SERVER_DB_NAME') or os.getenv('DB_NAME', 'bday')
    user = os.getenv('SERVER_DB_USER') or os.getenv('DB_USER', 'Sivahpdb')
    password = os.getenv('SERVER_DB_PASSWORD') or os.getenv('DB_PASSWORD', '')
    host = os.getenv('SERVER_DB_HOST') or os.getenv('DB_HOST', 'postgres-db')
    port = os.getenv('SERVER_DB_PORT') or os.getenv('DB_PORT', '5432')

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
