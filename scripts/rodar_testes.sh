#!/bin/bash
# Executa os testes gerados pela IA com pytest e salva o resultado.

set -e

PASTA_TESTES="./testes"
RESULTADO="$PASTA_TESTES/resultado_pytest.txt"

if [ -z "$(ls $PASTA_TESTES/test_*.py 2>/dev/null)" ]; then
    echo "Nenhum teste gerado encontrado em $PASTA_TESTES"
    echo "Execute o produtor.py e worker.py primeiro."
    exit 1
fi

echo "Executando testes gerados pela IA..."
python3 -m pytest "$PASTA_TESTES" -v --tb=short 2>&1 | tee "$RESULTADO"
echo ""
echo "Resultado salvo em $RESULTADO"
