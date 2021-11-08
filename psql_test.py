
import psycopg2
import sys
import boto3
import os

ENDPOINT="ec2-3-145-20-22.us-east-2.compute.amazonaws.com"
PORT=5432
USR="cloud"
REGION="us-east-2"
DBNAME="tasks"

#gets the credentials from .aws/credentials
session = boto3.Session()
client = session.client('rds', region_name=REGION)

token = client.generate_db_auth_token(DBHostname=ENDPOINT, Port=PORT, DBUsername=USR, Region=REGION)
try:
    print("Abrindo conexão com o banco de dados dentro da instância")
    conn = psycopg2.connect(host=ENDPOINT, port=PORT, database=DBNAME, user=USR, password=token, sslmode='prefer', sslrootcert="[full path]rds-combined-ca-bundle.pem")
    print("abriu conexão")
    # cur = conn.cursor()
    # cur.execute("""SELECT now()""")
    # query_results = cur.fetchall()
    # print(query_results)
    print(conn.closed)
except Exception as e:
    print("Database connection failed due to {}".format(e))                
                