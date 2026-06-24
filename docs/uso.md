# Uso

## Professor

1. Acesse `/conta/entrar/` com o usuário professor.
2. Entre em **Painel** para ver turmas, progresso e atividades.
3. Use **Turmas** para criar ou abrir uma turma.
4. Na turma, sincronize/publique aulas, cadastre alunos, crie atividades e envie materiais.
5. Em **Atividades**, abra a grade de checks e marque quais alunos concluíram cada item.

## Aluno

1. Acesse `/conta/entrar/` com um usuário aluno.
2. Entre em **Meu painel**.
3. Abra uma turma para estudar aulas liberadas.
4. Estude as aulas liberadas e marque progresso.
5. Use o Google Classroom da SEED-PR para entregas oficiais quando a atividade exigir envio.

## Seed de demonstração

O comando `seed_demo` cria:

- 1 professor.
- 8 alunos.
- 2 turmas.
- Aulas de catálogo publicadas em datas variadas.
- Materiais de apoio por link.
- Atividades de acompanhamento.
- Checks por aluno em estados feito/não feito.

O seed é idempotente: pode ser rodado novamente para recompor o cenário demo sem duplicar os registros principais.
