import os
import time
import random
import shutil
import logging
import json
import boto3

sqs = boto3.client('sqs', region_name='us-east-1')

QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/392545903651/fila-analise-codigo'

# Logging estruturado
os.makedirs('logs', exist_ok=True)

class _JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "componente": "produtor",
            "msg": record.getMessage()
        }, ensure_ascii=False)

_handler = logging.FileHandler('logs/produtor.log', encoding='utf-8')
_handler.setFormatter(_JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[_handler, logging.StreamHandler()])


def chamar_com_retry(funcao, max_tentativas=3, espera_base=2):
    for tentativa in range(max_tentativas):
        try:
            return funcao()
        except Exception as e:
            if tentativa == max_tentativas - 1:
                raise
            espera = espera_base * (2 ** tentativa) + random.uniform(0, 1)
            logging.warning(f"Tentativa {tentativa + 1}/{max_tentativas} falhou: {e}. Aguardando {espera:.1f}s...")
            time.sleep(espera)


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
                caminho_completo = os.path.join(raiz, arquivo)
                enviar_codigo_para_fila(caminho_completo)
                arquivos_enviados += 1

    os.makedirs('testes', exist_ok=True)
    with open(os.path.join('testes', 'total_arquivos.txt'), 'w') as f_total:
        f_total.write(str(arquivos_enviados))

    logging.info(f"Total de {arquivos_enviados} arquivos enviados para a fila.")


if __name__ == "__main__":
    PASTA_DE_TESTE = "./meu_codigo"

    if not os.path.exists(PASTA_DE_TESTE):
        os.makedirs(PASTA_DE_TESTE)
        print(f"Pasta '{PASTA_DE_TESTE}' criada. Coloca lá ficheiros .py e corre o script outra vez!")
    else:
        pasta_analises = os.path.join('testes', 'analises')
        if os.path.exists(pasta_analises):
            shutil.rmtree(pasta_analises)
        os.makedirs(pasta_analises, exist_ok=True)

        os.makedirs('testes', exist_ok=True)
        with open(os.path.join('testes', 'tempo_inicio.txt'), 'w') as f_tempo:
            f_tempo.write(str(time.time()))

        escanear_pasta_e_enviar(PASTA_DE_TESTE)
