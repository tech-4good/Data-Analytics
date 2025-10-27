#!/bin/bash

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log "Por favor, execute este script como root (usando sudo)"
    exit 1
fi

# Update system
log "Atualizando sistema..."
apt-get update
apt-get upgrade -y

# Install dependencies
log "Instalando dependências..."
apt-get install -y apt-transport-https ca-certificates wget software-properties-common gnupg net-tools

# Add Grafana repository
log "Adicionando repositório Grafana..."
mkdir -p /etc/apt/keyrings
wget -q -O - https://packages.grafana.com/gpg.key | gpg --dearmor | tee /etc/apt/keyrings/grafana.gpg > /dev/null
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://packages.grafana.com/oss/deb stable main" | tee /etc/apt/sources.list.d/grafana.list > /dev/null

# Update and install Grafana
log "Instalando Grafana..."
apt-get update
apt-get install -y grafana

# Start and enable Grafana
log "Iniciando serviço Grafana..."
systemctl daemon-reload
systemctl enable grafana-server
systemctl start grafana-server

# Configure firewall (if ufw is installed)
log "Configurando firewall..."
if command -v ufw >/dev/null 2>&1; then
    ufw allow 3000/tcp
    ufw reload
fi

# Double check service is running
log "Verificando status do serviço..."
if systemctl is-active --quiet grafana-server; then
    log "Grafana está rodando"
else
    log "ERRO: Grafana não está rodando"
    systemctl status grafana-server
fi

# Check port
log "Verificando porta 3000..."
check_port() {
    if command -v netstat >/dev/null 2>&1; then
        netstat -tuln | grep :3000 >/dev/null
    elif command -v ss >/dev/null 2>&1; then
        ss -tuln | grep :3000 >/dev/null
    elif command -v lsof >/dev/null 2>&1; then
        lsof -i :3000 >/dev/null
    else
        # Se nenhuma ferramenta estiver disponível, tenta curl localhost
        curl -s localhost:3000 >/dev/null
    fi
    return $?
}

if check_port; then
    log "Porta 3000 está aberta e em uso"
else
    log "AVISO: Não foi possível confirmar se a porta 3000 está em uso"
    log "Tentando reiniciar o serviço Grafana..."
    systemctl restart grafana-server
    sleep 5
    if check_port; then
        log "Porta 3000 está agora aberta e em uso após reinício"
    else
        log "ERRO: Porta 3000 ainda não está em uso após reinício"
        log "Status do serviço Grafana:"
        systemctl status grafana-server --no-pager
    fi
fi

# Print final status
log "Instalação completa"
log "Para acessar Grafana: http://$(curl -s ifconfig.me):3000"
log "Credenciais padrão: admin / admin"