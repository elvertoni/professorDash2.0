# Segundo cérebro: mapa de uso e biblioteca privada

Levantamento em 2026-10-16. Proposta original, seguida de implementação local em 2026-10-16; produção ainda não alterada. Veja [COMO-USAR.md](COMO-USAR.md). Código do ProfessorDash inspecionado em `/home/toni/PROJETOS/PESSOAL/professordash`. Fontes locais em `D:\VAULTS`.

## O que já existe

| Acervo | Conteúdo observado | Uso imediato |
|---|---|---|
| Cérebro pessoal | 37 notas: agentes 14, IA 4, infraestrutura 11, negócios 8; todas rascunho | Planejar projetos, consultar infraestrutura e estruturar serviços |
| PROF-TONI | 1.158 conceitos: 1.121 rascunhos, 36 vivos, 1 obsoleto | Estudo, referências para projetos e preparação de aulas |
| Aulas | 89 aprovadas; validador do manifesto passou sem divergências | Material pronto para o fluxo de publicação por turma |

As duas pós concentram 990 arquivos: 523 em IA/Robótica Educacional e 467 em Full Stack/Cloud. Um conceito obsoleto integra a contagem total; não deve aparecer como recomendação atual. O mapa gerado do Obsidian ainda informa 466 para Full Stack: usar os arquivos como fonte da contagem.

Inventário navegável completo: [INVENTARIO.md](INVENTARIO.md). Dados estruturados: [inventario.json](inventario.json). O inventário descreve o conteúdo; não certifica a correção das notas nem a disponibilidade de todos os originais citados.

## Por onde começar

| Sua necessidade | Notas e materiais | Resultado possível |
|---|---|---|
| Preparar uma aula de IA | RAG, chunking, embeddings e aulas 16–17 da trilha fundamentos de IA | Explicação, exemplo e exercício apoiados nas canônicas |
| Planejar atividade investigativa | Aprendizagem baseada em problemas, metodologias ativas e avaliação da aprendizagem | Roteiro com problema, investigação e critérios; revisar os rascunhos antes de usar |
| Estudar a pós Full Stack | API REST, HTTP, JSON, arquitetura em camadas, Docker | Recuperar conceitos por assunto e seguir as fontes da disciplina |
| Estudar a pós de Educação/Robótica | Aprendizagem significativa, PBL, pensamento computacional e acessibilidade | Revisão temática com referências ao material do curso |
| Elaborar proposta comercial de IA | Precificação de projeto de IA, processo comercial e modelos de negócio | Esqueleto de diagnóstico, escopo, piloto e suporte; exemplos de valores não são tabela de mercado |
| Organizar automações | Central de operações do agente, perfis isolados e servidor MCP da aplicação | Lista de componentes e decisões para um projeto; a nota não prova que a infraestrutura esteja implantada |
| Recuperar o ambiente | Dotfiles, Bitwarden, consistência de backups e o que o git push não leva | Checklist de recuperação a confrontar com backups reais |

### Amostras lidas integralmente

- [RAG](/mnt/d/VAULTS/PROF-TONI/conceitos/inteligencia-artificial/rag.md): marcado vivo; definição, mecânica, erros comuns, fontes e ligações com aulas. É um ponto inicial mais maduro.
- [Aprendizagem baseada em problemas](/mnt/d/VAULTS/PROF-TONI/conceitos/inovacao-inteligencia-artificial-e-robotica-educacional/aprendizagem-baseada-em-problemas.md): rascunho compacto, útil como lembrete e caminho para a fonte.
- [API REST](/mnt/d/VAULTS/PROF-TONI/conceitos/desenvolvimento-full-stack-e-cloud-computing/api-rest.md): rascunho ligado a HTTP/JSON e aulas de arquitetura/TCC.
- [Precificação de projeto de IA](/mnt/d/VAULTS/cerebro/3-recursos/negocios/precificacao-de-projeto-de-ia.md): rascunho mais desenvolvido, com cálculo ilustrativo e referências temporais à fonte.
- [Central de operações do agente](/mnt/d/VAULTS/cerebro/3-recursos/agentes/central-de-operacoes-do-agente.md): rascunho de arquitetura; declara que a transcrição não foi conferida. Preservar essa ressalva na consulta.

## Por que isso não aparece no ProfessorDash

O modelo `catalog.Conceito` contém somente `slug`, `nome` e `disciplina_slug`. O importador `load_concept_labels` lê esses campos do manifesto para resolver rótulos nas aulas. Ele não armazena o corpo Markdown dos conceitos. As URLs atuais do catálogo tratam aulas e importação, sem biblioteca de notas.

O vault pessoal tem outro schema e outro repositório, privado. Nenhum conector para ele foi identificado no fluxo inspecionado. O catálogo de aulas é um depósito interno; a biblioteca proposta não substitui a jornada de publicar por turma.

## Proposta: Minha biblioteca

Uma entrada privada no ProfessorDash, acessível à conta dona da biblioteca. Ela começa com busca e três coleções editoriais: **Estudar**, **Preparar aulas** e **Projetos e negócios**. A mesma nota pode aparecer em mais de uma coleção sem duplicar o texto.

1. **Encontrar:** pesquisar título, apelidos e corpo; filtrar por acervo, tema e status. Mostrar trecho correspondente, origem e atualização. Busca sem resultado explica que nada foi encontrado e permite remover filtros.
2. **Ler:** texto da nota, fontes, data, status e notas relacionadas. Rascunho permanece visível como rascunho; obsoleto fica fora do resultado padrão. Fonte ausente é indicada, sem inventar acesso ao original.
3. **Reutilizar:** copiar referência e abrir a aula relacionada quando houver. Consultar uma nota não publica material para alunos nem promove seu status.

Exemplo de jornada: buscar “como precificar projeto de IA” → abrir “Precificação de projeto de IA” → ver que é rascunho e consultar sua origem → seguir para “Processo comercial de serviços”. A busca inicial é textual; não promete compreender qualquer pergunta em linguagem natural.

## Limites e acesso

- Vaults continuam sendo as fontes editáveis. Portal recebe uma cópia para leitura; mudanças voltam ao vault pelo fluxo editorial existente.
- Acesso às notas pessoais restrito ao proprietário da biblioteca, com checagem também no detalhe, busca e anexos. `ProfessorRequiredMixin` sozinho não garante exclusividade ao Toni: permite outros professores e administradores. O desenho precisa fixar o proprietário explicitamente e tratar o poder administrativo de superusuários.
- Estudante, visitante e outro professor não recebem resultados, trechos ou arquivos privados, mesmo conhecendo a URL.
- Fontes brutas, cursos pagos, `lake/`, histórico do ai-memory e segredos ficam fora da importação inicial. Notas compiladas devem preservar suas referências e ressalvas.
- Primeira versão sem chatbot, geração de texto, embeddings ou novo servidor. O portal atual restringe IA nesta fase; busca textual e leitura cabem no stack existente.
- A biblioteca terá conteúdo pessoal em produção: a expansão do escopo do produto e a seleção das notas devem ficar explícitas no PRD antes da implementação.

## Implementação proposta

Nova app de domínio `library`, separada do espelho `catalog.Conceito`. Reutilizar autenticação, templates e Volta Atelier do portal.

- Fonte: identificador estável, rótulo, revisão importada e dono.
- Nota: identidade `(fonte, caminho relativo)`, slug, título, apelidos, tema, status original, Markdown, fontes, data na origem e hash. Mesmos slugs em vaults diferentes não colidem.
- Ligações: resolvidas dentro do acervo de origem; referências cruzadas só quando explícitas. Link ausente não cria conteúdo fictício.
- Importador com adaptadores para `conceitos/` e `3-recursos/`, lista permitida de caminhos, prévia de alterações e aplicação idempotente. Não eliminar notas automaticamente se faltarem num lote.
- Markdown sanitizado; rejeitar caminhos fora da fonte e conteúdo executável. Arquivos privados não passam por `/media/` público.
- Transporte inicial por pacote local selecionado e importado no servidor. Não colocar token do repo privado no navegador nem presumir que a VPS possa ler `D:`. O mecanismo de envio será definido na implementação.
- Busca PostgreSQL por título, apelidos e corpo; priorizar título e tratar acentos. Conteúdo indexado sujeito à mesma autorização da leitura.
- Backup: notas originais no Git apropriado; seleção e metadados da biblioteca no backup do banco do portal. Testar recuperação e atualização antes de considerar integração concluída.

## Entregas e validação manual

1. Incorporar escopo ao PRD e implementar um lote selecionado: 36 notas vivas de IA mais as cinco amostras acima, deduplicadas. Prévia deve informar a contagem real; rascunhos identificados. Confirmar seleção do conteúdo pessoal antes do envio a produção.
2. Importação repetida não duplica; alteração na origem atualiza somente a nota correspondente; erro não deixa importação parcial; nota ausente não é apagada.
3. Dono encontra “RAG”, “precificação” e “API REST”; detalhe mostra corpo, origem, status e ligações. Termos inexistentes têm estado vazio útil.
4. Visitante vai ao login; aluno e outro professor não acessam lista, busca, detalhe ou anexos. Checar também trechos de busca e URLs diretas.
5. Validar teclado, foco, claro/escuro, desktop e celular. Sem alterar navegação das turmas ou publicar aulas automaticamente.
6. Só ampliar para as demais notas após o lote inicial funcionar. Testes automatizados não serão criados, conforme regra atual do ProfessorDash; validação manual documentada.

## Estado desta entrega

Mapeamento preservado e primeira versão implementada localmente: biblioteca privada, lote piloto de 40 notas, busca, leitura, importação e validação em PostgreSQL. Nenhum arquivo dos vaults foi alterado. Publicação/deploy e importação em produção não realizados. Consulte [COMO-USAR.md](COMO-USAR.md) para estado, operação e limites.
