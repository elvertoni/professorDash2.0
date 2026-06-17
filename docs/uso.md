# Uso

## Professor

1. Acesse `/conta/login/` com o usuário professor.
2. Entre em **Painel** para ver turmas e entregas aguardando correção.
3. Use **Turmas** para criar ou abrir uma turma.
4. Na turma, publique aulas, cadastre alunos, crie atividades e envie materiais.
5. Em **Atividades**, abra as entregas e use **Corrigir** para lançar nota e feedback.

## Aluno

1. Acesse `/conta/login/` com um usuário aluno.
2. Entre em **Meu painel**.
3. Abra uma turma para estudar aulas liberadas.
4. Em atividades, envie resposta em texto e anexos quando necessário.
5. Após a correção, veja nota e feedback na própria atividade.

## Seed de demonstração

O comando `seed_demo` cria:

- 1 professor.
- 8 alunos.
- 2 turmas.
- Aulas de catálogo publicadas em datas variadas.
- Materiais de apoio por link.
- Atividades com prazos futuros e vencidos.
- Entregas pendentes, entregues, atrasadas e corrigidas.

O seed é idempotente: pode ser rodado novamente para recompor o cenário demo sem duplicar os registros principais.
