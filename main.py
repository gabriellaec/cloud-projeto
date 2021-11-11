import boto3
from boto3.session import Session
import os
from botocore.errorfactory import ClientError
import secrets

#session = Session(region_name='us-east-1')
############################################ Precisa mudar o dir

# ********** CHAVES ********** #
KEY_DIR = "/home/gabi/Documents/ec2-key-pair-projeto1-gabi.pem"
KEY_NAME = "ec2-key-pair-projeto1-gabi"


# ********** CONFIGURAÇÕES DAS INSTÂNCIAS ********** #
AMI_UBUNTU_LTS = "ami-020db2c14939a8efb"
INSTANCE_TYPE = "t2.micro"
AMI_NV = "image_client_NV"
TAG_KEY = "instance-proj"
TAG_VAL_OHIO = "ohio_psql"
TAG_VAL_NVIR = "north-virginia-orm"


# ********** CONFIGURAÇÕES DO SECURITY GROUP ********** #
SECURITY_GROUP_NAME_OHIO = "SecurityGpOhio"
SECURITY_GROUP_DESCRIPTION_OHIO = "Security Group para a instancia de Ohio"


# ********** boto3 CLIENT & RESOURCES ********** #
client_NVIRGINIA = boto3.client('ec2', region_name='us-east-1')
client_OHIO = boto3.client('ec2', region_name='us-east-2')

resource_OHIO = boto3.resource('ec2', region_name='us-east-2')
resource_NVIRGINIA = boto3.resource('ec2', region_name='us-east-1')


# ********** USER DATA ********** #
USER_DATA_POSTGRES = f'''#!/bin/bash
sudo apt update
sudo apt install postgresql postgresql-contrib -y
sudo -u postgres psql -c "CREATE USER {secrets.username} WITH PASSWORD '{secrets.password}';"
sudo -u postgres createdb -O cloud tasks
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/g" /etc/postgresql/10/main/postgresql.conf
sudo sh -c 'echo "host    all             all             0.0.0.0/0               trust" >> /etc/postgresql/10/main/pg_hba.conf'
sudo ufw allow 5432/tcp 
sudo systemctl restart postgresql 
'''

# sudo nano /etc/postgresql/10/main/pg_hba.conf
# sudo nano /etc/postgresql/10/main/postgresql.conf

####### ESSE TEM QUE MUDAR !!!
ohio_instance_ip=0
USER_DATA_ORM = f'''#!/bin/bash
git clone https://github.com/gabriellaec/tasks.git
sed -i "s/'HOST': 'node1'/'HOST': '{ohio_instance_ip}/g" /tasks/portfolio/settings.py
cd tasks
./install.sh 
sudo reboot
'''



# ohio_instance_ip=0
# USER_DATA_ORM = f'''#!/bin/bash
# git clone https://github.com/gabriellaec/tasks.git
# sed -i "s/'USER': 'cloud'/'USER': '{secrets.username}'/g" /tasks/portfolio/settings.py
# sed -i "s/'PASSWORD': 'cloud'/'PASSWORD': '{secrets.password}'/g" /tasks/portfolio/settings.py
# sed -i "s/'HOST': 'node1'/'HOST': '{ohio_instance_ip}/g" /tasks/portfolio/settings.py
# cd tasks
# ./install.sh 
# sudo reboot
# '''


#***************************************************#
# ******************** FUNÇÕES ******************** #
#***************************************************#

#  Função que cria um Key Pair  #
def create_key_pair(client, key_dir, key_name):
    try:
        print("criando key pair")
        key_pair = client.create_key_pair(KeyName=key_name)
        private_key = key_pair["KeyMaterial"]

        print("Escrevendo chave privada em um arquivo")
        with os.fdopen(os.open(key_dir, os.O_WRONLY | os.O_CREAT, 0o400), "w+") as handle:
                handle.write(private_key)
    except ClientError:  
        print("Chave já existe")
        


#  Função que cria uma instância  #
def create_instance(client, ami, instance_type, key_name, user_data, security_group, tag_key, tag_val):
    instances = client.run_instances(
        ImageId=ami,
        MinCount=1,
        MaxCount=1,
        InstanceType=instance_type,
        KeyName=key_name, 
        UserData=user_data,
        SecurityGroups=[security_group],
        TagSpecifications=[
        {   'ResourceType': 'instance',
            'Tags': [
                {
                    'Key': tag_key,
                    'Value': tag_val
                },
            ]
        },
    ]
    )
    instance_id = instances["Instances"][0]["InstanceId"]
    print(f'Instância com id={instance_id} criada com sucesso')
    print(f"Tag com chave={tag_key} e valor={tag_val} adicionada com sucesso à instância {instance_id}")

    return instance_id


def terminate_instance(ec2_client, ec2_resource, instance_id):

    instance = ec2_resource.Instance(instance_id)
    if instance.state['Name'] == 'running':
        response = ec2_client.terminate_instances(InstanceIds=[instance_id])

        print("Apagando instância...")
        print()
        print(response)
    else:
        print("Nenhuma instância com esse id rodando!")


def create_image(ec2_client, instance_id, name):
    ec2_client.create_image(InstanceId=instance_id, NoReboot=True, Name=name)


# https://boto3.amazonaws.com/v1/documentation/api/1.9.42/guide/ec2-example-security-group.html
def create_security_group(client_ec2, security_gp_name, description):
    print("Criando Security Group")
    try:
        response = client_ec2.describe_vpcs()
        vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
        response = client_ec2.create_security_group(GroupName=security_gp_name,
                                            Description=description,
                                            VpcId=vpc_id)
        security_group_id = response['GroupId']
        print('Security Group criado %s na vpc %s.' % (security_group_id, vpc_id))
        
        data = client_ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp',
                'FromPort': 5432,
                'ToPort': 5432,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ])
        print('Security Group criado com sucesso com as seguintes infotmações:\n%s\n' % data)
    except ClientError as e:
        print("Security Group já existe!")


def get_instance_id_by_tag(client_ec2, tag_key, tag_val):
        custom_filter = [{
            'Name': tag_key, 
            'Values': [tag_val]}]
            
        response = client_ec2.describe_instances(Filters=custom_filter)
        return response
#**************************************************#
# ******************** SCRIPT ******************** #
#**************************************************#

print("----------------------------------------")
print("---------- COMEÇANDO O SCRIPT ----------")
print("----------------------------------------")

print("* CRIANDO UM KEY PAIR")
create_key_pair(client_OHIO, KEY_DIR, KEY_NAME)
print()

print("* CRIANDO UM SECURITY GROUP PARA OHIO")
create_security_group(client_OHIO, SECURITY_GROUP_NAME_OHIO, SECURITY_GROUP_DESCRIPTION_OHIO)
print()

print("* CRIANDO A INSTÂNCIA DE OHIO")

old_ohio_id = get_instance_id_by_tag(client_OHIO, TAG_KEY, TAG_VAL_OHIO)
if old_ohio_id is not None:
    terminate_instance(client_OHIO, resource_OHIO, old_ohio_id)

instance_OHIO_id = create_instance(client_OHIO, AMI_UBUNTU_LTS, INSTANCE_TYPE, KEY_NAME, USER_DATA_POSTGRES, SECURITY_GROUP_NAME_OHIO, TAG_KEY, TAG_VAL_OHIO)
# add_tags(instance_OHIO_id, resource_OHIO, "instancia1", "OHIO")


# --------------- Criando a instância de NORTH VIRGINIA --------------- #
#instance_NVIRGINIA_id = create_instance(client_NVIRGINIA, AMI_UBUNTU_LTS, INSTANCE_TYPE, KEY_NAME, USER_DATA_ORM)

# INSTALAR O ORM --> MUDAR SCRIPT DO DJANGO



# 6
# create_image(client_NVIRGINIA, instance_NVIRGINIA_id, AMI_NV)
# terminate_instance(client_NVIRGINIA, instance_NVIRGINIA_id)




'''
Fontes:
Criando instâncias
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#client
https://www.learnaws.org/2020/12/16/aws-ec2-boto3-ultimate-guide/#how-to-create-a-new-ec2-instance-using-boto3

Script postgres
https://www.postgresql.org/docs/12/sql-createuser.html
https://stackoverflow.com/questions/18223665/postgresql-query-from-bash-script-as-database-user-postgres
https://www.cyberciti.biz/faq/linux-append-text-to-end-of-file/
https://docs.aws.amazon.com/pt_br/AWSEC2/latest/UserGuide/user-data.html
'''

