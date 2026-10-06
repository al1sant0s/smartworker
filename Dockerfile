FROM mambaorg/micromamba:2-debian12-slim

# Instala as dependências do conda-forge no ambiente base da imagem
COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml \
    && micromamba clean --all --yes

# Coloca o ambiente no PATH para que "docker compose exec web python ..." funcione
# (o exec não passa pelo entrypoint que ativa o ambiente)
ENV PATH=/opt/conda/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY --chown=$MAMBA_USER:$MAMBA_USER . .

# RUN não passa pelo entrypoint, então o ambiente precisa ser ativado aqui
ARG MAMBA_DOCKERFILE_ACTIVATE=1
# SECRET_KEY é obrigatória no settings; aqui basta um valor descartável
RUN SECRET_KEY=build-only python manage.py collectstatic --noinput \
    && mkdir -p /app/media

EXPOSE 8000

# O entrypoint da imagem micromamba já ativa o ambiente base
CMD ["sh", "-c", "python manage.py migrate && gunicorn smartworker.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
