# Minha biblioteca

A primeira versão está implementada para consulta privada no ProfessorDash. O lote piloto contém **40 notas**: 36 conceitos vivos e 2 rascunhos do PROF-TONI, mais 2 rascunhos do cérebro pessoal. A implantação em produção ainda não foi realizada.

## Para consultar

1. Entre com a conta proprietária e abra **Minha biblioteca** no menu da conta (avatar).
2. Busque palavras como `RAG`, `API REST` ou `precificacao`. A busca ignora acentos e maiúsculas; todas as palavras precisam estar presentes no título, apelidos ou texto. Não é um chatbot.
3. Use **Quero usar para** ou abra os filtros de acervo, tema e estado. Sem filtro de estado, notas obsoletas ficam ocultas.
4. Abra uma nota para ler, conferir fontes e seguir notas relacionadas. Uma referência sem correspondência importada continua como texto; o detalhe lista as referências pendentes.
5. Use **Copiar referência** para levar a identificação da nota ao seu trabalho. O texto também pode ser selecionado manualmente.

Os originais citados, PDFs, vídeos e imagens não estão no pacote. Links externos no corpo podem abrir seus sites de origem; referências locais não prometem acesso ao arquivo. Rascunhos continuam identificados. Para corrigir ou atualizar uma nota, edite o vault e gere um novo pacote.

## Configuração e carga

O servidor precisa de `LIBRARY_OWNER_EMAIL` com o email exato de uma conta ativa professor/admin. Vazio desabilita a biblioteca. Não há bypass de superusuário nas views, e os modelos não são registrados no admin. Administradores do servidor/banco continuam tendo acesso técnico aos dados.

A conta de desenvolvimento é fictícia; não deve ser usada como configuração de produção. O banco deve ser PostgreSQL, conforme as regras do projeto.

Na raiz do projeto, com `.venv` e `.env` configurados:

```bash
mkdir -p library-packages
.venv/bin/python manage.py package_library \
  --vault /mnt/d/VAULTS/PROF-TONI --source prof-toni \
  --output library-packages/prof-toni-pilot.json
.venv/bin/python manage.py package_library \
  --vault /mnt/d/VAULTS/cerebro --source pessoal \
  --output library-packages/pessoal-pilot.json
```

O comando não sobrescreve pacotes. Para atualizar, use outro nome de arquivo. A seleção padrão é `pilot`; `--selection all` é uma expansão deliberada, a revisar antes de enviar. Pacotes contêm notas pessoais e estão ignorados pelo Git em `library-packages/`.

Após revisar a lista, transfira **somente os pacotes selecionados** por canal autenticado para um diretório privado do servidor (fora de media, static e diretórios públicos). Não copie o vault inteiro. No container da aplicação, após o deploy e configuração do proprietário:

```bash
python manage.py migrate
python manage.py import_library --package /caminho-privado/prof-toni-pilot.json \
  --owner-email EMAIL_DA_CONTA
# A primeira execução é apenas prévia. Para gravar o mesmo pacote:
python manage.py import_library --package /caminho-privado/prof-toni-pilot.json \
  --owner-email EMAIL_DA_CONTA --apply
```

Repita para o pacote pessoal aprovado. Cada pacote é uma transação: erro reverte todas as alterações desse pacote. Identidade é `(fonte, caminho relativo)`, não slug. Mudanças atualizam a mesma nota; ausências não excluem. Renomear um arquivo cria outra identidade e conserva a antiga; esta versão não faz reconciliação de renomeações. A revisão da fonte identifica o último pacote aplicado, que pode ser parcial.

## Recuperação

As notas e seus metadados ficam no PostgreSQL, abrangidas pelo dump integral do banco do portal. Os vaults continuam com seu próprio histórico. Preserve também a configuração do proprietário fora do Git. Restaurar o banco e reconfigurar o proprietário restitui acesso; um pacote de atualização não substitui o backup integral.

## Validação realizada em 16/10/2026

- Python 3.14 / Django 6.0.6; migração em PostgreSQL 18 isolado localmente.
- Prévia: 38 + 2 novas, sem escrita; importação: 40 notas; reimportação: 40 inalteradas.
- Alteração de uma nota atualizou uma linha; um lote parcial preservou as outras 39.
- Falha de validação durante a gravação reverteu a transação; originais conferidos novamente.
- Dump e restauração em outro banco local: 40 notas e 2 fontes recuperadas.
- Navegação no Chromium: login retorna à biblioteca; `precificacao` encontra a nota acentuada; `RAG` fica em primeiro; estado vazio funcional; wikilinks disponíveis resolvem.
- Aluno, outro professor e superusuário não proprietário: HTTP 403 na lista/busca e no detalhe direto. Visitante redirecionado ao login.
- Renderização remove scripts, imagens remotas, links executáveis e caminhos relativos não resolvidos.
- Desktop 1440px e celular 360px, temas claro/escuro: sem transbordamento horizontal nas telas inspecionadas. Filtros por acervo/coleção, paginação e cópia de referência conferidos. Respostas privadas enviam `Cache-Control: private, no-store`.
- Nenhuma suíte de testes automatizados criada ou executada, conforme AGENTS.md. Conferência de interface pelo navegador local.

Produção, configuração da conta real e envio das duas notas pessoais permanecem pendentes. Os dados e aulas existentes em produção não foram alterados.
