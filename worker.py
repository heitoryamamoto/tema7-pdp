import time
import os
import json
import glob
import logging
import uuid
import boto3
import ollama
from agregador import consolidar_e_detectar_conflitos
from utils import chamar_com_retry, configurar_logging

WORKER_ID = str(uuid.uuid4())[:8]
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/392545903651/fila-analise-codigo'
DLQ_MAX_RECEIVES = 5
CHUNK_MAX_CHARS = 3000
POLLS_PARA_AGREGAR = 3

MODO_ANALISE = os.environ.get('MODO_ANALISE', 'testes')
PROMPT_FILE = 'prompts/v1_gerar_testes.txt' if MODO_ANALISE == 'testes' else 'prompts/v2_detectar_smells.txt'
OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2:1b')
S3_BUCKET = os.environ.get('S3_BUCKET', '')

sqs = boto3.client('sqs', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1') if S3_BUCKET else None
ollama_client = ollama.Client(host=OLLAMA_HOST)

configurar_logging(f'logs/worker_{WORKER_ID}.log', {"worker": WORKER_ID, "modo": MODO_ANALISE})


def carregar_system_prompt():
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        return f.read()


def chunkar_codigo(conteudo, max_chars=CHUNK_MAX_CHARS):
    """Divide código em chunks por definição de funções/classes se muito grande."""
    if len(conteudo) <= max_chars:
        return [conteudo]

    chunks, chunk_atual, tamanho = [], [], 0
    for linha in conteudo.split('\n'):
        nova_definicao = (linha.startswith('def ') or linha.startswith('class ')) and tamanho > max_chars // 2
        if nova_definicao and chunk_atual:
            chunks.append('\n'.join(chunk_atual))
            chunk_atual, tamanho = [linha], len(linha) + 1
        else:
            chunk_atual.append(linha)
            tamanho += len(linha) + 1

    if chunk_atual:
        chunks.append('\n'.join(chunk_atual))
    return chunks if chunks else [conteudo]


def combinar_testes(lista_codigos):
    """Combina testes de múltiplos chunks eliminando imports duplicados."""
    imports, corpo = set(), []
    for codigo in lista_codigos:
        for linha in codigo.splitlines():
            if linha.startswith('import ') or linha.startswith('from '):
                imports.add(linha)
            elif linha.strip():
                corpo.append(linha)
    return '\n'.join(sorted(imports)) + '\n\n' + '\n'.join(corpo)


def chamar_ia(nome_arquivo, codigo_chunk, nome_modulo, indice_chunk=1, total_chunks=1):
    system_prompt = carregar_system_prompt()
    contexto_chunk = f" (parte {indice_chunk}/{total_chunks})" if total_chunks > 1 else ""
    prompt_usuario = (
        f"Gere os testes unitários para o arquivo: {nome_arquivo}{contexto_chunk}\n"
        f"Use este import: from meu_codigo.{nome_modulo} import *\n\n"
        f"Código:\n{codigo_chunk}"
    )
    resposta = chamar_com_retry(
        lambda: ollama_client.chat(model=OLLAMA_MODEL, messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt_usuario}
        ])
    )
    return resposta['message']['content'], resposta.get('prompt_eval_count', 0), resposta.get('eval_count', 0)


def checar_fila_vazia_e_agregar():
    try:
        if S3_BUCKET:
            try:
                obj = s3.get_object(Bucket=S3_BUCKET, Key='testes/total_arquivos.txt')
                total_esperado = int(obj['Body'].read())
            except Exception as e:
                logging.warning(f"Não foi possível ler total_arquivos.txt do S3: {e}")
                return

            arquivos_analisados = s3.list_objects_v2(
                Bucket=S3_BUCKET, Prefix='testes/analises/'
            ).get('KeyCount', 0)

            if arquivos_analisados >= total_esperado:
                logging.info(f"Todos os {arquivos_analisados} arquivos no S3. Iniciando agregação...")
                time.sleep(1)
                consolidar_e_detectar_conflitos()
                s3.delete_object(Bucket=S3_BUCKET, Key='testes/total_arquivos.txt')
        else:
            caminho_total = os.path.join('testes', 'total_arquivos.txt')
            if not os.path.exists(caminho_total):
                return

            with open(caminho_total, 'r') as f:
                total_esperado = int(f.read())

            arquivos_analisados = len(glob.glob(os.path.join('testes', 'analises', '*.json')))

            if arquivos_analisados >= total_esperado:
                logging.info(f"Todos os {arquivos_analisados} arquivos processados. Iniciando agregação...")
                time.sleep(1)
                consolidar_e_detectar_conflitos()
                os.remove(caminho_total)
    except Exception as e:
        logging.error(f"Erro ao checar agregação: {e}")


def registrar_dlq(corpo_mensagem, receive_count, erro):
    pasta_dlq = os.path.join('testes', 'dlq')
    os.makedirs(pasta_dlq, exist_ok=True)
    entrada = {
        "ts": time.time(),
        "worker": WORKER_ID,
        "receive_count": receive_count,
        "erro": str(erro),
        "corpo_preview": corpo_mensagem[:300]
    }
    nome = os.path.join(pasta_dlq, f"dlq_{int(time.time())}_{WORKER_ID}.json")
    with open(nome, 'w', encoding='utf-8') as f:
        json.dump(entrada, f, indent=4, ensure_ascii=False)
    logging.warning(f"Mensagem movida para DLQ local: {nome}")


def processar_mensagem(corpo_mensagem):
    tempo_inicio = time.time()
    try:
        partes = corpo_mensagem.split('\n===CONTEUDO===\n')
        conteudo_codigo = partes[1]
        metadados = partes[0].split('\n===MODULO===')
        meta_nome = metadados[0].replace('===NOME_ARQUIVO===', '')
        meta_modulo = metadados[1]

        logging.info(f"Processando: {meta_nome} | {len(conteudo_codigo)} chars | modo={MODO_ANALISE}")

        chunks = chunkar_codigo(conteudo_codigo)
        if len(chunks) > 1:
            logging.info(f"Arquivo grande: dividido em {len(chunks)} chunks")

        resultados, tokens_prompt_total, tokens_resp_total = [], 0, 0
        for i, chunk in enumerate(chunks, 1):
            codigo_gerado, tp, tr = chamar_ia(meta_nome, chunk, meta_modulo, i, len(chunks))
            linhas_limpas = [l for l in codigo_gerado.splitlines() if '```' not in l]
            resultados.append('\n'.join(linhas_limpas))
            tokens_prompt_total += tp
            tokens_resp_total += tr

        codigo_final = combinar_testes(resultados) if len(resultados) > 1 else resultados[0]

        if "meu_codigo" not in codigo_final:
            import_obrigatorio = f"import pytest\nfrom meu_codigo.{meta_modulo} import *\n\n"
            codigo_final = import_obrigatorio + codigo_final.replace("import pytest", "").strip()

        os.makedirs('testes', exist_ok=True)
        with open(os.path.join('testes', f"test_{meta_nome}"), 'w', encoding='utf-8') as f:
            f.write(codigo_final)

        latencia = time.time() - tempo_inicio
        pasta_analises = os.path.join('testes', 'analises')
        os.makedirs(pasta_analises, exist_ok=True)

        relatorio = {
            "arquivo_original": meta_nome,
            "modulo": meta_modulo,
            "status": "Sucesso",
            "latencia_segundos": round(latencia, 2),
            "tokens_prompt": tokens_prompt_total,
            "tokens_resposta": tokens_resp_total,
            "chunks_processados": len(chunks),
            "worker_id": WORKER_ID,
            "modo_analise": MODO_ANALISE,
        }

        caminho_resumo = os.path.join(pasta_analises, f"resumo_{meta_modulo}.json")
        with open(caminho_resumo, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=4)

        if S3_BUCKET:
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=f'testes/analises/resumo_{meta_modulo}.json',
                Body=json.dumps(relatorio, indent=4).encode('utf-8'),
                ContentType='application/json'
            )

        logging.info(
            f"Concluído: {meta_nome} | latência={latencia:.2f}s | "
            f"chunks={len(chunks)} | tokens={tokens_prompt_total + tokens_resp_total}"
        )

        with open('metricas_performance.txt', 'a') as f:
            f.write(f"{meta_nome},{latencia:.2f},Sucesso,{WORKER_ID},"
                    f"{tokens_prompt_total},{tokens_resp_total},{len(chunks)}\n")

        return True
    except Exception as e:
        logging.error(f"Erro ao processar mensagem: {e}")
        return False


def iniciar_worker():
    logging.info(f"Worker {WORKER_ID} iniciado | modo={MODO_ANALISE} | modelo={OLLAMA_MODEL} | ollama={OLLAMA_HOST}")
    polls_vazios_consecutivos = 0

    while True:
        try:
            response = chamar_com_retry(
                lambda: sqs.receive_message(
                    QueueUrl=QUEUE_URL,
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=10,
                    AttributeNames=['ApproximateReceiveCount']
                )
            )

            if 'Messages' not in response:
                polls_vazios_consecutivos += 1
                logging.info(f"Fila vazia. Aguardando... ({polls_vazios_consecutivos}/{POLLS_PARA_AGREGAR})")
                if polls_vazios_consecutivos >= POLLS_PARA_AGREGAR:
                    checar_fila_vazia_e_agregar()
                    polls_vazios_consecutivos = 0
                continue

            mensagem = response['Messages'][0]
            receipt_handle = mensagem['ReceiptHandle']
            corpo = mensagem['Body']
            receive_count = int(mensagem.get('Attributes', {}).get('ApproximateReceiveCount', 1))

            if receive_count >= DLQ_MAX_RECEIVES:
                registrar_dlq(corpo, receive_count, "Excedeu tentativas máximas")
                chamar_com_retry(lambda: sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle))
                logging.warning(f"Mensagem descartada para DLQ após {receive_count} recebimentos.")
                continue

            if processar_mensagem(corpo):
                chamar_com_retry(lambda: sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle))
                logging.info("Mensagem removida da fila.")
                polls_vazios_consecutivos = 0
                checar_fila_vazia_e_agregar()

        except KeyboardInterrupt:
            logging.info("Worker encerrado pelo usuário.")
            break
        except Exception as e:
            logging.error(f"Erro no loop principal: {e}")
            time.sleep(5)


if __name__ == "__main__":
    iniciar_worker()
