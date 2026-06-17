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

## Produção

O PRD define VPS Ubuntu com Docker Compose, PostgreSQL e Caddy no domínio `prof.tonicoimbra.com`. A sprint de produção cria os artefatos finais (`docker-compose.prod.yml`, entrypoint, Caddyfile e backup). Até lá, mantenha as variáveis sensíveis fora do versionamento e use o `.env` da VPS.

Variáveis essenciais:

```env
DEBUG=False
SECRET_KEY=<valor-seguro>
ALLOWED_HOSTS=prof.tonicoimbra.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://prof.tonicoimbra.com
DATABASE_URL=postgres://professordash:SENHA@db:5432/professordash
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
