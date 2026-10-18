"""
Entrypoint WSGI para servidores de producao (gunicorn).

Uso tipico (ver backend/Dockerfile):
    gunicorn --bind 0.0.0.0:5000 wsgi:app
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
