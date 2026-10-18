FROM python:3.11-slim

# Dependencias de sistema minimas para compilar/rodar PyMySQL/bcrypt e
# outras libs nativas comuns do ecossistema Flask.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala as dependencias Python primeiro para aproveitar o cache de
# camadas do Docker quando so o codigo da aplicacao muda.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usuario nao-root para rodar a aplicacao.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "60", "wsgi:app"]
