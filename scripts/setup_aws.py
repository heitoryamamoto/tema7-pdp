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
MAX_RECEIVE_COUNT = 5       # Tentativas antes de ir para DLQ
VISIBILITY_TIMEOUT = 120    # Segundos para processar uma mensagem


def criar_infraestrutura():
    sqs = boto3.client('sqs', region_name=REGIAO)

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

    print("\n--- CONFIGURACAO ---")
    print(f"Substitua QUEUE_URL em produtor.py e worker.py por:")
    print(f"QUEUE_URL = '{main_url}'")


if __name__ == "__main__":
    criar_infraestrutura()
