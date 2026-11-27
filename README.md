# Markinho — Conversor Markdown

> **Versão em preparação:** ainda não há instaladores publicados. Quando a primeira versão sair, os
> instaladores estarão na página **Releases** deste repositório.

Converte documentos **para Markdown** e de **Markdown para outros formatos**, com
interface gráfica e linha de comando, em **português, inglês e espanhol**. **Tudo roda no seu
computador**: nenhum documento é enviado para a internet.

Reúne num só programa as ideias do
[markitdown](https://github.com/microsoft/markitdown), do
[Docling](https://github.com/docling-project/docling), do
[Marker](https://github.com/datalab-to/marker), do [Pandoc](https://pandoc.org) e do
[PyMuPDF4LLM](https://github.com/pymupdf/pymupdf4llm), e já vem com soluções para os
problemas mais comuns de conversão.

## Edições

| | **LEVE** | **PADRÃO** | **COMPLETA** |
|---|:---:|:---:|:---:|
| Motor nativo: PDF (títulos, tabelas, colunas, código, imagens), Word, Excel, PowerPoint, HTML, EPUB, CSV… | ✔ | ✔ | ✔ |
| AnyDoc: Word/Excel/PowerPoint antigos (.doc, .xls, .ppt), OpenDocument (.odt/.ods/.odp), RTF | ✔ | ✔ | ✔ |
| Correção de caracteres, imagens (pasta/base64), frontmatter, perfis (GFM, Obsidian, IA…) | ✔ | ✔ | ✔ |
| Exportação para DOCX, PDF, HTML e TXT | ✔ | ✔ | ✔ |
| **Pedaços para RAG/IA** (JSON/JSONL), por título, página ou tamanho | ✔ | ✔ | ✔ |
| **Servidor MCP local**: Claude Desktop, Cursor e VS Code convertem arquivos pelo Markinho | ✔ | ✔ | ✔ |
| **Exportar como skill para IA** (índice + um arquivo por capítulo para Claude Code, Claude.ai, Codex…) | ✔ | ✔ | ✔ |
| Interface em **português, inglês e espanhol** | ✔ | ✔ | ✔ |
| Descrição de imagens com IA local (se o Ollama estiver instalado) | ✔ | ✔ | ✔ |
| **Pandoc**: ~35 formatos de entrada e 21 de exportação (ODT, EPUB, LaTeX, RTF, PowerPoint…) | | ✔ | ✔ |
| **OCR** (escaneados e imagens): português e inglês | | ✔ | ✔ |
| **IA de layout (Docling)**, com modelos incluídos para funcionar **sem internet** | | | ✔ |
| MarkItDown e RapidOCR | | | ✔ |
| Tamanho aproximado do instalador | ~50–90 MB | ~100–150 MB | ~1–2 GB |

### Qual edição escolher?

Cada edição tem tudo o que a anterior tem, e mais um pouco. Todas funcionam 100% no computador.

| Se você… | Edição |
|---|---|
| Só converte **arquivos digitais** (Word, planilhas, PDFs gerados no computador) | **LEVE** |
| Também tem **escaneados, fotos de documentos ou prints**, ou quer exportar para muitos formatos | **PADRÃO** |
| Trabalha com **PDFs difíceis** (artigos científicos, tabelas complicadas, fórmulas) e tem um computador bom | **COMPLETA** |

- **LEVE — o essencial.** Converte PDF (títulos, tabelas, colunas, imagens), Word, Excel, PowerPoint,
  HTML, EPUB e CSV, inclusive os formatos antigos (.doc, .xls, .ppt), do LibreOffice e RTF. Corrige
  caracteres trocados, exporta para Word/PDF/HTML/TXT, gera pedaços para IA (RAG), tem o servidor MCP e o
  menu do botão direito no Windows. **Não lê texto em imagens nem em PDFs escaneados.**
- **PADRÃO — LEVE + OCR + Pandoc.** O **OCR** (português e inglês) lê PDFs escaneados, fotos e prints:
  trata a imagem antes, endireita páginas tortas e gira as de cabeça para baixo (no Windows, o modo
  *Máxima qualidade* usa modelos mais precisos). O **Pandoc** aceita ~35 formatos de entrada e exporta
  para **21** (EPUB, ODT, PowerPoint, LaTeX, RTF…), contra 4 da LEVE.
- **COMPLETA — PADRÃO + IA de layout.** O **Docling** entende a página como uma pessoa: ordem de leitura
  em layouts complexos, tabelas com células mescladas, fórmulas e código. Funciona **sem internet**
  (os modelos vêm no instalador — por isso o tamanho). Traz também o MarkItDown (Microsoft) e o RapidOCR
  (OCR reserva; o Tesseract continua o principal). É mais lenta em PDFs: a IA usa muito o processador.

Para mudar de edição, instale a outra **por cima**: ela substitui a atual e as configurações
são mantidas. Todas as edições são **gratuitas**. Os componentes incluídos têm licenças
permissivas (MIT, BSD, Apache, LGPL…; veja [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)).

## Instalação

Baixe o arquivo da edição e do sistema na página
[**Releases**](https://github.com/dontstopbelieve/markinho/releases). `<Edição>` é `Leve`,
`Padrao` ou `Completa`:

| Sistema | Arquivo | Para quem |
|---|---|---|
| **Windows** | `Markinho-<Edição>-…-windows-x64-setup.exe` | **Recomendado.** Instalador com atalhos, menu **Markinho** no botão direito (“Converter para Markdown aqui” e “Abrir no Markinho”) e desinstalador. Não precisa de senha de administrador |
| Windows | `Markinho-<Edição>-…-windows-x64.msi` | Empresas e implantação em várias máquinas (GPO, Intune) |
| Windows | `Markinho-<Edição>-…-windows-x64-portatil.zip` | Pasta portátil: descompacte e abra `Markinho.exe` |
| Windows | `Markinho-<Edição>-…-windows-x64-portatil.exe` | Um arquivo só, sem instalar (LEVE e PADRÃO). Abre mais devagar |
| **macOS** | `Markinho-<Edição>-…-macos-arm64.dmg` (M1/M2/M3…) ou `…-macos-x64.dmg` (Intel) | Arraste para Aplicativos. Na primeira vez: botão direito no app > **Abrir** (o app não é assinado pela Apple) |
| **Linux** | `markinho-<edição>_…_amd64.deb` | Ubuntu, Debian, Mint: `sudo apt install ./markinho-padrao_…_amd64.deb` |
| Linux | `Markinho-<Edição>-…-x86_64.AppImage` | Qualquer distribuição: `chmod +x` e abra |
| Linux | `Markinho-<Edição>-…-linux-x64.tar.gz` | Pasta portátil |
| **Python** | `markinho-…-py3-none-any.whl` | `pipx install "markinho[padrao]"` ou `"markinho[completa]"` a partir do arquivo |

Os instaladores **não têm assinatura digital** (que é paga). Por isso, na primeira vez, o
**Windows** pode mostrar “O Windows protegeu o computador”: clique em **Mais informações** >
**Executar assim mesmo**. No **macOS**: botão direito no app > **Abrir** > **Abrir**.
Isso acontece com arquivos baixados da internet: depois de liberado uma vez, o aviso não volta para
aquele arquivo, e o programa **instalado** não mostra o aviso. Na versão **ZIP portátil**, para evitar o
aviso em cada executável: antes de extrair, clique com o botão direito no `.zip` > **Propriedades** >
marque **Desbloquear** > **OK**, e só então extraia.

**Botão direito no Windows** (instalador `.exe`): selecione um ou vários arquivos > **Markinho** >
- **Converter para Markdown…**: pergunta onde salvar (com vários arquivos, só a pasta), mostra uma
  janelinha com a porcentagem — que pode ser ocultada ou desligada — e avisa ao terminar, com
  “Abrir arquivo” e “Abrir pasta”.
- **Converter para Markdown aqui**: igual, mas sem perguntar: grava o `.md` ao lado de cada arquivo.
- **Abrir no Markinho**: abre os arquivos na fila do programa (uma janela só, mesmo com vários arquivos).
- Em arquivos **.md**: **Converter Markdown para…** escolhe o formato (Word — inclusive ABNT —, PDF,
  HTML, ODT, EPUB…) e onde salvar, com a mesma janelinha de andamento e o aviso de concluído.

Todas usam as configurações salvas no programa (modo, imagens, correção, padrão de nome).

Na versão **ZIP portátil** (que não instala nada) ou se o menu não aparecer, ligue-o pelo próprio
programa: **Ferramentas > Botão direito do Windows** (só para o seu usuário, sem senha de administrador).
O assistente da primeira abertura também oferece essa opção. No Windows 11 o menu fica em **Mostrar mais opções** (o menu novo exige um pacote com assinatura digital
paga). O Windows não deixa programas se fixarem sozinhos na barra de tarefas: abra o Markinho, clique com o
botão direito no ícone dele na barra e escolha **Fixar na barra de tarefas**.

No **Windows**, o OCR (Tesseract) já vem dentro do instalador das edições PADRÃO e
COMPLETA. No **Linux**, o `.deb` instala o Tesseract do sistema automaticamente. No
**macOS** (e no AppImage/tar.gz), instale o Tesseract à parte para ter OCR com acentos (a
COMPLETA também traz o RapidOCR, que funciona sem instalar nada, mas perde acentos):

```bash
brew install tesseract tesseract-lang
```

### Pelo código-fonte

Precisa do Python 3.10 ou mais recente. Escolha a edição pelo arquivo de dependências
(`requirements-leve.txt`, `requirements-padrao.txt` ou `requirements-completa.txt`):

```bash
pip install -r requirements-padrao.txt
```

```bash
python run.py
```

## Recursos para o dia a dia

| Recurso | Como usar |
|---|---|
| **Sumário clicável** | Ao lado do texto aparecem os títulos do documento; clique para ir até eles (Exibir > Sumário, Ctrl+Shift+O) |
| **Prévia enquanto converte** | Em PDFs grandes, o texto das páginas já lidas aparece enquanto o resto converte (provisório; o texto final, com títulos e tabelas, vem ao terminar) |
| **Ler imagem como tabela ou código** | Botão direito numa foto/print da lista > **Ler esta imagem como tabela / código / texto corrido**: o OCR monta colunas de tabela ou mantém a indentação do código |
| **Comparar duas versões** | Ferramentas > Comparar duas versões: escolha a versão antiga e a nova (PDF, Word, Markdown…) e veja o que saiu, entrou ou mudou, palavra por palavra; salva um relatório em HTML |
| **Código colorido** | Blocos de código aparecem coloridos na Visualização e no HTML exportado |
| **Colar e converter** | Copie um trecho de uma página da web, do Word ou de um e-mail e use **Colar** (Ctrl+Shift+V): vira Markdown na hora. Uma imagem copiada (print de tela) passa pelo OCR |
| **Copiar para IA** | Botão **Para IA** (Ctrl+Alt+C): texto enxuto (sem imagens e comentários), contagem de *tokens* e divisão em partes que cabem no ChatGPT, Claude ou Gemini — cada parte avisa o assistente para esperar a última |
| **Word no padrão ABNT** | **Exportar** > DOCX > Modelo do Word: **ABNT** — Times New Roman 12, margens 3/2 cm, espaçamento 1,5, recuo de parágrafo, citações longas recuadas, seções numeradas e número de página |
| **PDFs de tribunais e órgãos públicos** | Remove a faixa vertical “Assinado eletronicamente por…”, códigos verificadores e endereços de conferência do PJe, SEI, eproc, e-SAJ (também a faixa lateral dos artigos do arXiv). Pode ser desligado nas opções do motor Nativo |
| **Páginas a revisar** | Quando o OCR tem baixa confiança ou uma página fica sem texto, aparece uma faixa amarela com as páginas; clique numa delas para ver o original ao lado |
| **Progresso e Parar** | PDFs grandes mostram “página 12 de 80” na lista; **Parar** (Esc) interrompe na próxima página |
| **Pasta monitorada** | Ferramentas > Pasta monitorada: todo arquivo novo que cair na pasta (Downloads, scanner…) é convertido sozinho enquanto o Markinho estiver aberto |
| **Exportar como skill para IA** | Ferramentas > Exportar como skill para IA: o documento vira um índice + um arquivo por capítulo que o assistente consulta só onde precisa (veja [Skills para assistentes de IA](#skills-para-assistentes-de-ia)) |
| **Idioma da interface** | Configurações > Aparência > Idioma: português, inglês ou espanhol (ou o do sistema). Veja [Idiomas](#idiomas) |
| **Juntar e dividir** | Arquivo > Juntar todos em um .md; Ferramentas > Dividir por títulos (um arquivo por capítulo) |
| **Relatório do lote** | Ferramentas > Relatório do lote: planilha (CSV, abre no Excel) ou página HTML com o que deu certo, avisos e erros |
| **Relatório de erro** | Ajuda > Gerar relatório de erro: texto para mandar ao suporte, **sem o conteúdo dos documentos** (você confere antes de salvar) |
| **Assistente inicial e modo simples** | Na primeira abertura, o Markinho pergunta para que você vai usá-lo (IA, Obsidian, documentação) e ajusta as opções. O **modo simples** esconde motores e opções avançadas (Exibir > Modo simples) |

**Atualizar ou trocar de edição:** basta rodar o instalador novo. Ele substitui a versão instalada no
mesmo lugar (não fica um programa duplicado), apaga antes os arquivos internos da versão anterior e
mantém as suas configurações. Vale para atualizar (3.0 → 3.1) e para subir ou descer de edição
(LEVE ↔ PADRÃO ↔ COMPLETA). No `.msi` e no `.deb` funciona do mesmo jeito.

## Problemas comuns e como o Markinho resolve

| Problema | Solução no Markinho |
|---|---|
| **Tabelas quebradas** | Tabelas com linhas desenhadas no PDF são reconstruídas. Células **mescladas** (DOCX, PPTX, XLSX) viram tabela HTML com `rowspan`/`colspan`, que o Markdown aceita. Docling (IA) para tabelas difíceis |
| **Imagens perdidas** | Extraídas de DOCX, PPTX e PDF: numa pasta `<nome>_assets/` ao lado do `.md`, **embutidas** (base64) ou removidas. Opcional: descrição automática (texto alternativo) com IA local via **Ollama** |
| **Escaneados e prints** | **OCR local** automático nas páginas sem texto e em imagens (Tesseract, que mantém os acentos; ou RapidOCR). Docling e Marker têm OCR próprio |
| **Fotos de celular e cópias ruins** | Antes do OCR a imagem é tratada: tons de cinza, contraste automático, página torta endireitada e página de lado ou de cabeça para baixo girada. No modo **Máxima qualidade**, o Windows (PADRÃO/COMPLETA) usa os modelos *best* do Tesseract, mais precisos |
| **Várias colunas** | O leitor de PDF acha o espaço entre as colunas e lê uma coluna inteira antes da outra |
| **Cabeçalhos e rodapés** | Remove linhas repetidas no topo/rodapé das páginas e/ou corta uma margem fixa (%) |
| **Código e fórmulas** | Texto em fonte monoespaçada vira bloco de código com a indentação preservada. Fórmulas em LaTeX: Docling (opção “fórmulas”) ou Marker |
| **Caracteres trocados** | Correção de mojibake (`Ã§` → `ç`), acentos soltos, ligaduras, hifenização e mais, com relatório do antes e depois |
| **Dialetos de Markdown** | Perfis de saída: GitHub (GFM), padronizado (mdformat), **Obsidian** e **Texto para IA** (sem imagens nem comentários, para economizar tokens) |
| **Metadados** | Frontmatter YAML opcional com título, autor, datas, nº de páginas e arquivo de origem |
| **IA que altera o texto** | A conversão é determinística: nada é resumido nem reescrito. A IA local só entra se você pedir (OCR, layout, descrição de imagens) |

## Motores de conversão

| Motor | Ponto forte | Licença | Edição |
|---|---|---|---|
| **Nativo** | Rápido, sem IA: layout de PDF, colunas, código, imagens, OCR, tabelas mescladas | MIT | todas |
| **AnyDoc** | Muito rápido (Rust). Word/Excel/PowerPoint **antigos** (.doc, .xls, .ppt), OpenDocument, RTF, notas de rodapé, equações. O Markinho usa só o modo local | MIT | todas |
| **Pandoc** | DOCX, ODT, EPUB, LaTeX, RST, RTF, Jupyter e dezenas de outros | GPL-2.0 (programa separado) | PADRÃO e COMPLETA |
| **Docling** | IA de layout: ordem de leitura, tabelas, fórmulas, OCR | MIT | COMPLETA |
| **MarkItDown** | Microsoft; amplo suporte a Office, HTML e Outlook (.msg) | MIT | COMPLETA |
| **Marker** | PDF de alta precisão com OCR e equações | GPL-3.0 + modelos com restrição comercial | não incluído (o usuário pode instalar) |
| **PyMuPDF4LLM** | PDF muito rápido em CPU | **AGPL-3.0** | não incluído (o usuário pode instalar) |

**Uso offline:** a edição COMPLETA já traz os modelos do Docling e funciona sem internet.
Rodando pelo código-fonte, use *Motores* > **Baixar modelos** (ou
`markinho --download-models docling`) uma vez, num computador com internet.

## Nomes dos arquivos de saída

Em **Salvar todos** e em **Exportar** (um arquivo por documento), um **padrão** define o nome
de cada arquivo, com prévia antes de salvar:

| Marcador | Significado | Exemplo |
|---|---|---|
| `{nome}` | nome original, sem extensão (ou o nome dado com F2) | `contrato` |
| `{n}` | número na ordem da lista (zeros à esquerda configuráveis; `{n:02}` também funciona) | `001` |
| `{titulo}` | título do documento | `Relatório Anual` |
| `{data}` | data de hoje | `2026-11-13` |
| `{original}` | nome original com extensão | `contrato.pdf` |
| `{pasta}` / `{motor}` | pasta de origem / motor usado | `Clientes` / `anydoc` |

- Padrões prontos: manter o nome, número + nome (`001_contrato.md`), número + título, data + nome…
- Extensão do Markdown: `.md`, `.markdown` ou `.txt`.
- **Nomes seguros:** sem acentos nem espaços, em minúsculas (`Relatório Final.pdf` → `relatorio-final.md`).
- Se o arquivo já existir: acrescentar `_2`, substituir ou pular.
- A pasta de imagens acompanha o novo nome (`001_contrato_assets/`) e os links no `.md` são corrigidos.

No terminal: `markinho *.pdf -o saida/ --nome "{n}_{nome}" --nome-seguro --se-existir skip`
(opções `--inicio`, `--digitos` e `--ext` também existem).

## Pedaços para RAG / IA

Para alimentar bancos vetoriais e buscas com IA (LangChain, LlamaIndex, Chroma…), o Markinho
divide o Markdown em **pedaços** e grava em JSONL (um por linha) ou JSON:

- **Por título** (padrão): cada seção vira um pedaço; seções longas são divididas e as muito
  pequenas são unidas. **Por página** (com as marcas de página do PDF) ou **só por tamanho**.
- Tamanho máximo e **sobreposição** configuráveis.
- **Tabelas e código nunca são cortados no meio**: tabelas grandes são divididas por linhas,
  repetindo o cabeçalho.
- Cada pedaço traz `id`, `text`, `headings` (caminho de títulos, repetido no início do texto),
  `page_start`/`page_end`, `kinds`, `chars`, `tokens` (estimativa) e `source`, além dos
  metadados do documento.

Na interface: **Exportar…** > “Pedaços para RAG / IA”. No terminal:
`markinho manual.pdf --chunks -o manual.jsonl --chunk-size 1000 --chunk-overlap 100`.

## Skills para assistentes de IA

Uma *skill* é um pacote que assistentes como **Claude Code, Claude.ai, Codex, GitHub Copilot** e outros
compatíveis com o formato aberto **Agent Skills** consultam quando a pergunta é sobre aquele assunto. Em vez
de colar o documento inteiro na conversa, o assistente lê um índice curto e abre **só o capítulo de que
precisa**: gasta bem menos *tokens* e responde pelo texto real, dizendo de qual capítulo veio a resposta.

**Como criar:** converta o documento e use **Ferramentas > Exportar como skill para IA…**

1. Escolha **o que exportar**: o documento atual ou todos os convertidos numa skill só (um grupo de
   capítulos por documento).
2. Confira o **nome** (vira o comando no assistente, ex.: `/manual-do-produto`) e a **descrição** — é ela
   que o assistente lê para decidir quando consultar a skill. Os dois já vêm preenchidos.
3. Escolha **onde salvar**: numa **pasta** (para copiar para a pasta de skills do seu assistente), num
   **.zip** (para enviar nas configurações do Claude.ai, na parte de Skills) ou **direto no Claude Code**
   deste computador (`~/.claude/skills`).

**O que é gerado:**

```
manual-do-produto/
  SKILL.md                 nome, descrição, instruções ao assistente e índice dos capítulos
  chapters/
    01-introducao.md
    02-instalacao.md
    …
```

- Os capítulos saem dos **títulos do documento** (nível 1; se não houver, nível 2 ou 3). Capítulos muito
  grandes são divididos de novo (~6 mil *tokens* no máximo) e trechos minúsculos (nomes de autores,
  palavras-chave…) juntam-se ao vizinho. Blocos de código nunca são cortados no meio.
- O índice mostra, para cada capítulo, os assuntos (subtítulos) e o tamanho estimado em *tokens*.
- As instruções pedem ao assistente que abra só o capítulo necessário, cite de onde veio a informação, não
  invente e **não siga ordens escritas dentro dos documentos** (proteção contra textos maliciosos).
- Imagens ficam de fora (o assistente não as vê); a descrição delas, se houver, é mantida.
- Feito **sem IA e sem internet**. Se você usar a skill num assistente on-line, o texto dos capítulos vai
  para esse serviço: em documentos sigilosos, anonimize antes.

No terminal: `markinho manual.pdf --skill -o manual.zip` (ou `-o pasta/`; vários arquivos viram uma skill
só; `--skill nome-da-skill` define o nome). Ideia inspirada no
[book-to-skill](https://github.com/virgiliojr94/book-to-skill); o código do Markinho é próprio.

## Idiomas

A interface está em **português (Brasil)**, **inglês** e **espanhol**: menus, botões, mensagens, janelas,
ajuda do terminal, servidor MCP, relatório do lote e o texto de Privacidade.

- Por padrão o Markinho usa o **idioma do sistema** (português → português, espanhol → espanhol, os outros
  → inglês). Para escolher: **Configurações > Aparência > Idioma**; vale ao abrir o programa de novo.
- No terminal, a variável `MARKINHO_LANG` escolhe o idioma (`MARKINHO_LANG=en markinho --help`).
- Os números seguem o idioma (1.000 em português e espanhol, 1,000 em inglês).
- Ficam em português de propósito: o relatório de erro (é lido pelo suporte), os marcadores do texto
  anonimizado (`[PESSOA 1]`, `[CPF]`), as marcas de página dentro do Markdown e os nomes das opções do
  terminal.
- A anonimização e o OCR ainda são pensados para o Brasil: os documentos reconhecidos são brasileiros (CPF,
  CNPJ, PIS…) e o OCR lê português e inglês. E-mails, cartões de crédito e a sua lista funcionam em
  qualquer idioma.

## Assistentes de IA (servidor MCP local)

Claude Desktop, Cursor, VS Code e outros assistentes compatíveis com **MCP** podem usar o
Markinho para ler seus documentos, sem nada sair do computador:

1. No Markinho, abra **Assistentes IA**, adicione as **pastas autorizadas** e, se quiser,
   permita que o assistente salve arquivos nelas.
2. Clique em **Configurar no Claude Desktop** (ou copie a configuração para o Cursor/VS Code)
   e reinicie o assistente.
3. Peça, por exemplo: “Liste os documentos que o Markinho pode ler” ou “Converta o contrato
   X.pdf e resuma as cláusulas de multa”.

Ferramentas oferecidas ao assistente: `markinho_info`, `list_documents`, `convert_document`,
`convert_to_chunks` (somente leitura) e `export_markdown`/`save_markdown` (só com permissão
de gravação; nunca substituem arquivos sem pedido).

**Segurança:** o assistente só acessa arquivos dentro das pastas autorizadas. Caminhos com
`..` e links simbólicos são resolvidos antes da verificação. Sem pastas autorizadas, nada pode
ser lido. No terminal: `markinho --mcp` inicia o servidor; `markinho --mcp-config claude`
mostra a configuração; `markinho --mcp-config install-claude` instala no Claude Desktop. A
variável `MARKINHO_MCP_FOLDERS` substitui as pastas configuradas.

## Exportação (Markdown →)

Word, PDF, HTML, ODT, EPUB, PowerPoint, RTF, LaTeX, Typst, reStructuredText, AsciiDoc,
MediaWiki, Org, Textile, Jira, DocBook, Jupyter, texto puro e outros dialetos de Markdown,
com título, sumário, numeração de seções e **modelo de estilos** (.docx/.odt/.pptx). As
imagens extraídas vão junto. Sem Pandoc, os exportadores nativos geram DOCX, PDF (sem
precisar de LaTeX), HTML e TXT.

## Uso

**Interface gráfica:** abra o Markinho, ou rode `markinho` sem argumentos.

- **Fila:** arraste arquivos ou pastas para **qualquer lugar da janela**. Eles se acumulam na fila
  (⏸) e só são convertidos quando você clica em **Converter** (F5). Shift+F5 converte só os
  selecionados, **Cancelar** devolve à fila o que ainda não começou, e a opção **Converter ao
  adicionar** volta ao comportamento automático.
- Arraste os itens dentro da lista para **reordenar**; **F2** (ou duplo clique) define outro
  **nome de saída** para o item.
- Ícones: ✔ = pronto, ⚠ = avisos (caracteres irrecuperáveis etc.), ✖ = erro.
- **Ver original ao lado** (Ctrl+D): o arquivo original aparece ao lado do texto convertido (PDF com as
  páginas de verdade). Em PDFs, **as páginas acompanham a leitura**: rolando o texto, o PDF vai para a
  página correspondente, e vice-versa (caixa **Rolar junto**: ao ligar, os dois lados se alinham na hora,
  pela página). **Mais espaço** esconde a lista e o painel enquanto você confere;
  as divisórias entre as colunas podem ser arrastadas.
  Também mostra imagens e prévia de Word/ODT/PowerPoint/Excel/EPUB. Depois de **Exportar**, o arquivo
  gerado pode ser aberto **dentro do programa** (“Ver aqui”) ou no aplicativo padrão.
- **Modo** (painel Configurações): **Rápido** (sem OCR, layout e imagens — lotes grandes),
  **Equilibrado** (padrão) ou **Máxima qualidade** (IA de layout Docling, na edição COMPLETA), e
  quantas **conversões ao mesmo tempo**. No terminal: `--modo rapido|equilibrado|qualidade`.
- No modo Automático, se um motor não conseguir ler um arquivo, o Markinho **tenta outro motor**
  sozinho e avisa qual usou.
- Abas: **Markdown** (editável), **Visualização** (com imagens) e **Correções**.
- Painel **Configurações**: motor e opções, correção de caracteres, **Saída** (imagens,
  perfil, metadados, Ollama) e **Aparência** (tema claro/escuro e idioma).
- Correções, perfil, metadados e modo das imagens mudam na hora, sem reconverter.

**Terminal:** com arquivos, o mesmo comando roda sem interface. No Windows, use
`markinho-cli.exe`, que fica na pasta de instalação.

```bash
markinho relatorio.pdf -o relatorio.md
```

```bash
markinho scan.pdf --opt ocr=force
```

```bash
markinho artigo.pdf --images base64 --frontmatter
```

```bash
markinho *.pdf -o saida/ --profile llm
```

```bash
markinho tese.docx -e pandoc --opt flavor=commonmark_x
```

```bash
markinho relatorio.pdf -t docx -o relatorio.docx
```

```bash
markinho fotos/*.png --describe qwen2.5vl:3b
```

```bash
markinho manual.pdf --skill -o manual.zip
```

```bash
markinho --engines
```

Os exemplos, na ordem: converter um arquivo; forçar OCR em todas as páginas; embutir as
imagens e incluir metadados; converter vários arquivos com o perfil “Texto para IA”; usar o
Pandoc com outro dialeto; converter PDF → Markdown → Word; descrever imagens com o Ollama;
criar uma skill para assistentes de IA; listar motores, OCR e formatos disponíveis.

**Como biblioteca:**

```python
from markinho import convert
from markinho.textfix import FixOptions
from markinho.postprocess import OutputOptions
from markinho.assets import write_assets
from markinho.exporter import export

r = convert("arquivo.pdf", fix=FixOptions(), output=OutputOptions(frontmatter=True))
print(r.markdown)
write_assets(r.markdown, r.assets, "pasta_destino")   # imagens extraídas
export(r.markdown, "arquivo.docx", "docx")
```

## Gerar os instaladores

Os instaladores são gerados automaticamente pelo GitHub Actions
(`.github/workflows/release.yml`): na aba **Actions** > **Instaladores** > **Run workflow**,
ou criando uma tag `v3.0.0`, que também publica uma Release. Para gerar no seu computador:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

```bash
python packaging/build.py --edition padrao all
```

`--edition` aceita `leve`, `padrao` ou `completa`; instale antes as dependências da
edição (`requirements-<edição>.txt`). `all` gera tudo o que o sistema atual permite.
Também dá para pedir alvos específicos: `app`, `zip`, `onefile`, `inno`, `msi`, `dmg`,
`deb`, `appimage`, `tessdata`, `models`, `wheel`. O `inno` precisa do Inno Setup, e o `msi`
precisa do WiX (`dotnet tool install --global wix`). Para a COMPLETA sem placa de vídeo,
instale antes o PyTorch para processador:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

## Estrutura

```
markinho/
  core.py         convert(): motor → imagens → correção → perfil/metadados
  engines.py      motores: Nativo, AnyDoc, Pandoc, Docling, Marker, MarkItDown, PyMuPDF4LLM
  anydoc_engine.py AnyDoc: modelo do documento → Markdown (imagens, tabelas mescladas, notas)
  converters.py   conversores nativos (DOCX, XLSX, PPTX, HTML, EPUB, CSV, ZIP…)
  pdf.py          PDF: layout, colunas, código, imagens, OCR, cabeçalhos
  ocr.py          Tesseract / RapidOCR
  assets.py       imagens (pasta/base64) e tabelas HTML
  postprocess.py  frontmatter YAML e perfis de saída
  describe.py     texto alternativo com IA local (Ollama)
  textfix.py      correção de caracteres
  chunker.py      pedaços para RAG (JSON/JSONL)
  aitools.py      Copiar para IA: tokens e divisão em partes
  skillpack.py    Exportar como skill para IA (SKILL.md + capítulos)
  anonymize.py    anonimização de dados pessoais
  compare.py      comparar duas versões
  naming.py       padrões de nome dos arquivos de saída
  presets.py      modos Rápido / Equilibrado / Máxima qualidade
  exporter.py     Markdown → DOCX/PDF/HTML/… (Pandoc ou nativo)
  models.py       modelos de IA para uso offline
  edition.py      edições LEVE / PADRÃO / COMPLETA
  credits.py      créditos (incluídos × inspiração) e textos de licença
  mcp_server.py   servidor MCP local (pastas autorizadas)
  i18n.py         idiomas da interface: tr() e locale/en.json, locale/es.json
  privacy.py      texto de privacidade (PRIVACIDADE.md é cópia)
  gui.py          interface PySide6
  gui_tools.py    janelas das ferramentas (Para IA, skill, dividir, pasta monitorada…)
packaging/        PyInstaller, Inno Setup, WiX, .deb, AppImage, DMG, ícones
tests/            pytest
```

## Licença e manutenção

O Markinho é **software livre e gratuito**, sob a licença
**[GNU AGPL-3.0](LICENSE)**: você pode usar, estudar, modificar e distribuir; quem distribuir uma
versão modificada — ou oferecê-la como serviço pela internet — precisa liberar o código-fonte dela
sob a mesma licença. Para uso em produto de código fechado, peça uma licença comercial ao autor.

É fornecido **“como está”, sem garantia de qualquer tipo**. É um **projeto pessoal**: não há
garantia de atualizações, correções ou suporte. **Relatos de problema** (issues) são bem-vindos;
**contribuições de código não são aceitas** (pull requests são fechados sem revisão; motivo em
[CONTRIBUTING.md](CONTRIBUTING.md)).

Copyright © 2026 dontstopbelieve.

Segurança: veja [SEGURANCA.md](SEGURANCA.md) (verificações já feitas e como relatar uma falha).

## Apoie o Markinho

O Markinho é gratuito e continuará gratuito. Se ele foi útil e você quiser agradecer, pode fazer
uma doação de qualquer valor por **Pix**. É totalmente **opcional** e **não cria nenhuma obrigação**
de suporte, correções ou novas versões — o projeto continua “como está”.

<img src="markinho/resources/apoie-pix.png" alt="QR Code do Pix para apoiar o Markinho" width="200">

**Chave Pix (aleatória), por extenso:**

```
1487d3bd-979f-482e-a83a-026329e0b143
```

**Pix copia e cola** (para colar no app do banco):

```
00020126580014br.gov.bcb.pix01361487d3bd-979f-482e-a83a-026329e0b1435204000053039865802BR5908MARKINHO6006BRASIL62070503***63047522
```

No aplicativo do banco aparece o nome do mantenedor como recebedor — é o padrão do Pix.
No programa: **Ajuda > Apoie o Markinho**.
Outras formas de ajudar (sem dinheiro): relatar problemas, sugerir funções e indicar o Markinho
(veja [CONTRIBUTING.md](CONTRIBUTING.md)).

## Créditos

O Markinho é feito sobre o trabalho de muitos projetos de código aberto: **Ajuda > Sobre o
Markinho** mostra os créditos, com autores, licenças e links, além dos projetos que inspiraram
ideias (markitdown, Docling, Marker, Pandoc, Unstructured…). Os textos completos das licenças
estão em **Ajuda > Licenças de terceiros**, na pasta `licenses/` e em
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). O Markinho é independente e não é afiliado
a esses projetos. Obrigado a todos os desenvolvedores!

## Anonimizar dados pessoais

Marque **Anonimizar dados pessoais** nas configurações (botão **Opções…** para escolher o quê) ou use
**Ferramentas > Anonimizar um arquivo Markdown…** para um .md já salvo. Tudo no computador, só com regras:

- **Números com dígito verificador conferido** (não apaga números comuns): CPF, CNPJ (inclusive o novo
  CNPJ com letras), PIS/NIS, título de eleitor, cartão de crédito.
- **Outros dados**: e-mail, telefone, CEP, número de processo (CNJ), OAB, RG/CNH (com “RG”/“CNH” antes),
  placa (com “placa” antes), endereço IP.
- **Nomes**: assinaturas eletrônicas (“Assinado eletronicamente por…”) e nomes depois de pistas como
  Sr., Dra., réu, autor, paciente, nome: — cada nome encontrado é trocado no texto todo.
- **Sua lista** de nomes, empresas e lugares (sem diferenciar maiúsculas e acentos; `termo = substituto`).
- **Metadados e imagens**: tira autor, datas, assunto e nome do arquivo do frontmatter; tira GPS/câmera
  das imagens sem recompactar; opção de não incluir imagens.
- **Como trocar**: pseudônimo numerado (`[PESSOA 1]`, o mesmo dado sempre com o mesmo número),
  marcador (`[CPF]`) ou máscara parcial (`***.982.247-**`, `J. S.`).

No terminal: `markinho contrato.pdf --anonimizar` (ou `--anonimizar-lista nomes.txt`).

**Como a lista funciona:** maiúsculas, minúsculas e acentos **não** fazem diferença (“joão”, “JOÃO” e
“Joao” são iguais), mas **cada variação precisa ser escrita**: “João da Silva” não esconde “João”,
“Sr. Silva” nem “J. Silva”. Coloque todas as formas, uma por linha (apelidos, sobrenome sozinho, siglas,
plural, erros de digitação). Para que variações virem o mesmo marcador, use `João = [PESSOA A]`.

> **Aviso:** a anonimização automática nunca é 100%. **O Markinho não se responsabiliza por dados que
> deixarem de ser encontrados ou que forem trocados por engano; cabe ao usuário revisar o arquivo
> anonimizado antes de qualquer uso ou compartilhamento.** Trocar nomes por `[PESSOA 1]` é
> *pseudonimização* (para a LGPD ainda pode ser dado pessoal se der para descobrir quem é).

## Privacidade

Tudo roda no seu computador: nenhum documento, texto ou nome de arquivo vai para a internet, e não
há telemetria. O **relatório de erro** (Ajuda > Gerar relatório de erro…) junta a versão, dados
básicos do sistema (sistema operacional, processador, memória, idioma, tela), as configurações
sem pastas e, para cada erro, o nome/tipo/tamanho do arquivo, a mensagem, os detalhes técnicos e a
configuração usada — **nunca o conteúdo dos documentos** nem o nome do usuário. Ele só fica na
memória enquanto o programa está aberto e nada é enviado sozinho: você confere e decide.
**Copiar para IA** e **Exportar como skill para IA** só preparam o texto ou os arquivos no computador;
quando você usa esse material num assistente on-line, ele vai para esse serviço, conforme as regras dele.
Detalhes em [PRIVACIDADE.md](PRIVACIDADE.md) e em **Ajuda > Privacidade e relatório de erro**.

## Diagnóstico

Se uma conversão falhar, rode no terminal com `MARKINHO_DEBUG=1` para ver os registros
internos dos motores e o erro completo, por exemplo
`MARKINHO_DEBUG=1 markinho arquivo.pdf -e docling` (no Windows:
`set MARKINHO_DEBUG=1` antes de `markinho-cli.exe`).

## Testes

```bash
python -m pytest
python -m pytest --cov --cov-report=html     # cobertura: abra htmlcov/index.html
```

A cobertura (quanto do código os testes usam) é medida também no GitHub a cada envio: o relatório
fica em Actions > Testes > Artifacts > `cobertura-testes` (7 dias). Se a cobertura cair abaixo do
mínimo definido em `pyproject.toml` (`fail_under`), o teste falha. As regras de negócio (correção de
caracteres, pedaços para IA, exportação, anonimização, MCP) ficam acima de 89%. Os testes também
conferem que todo texto da interface tem tradução em inglês e espanhol.
