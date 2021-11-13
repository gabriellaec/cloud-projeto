import boto3
from boto3.session import Session
import os
from botocore.errorfactory import ClientError
import secrets
import time

#session = Session(region_name='us-east-1')
############################################ Precisa mudar o dir

# ********** CHAVES ********** #
KEY_DIR = "/home/gabi/Documents/ec2-key-pair-projeto1-gabi.pem"
KEY_NAME = "ec2-key-pair-projeto1-gabi"

KEY_DIR_NV = "/home/gabi/Documents/ec2-key-pair-projeto1-gabi2.pem"
KEY_NAME_NV = "ec2-key-pair-projeto1-gabi2"


# ********** CONFIGURAÇÕES DAS INSTÂNCIAS ********** #
AMI_UBUNTU_LTS_OHIO = "ami-020db2c14939a8efb"
AMI_UBUNTU_LTS_NVIR = "ami-0279c3b3186e54acd"
INSTANCE_TYPE = "t2.micro"
AMI_NV = "image_client_N_Virginia"
TAG_KEY = "instance-proj"
TAG_VAL_OHIO = "OhioPsql"
TAG_VAL_NVIR = "NorthVirginia"


# ********** CONFIGURAÇÕES DO SECURITY GROUP ********** #
SECURITY_GROUP_NAME_OHIO = "SecurityGroupOhio"
SECURITY_GROUP_DESCRIPTION_OHIO = "Security Group para a instancia de Ohio"

SECURITY_GROUP_NAME_NVIR = "SecurityGroupNVir"
SECURITY_GROUP_DESCRIPTION_NVIR = "Security Group para a instancia de North Virginia"


# ********** boto3 CLIENT & RESOURCES ********** #
NORTH_VIRGINIA='us-east-1'
OHIO='us-east-2'
client_NVIRGINIA = boto3.client('ec2', region_name=NORTH_VIRGINIA)
client_OHIO = boto3.client('ec2', region_name=OHIO)

resource_OHIO = boto3.resource('ec2', region_name='us-east-2')
resource_NVIRGINIA = boto3.resource('ec2', region_name='us-east-1')


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
    instance = instances["Instances"][0]
    # print("Criando a instância...")
    # instance.wait_until_running()
    # instance_state = instances["Instances"][0]["State"]["Name"]
    # print(instance_state)
    
    # print("Criando a instância...")
    # while instance_state != 'running':
    #    print(f"Instância está {instance_state}...")
    #    time.sleep(10)
    #    instance.update()
    #    instance_state = instances["Instances"][0]["State"]["Name"]

    instance_id = instance["InstanceId"]

    print(f'Instância com id={instance_id} criada com sucesso')
    print(f"Tag com chave={tag_key} e valor={tag_val} adicionada com sucesso à instância {instance_id}")

    return instance_id


#  Função que deleta uma instância  #
def terminate_instance(ec2_client, ec2_resource, instance_id):

    instance = ec2_resource.Instance(instance_id)
    if instance.state['Name'] == 'running':
        response = ec2_client.terminate_instances(InstanceIds=[instance_id])

        print("Apagando instância...")
        print()
        print(response)
    else:
        print(f"Nenhuma instância com id={instance_id} rodando!")



#  Função que cria uma AMI #
def create_image(ec2_client, resource_ec2, instance_id, name):
    try:
        print(f"Criando imagem {name}...")
        image = ec2_client.create_image(InstanceId=instance_id, NoReboot=True, Name=name)
    
        print(f"\n {image} \n")
    except ClientError:
        print(f"Imagem {name} já existe\n")
        response = ec2_client.describe_images(Filters=[
        {'Name': 'name',
         'Values': [name]}])

        ami_id = response['Images'][0]['ImageId']
        print(f"ID da AMI: {ami_id}")

        print("Deletando imagem...\n")
        ami = list(resource_ec2.images.filter(ImageIds=[ami_id]).all())[0]
        ami.deregister(DryRun=False)       
        
        create_image(ec2_client, resource_ec2, instance_id, name)
        # ec2_client.create_image(InstanceId=instance_id, NoReboot=True, Name=name)


#  Função que cria um Security Group #
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
                'FromPort': 8080,
                'ToPort': 8080,
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



def get_instance_id_by_tag(client_ec2, tag_val):
        filter = [{
            'Name': 'tag:instance-proj', 
            'Values': [tag_val]}]
            
        response = client_ec2.describe_instances(Filters=filter)
        if response is not None:
            instanceid = response["Reservations"][0]['Instances'][0]['InstanceId']
            return instanceid


# Função que pega o IP de uma instância pelo ID
def get_ip_by_id(resource_ec2, instance_id):
    
    running_instances = resource_ec2.instances.filter(Filters=[{
    'Name': 'instance-state-name',
    'Values': ['pending', 'running']}])

    print("Buscando ip da instância...")
    for instance in running_instances:
        if instance.id==instance_id:
            ip=instance.public_ip_address
            print(f"Instância com id={instance_id} possui o ip={ip}\n")
            return ip



#**************************************************#
# ******************** SCRIPT ******************** #
#**************************************************#

print("----------------------------------------")
print("---------- COMEÇANDO O SCRIPT ----------")
print("----------------------------------------")
print()
print("----------------- OHIO -----------------")


print("* CRIANDO UM KEY PAIR PARA OHIO")
create_key_pair(client_OHIO, KEY_DIR, KEY_NAME)
print()

print("* CRIANDO UM SECURITY GROUP PARA OHIO")
create_security_group(client_OHIO, SECURITY_GROUP_NAME_OHIO, SECURITY_GROUP_DESCRIPTION_OHIO)
print()

print("* CRIANDO A INSTÂNCIA DE OHIO")

# old_ohio_id = get_instance_id_by_tag(client_OHIO, TAG_VAL_OHIO)
# if old_ohio_id is not None:
#     print(f"id da instância antiga: {old_ohio_id}")
#     terminate_instance(client_OHIO, resource_OHIO, old_ohio_id)

USER_DATA_POSTGRES=f'''#!/bin/bash
sudo apt update
sudo apt install postgresql postgresql-contrib -y
sudo -u postgres psql -c "CREATE USER {secrets.username} WITH PASSWORD '{secrets.password}';"
sudo -u postgres createdb -O cloud tasks
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/g" /etc/postgresql/10/main/postgresql.conf
sudo sh -c 'echo "host    all             all             0.0.0.0/0               trust" >> /etc/postgresql/10/main/pg_hba.conf'
sudo ufw allow 5432/tcp 
sudo systemctl restart postgresql 
'''

instance_OHIO_id = create_instance(client_OHIO, AMI_UBUNTU_LTS_OHIO, INSTANCE_TYPE, KEY_NAME, USER_DATA_POSTGRES, SECURITY_GROUP_NAME_OHIO, TAG_KEY, TAG_VAL_OHIO)

# instance = resource_OHIO.Instance(id=instance_OHIO_id)
print("Esperando a instância estar rodando...")
# instance.wait_until_running()

# waiter_status_ok = client_OHIO.get_waiter("instance_status_ok")
# waiter_status_ok.wait(InstanceIds=[ instance_OHIO_id])
# --------------- Criando a instância de NORTH VIRGINIA --------------- #
print()
print("------------- NORTH VIRGINIA -------------")
print()
print("* CRIANDO UM KEY PAIR PARA NORTH VIRGINIA")
create_key_pair(client_NVIRGINIA, KEY_DIR_NV, KEY_NAME_NV)


print("* CRIANDO UM SECURITY GROUP PARA NORTH VIRGINIA")
create_security_group(client_NVIRGINIA, SECURITY_GROUP_NAME_NVIR, SECURITY_GROUP_DESCRIPTION_NVIR)
print()

instance_OHIO_ip = get_ip_by_id(resource_OHIO, instance_OHIO_id)
print(f"ip Ohio: {instance_OHIO_ip}")
USER_DATA_ORM=f'''#!/bin/bash
sudo apt update -y
cd /home/ubuntu
git clone https://github.com/gabriellaec/tasks.git
sudo sed -i "s/'HOST': 'node1'/'HOST': '{instance_OHIO_ip}'/g" tasks/portfolio/settings.py
cd tasks
./install.sh 
sudo reboot
        '''

instance_NVIRGINIA_id = create_instance(client_NVIRGINIA, AMI_UBUNTU_LTS_NVIR, INSTANCE_TYPE, KEY_NAME_NV, USER_DATA_ORM, SECURITY_GROUP_NAME_NVIR, TAG_KEY, TAG_VAL_NVIR)
instance = resource_NVIRGINIA.Instance(id=instance_NVIRGINIA_id)
print("Esperando a instância estar rodando...")
instance.wait_until_running()

# delete_ami_if_exists(client_NVIRGINIA, resource_NVIRGINIA, AMI_NV)
create_image(client_NVIRGINIA, resource_NVIRGINIA, instance_NVIRGINIA_id, AMI_NV)
terminate_instance(client_NVIRGINIA, resource_NVIRGINIA, instance_NVIRGINIA_id)


#### LOAD BALANCER
# http://boto.cloudhackers.com/en/latest/elb_tut.html
#https://www.stratoscale.com/knowledge/load-balancing/aws-elb/boto-3-for-elb/example-work-with-a-load-balancer-and-target-group/


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

https://stackoverflow.com/questions/10437026/using-boto-to-determine-if-an-aws-ami-is-available
 https://newbedev.com/ec2-waiting-until-a-new-instance-is-in-running-state
https://boto3.amazonaws.com/v1/documentation/api/1.9.42/guide/ec2-example-security-group.html
https://dashbird.io/blog/boto3-aws-python/
'''

