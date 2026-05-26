#!/bin/bash
# Deploy completo do Tema 7 em EC2 com GPU (Opcao A do enunciado)
# Instala: Ollama, drivers NVIDIA, Python, dependencias e o projeto
#
# Uso (apos conectar via SSH na instancia EC2):
#   chmod +x deploy_ec2.sh && ./deploy_ec2.sh

set -e

echo "======================================================"
echo "  Tema 7 - Deploy EC2 com Ollama + GPU"
echo "======================================================"

# --- Detecta distro ---
if command -v yum &>/dev/null; then
    PKG="yum"
else
    PKG="apt-get"
fi

echo ""
echo "[1/6] Atualizando pacotes..."
sudo $PKG update -y
sudo $PKG install -y python3-pip git

# --- Drivers NVIDIA (so se houver GPU) ---
echo ""
echo "[2/6] Verificando GPU..."
if lspci | grep -qi nvidia; then
    echo "GPU NVIDIA detectada. Instalando drivers..."
    if [ "$PKG" = "yum" ]; then
        sudo yum install -y kernel-devel-$(uname -r) kernel-headers-$(uname -r)
        sudo dnf install -y nvidia-driver nvidia-cuda-toolkit 2>/dev/null || \
        sudo yum install -y nvidia-driver 2>/dev/null || \
        echo "Instale os drivers NVIDIA manualmente se necessario."
    else
        sudo apt-get install -y nvidia-driver-535 nvidia-cuda-toolkit 2>/dev/null || \
        echo "Instale os drivers NVIDIA manualmente se necessario."
    fi
else
    echo "Sem GPU detectada. Ollama rodara em CPU (3-10 tokens/s — aceitavel para fins academicos)."
fi

# --- Ollama ---
echo ""
echo "[3/6] Configurando swap (necessario em t3.small/micro)..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "Swap de 2GB criado."
else
    echo "Swap ja existe."
fi
free -h

echo ""
echo "[4/6] Instalando Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Inicia o servico (systemd)
sudo systemctl enable ollama
sudo systemctl start ollama

echo "Aguardando Ollama inicializar..."
sleep 5

# Verifica se subiu
curl -s http://localhost:11434/api/tags > /dev/null && echo "Ollama OK" || {
    echo "Erro: Ollama nao respondeu. Verifique com: sudo systemctl status ollama"
    exit 1
}

# --- Modelo ---
echo ""
echo "[5/6] Baixando modelo llama3.2:1b (otimizado para CPU com pouca RAM)..."
ollama pull llama3.2:1b
echo "Modelo baixado com sucesso."

# --- Projeto ---
echo ""
echo "[6/6] Configurando projeto..."
pip3 install --quiet boto3 ollama

# Se o projeto ainda nao estiver na instancia, clonar do git
if [ ! -f "produtor.py" ]; then
    echo "Arquivo produtor.py nao encontrado no diretorio atual."
    echo "Copie o projeto para esta instancia via scp ou git clone, depois rode este script novamente."
    echo ""
    echo "Exemplo scp (do seu PC):"
    echo "  scp -i chave.pem -r ./tema7-pdp ec2-user@<IP>:~/"
    exit 1
fi

mkdir -p logs testes/analises testes/dlq

# --- Instrucoes finais ---
echo ""
echo "[7/7] Verificando instalacao..."
python3 -c "import boto3, ollama; print('boto3 e ollama OK')"
curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; m=json.load(sys.stdin)['models']; print(f'Modelos disponiveis: {[x[\"name\"] for x in m]}')"

echo ""
echo "======================================================"
echo "  Deploy concluido!"
echo "======================================================"
echo ""
echo "Para rodar o sistema:"
echo ""
echo "  Terminal 1 (produtor):"
echo "    python3 produtor.py"
echo ""
echo "  Terminal 2 e 3 (workers em paralelo):"
echo "    python3 worker.py"
echo ""
echo "  Modo deteccao de code smells:"
echo "    MODO_ANALISE=smells python3 worker.py"
echo ""
echo "  Acompanhar logs em tempo real:"
echo "    tail -f logs/worker_*.log"
echo ""
