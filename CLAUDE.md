# CLAUDE.md — memória do projeto

Lido automaticamente pelo Claude Code no início de cada sessão. Mantenha curto e atual.

## O projeto

**Markinho — Conversor Markdown** (nome definido em 13/11/2026): conversor de documentos para
Markdown e de Markdown para outros formatos, com interface gráfica (PySide6) e linha de comando.
**Tudo roda no computador do usuário; nenhum documento vai para a internet.** Duas edições (PADRÃO e
COMPLETA; a LEVE foi juntada à PADRÃO em 27/11/2026). **Decidido em 16/11/2026:** gratuito e aberto sob **AGPL-3.0** (aplicada: LICENSE, cabeçalho SPDX nos .py),
“como está”, sem obrigação de atualizações; **não aceita código de terceiros** (o dono é o único autor,
para poder oferecer licença comercial no futuro).

- Dono: `dontstopbelieve` (GitHub, repositório `dontstopbelieve/markinho`). Explique os passos de forma
  simples, sem jargão.
- **Idioma**: conversa, interface, mensagens, comentários e commits em **português do Brasil**.
  Interface em pt-BR, **inglês** e **espanhol** (`i18n.tr("texto em português")`; traduções em `markinho/locale/en.json` e `es.json`).
- Antes de começar, leia **`PENDENCIAS.md`** (lista viva do que falta e do que foi decidido).

## Regras que não podem ser quebradas

1. **Só componentes com licença permissiva** (MIT, BSD, Apache, PSF, LGPL com ligação dinâmica,
   CDLA-Permissive): mantém possível uma licença comercial futura. Nada AGPL/GPL embutido no programa, nem modelos com restrição
   comercial. **Marker** e **PyMuPDF/PyMuPDF4LLM** nunca entram nos instaladores (o código só os
   usa se o usuário instalar por conta própria). Pandoc (GPL) vai como programa separado.
   Ao incluir algo novo, confira a licença de toda a árvore de dependências e atualize
   `THIRD_PARTY_LICENSES.md` **e** `markinho/credits.py` (janela Sobre > Créditos). Ideias de outros
   projetos entram em `INSPIRED_BY`; nunca copie código de terceiros.
2. **Nada sai do computador**: o “OCR hospedado” do AnyDoc nunca é usado (chamamos direto
   `anydoc._anydoc`, sem caminho de rede); a descrição de imagens só usa Ollama local.
3. **Servidor MCP**: só acessa as pastas autorizadas; gravar exige permissão; nunca sobrescreve
   sem pedido. Qualquer mudança aí precisa manter os testes de acesso negado.
4. **Sem custos**: o dono não paga assinatura digital, serviços ou planos. O repositório é **público**
   desde 26/11/2026 (Actions e armazenamento gratuitos, inclusive macOS).
5. Arquivo `.py` novo começa com `# SPDX-License-Identifier: AGPL-3.0-only` e a linha de copyright.
6. Commit e push **ao fim de cada etapa**, com mensagem em português e as linhas de atribuição.

## Estrutura

```
markinho/
  core.py          convert(): motor → imagens → descrição → correção → perfil/metadados;
                   tentativa automática com outro motor no modo "auto"
  engines.py       motores: Nativo, AnyDoc, Pandoc, Docling, Marker, MarkItDown, PyMuPDF4LLM
  converters.py    conversores nativos (DOCX com sdt/caixas de texto, XLSX/XLS, PPTX, HTML, EPUB, ZIP…)
  pdf.py           PDF nativo: layout, colunas, código, imagens, OCR, cabeçalhos/rodapés
  anydoc_engine.py AnyDoc: modelo do documento → Markdown (imagens, tabelas mescladas, notas)
  ocr.py           Tesseract (principal, mantém acentos) / RapidOCR
  assets.py        imagens (pasta <nome>_assets / base64 / nenhuma), tabelas HTML
  postprocess.py   frontmatter YAML, perfis (gfm, mdformat, obsidian, llm)
  textfix.py       correção de caracteres (mojibake, acentos, ligaduras…) com relatório
  chunker.py       pedaços para RAG (JSON/JSONL)
  batch.py         retomar lotes (terminal, botão direito, pasta monitorada, janela): .markinho-lote.json com
                   SHA-256 do conteúdo e do caminho (sem nomes de origem) + configuração; gravação atômica
  naming.py        padrões de nome de saída ({nome} {n} {titulo} {data}…)
  presets.py       modos Rápido / Equilibrado / Máxima qualidade
  exporter.py      Markdown → DOCX/PDF/HTML/… (Pandoc ou nativo)
  mcp_server.py    servidor MCP local (pastas autorizadas)
  describe.py      texto alternativo via Ollama local
  models.py        modelos de IA offline (pasta do usuário / embutidos na COMPLETA)
  packs.py         pacotes extras (Idiomas do OCR; Fórmulas na COMPLETA): .zip nas Releases, conferido (SHA-256) e
                   instalado na pasta do usuário; junta com os embutidos/do sistema (atalhos); instalador do Windows oferece
  edition.py       edições PADRÃO / COMPLETA (marca gravada no build; “leve” antiga = PADRÃO)
  credits.py       créditos e textos de licença (Ajuda > Sobre)
  gui.py           interface: fila, comparar com original, configurações, exportar, MCP…
  quick.py         botão direito “Converter para Markdown aqui” (sem a janela; configurações salvas)
  single.py        instância única: vários arquivos do botão direito → uma janela/um lote
  safety.py        proteções: ZIP-bomba, partes grandes, páginas de PDF gigantes
  paste.py         colar e converter (HTML/texto/imagem da área de transferência)
  aitools.py       Copiar para IA: tokens e divisão em partes
  agent_skill.py   skill “markinho” para Claude Code & cia. usarem o CLI (--instalar-skill/--mostrar-skill; botão no MCP)
  skillpack.py     Exportar como skill para IA (SKILL.md + chapters/; pasta, .zip ou ~/.claude/skills; --skill)
  tables.py        só as tabelas → Excel/CSV (formatos "xlsx"/"csv" do exportador; números, mesclagens, sem fórmulas)
  abnt.py          modelo de Word ABNT (exportação DOCX, nativo e Pandoc)
  splitter.py      dividir Markdown por títulos
  report.py        relatório do lote (CSV/HTML)
  diagnostics.py   relatório de erro: sistema, configurações, erros com a configuração usada (sem conteúdo)
  anonymize.py     anonimizar: CPF/CNPJ/PIS… (dígito verificador), e-mail, telefone, nomes com pista, lista,
                   metadados, EXIF das imagens (OutputOptions.anon; aplicado em finalize_result)
  outline.py       títulos do Markdown (painel Sumário)
  compare.py       comparar duas versões (parágrafos e palavras; relatório HTML)
  updates.py       lembrete de atualização sem internet (a cada 60 dias; data do build em resources/build-date.txt)
  support.py       Apoie o Markinho: Pix e agradecimento único aos 100/1.000 documentos
  privacy.py       texto de privacidade (Ajuda > Privacidade); PRIVACIDADE.md é cópia (teste confere)
  watch.py         pasta monitorada (QFileSystemWatcher + varredura)
  gui_simple.py    modos Simples/Completo (cabeçalho com a troca, SimpleView) e a folha de estilo comum (claro/escuro)
  gui_tools.py     janelas: Para IA, Dividir, Pasta monitorada, Relatório de erro, Assistente inicial
  winshell.py      liga/desliga o menu do botão direito do Windows pelo programa (HKCU; igual ao instalador)
  pagesync.py      “Ver original ao lado”: posição no texto ↔ página do PDF
  i18n.py          idiomas: tr(), num() (1.000 / 1,000); locale/en.json e es.json; idioma: MARKINHO_LANG > ui/lang > sistema
  sanitize.py      limpeza antes de exportar: sem downloads, sem scripts, imagens só das pastas do MCP
  __main__.py      `markinho` sem argumentos abre a interface; com arquivos roda no terminal
packaging/         build.py (todos os instaladores), markinho.spec (PyInstaller por edição),
                   windows/ (Inno Setup, WiX), icons/ (ícone: markinho.svg é o original; LEIA-ME.md explica)
tests/             pytest; fixtures/ com .doc/.xls/.ppt/.odt/.rtf de teste
SEGURANCA.md       registro das verificações de segurança: acrescente uma entrada a cada nova verificação
```

## Comandos

```bash
pip install -r requirements-padrao.txt -r requirements-dev.txt   # padrao | completa
QT_QPA_PLATFORM=offscreen python -m pytest -q                    # ~270 testes, ~35 s
QT_QPA_PLATFORM=offscreen python -m pytest -q --cov               # cobertura (mínimo em pyproject: fail_under)
python run.py                                                    # interface
python -m markinho arquivo.pdf -o saida.md                        # terminal
python packaging/build.py --edition padrao app zip deb           # instaladores (alvos: --help)
```

- Testes de interface rodam sem tela com `QT_QPA_PLATFORM=offscreen`.
- Função nova = teste novo (a cobertura mínima trava o CI). Regras de negócio (textfix, chunker, exporter,
  anonymize, mcp_server) devem ficar ≥ 90%; `quick.py` é testado também em subprocesso (não entra na conta).
- Tesseract do sistema: `apt-get install tesseract-ocr tesseract-ocr-por`.
- Modelos do Docling: `python -m markinho --download-models docling` (precisa de acesso ao
  Hugging Face; no ambiente de nuvem do projeto os hosts já estão liberados, exceto modelscope.cn).
- Acervo de documentos reais para teste: `git clone --depth 1 --filter=blob:none --sparse
  https://github.com/docling-project/docling` + `git sparse-checkout set tests/data`
  (só para testar localmente; **não** copiar esses arquivos para o repositório).

## Armadilhas conhecidas

- Python 3.13 + ElementTree: use `iterfind(".//{*}tag")`, não `iter("{*}tag")` (curinga não funciona).
- python-docx usa caminhos como `docx/parts/../templates`: o PyInstaller precisa das pastas
  intermediárias (marcadores em `packaging/pyinstaller/keep.txt`).
- Docling 2.x é “guarda-chuva” (`docling-slim[...]`): o spec segue os extras das dependências.
- O exportador cria `QApplication` (não só `QGuiApplication`), senão a interface quebra depois.
- QtPdf **precisa** ficar nos instaladores (visualizador “Comparar com o original”).
- Links Markdown não aceitam espaço: pastas de imagens usam `safe_stem()`.
- Repositório público: dá para ver o GitHub Actions daqui sem login, pela API
  (`curl -s https://api.github.com/repos/dontstopbelieve/markinho/actions/runs?per_page=5` e `/runs/<id>/jobs`).
  Os registros completos (logs) exigem login: peça ao dono o print da etapa vermelha.
- Sinais de QThread ligados a função comum rodam na thread de quem emite: use um QObject receptor
  (ver `quick.py`), senão a interface é mexida fora da thread principal e entra em loop.
- Segurança (auditoria de 14/11/2026): não use regex com `.*?` seguido de `\s*`/fechamento em texto
  vindo de documentos (trava com texto preparado; ver `chunker._HeadingRe`, `postprocess.strip_comments`);
  leia partes de ZIP com `safety.read_zip_member`; toda exportação passa por `sanitize.sanitize_markdown`.
  Testes em `tests/test_safety.py` e `tests/test_sanitize.py`.
- Avisos de conversão: `core.warn(msg, pages, info=False)`; páginas a revisar vão para
  `ConversionResult.review_pages`; `info=True` não mostra ⚠. Progresso/parada: `report_progress`,
  `check_cancel` (o PDF nativo chama a cada página).
- Testes com Qt: um único QApplication (`tests/conftest.py`); nunca crie/destrua QCoreApplication em
  testes. A janela abre no modo Simples; o conftest força o Completo (`MainWindow.DEFAULT_MODE`) e apaga
  `ui/mode` antes de cada teste — testes do Simples ficam em `tests/test_modos.py`. Tarefas em segundo plano recebem `quick.SettingsSnapshot`, não QSettings.
- Idiomas: texto novo na tela = `tr("...")` com texto literal (f-string vira `tr("{0}").format(x)`) **e** a
  tradução em `locale/en.json` e `locale/es.json` (o teste `test_i18n` acusa). Nunca passe códigos internos por `tr()` nem decida
  nada comparando texto traduzido. Testes rodam em português (`MARKINHO_LANG=pt` no conftest).
- Console do Windows é cp1252: não imprima “→”/acentos sem `reconfigure` (já feito em build.py e __main__).
