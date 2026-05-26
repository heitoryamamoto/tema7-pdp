#!/bin/bash
# Script de user-data para EC2: instala Ollama e baixa o modelo llama3.2:3b
# Testado em: Amazon Linux 2023 e Ubuntu 22.04
# Uso: cole este arquivo em "Advanced Details > User data" ao criar a instância EC2,
#      ou execute manualmente após conectar via SSH.

set -e

echo "[1/4] Atualizando pacotes..."
if command -v yum &>/dev/null; then
    yum update -y
else
    apt-get update -y
fi

echo "[2/4] Instalando Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

echo "[3/4] Configurando Ollama para escutar em todas as interfaces..."
# Permite conexões externas (não apenas localhost)
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
EOF

systemctl daemon-reload
systemctl enable ollama
systemctl start ollama

# Swap necessario em instancias com pouca RAM (t3.small/micro)
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "[4/4] Baixando modelo llama3.2:1b (otimizado para CPU com pouca RAM)..."
sleep 5  # aguarda Ollama inicializar
ollama pull llama3.2:1b

echo ""
echo "=== Setup concluido ==="
echo "Ollama rodando em: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):11434"
echo "Teste: curl http://localhost:11434/api/tags"
