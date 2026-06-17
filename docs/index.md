# Prof. Toni Coimbra

Portal educacional do Prof. Toni Coimbra que entrega ao aluno o acervo de aulas. O professor publica aulas por turma, cria atividades, corrige entregas com nota e feedback, e acompanha a evolução da turma.

## Escopo atual

- Login por e-mail com autenticação nativa do Django.
- Catálogo de aulas importadas do acervo.
- Turmas, matrículas, publicação de aulas e progresso do aluno.
- Atividades, entregas, correção e materiais protegidos.
- Seed de demonstração com dados fakes para validar as jornadas.

## Comandos úteis

```bash
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Usuários demo criados pelo seed:

| Perfil | E-mail | Senha padrão |
|---|---|---|
| Professor | `professor@professordash.local` | `professordash123` |
| Aluno | `ana.lima@professordash.local` | `professordash123` |

Use `python manage.py seed_demo --password outra-senha --reset-passwords` para redefinir as senhas demo.

