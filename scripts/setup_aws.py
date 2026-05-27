"""
Script de setup da infraestrutura AWS.
Cria a fila SQS principal e a Dead Letter Queue vinculada.

Uso:
    python3 scripts/setup_aws.py
"""
import json
import boto3

REGIAO = 'us-east-1'
NOME_FILA = 'fila-analise-codigo'
NOME_DLQ = 'fila-analise-codigo-dlq'
NOME_BUCKET = 'tema7-pdp-resultados'
MAX_RECEIVE_COUNT = 5       # Tentativas antes de ir para DLQ
VISIBILITY_TIMEOUT = 120    # Segundos para processar uma mensagem


def criar_infraestrutura():
    sqs = boto3.client('sqs', region_name=REGIAO)
    s3 = boto3.client('s3', region_name=REGIAO)

    print("Criando Dead Letter Queue...")
    resp_dlq = sqs.create_queue(
        QueueName=NOME_DLQ,
        Attributes={'MessageRetentionPeriod': '1209600'}  # 14 dias
    )
    dlq_url = resp_dlq['QueueUrl']
    dlq_arn = sqs.get_queue_attributes(
        QueueUrl=dlq_url, AttributeNames=['QueueArn']
    )['Attributes']['QueueArn']
    print(f"DLQ criada: {dlq_url}")

    print("Criando fila principal com DLQ vinculada...")
    try:
        resp = sqs.create_queue(
            QueueName=NOME_FILA,
            Attributes={
                'MessageRetentionPeriod': '86400',
                'VisibilityTimeout': str(VISIBILITY_TIMEOUT),
                'RedrivePolicy': json.dumps({
                    'deadLetterTargetArn': dlq_arn,
                    'maxReceiveCount': str(MAX_RECEIVE_COUNT)
                })
            }
        )
        main_url = resp['QueueUrl']
        print(f"Fila principal criada: {main_url}")
    except sqs.exceptions.QueueNameExists:
        main_url = sqs.get_queue_url(QueueName=NOME_FILA)['QueueUrl']
        print(f"Fila já existe: {main_url}")

    print("\nCriando bucket S3 para resultados compartilhados...")
    try:
        s3.create_bucket(Bucket=NOME_BUCKET)
        print(f"Bucket criado: s3://{NOME_BUCKET}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"Bucket já existe: s3://{NOME_BUCKET}")

    print("\n--- CONFIGURACAO ---")
    print(f"Substitua QUEUE_URL em produtor.py e worker.py por:")
    print(f"QUEUE_URL = '{main_url}'")
    print(f"\nExporte a variável S3_BUCKET nas instâncias EC2:")
    print(f"export S3_BUCKET='{NOME_BUCKET}'")


if __name__ == "__main__":
    criar_infraestrutura()
