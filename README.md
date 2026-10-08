# Smartworker

Sistema interno para cadastro de empreendimentos imobiliários e acompanhamento
mensal da disponibilidade de unidades.

- **management**: empresas, empreendimentos, municípios (IBGE), estruturas
  (piscina, academia...) e condições de pagamento. Cada empreendimento tem um
  histórico de acompanhamento (`TrackingEvent`) que define se ele está ativo.
- **checklist**: um checklist por empreendimento ativo a cada mês, com as
  fontes de consulta (links, e-mails, telefones) e as planilhas de
  disponibilidade enviadas.

O login é feito pelo e-mail. O admin (`/admin/`) exige autenticação em dois
fatores (app autenticador), configurada em `/account/two_factor/setup/`.

## Desenvolvimento local

Requer [conda/mamba](https://github.com/conda-forge/miniforge).

```sh
mamba env create -f environment.yml
mamba activate smartworker
cp .env.example .env          # ajuste SECRET_KEY etc.
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Sem `DATABASE_URL`, o projeto usa o SQLite local (`db.sqlite3`).

## Configuração

Tudo é configurado por variáveis de ambiente (ou pelo `.env`). Banco, cache,
storages e e-mail são definidos por URLs, interpretadas pelo
[django-service-urls](https://github.com/rsalmaso/django-service-urls).
Veja todas as opções em [`.env.example`](.env.example).

| Variável | Uso |
|---|---|
| `SECRET_KEY`, `DEBUG` | Básicos do Django |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Domínios aceitos (separados por vírgula) |
| `DATABASE_URL` | Ex: `postgres://usuario:senha@host:5432/smartworker` |
| `STORAGE_DEFAULT` | Arquivos de mídia: `fs://` (disco) ou `s3://?bucket_name=...` |
| `AWS_*` | Credenciais do bucket S3, lidas pelo boto3 |
| `TRUST_X_FORWARDED_PROTO` | `1` quando um proxy termina o HTTPS (Railway, nginx) |
| `TIME_ZONE` | Padrão `America/Sao_Paulo` |

### Arquivos de mídia

As planilhas de disponibilidade usam o storage `default`. Com `fs://`, ficam em
`MEDIA_ROOT` e precisam ser servidas pelo nginx (o Django não serve mídia com
`DEBUG` desligado). Com S3 ou um serviço compatível (Cloudflare R2, Railway
Buckets, MinIO — informe `AWS_ENDPOINT_URL`), os links são URLs assinadas e
temporárias, então os arquivos continuam privados.

## Checklists mensais

```sh
python manage.py create_monthly_checklists              # mês atual
python manage.py create_monthly_checklists --month 2026-11
```

Cria um checklist pendente para cada empreendimento ativo que ainda não tem um
no mês. Pode rodar várias vezes: os que já existem são ignorados. Também é
possível gerar pela tela de checklists.

## Deploy com Docker Compose

```sh
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

Serviços:

- **web**: aplica as migrações, roda o `collectstatic` e sobe o gunicorn na
  porta 8000. Estáticos e mídia são gravados em pastas do host
  (`STATIC_HOST_DIR`, `MEDIA_HOST_DIR`) servidas pelo nginx.
- **scheduler**: roda `create_monthly_checklists` uma vez por dia.
- **db**: PostgreSQL 17. As credenciais vêm de `POSTGRES_*` no `.env`.

Para desenvolver com recarga automática: `docker compose watch`.

## Deploy no Railway

O Railway não usa o `compose.yaml`; cada parte vira um serviço:

1. **Postgres**: adicione o banco do Railway.
2. **Bucket**: um [Railway Bucket](https://docs.railway.com/storage-buckets)
   (compatível com S3) ou um S3 próprio, para a mídia (o disco do container é
   apagado a cada deploy). O bucket é privado; os links das planilhas são URLs
   assinadas.
3. **Web**: serviço a partir deste repositório (usa o `Dockerfile`; o gunicorn
   escuta em `$PORT`). Variáveis:
   - `DATABASE_URL` (referência ao Postgres)
   - `SECRET_KEY`, `DEBUG=0`
   - `ALLOWED_HOSTS=<app>.up.railway.app`
   - `CSRF_TRUSTED_ORIGINS=https://<app>.up.railway.app`
   - `TRUST_X_FORWARDED_PROTO=1`
   - `STORAGE_DEFAULT` e as credenciais do bucket, por referência ao serviço
     do bucket (troque `Bucket` pelo nome dele no Railway):

     ```
     STORAGE_DEFAULT=s3://?bucket_name=${{Bucket.AWS_S3_BUCKET_NAME}}&addressing_style=virtual
     AWS_ENDPOINT_URL=${{Bucket.AWS_ENDPOINT_URL}}
     AWS_ACCESS_KEY_ID=${{Bucket.AWS_ACCESS_KEY_ID}}
     AWS_SECRET_ACCESS_KEY=${{Bucket.AWS_SECRET_ACCESS_KEY}}
     AWS_DEFAULT_REGION=${{Bucket.AWS_DEFAULT_REGION}}
     ```
4. **Cron**: outro serviço do mesmo repositório, com as mesmas variáveis,
   comando `python manage.py create_monthly_checklists` e agendamento
   `0 6 * * *` (UTC). Substitui o serviço `scheduler` do Compose.

Os estáticos são servidos pelo WhiteNoise; não defina `STATIC_ROOT`.
