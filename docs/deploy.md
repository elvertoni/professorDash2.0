# Deploy

## Desenvolvimento local

Requisitos:

- Python maior que 3.13.
- PostgreSQL.
- `.env` criado a partir de `.env.example`.

Passos:

Use `uv` para instalar dependências; a `.venv` não precisa ter `pip` instalado.

```powershell
uv venv --python 3.13 .venv
uv pip install --python .\.venv\Scripts\python.exe -r requirements.txt
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Com Docker Compose de desenvolvimento:

```bash
docker compose up --build
docker compose exec app python manage.py migrate
docker compose exec app python manage.py seed_demo
```

## Produção (Easypanel)

O deploy de produção roda na VPS via **Easypanel**, que substitui o Caddy do PRD
original: o próprio Easypanel faz reverse proxy + TLS automático (Let's Encrypt) e
oferece Postgres gerenciado. Por isso **não** usamos `caddy` nem expomos 80/443 no
container — o app só escuta HTTP em `0.0.0.0:8000` e o Easypanel proxia.

Passo a passo completo: **[deploy-easypanel.md](deploy-easypanel.md)**.

Artefatos de produção no repositório:

- `Dockerfile.prod` — imagem com Gunicorn (dev continua no `Dockerfile` com runserver).
- `docker/entrypoint.sh` — espera o DB, `migrate`, `collectstatic --clear`, superuser opcional.
- `scripts/backup.sh` — dump do Postgres + tar da media (alternativa ao backup do Easypanel).

Variáveis essenciais (definidas no painel do App service):

```env
DEBUG=False
SECRET_KEY=<valor-seguro>
ALLOWED_HOSTS=prof.tonicoimbra.com
CSRF_TRUSTED_ORIGINS=https://prof.tonicoimbra.com
PRODUCTION_SECURITY=True
DATABASE_URL=postgres://USER:SENHA@<nome-do-service-db>:5432/professordash
```

## Documentação

Rode a documentação local com:

```bash
mkdocs serve
```

Build estático:

```bash
mkdocs build --strict
```
