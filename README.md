# Gerador Paralelo de Testes e Análise de Código

Sistema distribuído que recebe arquivos Python, distribui entre workers via AWS SQS e usa um SLM auto-hospedado (Ollama) em instâncias EC2 para gerar testes unitários automaticamente. Tema 7 — Programação Distribuída e Paralela.

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
  ┌───┴────────────────────┐
[Worker 1]              [Worker 2]     ← instâncias EC2 independentes
EC2 #1 (t3.small)       EC2 #2 (t3.small)
Ollama llama3.2:1b       Ollama llama3.2:1b
      |                       |
      └──────────┬────────────┘
              AWS S3
        (resultados compartilhados)
              |
          [Agregador]
          agregador.py
              |
    testes/relatorio_final_consolidado.json
```

**Fluxo:**
1. Produtor escaneia `meu_codigo/`, envia cada `.py` como mensagem SQS e registra controle no S3
2. Workers em instâncias EC2 separadas consomem a fila em paralelo, cada um com seu Ollama próprio
3. Cada worker salva o resultado da análise no S3 compartilhado
4. Quando todos os arquivos são processados, o agregador lê do S3 e consolida métricas globais

## Pré-requisitos

- Python 3.8+
- Instâncias EC2 com IAM Role `LabInstanceProfile` (acesso ao SQS e S3)

```bash
pip3 install boto3 ollama
```

## Setup

### 1. Criar infraestrutura AWS (SQS + S3)

```bash
python3 scripts/setup_aws.py
```

Cria a fila SQS principal, a Dead Letter Queue e o bucket S3 para resultados compartilhados.

### 2. Provisionar instâncias EC2

Para cada instância (recomendado: 2 instâncias t3.small):

- AMI: Amazon Linux 2023
- Instance type: `t3.small`
- Key pair: `vockey`
- IAM Role: `LabInstanceProfile`
- Security Group: porta 22 aberta

Conecte via SSH e rode em cada instância:

```bash
sudo yum install -y python3-pip git
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable ollama && sudo systemctl start ollama
ollama pull llama3.2:1b
pip3 install boto3 ollama
```

Ou use o script automatizado:

```bash
chmod +x scripts/deploy_ec2.sh && ./scripts/deploy_ec2.sh
```

### 3. Copiar o projeto para as instâncias

```bash
scp -i chave.pem -r ./tema7-pdp ec2-user@<IP>:~/
```

## Como Rodar

### Execução distribuída (2 instâncias EC2)

**Instância 1 e 2 — suba os workers primeiro:**
```bash
export S3_BUCKET='tema7-pdp-resultados'
python3 worker.py
```

**Aguarde os dois mostrarem `"Fila vazia. Aguardando..."`, depois rode o produtor:**
```bash
export S3_BUCKET='tema7-pdp-resultados'
python3 produtor.py
```

### Modo detecção de code smells

```bash
MODO_ANALISE=smells python3 worker.py
```

### Variáveis de ambiente disponíveis

| Variável | Padrão | Descrição |
|---|---|---|
| `S3_BUCKET` | `` (vazio) | Bucket S3 para resultados compartilhados |
| `MODO_ANALISE` | `testes` | Modo de análise: `testes` ou `smells` |
| `OLLAMA_HOST` | `http://localhost:11434` | URL do servidor Ollama |
| `OLLAMA_MODEL` | `llama3.2:1b` | Modelo a usar |

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
tema7-pdp/
├── prompts/
│   ├── v1_gerar_testes.txt     # System prompt para geração de testes
│   └── v2_detectar_smells.txt  # System prompt para detecção de code smells
├── scripts/
│   ├── setup_aws.py            # Cria SQS, DLQ e bucket S3
│   ├── setup_ec2.py            # Provisiona instância EC2 via boto3
│   ├── deploy_ec2.sh           # Instala Ollama e dependências no EC2
│   ├── ec2_setup_ollama.sh     # User-data para setup automático do EC2
│   └── rodar_testes.sh         # Executa os testes gerados com pytest
├── meu_codigo/                 # Arquivos Python a analisar
├── testes/                     # Saída: testes gerados + relatórios
├── logs/                       # Logs estruturados em JSON
├── produtor.py                 # Envia arquivos para a fila SQS
├── worker.py                   # Consome fila, chama LLM, salva testes
├── agregador.py                # Consolida métricas e detecta conflitos
└── utils.py                    # Retry com backoff e logging compartilhados
```

## Tolerância a Falhas

| Ponto crítico | Estratégia |
|---|---|
| Falha no Ollama | Retry com exponential backoff (3 tentativas: 2s → 4s → 8s) |
| Falha no SQS | Retry com exponential backoff nas chamadas receive/delete |
| Falha no S3 | Log de warning + retorno gracioso sem travar o worker |
| Mensagem processada 5+ vezes | Movida para DLQ local (`testes/dlq/`) e removida da fila |
| Worker encerra inesperadamente | Mensagem retorna à fila após `VisibilityTimeout` (120s) |

## Resultados Experimentais

| Métrica | 1 Worker | 2 Workers |
|---|---|---|
| Tempo real | 126.03s | **56.97s** |
| Throughput | 0.032 arq/s | **0.070 arq/s** |
| Speedup | 1x | **2.21x** |

Speedup próximo do linear (ideal = 2x) demonstra paralelismo embaraçoso eficiente com workers em instâncias separadas.

## Bônus SLM

Este projeto usa Ollama com `llama3.2:1b` auto-hospedado em instâncias EC2 t3.small (CPU-only) em vez do Amazon Bedrock, permitindo controle total da infraestrutura de inferência e demonstração direta do impacto do paralelismo no throughput agregado.
