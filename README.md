# cloud-projeto

## INSTRUÇÕES DE USO

**Criar um arquivo ~/.aws/credentials com as seguintes configurações:**

[default]

aws_access_key_id = YOUR_ACCESS_KEY

aws_secret_access_key = YOUR_SECRET_KEY

region=us-east-1


**Criar um arquivo psql_secrets.py com suas credenciais do banco de dados:**

username="..."

password="..."


**Para rodar o script:**

python3 mainv2.py


**Para rodar o client:**

python3 client.py 


**OBS:** Após execução, os logs ficam armazenados no arquivo proj_logs.txt
