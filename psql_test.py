
import psycopg2
import sys
import boto3
import os

ENDPOINT="ec2-3-16-40-101.us-east-2.compute.amazonaws.com"
PORT="5432"
USR="cloud"
REGION="us-east-2"
DBNAME="tasks"
PASSWORD="cloud"

#gets the credentials from .aws/credentials
session = boto3.Session()
client = session.client('rds', region_name=REGION)

try:
    print("Abrindo conexão com o banco de dados dentro da instância")
    conn = psycopg2.connect(
        host=ENDPOINT, 
        port=PORT, 
        database=DBNAME, 
        user=USR, 
        password=PASSWORD, 
        )
    print("abriu conexão")
    # cur = conn.cursor()
    # cur.execute("""SELECT now()""")
    # query_results = cur.fetchall()
    # print(query_results)
    if conn.closed==0:
         print("conexão OK") 
    else:
         print("Deu ruim")
except Exception as e:
    print("Database connection failed due to {}".format(e))                
                

# https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.Connecting.Python.html

# ssh -i /home/gabi/Documents/ec2-key-pair-projeto1-gabi.pem ubuntu@3.16.40.101
# nano postgres-script.sh
# chmod u+x postgres-script.sh