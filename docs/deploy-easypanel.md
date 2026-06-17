# Deploy em produção via Easypanel

Guia passo a passo para subir o ProfessorDash numa VPS usando **Easypanel**
(App service buildando o `Dockerfile.prod` do GitHub + Postgres gerenciado).

O Easypanel cuida do reverse proxy e do TLS automático (Let's Encrypt), então
**não** há Caddy nem binding de 80/443 no container — o app escuta HTTP em
`0.0.0.0:8000` e o Easypanel proxia.

## Pré-requisitos

- VPS com Easypanel instalado (`curl -sSL https://get.easypanel.io | sh`).
- DNS: registro **A** `prof.tonicoimbra.com` → IP da VPS (Cloudflare; se usar
  proxy laranja, garanta SSL "Full"). O Easypanel emite o certificado via HTTP-01.
- Repositório `elvertoni/professordash` acessível pelo Easypanel (GitHub).

## 1. Criar o projeto

No Easypanel, **Create Project** → nome `professordash`.

## 2. Postgres gerenciado

Dentro do projeto: **+ Service → Postgres**.

- Service name: `db` (o host interno vira `professordash_db`).
- Anote **user**, **password** e **database** gerados (aba *Credentials*).

## 3. App service (Django)

**+ Service → App**.

- **Source**: GitHub → repo `elvertoni/professordash`, branch `main`.
- **Build**: tipo *Dockerfile*, caminho `Dockerfile.prod`.
- **Environment** (aba Environment), cole:

  ```env
  DEBUG=False
  SECRET_KEY=<gerar>
  ALLOWED_HOSTS=prof.tonicoimbra.com
  CSRF_TRUSTED_ORIGINS=https://prof.tonicoimbra.com
  PRODUCTION_SECURITY=True
  DATABASE_URL=postgres://USER:SENHA@professordash_db:5432/professordash
  DJANGO_SUPERUSER_EMAIL=admin@prof.tonicoimbra.com
  DJANGO_SUPERUSER_PASSWORD=<senha-forte>
  DJANGO_SUPERUSER_NOME_COMPLETO=Toni Coimbra
  ```

  Gerar `SECRET_KEY`:
  `python -c "import secrets; print(secrets.token_urlsafe(64))"`.

  `DATABASE_URL`: use o host `professordash_db` (nome do service de banco) e as
  credenciais do passo 2.

## 4. Domínio + porta

- Aba **Domains**: adicionar `prof.tonicoimbra.com`, **HTTPS on**, **port 8000**.
  O Easypanel emite o certificado automaticamente.

## 5. Volumes persistentes

Media e media protegida precisam sobreviver a redeploys. Na aba **Mounts** do App:

- Volume → `/app/media`
- Volume → `/app/protected_media`

> `staticfiles` é regerado pelo `collectstatic` a cada build — não precisa de volume.

## 6. Deploy

Clique **Deploy**. O `entrypoint.sh` no boot:

1. espera o Postgres;
2. `migrate --noinput`;
3. `collectstatic --noinput --clear`;
4. cria o superuser (se as vars `DJANGO_SUPERUSER_*` existirem — idempotente);
5. sobe o Gunicorn.

Acompanhe em **Logs**. Healthcheck: `GET /health/` deve retornar 200.

## 7. Importar o acervo

Pelo console do App service (aba **Console** / terminal do Easypanel):

```bash
# O acervo PROF-TONI precisa estar acessível dentro do container.
# Opção simples: clonar dentro do container (efêmero) e importar:
git clone https://github.com/elvertoni/PROF-TONI.git /tmp/acervo
python manage.py import_acervo --path /tmp/acervo --only-aprovada
```

> Como o `import_acervo` é idempotente (casa por disciplina/trilha/ordem/slug),
> pode rodar de novo a cada atualização do acervo.

## 8. Smoke test

- [ ] `https://prof.tonicoimbra.com/health/` → 200.
- [ ] Login do admin (`/conta/`) com o superuser.
- [ ] Jornada professor: criar turma, publicar aula, criar atividade, dar check.
- [ ] Jornada aluno: matricular, ver aula liberada, entregar, ver feedback.
- [ ] Upload de material e entrega: download protegido respeita permissão.

## 9. Redeploy

Push na branch `main` → **Deploy** no Easypanel (ou habilite auto-deploy por
webhook na aba Source). Migrations e estáticos rodam de novo no entrypoint.

## 10. Backup

Mais simples: habilitar o **backup automático** do service Postgres no painel do
Easypanel. Alternativa via script: `scripts/backup.sh` (dump + tar da media),
agendável por cron na VPS.
