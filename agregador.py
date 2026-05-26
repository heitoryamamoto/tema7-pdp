import os
import json
import glob
import time

def consolidar_e_detectar_conflitos():
    print("🧐 [Agregador] Iniciando consolidação na pasta 'testes/analises'...")

    pasta_analises = os.path.join("testes", "analises")
    arquivos_json = glob.glob(os.path.join(pasta_analises, "*.json"))

    if not arquivos_json:
        print("⚠️ [Agregador] Nenhum relatório individual encontrado para agregar.")
        return

    relatorio_consolidado = {
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

    for caminho_json in arquivos_json:
        with open(caminho_json, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        relatorio_consolidado["total_arquivos_analisados"] += 1
        relatorio_consolidado["tempo_total_acumulado_cpu_segundos"] += dados.get("latencia_segundos", 0)
        relatorio_consolidado["total_tokens_prompt"] += dados.get("tokens_prompt", 0)
        relatorio_consolidado["total_tokens_resposta"] += dados.get("tokens_resposta", 0)

        if dados.get("worker_id"):
            workers_vistos.add(dados["worker_id"])

        if dados["status"] == "Sucesso":
            relatorio_consolidado["sucessos"] += 1
        else:
            relatorio_consolidado["falhas"] += 1

        nome_modulo = dados["modulo"]
        if nome_modulo in modulos_vistos:
            msg_conflito = f"⚠️ CONFLITO: O módulo '{nome_modulo}' foi processado mais de uma vez!"
            relatorio_consolidado["conflitos_detectados"].append(msg_conflito)
        else:
            modulos_vistos.add(nome_modulo)
            relatorio_consolidado["modulos_processados"].append(nome_modulo)

    if relatorio_consolidado["falhas"] > 0:
        relatorio_consolidado["conflitos_detectados"].append(
            f"❌ INCONSISTÊNCIA: {relatorio_consolidado['falhas']} arquivo(s) falharam."
        )

    relatorio_consolidado["workers_utilizados"] = list(workers_vistos)

    caminho_tempo_inicio = os.path.join('testes', 'tempo_inicio.txt')
    if os.path.exists(caminho_tempo_inicio):
        with open(caminho_tempo_inicio, 'r') as f_inicio:
            timestamp_inicio = float(f_inicio.read())
        tempo_real = time.time() - timestamp_inicio
        relatorio_consolidado["tempo_real_relogio_segundos"] = round(tempo_real, 2)
        if tempo_real > 0:
            relatorio_consolidado["throughput_arquivos_por_segundo"] = round(
                relatorio_consolidado["total_arquivos_analisados"] / tempo_real, 3
            )

    caminho_consolidado = os.path.join("testes", "relatorio_final_consolidado.json")
    with open(caminho_consolidado, "w", encoding="utf-8") as f_final:
        json.dump(relatorio_consolidado, f_final, indent=4)

    total_tokens = relatorio_consolidado["total_tokens_prompt"] + relatorio_consolidado["total_tokens_resposta"]
    print("\n========================================================")
    print("🏆 [Agregador] Relatório Final Consolidado com Sucesso!")
    print(f"📈 Total de Arquivos: {relatorio_consolidado['total_arquivos_analisados']}")
    print(f"⏱️ CPU (Soma das Latências): {relatorio_consolidado['tempo_total_acumulado_cpu_segundos']:.2f}s")
    print(f"⏳ Tempo Real de Relógio: {relatorio_consolidado['tempo_real_relogio_segundos']:.2f}s")
    print(f"🚀 Throughput: {relatorio_consolidado['throughput_arquivos_por_segundo']} arq/s")
    print(f"🔢 Tokens Totais: {total_tokens} (prompt={relatorio_consolidado['total_tokens_prompt']}, resposta={relatorio_consolidado['total_tokens_resposta']})")
    print(f"👷 Workers Utilizados: {relatorio_consolidado['workers_utilizados']}")
    print(f"⚠️ Conflitos Detectados: {len(relatorio_consolidado['conflitos_detectados'])}")
    print(f"💾 Relatório salvo em: {caminho_consolidado}")
    print("========================================================")


if __name__ == "__main__":
    consolidar_e_detectar_conflitos()
