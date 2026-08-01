# ---------------------------------------------------------------------------
# Dockerfile - Gestor de Clientes (Streamlit)
# Imagem leve baseada em python:3.11-slim
# ---------------------------------------------------------------------------

FROM python:3.11-slim

# Evita que o Python gere arquivos .pyc e garante logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Diretório de trabalho dentro do container
WORKDIR /app

# Instala apenas o essencial de dependências de sistema exigidas pelo
# openpyxl/pandas (evita inchar a imagem)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala primeiro só o requirements.txt para aproveitar cache
# de camadas do Docker (só reinstala libs se requirements.txt mudar)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Agora copia o restante do código da aplicação
COPY . .

# Porta padrão do Streamlit
EXPOSE 8501

# Healthcheck simples para orquestradores (docker, swarm, etc.)
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Comando de inicialização do app
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
