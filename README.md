# Gerador Paralelo de Testes e Análise de Código

Sistema distribuído que recebe arquivos Python, distribui entre workers via AWS SQS e usa um SLM local (Ollama) para gerar testes unitários automaticamente. Tema 7 — Programação Distribuída e Paralela.

## Arquitetura

```
meu_codigo/*.py
      |
  [Produtor]
  produtor.py
      |
   AWS SQS
  (fila-analise-codigo)
      |
  ┌───┴───┐
[Worker 1] [Worker 2]   ← processos independentes (paralelismo real)
  worker.py worker.py
      |          |
  [Ollama llama3.2:3b]  ← SLM local auto-hospedado
      |          |
  └───┬───┘
  [Agregador]
  agregador.py
      |
  testes/relatorio_final_consolidado.json
```

**Fluxo:**
1. Produtor escaneia `meu_codigo/`, envia cada `.py` como mensagem SQS
2. Workers consomem em paralelo, chamam o LLM e salvam os testes em `testes/`
3. Ao terminar todos os arquivos, o agregador consolida métricas e detecta conflitos

## Pré-requisitos

- Python 3.8+
- [Ollama](https://ollama.com) instalado localmente
- AWS CLI configurado (`~/.aws/credentials`) com acesso ao SQS

```bash
pip install boto3 ollama
ollama pull llama3.2:3b
```

## Setup

### 1. Criar a infraestrutura AWS

```bash
python3 scripts/setup_aws.py
```

Isso cria a fila SQS principal e a Dead Letter Queue vinculada. Copie a URL gerada e substitua `QUEUE_URL` em `produtor.py` e `worker.py`.

### 2. Colocar os arquivos a analisar

Coloque os arquivos `.py` que deseja analisar na pasta `meu_codigo/`.

## Como Rodar

### Execução simples (1 worker)

```bash
# Terminal 1
python3 produtor.py

# Terminal 2
python3 worker.py
```

### Execução paralela (múltiplos workers)

```bash
# Terminal 1 — envia os arquivos para a fila
python3 produtor.py

# Terminal 2 — worker 1
python3 worker.py

# Terminal 3 — worker 2 (em paralelo)
python3 worker.py
```

O campo `workers_utilizados` no relatório final mostrará os IDs dos dois workers.

### Modo detecção de code smells

```bash
MODO_ANALISE=smells python3 worker.py
```

## Resultados

| Arquivo | Conteúdo |
|---|---|
| `testes/test_*.py` | Testes gerados pela IA |
| `testes/analises/*.json` | Relatório individual por arquivo |
| `testes/relatorio_final_consolidado.json` | Métricas agregadas |
| `testes/dlq/*.json` | Mensagens que falharam após 5 tentativas |
| `metricas_performance.txt` | CSV: arquivo, latência, status, worker, tokens, chunks |
| `logs/worker_<id>.log` | Log estruturado em JSON por worker |

### Executar os testes gerados

```bash
bash scripts/rodar_testes.sh
```

## Estrutura do Projeto

```
distribuido/
├── prompts/
│   ├── v1_gerar_testes.txt     # Prompt para geração de testes
│   └── v2_detectar_smells.txt  # Prompt para detecção de code smells
├── scripts/
│   ├── setup_aws.py            # Cria filas SQS e DLQ na AWS
│   └── rodar_testes.sh         # Executa os testes gerados com pytest
├── meu_codigo/                 # Arquivos Python a analisar
├── testes/                     # Saída: testes gerados + relatórios
├── logs/                       # Logs estruturados em JSON
├── produtor.py                 # Envia arquivos para a fila SQS
├── worker.py                   # Consome fila, chama LLM, salva testes
└── agregador.py                # Consolida métricas e detecta conflitos
```

## Tolerância a Falhas

| Ponto crítico | Estratégia |
|---|---|
| Falha no Ollama | Retry com exponential backoff (3 tentativas, espera 2s → 4s → 8s) |
| Falha no SQS | Retry com exponential backoff nas chamadas receive/delete |
| Mensagem processada 5+ vezes | Movida para DLQ local (`testes/dlq/`) e removida da fila |
| Worker cai no meio | Mensagem volta para a fila após `VisibilityTimeout` (120s) |

## Bônus SLM

Este projeto usa Ollama com `llama3.2:3b` auto-hospedado em vez do Amazon Bedrock, o que permite controle total da infraestrutura de inferência e demonstração direta do impacto do paralelismo no throughput de tokens por segundo.
