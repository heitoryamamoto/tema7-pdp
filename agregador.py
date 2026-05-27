import os
import json
import glob
import time
import boto3

S3_BUCKET = os.environ.get('S3_BUCKET', '')
s3 = boto3.client('s3', region_name='us-east-1') if S3_BUCKET else None

def consolidar_e_detectar_conflitos():
    if S3_BUCKET:
        _consolidar_s3()
    else:
        _consolidar_local()


def _carregar_dados_s3():
    """Baixa todos os JSONs de análise do S3."""
    dados_lista = []
    resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix='testes/analises/')
    for obj in resp.get('Contents', []):
        body = s3.get_object(Bucket=S3_BUCKET, Key=obj['Key'])['Body'].read()
        dados_lista.append(json.loads(body))
    return dados_lista


def _consolidar_s3():
    print("🧐 [Agregador] Consolidando resultados do S3...")
    dados_lista = _carregar_dados_s3()

    if not dados_lista:
        print("⚠️ [Agregador] Nenhum relatório encontrado no S3.")
        return

    relatorio_consolidado = _calcular_relatorio(dados_lista)

    # Lê tempo_inicio do S3
    try:
        obj = s3.get_object(Bucket=S3_BUCKET, Key='testes/tempo_inicio.txt')
        timestamp_inicio = float(obj['Body'].read())
        tempo_real = time.time() - timestamp_inicio
        relatorio_consolidado["tempo_real_relogio_segundos"] = round(tempo_real, 2)
        if tempo_real > 0:
            relatorio_consolidado["throughput_arquivos_por_segundo"] = round(
                relatorio_consolidado["total_arquivos_analisados"] / tempo_real, 3)
    except Exception:
        pass

    resultado_json = json.dumps(relatorio_consolidado, indent=4)
    s3.put_object(Bucket=S3_BUCKET, Key='testes/relatorio_final_consolidado.json',
                  Body=resultado_json.encode('utf-8'), ContentType='application/json')

    os.makedirs('testes', exist_ok=True)
    with open(os.path.join('testes', 'relatorio_final_consolidado.json'), 'w', encoding='utf-8') as f:
        f.write(resultado_json)

    _imprimir_relatorio(relatorio_consolidado)


def _calcular_relatorio(dados_lista):
    relatorio = {
        "total_arquivos_analisados": 0,
        "sucessos": 0,
        "falhas": 0,
        "tempo_total_acumulado_cpu_segundos": 0.0,
        "tempo_real_relogio_segundos": 0.0,
        "throughput_arquivos_por_segundo": 0.0,
        "total_tokens_prompt": 0,
        "total_tokens_resposta": 0,
        "workers_utilizados": [],
        "modulos_processados": [],
        "conflitos_detectados": []
    }
    modulos_vistos = set()
    workers_vistos = set()

    for dados in dados_lista:
        relatorio["total_arquivos_analisados"] += 1
        relatorio["tempo_total_acumulado_cpu_segundos"] += dados.get("latencia_segundos", 0)
        relatorio["total_tokens_prompt"] += dados.get("tokens_prompt", 0)
        relatorio["total_tokens_resposta"] += dados.get("tokens_resposta", 0)
        if dados.get("worker_id"):
            workers_vistos.add(dados["worker_id"])
        if dados["status"] == "Sucesso":
            relatorio["sucessos"] += 1
        else:
            relatorio["falhas"] += 1
        nome_modulo = dados["modulo"]
        if nome_modulo in modulos_vistos:
            relatorio["conflitos_detectados"].append(
                f"⚠️ CONFLITO: O módulo '{nome_modulo}' foi processado mais de uma vez!")
        else:
            modulos_vistos.add(nome_modulo)
            relatorio["modulos_processados"].append(nome_modulo)

    if relatorio["falhas"] > 0:
        relatorio["conflitos_detectados"].append(
            f"❌ INCONSISTÊNCIA: {relatorio['falhas']} arquivo(s) falharam.")

    relatorio["workers_utilizados"] = list(workers_vistos)
    return relatorio


def _imprimir_relatorio(r):
    total_tokens = r["total_tokens_prompt"] + r["total_tokens_resposta"]
    print("\n========================================================")
    print("🏆 [Agregador] Relatório Final Consolidado com Sucesso!")
    print(f"📈 Total de Arquivos: {r['total_arquivos_analisados']}")
    print(f"⏱️ CPU (Soma das Latências): {r['tempo_total_acumulado_cpu_segundos']:.2f}s")
    print(f"⏳ Tempo Real de Relógio: {r['tempo_real_relogio_segundos']:.2f}s")
    print(f"🚀 Throughput: {r['throughput_arquivos_por_segundo']} arq/s")
    print(f"🔢 Tokens Totais: {total_tokens} (prompt={r['total_tokens_prompt']}, resposta={r['total_tokens_resposta']})")
    print(f"👷 Workers Utilizados: {r['workers_utilizados']}")
    print(f"⚠️ Conflitos Detectados: {len(r['conflitos_detectados'])}")
    print("========================================================")


def _consolidar_local():
    print("🧐 [Agregador] Iniciando consolidação na pasta 'testes/analises'...")
    pasta_analises = os.path.join("testes", "analises")
    arquivos_json = glob.glob(os.path.join(pasta_analises, "*.json"))

    if not arquivos_json:
        print("⚠️ [Agregador] Nenhum relatório individual encontrado para agregar.")
        return

    dados_lista = []
    for caminho_json in arquivos_json:
        with open(caminho_json, 'r', encoding='utf-8') as f:
            dados_lista.append(json.load(f))

    relatorio_consolidado = _calcular_relatorio(dados_lista)

    caminho_tempo_inicio = os.path.join('testes', 'tempo_inicio.txt')
    if os.path.exists(caminho_tempo_inicio):
        with open(caminho_tempo_inicio, 'r') as f_inicio:
            timestamp_inicio = float(f_inicio.read())
        tempo_real = time.time() - timestamp_inicio
        relatorio_consolidado["tempo_real_relogio_segundos"] = round(tempo_real, 2)
        if tempo_real > 0:
            relatorio_consolidado["throughput_arquivos_por_segundo"] = round(
                relatorio_consolidado["total_arquivos_analisados"] / tempo_real, 3)

    caminho_consolidado = os.path.join("testes", "relatorio_final_consolidado.json")
    with open(caminho_consolidado, "w", encoding="utf-8") as f_final:
        json.dump(relatorio_consolidado, f_final, indent=4)

    _imprimir_relatorio(relatorio_consolidado)
    print(f"💾 Relatório salvo em: {caminho_consolidado}")
    print("========================================================")


if __name__ == "__main__":
    consolidar_e_detectar_conflitos()
