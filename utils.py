import os
import time
import random
import logging
import json


def chamar_com_retry(funcao, max_tentativas=3, espera_base=2):
    """Retry com exponential backoff para chamadas a serviços externos."""
    for tentativa in range(max_tentativas):
        try:
            return funcao()
        except Exception as e:
            if tentativa == max_tentativas - 1:
                raise
            espera = espera_base * (2 ** tentativa) + random.uniform(0, 1)
            logging.warning(f"Tentativa {tentativa + 1}/{max_tentativas} falhou: {e}. Aguardando {espera:.1f}s...")
            time.sleep(espera)


def configurar_logging(arquivo_log, campos_extras):
    """Logging estruturado em JSON com campos dinâmicos por componente."""
    os.makedirs('logs', exist_ok=True)

    class _JsonFormatter(logging.Formatter):
        def format(self, record):
            entrada = {
                "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                "level": record.levelname,
                "msg": record.getMessage()
            }
            entrada.update(campos_extras)
            return json.dumps(entrada, ensure_ascii=False)

    handler = logging.FileHandler(arquivo_log, encoding='utf-8')
    handler.setFormatter(_JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()])
