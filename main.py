import boto3
from boto3.session import Session
import os
from botocore.errorfactory import ClientError
import secrets
import time
import logging


##################### lOGS #####################
open('proj_logs.txt', 'w').close()
logging.basicConfig(format='%(asctime)s %(message)s',
    datefmt='%d-%m-%Y:%H:%M:%S',
    level=logging.INFO,
    filename='proj_logs.txt')
logger = logging.getLogger('my_app')

############################################ Precisa mudar o dir

# ********** CHAVES ********** #
KEY_DIR = "/home/gabi/Documents/eec2-key-pair-proj.pem"
KEY_NAME = "ec2-key-pair-proj"

KEY_DIR_NV = "/home/gabi/Documents/ec2-key-pair-proj2.pem"
KEY_NAME_NV = "ec2-key-pair-proj2"


# ********** CONFIGURAÇÕES DO SECURITY GROUP ********** #
SECURITY_GROUP_NAME_OHIO = "SecurityGroupOhio"
SECURITY_GROUP_DESCRIPTION_OHIO = "Security Group para a instancia de Ohio"

SECURITY_GROUP_NAME_NVIR = "SecurityGroupNVir"
SECURITY_GROUP_DESCRIPTION_NVIR = "Security Group para a instancia de North Virginia"


# ********** CONFIGURAÇÕES DAS INSTÂNCIAS ********** #
INSTANCE_TYPE = "t2.micro"

## AMIs
AMI_UBUNTU_LTS_OHIO = "ami-020db2c14939a8efb"
AMI_UBUNTU_LTS_NVIR = "ami-0279c3b3186e54acd"
AMI_NV = "image_client_N_Virginia"

## Tags
TAG_KEY = "instance-proj"
TAG_VAL_OHIO = "OhioPsql"
TAG_VAL_NVIR = "NorthVirginia"


# ********** CONFIGURAÇÕES DO LOAD BALANCER E AUTOSCALING GROUP ********** #
LB_NAME = "LoadBalORM"
LAUNCH_CONFIG_NAME = "LaunchConORM"
AUTOSCALING_NAME = "AutoScalORM"
POLICY_NAME = "PolicyASG"

## Tags
TAG_VAL_LB = "LoadBalProj"
TAG_VAL_LC = "LaunchCOnfigProj"
TAG_VAL_ASG = "AutoScalProj"


# ********** boto3 CLIENT & RESOURCES ********** #
OHIO='us-east-2'
NORTH_VIRGINIA='us-east-1'

client_OHIO = boto3.client('ec2', region_name=OHIO)
client_NVIRGINIA = boto3.client('ec2', region_name=NORTH_VIRGINIA)

resource_OHIO = boto3.resource('ec2', region_name='us-east-2')
resource_NVIRGINIA = boto3.resource('ec2', region_name='us-east-1')

client_lb = boto3.client('elb', region_name=NORTH_VIRGINIA)
client_asg = boto3.client('autoscaling', region_name=NORTH_VIRGINIA)


#***************************************************#
# ******************** FUNÇÕES ******************** #
#***************************************************#

#  Função que cria um Key Pair  #
def create_key_pair(client, key_dir, key_name):
    try:
        print("criando key pair")
        key_pair = client.create_key_pair(KeyName=key_name)
        private_key = key_pair["KeyMaterial"]

        print("Escrevendo chave privada em um arquivo\n")
        with os.fdopen(os.open(key_dir, os.O_WRONLY | os.O_CREAT, 0o400), "w+") as handle:
                handle.write(private_key)
    except ClientError as e:  
        print(e)
        

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
            'Tags': [{
                    'Key': tag_key,
                    'Value': tag_val}]}]
    )
    instance = instances["Instances"][0]
    instance_id = instance["InstanceId"]
    print(f'Instância com id={instance_id} criada com sucesso')
    print(f"Tag com chave={tag_key} e valor={tag_val} adicionada com sucesso à instância {instance_id}\n")
    return instance_id


#  Função que deleta uma instância  #
def terminate_instance(ec2_client, ec2_resource, instance_id):
    instance = ec2_resource.Instance(instance_id)
    if instance.state['Name'] == 'running':
        ec2_client.terminate_instances(InstanceIds=[instance_id])
        print(f"Apagando instância de id={instance_id}...")
    else:
        print(f"Nenhuma instância com id={instance_id} rodando!")


#  Função que cria uma AMI #
def create_image(ec2_client, instance_id, name):
    try:
        print(f"Criando imagem {name}...")
        ec2_client.create_image(InstanceId=instance_id, NoReboot=True, Name=name)
    except ClientError as e:
        print(e)

def delete_image(ec2_client, resource_ec2, name):

    response = ec2_client.describe_images(Filters=[
    {'Name': 'name',
    'Values': [name]
    }])
    ami_id=None
    for image in response['Images']:
        if image['Name'] == name:
            ami_id = image['ImageId']
    if ami_id is not None:
        print(f"Imagem {name} já existe\n")
        print(f"ID da AMI: {ami_id}")
        print("Deletando imagem...\n")
        ami = list(resource_ec2.images.filter(ImageIds=[ami_id]).all())[0]
        ami.deregister(DryRun=False) 
        return
    print(f"Nenhuma AMI com o nome {name} para ser deletada\n")      


#  Função que cria um Security Group #
def create_security_group(client_ec2, security_gp_name, description):
    
    print("Criando Security Group\n")
    try:
        response = client_ec2.describe_vpcs()
        vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
        response = client_ec2.create_security_group(GroupName=security_gp_name,
                                            Description=description,
                                            VpcId=vpc_id)
        security_group_id = response['GroupId']
        print(f'Security Group {security_group_id} criado na vpc {vpc_id}')
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
        print(f'Security Group {security_gp_name } criado com sucesso!')
    
    except ClientError as e:
        print(e)


def delete_security_group(client_ec2, security_gp_name):
    try:
        print("Procurando Security Group para deletar...")
        for sg in client_ec2.describe_security_groups()['SecurityGroups']:
            if sg['GroupName'] == security_gp_name:
                print(f"Security Group {security_gp_name} já existe! Deletando para criar um novo")
                client_ec2.delete_security_group(GroupName=security_gp_name)
                return
        print("Nenhum Security Group com este nome encontrado!")
    except ClientError as e:
        print("Esperando instâncias 'Available' serem deletadas...")
        time.sleep(60)
        delete_security_group(client_ec2, security_gp_name)

def get_instance_id_by_tag(client_ec2, tag_val):
        filter = [
            {'Name': 'tag:instance-proj', 
            'Values': [tag_val]},
            {'Name': 'instance-state-name', 
            'Values': ['running']
            }]    
        ids=[]
        response = client_ec2.describe_instances(Filters=filter)
        for reservation in response["Reservations"]:
                instanceid = reservation['Instances'][0]['InstanceId']
                ids.append(instanceid)
        return ids


# Função que pega o IP de uma instância pelo ID
def get_ip_by_id(resource_ec2, instance_id):
    running_instances = resource_ec2.instances.filter(Filters=[
    {'Name': 'instance-state-name',
    'Values': ['pending', 'running']}
    ])
    print("Buscando ip da instância...")
    for instance in running_instances:
        if instance.id==instance_id:
            ip=instance.public_ip_address
            print(f"Instância com id={instance_id} possui o ip={ip}\n")
            return ip


def create_lb(client_ec2, client_lb, name, security_gp, tag_key, tag_val):
    try:

        response = client_ec2.describe_security_groups(Filters=[
            {'Name':'group-name', 
            'Values':[security_gp]}])
        securitygp_id = response['SecurityGroups'][0]['GroupId']
        
        print(f"Security group id: {securitygp_id}")
        subnets_list = []
        subnets = client_ec2.describe_subnets()
        for subnet in subnets['Subnets']:
            id_subnet = subnet["SubnetId"]
            subnets_list.append(id_subnet)
        print(f"Subnets: {subnets_list}")

        lb = client_lb.create_load_balancer(
            LoadBalancerName=name,
            Listeners=[{   
                    'Protocol': 'TCP',
                    'LoadBalancerPort': 8080,
                    'InstanceProtocol': 'TCP',
                    'InstancePort': 8080},{   
                    'Protocol': 'HTTP',
                    'LoadBalancerPort': 80,
                    'InstanceProtocol': 'HTTP',
                    'InstancePort': 80
                }],
            Subnets=subnets_list,
            SecurityGroups=[securitygp_id],
            Tags=[{
                    'Key': tag_key,
                    'Value': tag_val
                }]
        )
        dns = lb["DNSName"]
        print(f"LoadBalancer criado com DNS={dns}")
        return dns
    except ClientError as e:
        print("LoadBalancer já existe!")
        print(f"\n\n{e}\n\n")


def create_launch_configuration(client_ec2, client_asg, name, AMI_name, KeyName, securitygp, instanceType, user_data):
        try:
            response = client_ec2.describe_images(
            Filters=[{
                    'Name': 'name',
                    'Values': [AMI_name]
            }])
            list_ids=[]
            for img in response["Images"]:
                list_ids.append(img["ImageId"])
            print(f"AMIs disponíveis com essas especificações: {list_ids}")
            AMI_id=list_ids[0]
            print(f"AMI a ser utilizada{AMI_id}")

            client_asg.create_launch_configuration(
                LaunchConfigurationName=name,
                UserData=user_data,
                ImageId=AMI_id,
                KeyName=KeyName,
                SecurityGroups=[securitygp],        
                InstanceType=instanceType
            )
            print("Launch Configuration criada com sucesso")

        except ClientError as e:
            print("Launch Configuration já existe")
            print(f"\n\n{e}\n\n")


def autoscallig_group(client_asg, name, launch_config, tag_key, tag_value, load_balancer):
    try:
        client_asg.create_auto_scaling_group(
            AutoScalingGroupName=name,
            LaunchConfigurationName=launch_config,       
            MinSize=1,
            MaxSize=10,
            DesiredCapacity=2,
            AvailabilityZones=[
                    'us-east-1a',
                    'us-east-1b',
                    'us-east-1c',
                    'us-east-1d',
                    'us-east-1e'
            ],
            LoadBalancerNames=[load_balancer],
            Tags=[{
                    'Key': tag_key,
                    'Value': tag_value
                }]
        )
        print("AutoScaling Group criado com sucesso")

    except ClientError as e:
            print("AutoScaling Group já existe")
            print(f"\n\n{e}\n\n")


def save_dns_address(dns):
    if os.path.exists('dns.py'):
        os.remove('dns.py')
    with open('dns.py','w') as fout :
        fout.write(f'dns_address="http://{dns}:8080/tasks"')


def attach_lb_to_autoscaling(client_asg, autoscal_name, lb_name):
    try:
        client_asg.attach_load_balancers(
            AutoScalingGroupName=autoscal_name,
            LoadBalancerNames=[lb_name]
        )
        print("anexando Load Balancer ao Autoscalling Group")
    except ClientError as e:
        print(f"\n\n{e}\n\n")


def delete_lb(client_lb, name):
    try:
        lbs = client_lb.describe_load_balancers(
            LoadBalancerNames=[name]
        )
        for lb in lbs['LoadBalancerDescriptions']:
            if lb['LoadBalancerName']==name:
                print(f"Deletando Load Balancer {name}")
                client_lb.delete_load_balancer(LoadBalancerName=name)
                return
        print("Nenhum Load Balancer com esse nome existe ainda")
    except ClientError as e:
        if 'LoadBalancerNotFound' in e.response['Error']['Code']:
            print("Nenhum Load Balancer com esse nome existe ainda")


def delete_autoscalling_group(client_asg, name):

    instance_ids=[]
    asgs = client_asg.describe_auto_scaling_groups(AutoScalingGroupNames=[name])
    for asg in asgs['AutoScalingGroups']:
        if asg['AutoScalingGroupName']==name:
            for k in asg['Instances']:
                instance_ids.append(k['InstanceId'])
            print(f"Deletando AutoScaling Group {name}")
            client_asg.delete_auto_scaling_group(AutoScalingGroupName=name,ForceDelete=True)
            return instance_ids
    print("Nenhum AutoScaling Group existe ainda com esse nome")
    
    
def delete_launch_config(client_asg, name):
    lcs = client_asg.describe_launch_configurations(LaunchConfigurationNames=[name])
    
    for lc in lcs['LaunchConfigurations']:
        if lc['LaunchConfigurationName']==name:
            print(f"Deletando Launch Configuration {name}")
            client_asg.delete_launch_configuration(LaunchConfigurationName=name)
            return
    print("Nenhuma Launch Configuration existe ainda com esse nome")
    

def delete_key_pair(client, key_dir, key_name):
    try:
        keys=client.describe_key_pairs(
            KeyNames=[key_name]
        )
        exists=False
        for key in keys['KeyPairs']:
            if key['KeyName']==key_name:
                exists=True

        if exists:
            print(f"Chave {key_name} já existe, deletando para criar uma nova...")
            print(f"Deletando arquivo {key_dir}")
            if os.path.exists(key_dir):
                os.remove(key_dir)
            if not os.path.exists(key_dir):
                print("Arquivo deletado com sucesso!")
            client.delete_key_pair(KeyName=key_name)
            print("chave deletada com sucesso!\n")
    except ClientError as e:
        print(e.response['Error']['Code'])
        if 'InvalidKeyPair.NotFound' in e.response['Error']['Code']:
            print("Nenhuma chave com este nome para deletar\n")
            

def attach_policy_to_autoscaling(client_asg, asg_name, policy_name):
    try:
        client_asg.put_scaling_policy(
            AutoScalingGroupName=asg_name,
            PolicyName=policy_name,
            PolicyType='TargetTrackingScaling',
            TargetTrackingConfiguration={
                'PredefinedMetricSpecification': {
                    'PredefinedMetricType': 'ASGAverageCPUUtilization'
                },
                'TargetValue': 25.0,
                # 'DisableScaleIn': True
            },
            Enabled=True
        )
        print("Policy vinculada ao autoscaling group com sucesso!\n")
    except ClientError as e:
        print(e)

#**************************************************#
# ******************** SCRIPT ******************** #
#**************************************************#

print("----------------------------------------")
print("---------- COMEÇANDO O SCRIPT ----------")
print("----------------------------------------")
print()
logger.info('***** COMEÇO DO SCRIPT DE IMPLEMENTAÇÃO *****')

print("* APAGANDO COISAS ANTERIORES")

logger.info('Apagando LOAD BALANCER, AUTOSCALING GROUP E LAUNCH CONFIGURATION se já existem')
# ----- Apagando LOAD BALANCER, AUTOSCALING GROUP E LAUNCH CONFIGURATION se já existem ----- #
instance_ids_list = delete_autoscalling_group(client_asg, AUTOSCALING_NAME)
delete_launch_config(client_asg, LAUNCH_CONFIG_NAME)
delete_lb(client_lb, LB_NAME)


# ----- Apagando instância de OHIO se já existe ----- #
print("Deletando instâncias antigas existentes em OHIO...\n")
old_ohio_id = get_instance_id_by_tag(client_OHIO, TAG_VAL_OHIO)
print(f"ID da instância antiga: {old_ohio_id}\n")
if old_ohio_id:
    for inst_id in old_ohio_id:
        terminate_instance(client_OHIO, resource_OHIO, inst_id)
        logger.info('Apagando instância de OHIO')

# ----- Apagando instância de NORTH VIRGINIA se já existe ----- #
print("Deletando instâncias antigas existentes...\n")
old_NV_id = get_instance_id_by_tag(client_NVIRGINIA, TAG_VAL_NVIR)
print(f"ID da instância antiga: {old_NV_id}\n")
if old_NV_id:
    for inst_id in old_NV_id:
        terminate_instance(client_NVIRGINIA, resource_NVIRGINIA, inst_id)
        logger.info('Apagando instância de NORTH VIRGINIA')

delete_image(client_NVIRGINIA, resource_NVIRGINIA, AMI_NV)

# ----- Esperando até tudo estar terminated ----- #
print("Esperando as instâncias serem deletadas...")
if old_ohio_id:
    waiter_terminated = client_OHIO.get_waiter('instance_terminated')
    for inst_id in old_ohio_id:
        waiter_terminated.wait(InstanceIds=[inst_id])

if old_NV_id:
    waiter_terminated = client_NVIRGINIA.get_waiter('instance_terminated')
    for inst_id in old_NV_id:
        waiter_terminated.wait(InstanceIds=[inst_id])

print("\n*&***************")
print(instance_ids_list)
if instance_ids_list:
    waiter_terminated = client_NVIRGINIA.get_waiter('instance_terminated')
    for inst_id in instance_ids_list:
        waiter_terminated.wait(InstanceIds=[inst_id])

logger.info('Instâncias deletadas')


# ----- Apagando KEY PAIRS ----- #
delete_key_pair(client_OHIO, KEY_DIR, KEY_NAME)
delete_key_pair(client_NVIRGINIA, KEY_DIR_NV, KEY_NAME_NV)
logger.info('Key pairs deletados')

# ----- Apagando SECURITY GROUPS ----- #
delete_security_group(client_OHIO, SECURITY_GROUP_NAME_OHIO)
delete_security_group(client_NVIRGINIA, SECURITY_GROUP_NAME_NVIR)
logger.info('Security Groups deletados')



# --------------- Instância de OHIO --------------- #
print("----------------- OHIO -----------------")
print()
print("* CRIANDO UM KEY PAIR PARA OHIO")
logger.info('CRIANDO UM KEY PAIR PARA OHIO')
create_key_pair(client_OHIO, KEY_DIR, KEY_NAME)
print()
print("* CRIANDO UM SECURITY GROUP PARA OHIO")
logger.info('CRIANDO UM SECURITY GROUP PARA OHIO')
create_security_group(client_OHIO, SECURITY_GROUP_NAME_OHIO, SECURITY_GROUP_DESCRIPTION_OHIO)
print()
print("* INSTÂNCIA DE OHIO")

# --------------- UserData OHIO --------------- #
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

# ----- Criando instância ----- #
print("Criando instância de OHIO...")
logger.info('Criando instância de OHIO (postgres)')

instance_OHIO_id = create_instance(client_OHIO, AMI_UBUNTU_LTS_OHIO, INSTANCE_TYPE, KEY_NAME, USER_DATA_POSTGRES, SECURITY_GROUP_NAME_OHIO, TAG_KEY, TAG_VAL_OHIO)

instance = resource_OHIO.Instance(id=instance_OHIO_id)
print("Esperando a instância estar rodando...\n")
instance.wait_until_running()


# --------------- Instância de NORTH VIRGINIA --------------- #
print("------------- NORTH VIRGINIA -------------\n")

print("* INSTÂNCIA DE NORTH VIRGINIA\n")
print("* CRIANDO UM KEY PAIR PARA NORTH VIRGINIA")
logger.info('CRIANDO UM KEY PAIR PARA NORTH VIRGINIA')
create_key_pair(client_NVIRGINIA, KEY_DIR_NV, KEY_NAME_NV)


print("* CRIANDO UM SECURITY GROUP PARA NORTH VIRGINIA")
logger.info('CRIANDO UM SECURITY GROUP PARA NORTH VIRGINI')
create_security_group(client_NVIRGINIA, SECURITY_GROUP_NAME_NVIR, SECURITY_GROUP_DESCRIPTION_NVIR)
print()

# --------------- UserData NORTH VIRGINIA --------------- #
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

# ----- Criando instância ----- #
instance_NVIRGINIA_id = create_instance(client_NVIRGINIA, AMI_UBUNTU_LTS_NVIR, INSTANCE_TYPE, KEY_NAME_NV, USER_DATA_ORM, SECURITY_GROUP_NAME_NVIR, TAG_KEY, TAG_VAL_NVIR)
instance = resource_NVIRGINIA.Instance(id=instance_NVIRGINIA_id)
print("Esperando a instância estar rodando...")
waiter_status_ok = client_NVIRGINIA.get_waiter("instance_status_ok")
waiter_status_ok.wait(InstanceIds=[ instance_NVIRGINIA_id])

logger.info('CRIANDO INSTÂNCIA PARA NORTH VIRGINIA (Django ORM)')
# ----- Criando AMI e deletando instância ----- #
create_image(client_NVIRGINIA, instance_NVIRGINIA_id, AMI_NV)
logger.info('CRIANDO AMI DA INSTÂNCIA DE NORTH VIRGINIA')

terminate_instance(client_NVIRGINIA, resource_NVIRGINIA, instance_NVIRGINIA_id)
logger.info('DELETANDO INSTÂNCIA ORIGINAL DE NORTH VIRGINIA')

# ----- Criando Load Balancer----- #
dns=create_lb(client_NVIRGINIA, client_lb, LB_NAME, SECURITY_GROUP_NAME_NVIR, TAG_KEY, TAG_VAL_LB)
save_dns_address(dns)
logger.info('CRIANDO LOAD BALANCER')

# ----- Criando Launch Configuration e AutoScaling Group ----- #
create_launch_configuration(client_NVIRGINIA, client_asg, LAUNCH_CONFIG_NAME, AMI_NV, KEY_NAME_NV, SECURITY_GROUP_NAME_NVIR, INSTANCE_TYPE, USER_DATA_ORM)
logger.info('CRIANDO LOAD LAUNCH CONFIGURATION')
autoscallig_group(client_asg, AUTOSCALING_NAME, LAUNCH_CONFIG_NAME, TAG_KEY, TAG_VAL_ASG, LB_NAME)
logger.info('CRIANDO AUTOSCALING GROUP')
attach_lb_to_autoscaling(client_asg, AUTOSCALING_NAME, LB_NAME)
attach_policy_to_autoscaling(client_asg, AUTOSCALING_NAME, POLICY_NAME)
logger.info('ADICIONANDO POLICY AO ASG')

logger.info('***** FIM DO SCRIPT DE IMPLEMENTAÇÃO *****')

print("\n\n   ----------------------- FIM DO SCRIPT -----------------------\n")
print("Espere até pelo menos uma instância do AutoScaling Group estar rodando para testar o Client\n")
print("--------------------------------------------------------------------")






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
http://boto.cloudhackers.com/en/latest/elb_tut.html
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elb.html
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/autoscaling.html
'''


# LOGS
# https://operatingops.com/2019/02/20/python-boto3-logging/
# https://gist.github.com/olegdulin/fd18906343d75142a487b9a9da9042e0

# VPN
# https://pypi.org/project/openvpn-api/