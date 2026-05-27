import os
import time
import shutil
import logging
import boto3
from utils import chamar_com_retry, configurar_logging

QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/392545903651/fila-analise-codigo'
S3_BUCKET = os.environ.get('S3_BUCKET', '')

sqs = boto3.client('sqs', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1') if S3_BUCKET else None

configurar_logging('logs/produtor.log', {"componente": "produtor"})


def enviar_codigo_para_fila(caminho_arquivo):
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            conteudo_codigo = f.read()

        nome_arquivo = os.path.basename(caminho_arquivo)
        nome_modulo = os.path.splitext(nome_arquivo)[0]
        corpo_mensagem = f"===NOME_ARQUIVO==={nome_arquivo}\n===MODULO==={nome_modulo}\n===CONTEUDO===\n{conteudo_codigo}"

        response = chamar_com_retry(
            lambda: sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=corpo_mensagem)
        )
        logging.info(f"Arquivo enviado: {nome_arquivo} | MessageId: {response['MessageId']}")

    except Exception as e:
        logging.error(f"Erro ao enviar {caminho_arquivo}: {e}")


def escanear_pasta_e_enviar(diretorio_alvo):
    logging.info(f"Escaneando pasta: {diretorio_alvo}")
    arquivos_enviados = 0

    for raiz, _, arquivos in os.walk(diretorio_alvo):
        for arquivo in arquivos:
            if arquivo.endswith('.py') and not arquivo.startswith('__'):
                enviar_codigo_para_fila(os.path.join(raiz, arquivo))
                arquivos_enviados += 1

    os.makedirs('testes', exist_ok=True)
    with open(os.path.join('testes', 'total_arquivos.txt'), 'w') as f:
        f.write(str(arquivos_enviados))

    if S3_BUCKET:
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix='testes/analises/'):
            for obj in page.get('Contents', []):
                s3.delete_object(Bucket=S3_BUCKET, Key=obj['Key'])
        s3.put_object(Bucket=S3_BUCKET, Key='testes/total_arquivos.txt',
                      Body=str(arquivos_enviados).encode())
        s3.put_object(Bucket=S3_BUCKET, Key='testes/tempo_inicio.txt',
                      Body=str(time.time()).encode())
        logging.info(f"Arquivos de controle enviados para S3: s3://{S3_BUCKET}/testes/")

    logging.info(f"Total de {arquivos_enviados} arquivos enviados para a fila.")


if __name__ == "__main__":
    PASTA_CODIGO = "./meu_codigo"

    if not os.path.exists(PASTA_CODIGO):
        os.makedirs(PASTA_CODIGO)
        print(f"Pasta '{PASTA_CODIGO}' criada. Adicione arquivos .py e rode novamente.")
    else:
        pasta_analises = os.path.join('testes', 'analises')
        if os.path.exists(pasta_analises):
            shutil.rmtree(pasta_analises)
        os.makedirs(pasta_analises, exist_ok=True)

        with open(os.path.join('testes', 'tempo_inicio.txt'), 'w') as f:
            f.write(str(time.time()))

        escanear_pasta_e_enviar(PASTA_CODIGO)
