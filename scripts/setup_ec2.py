"""
Provisiona uma instância EC2 com Ollama para servir o modelo llama3.2:3b.
Cria também o Security Group necessário.

Uso:
    python3 scripts/setup_ec2.py

Pré-requisito:
    AWS CLI configurado (~/.aws/credentials) com permissões EC2.
    Par de chaves SSH já criado na conta (KEY_PAIR_NAME abaixo).
"""
import boto3
import os

REGIAO = 'us-east-1'
KEY_PAIR_NAME = os.environ.get('AWS_KEY_PAIR', 'vockey')   # nome do par de chaves na sua conta
INSTANCE_TYPE = 't3.large'   # CPU-only; trocar por g4dn.xlarge se GPU disponível
AMI_ID = 'ami-0c02fb55956c7d316'  # Amazon Linux 2023 us-east-1 (verifique se é atual na sua conta)

USER_DATA = open(os.path.join(os.path.dirname(__file__), 'ec2_setup_ollama.sh')).read()


def criar_security_group(ec2):
    nome = 'ollama-sg'
    try:
        resp = ec2.create_security_group(
            GroupName=nome,
            Description='Acesso ao Ollama (porta 11434) e SSH (22)'
        )
        sg_id = resp['GroupId']
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {'IpProtocol': 'tcp', 'FromPort': 11434, 'ToPort': 11434,
                 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Ollama API'}]},
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22,
                 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH'}]},
            ]
        )
        print(f"Security Group criado: {sg_id}")
        return sg_id
    except ec2.exceptions.ClientError as e:
        if 'already exists' in str(e):
            sgs = ec2.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': [nome]}])
            sg_id = sgs['SecurityGroups'][0]['GroupId']
            print(f"Security Group já existe: {sg_id}")
            return sg_id
        raise


def provisionar_ec2():
    ec2 = boto3.client('ec2', region_name=REGIAO)
    ec2_resource = boto3.resource('ec2', region_name=REGIAO)

    sg_id = criar_security_group(ec2)

    print(f"Criando instância EC2 ({INSTANCE_TYPE})...")
    instancias = ec2_resource.create_instances(
        ImageId=AMI_ID,
        InstanceType=INSTANCE_TYPE,
        KeyName=KEY_PAIR_NAME,
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[sg_id],
        UserData=USER_DATA,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'tema7-ollama-worker'}]
        }]
    )

    instancia = instancias[0]
    print(f"Instância criada: {instancia.id} | Aguardando ficar 'running'...")
    instancia.wait_until_running()
    instancia.reload()

    ip_publico = instancia.public_ip_address
    print(f"\n=== EC2 pronta ===")
    print(f"ID:         {instancia.id}")
    print(f"IP Público: {ip_publico}")
    print(f"SSH:        ssh -i ~/.ssh/{KEY_PAIR_NAME}.pem ec2-user@{ip_publico}")
    print(f"\nAguarde ~3 minutos para o Ollama inicializar e o modelo ser baixado.")
    print(f"Depois rode os workers com:")
    print(f"  $env:OLLAMA_HOST = 'http://{ip_publico}:11434'  # PowerShell")
    print(f"  python worker.py")
    print(f"\nOu teste direto: curl http://{ip_publico}:11434/api/tags")


if __name__ == "__main__":
    provisionar_ec2()
