import boto3
from boto3.session import Session
import os
from botocore.errorfactory import ClientError
import os

#session = Session(region_name='us-east-1')
############################################ Precisa mudar o dir
KEY_DIR = "/home/gabi/Documents/ec2-key-pair-projeto1-gabi.pem"
KEY_NAME = "ec2-key-pair-projeto1-gabi"

AMI_UBUNTU_LTS = "ami-020db2c14939a8efb"
INSTANCE_TYPE = "t2.micro"

SECURITY_GROUP_NAME_OHIO = "SecurityGpOhio"
SECURITY_GROUP_DESCRIPTION_OHIO = "Security Group para a instancia de Ohio"

client_NVIRGINIA = boto3.client('ec2', region_name='us-east-1')
client_OHIO = boto3.client('ec2', region_name='us-east-2')

resource_OHIO = boto3.resource('ec2', region_name='us-east-2')
resource_NVIRGINIA = boto3.resource('ec2', region_name='us-east-1')


USER_DATA_POSTGRES = '''#!/bin/bash
echo "----- Iniciando script -----"
sudo apt update
echo "----- Instalando o Postgres -----"
sudo apt install postgresql postgresql-contrib -y
echo "----- Criando um usuario -----"
sudo su - postgres
sudo -u postgres psql -c "CREATE USER cloud WITH PASSWORD 'cloud';"
echo "----- Criando e configurando um database -----"
sudo -u createdb -O cloud tasks 
sudo sed 's/listen_addresses = 'localhost'/listen_addresses = '*'/g' /etc/postgresql/10/main/postgresql.conf
sudo echo "host	all	all	0.0.0.0/0	trust" > /etc/postgresql/10/main/pg_hba.conf
sudo exit
sudo ufw allow 5432/tcp 
sudo systemctl restart postgresql 
'''


USER_DATA_ORM = '''#!/bin/bash
git clone https://github.com/raulikeda/tasks.git 
cd tasks
./install.sh 
sudo reboot
'''

#  Função que cria um Key Pair  #
def create_key_pair(client, KEY_DIR, KEY_NAME):
    try:
        print("criando key pair")
        key_pair = client.create_key_pair(KeyName=KEY_NAME)
        private_key = key_pair["KeyMaterial"]

        print("Escrevendo chave privada em um arquivo")
        with os.fdopen(os.open(KEY_DIR, os.O_WRONLY | os.O_CREAT, 0o400), "w+") as handle:
                handle.write(private_key)
    except ClientError:  
        print("Chave já existe")
        


#  Função que cria uma instância  #
def create_instance(client, AMI, INSTANCE_TYPE, KEY_NAME, user_data, security_group):
    instances = client.run_instances(
        ImageId=AMI,
        MinCount=1,
        MaxCount=1,
        InstanceType=INSTANCE_TYPE,
        KeyName=KEY_NAME, 
        UserData=user_data,
        SecurityGroups=[security_group]
    )
    instance_id = instances["Instances"][0]["InstanceId"]
    print(f'Instância com id={instance_id} criada com sucesso')
    return instance_id

def add_tags(instance_id, resource, tag_key, tag_value):
    resource.create_tags(
    Resources=[
        instance_id,      
    ],
    Tags=[
        {
            'Key': tag_key,
            'Value': tag_value
        },
    ]
    )
    print(f"Tag com chave={tag_key} e valor={tag_value} adicionada com sucesso à instância {instance_id}")



def terminate_instance(ec2_client, instance_id):
    response = ec2_client.terminate_instances(InstanceIds=[instance_id])
    print(response)


def create_image(ec2_client, instance_id, name):
    ec2_client.create_image(InstanceId=instance_id, NoReboot=True, Name=name)


# https://boto3.amazonaws.com/v1/documentation/api/1.9.42/guide/ec2-example-security-group.html
def create_security_group(client_ec2, SECURITY_GROUP_NAME, DESCRIPTION):
    print("Criando Security Group")
    try:
        response = client_ec2.describe_vpcs()
        vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
        response = client_ec2.create_security_group(GroupName=SECURITY_GROUP_NAME,
                                            Description=DESCRIPTION,
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








# --------------- Criando a instância de OHIO --------------- #
print("----------------------------------------")
print("---------- COMEÇANDO O SCRIPT ----------")
print("----------------------------------------")

print("     ----- CRIANDO UM KEY PAIR -----")
create_key_pair(client_OHIO, KEY_DIR, KEY_NAME)

print("     ----- CRIANDO UM SECURITY GROUP PARA OHIO -----")
create_security_group(client_OHIO, SECURITY_GROUP_NAME_OHIO, SECURITY_GROUP_DESCRIPTION_OHIO)

print("     ----- CRIANDO A INSTÂNCIA DE OHIO -----")
instance_OHIO_id = create_instance(client_OHIO, AMI_UBUNTU_LTS, INSTANCE_TYPE, KEY_NAME, USER_DATA_POSTGRES, SECURITY_GROUP_NAME_OHIO)
# add_tags(instance_OHIO_id, resource_OHIO, "instancia1", "OHIO")


# --------------- Criando a instância de NORTH VIRGINIA --------------- #
#instance_NVIRGINIA_id = create_instance(client_NVIRGINIA, AMI_UBUNTU_LTS, INSTANCE_TYPE, KEY_NAME, USER_DATA_ORM)

# INSTALAR O ORM --> MUDAR SCRIPT DO DJANGO



# 6
# create_image(client_NVIRGINIA, instance_NVIRGINIA_id, "image_client_NV")
# terminate_instance(client_NVIRGINIA, instance_NVIRGINIA_id)




'''
Fontes:
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#client
https://www.postgresql.org/docs/12/sql-createuser.html
https://stackoverflow.com/questions/18223665/postgresql-query-from-bash-script-as-database-user-postgres
https://docs.aws.amazon.com/pt_br/AWSEC2/latest/UserGuide/user-data.html
https://www.learnaws.org/2020/12/16/aws-ec2-boto3-ultimate-guide/#how-to-create-a-new-ec2-instance-using-boto3
'''