# Arquitetura

O projeto é single-tenant e segue apps Django por domínio, na raiz do repositório. O app `core` concentra configuração e URLs globais; `base` concentra recursos compartilhados; os apps de domínio implementam contas, catálogo, turmas, materiais e atividades.

```mermaid
flowchart LR
    acervo[Acervo PROF-TONI] --> command[import_acervo]
    command --> catalog[Catalog: Aula]
    catalog --> classroom[Classroom: AulaPublicada]
    classroom --> student[Aluno]
    classroom --> activities[Activities]
    materials[Materials] --> activities
    student --> submissions[Entregas]
    submissions --> correction[Correção do professor]
```

## Apps

| App | Responsabilidade |
|---|---|
| `accounts` | Usuário custom, login por e-mail e perfis de professor/aluno. |
| `catalog` | Taxonomia e aulas canônicas importadas do acervo. |
| `classroom` | Turmas, matrículas, aulas publicadas e progresso. |
| `materials` | Materiais extras com download protegido. |
| `activities` | Atividades, entregas, anexos e correção. |
| `base` | Model base, storage protegido e comandos transversais. |

## Regras de segurança

Arquivos de materiais e entregas usam storage protegido fora de `MEDIA_ROOT`. O acesso passa por views com checagem de permissão: professor dono da turma, aluno matriculado ou admin.

## Modelo resumido

```mermaid
erDiagram
    User ||--o{ Matricula : aluno
    User ||--o{ Turma : professor
    Turma ||--o{ Matricula : tem
    Turma ||--o{ AulaPublicada : publica
    AulaPublicada ||--o{ ProgressoAula : acompanha
    Turma ||--o{ Atividade : tem
    Atividade ||--o{ Entrega : recebe
    Entrega ||--o{ EntregaArquivo : anexa
    Turma ||--o{ Material : tem
```

