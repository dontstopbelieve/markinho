# Markinho — Conversor Markdown

> **Versão em preparação:** ainda não há instaladores publicados. Quando a primeira versão sair, os
> instaladores estarão na página **Releases** deste repositório.

## O conversor para documentos sigilosos

Contratos, processos, prontuários, folhas de pagamento, balanços: o Markinho transforma esses documentos em
texto limpo (Markdown) — para salvar, copiar para a IA, exportar para Word/PDF/Excel — **sem que nenhum deles
saia do seu computador**. Funciona com a internet desligada, não tem telemetria e não depende de nenhuma
empresa externa. Interface gráfica e linha de comando, em **português, inglês e espanhol**.

### Por que isso importa

Muitos conversores “inteligentes” mandam o arquivo para um servidor de outra empresa. A partir daí você não
controla mais onde ele fica, quem lê, por quanto tempo é guardado ou se é usado para treinar IA — um problema
real para quem lida com dados de clientes, pacientes ou funcionários (sigilo profissional, LGPD, GDPR).

| | Documento sai do computador? | Precisa de placa de vídeo? | Janela fácil (sem programar)? | Anonimiza dados pessoais? |
|---|:---:|:---:|:---:|:---:|
| Serviços na nuvem (Mistral OCR, GPT-4o, Gemini…) | **sim** — vai para a empresa | — | — | não |
| Modelos de IA locais (olmOCR, Qwen-VL, GOT-OCR) | não | sim, potente | não | não |
| Conversores com IA (Marker, MinerU) | não | melhor com | não | não |
| **Markinho** | **não — verificado** | **não** | **sim** | **sim** (CPF, CNPJ, nomes, PJe/SEI) |

### Sigilo verificado, não só prometido

- **Testado sem internet a cada mudança:** no GitHub, os testes de conversão rodam numa máquina **sem rede
  nenhuma** (PDF, escaneado com OCR, Word, Excel, formatos antigos, anonimização e exportação para 9 formatos).
  Se alguma parte do Markinho tentar se conectar, o teste falha e a versão não sai
  ([tests/test_offline.py](tests/test_offline.py)).
- **Nada é baixado sem você pedir:** imagens da internet dentro de um documento viram links (não são
  baixadas ao exportar); o programa não procura atualizações sozinho (só lembra você de conferir).
- **Código aberto (AGPL-3.0):** qualquer pessoa pode conferir o que o programa faz. Detalhes em
  [PRIVACIDADE.md](PRIVACIDADE.md) e [SEGURANCA.md](SEGURANCA.md).

### Qualidade, com honestidade

No teste público [olmOCR-bench](https://huggingface.co/datasets/allenai/olmOCR-bench) (Allen AI), a edição
PADRÃO — que roda em qualquer computador, sem IA, a ~0,5 s por página — tirou **cerca de 46%** (42,5% antes das
melhorias de cabeçalhos e colunas de 27/11/2026), e a COMPLETA, com IA de layout que também roda no computador, **53,5%**. Empata com
os melhores em **não perder texto** (99,5%) e fica atrás dos programas com IA pesada em fórmulas matemáticas e
escaneados muito antigos. Os líderes do teste usam IA com placa de vídeo ou serviços na nuvem (que mandam o
documento para fora).

O Markinho reúne num só programa ideias do [markitdown](https://github.com/microsoft/markitdown), do
[Docling](https://github.com/docling-project/docling), do [Marker](https://github.com/datalab-to/marker), do
[Pandoc](https://pandoc.org) e do [PyMuPDF4LLM](https://github.com/pymupdf/pymupdf4llm) (sem copiar código) e
já vem com soluções para os problemas mais comuns de conversão.

## Edições

| | **PADRÃO** | **COMPLETA** |
|---|:---:|:---:|
| Motor nativo: PDF (títulos, tabelas, colunas, código, imagens), Word, Excel, PowerPoint, HTML, EPUB, CSV… | ✔ | ✔ |
| AnyDoc: Word/Excel/PowerPoint antigos (.doc, .xls, .ppt), OpenDocument (.odt/.ods/.odp), RTF | ✔ | ✔ |
| **OCR** (escaneados, fotos e prints): português e inglês | ✔ | ✔ |
| **Pandoc**: ~35 formatos de entrada e 21 de exportação (Word, PDF, ODT, EPUB, LaTeX, PowerPoint…) | ✔ | ✔ |
| Correção de caracteres, imagens (pasta/base64), frontmatter, perfis (GFM, Obsidian, IA…) | ✔ | ✔ |
| **Pedaços para RAG/IA** (JSON/JSONL), por título, página ou tamanho | ✔ | ✔ |
| **Servidor MCP local**: Claude Desktop, Cursor e VS Code convertem arquivos pelo Markinho | ✔ | ✔ |
| **Exportar como skill para IA** (índice + um arquivo por capítulo para Claude Code, Claude.ai, Codex…) | ✔ | ✔ |
| Interface em **português, inglês e espanhol** | ✔ | ✔ |
| Descrição de imagens com IA local (se o Ollama estiver instalado) | ✔ | ✔ |
| **IA de layout (Docling)**, com modelos incluídos para funcionar **sem internet** | | ✔ |
| MarkItDown e RapidOCR | | ✔ |
| Tamanho aproximado do instalador | ~100–150 MB | ~1–1,5 GB |
| **Pacote extra Idiomas do OCR** (espanhol, francês, alemão, russo, chinês, árabe), opcional | ✔ | ✔ |
| **Pacote extra Fórmulas e código** (LaTeX), opcional | | ✔ |

### Qual edição escolher?

| Se você… | Edição |
|---|---|
| Converte documentos do dia a dia: Word, planilhas, PDFs, **escaneados, fotos e prints** | **PADRÃO** (recomendada) |
| Trabalha com **PDFs difíceis** (artigos científicos, tabelas complicadas, fórmulas) e tem um computador bom | **COMPLETA** |

- **PADRÃO — tudo para o dia a dia.** Converte PDF (títulos, tabelas, colunas, imagens), Word, Excel,
  PowerPoint, HTML, EPUB e CSV, inclusive os formatos antigos (.doc, .xls, .ppt), do LibreOffice e RTF.
  O **OCR** (português e inglês) lê PDFs escaneados, fotos e prints: trata a imagem antes, endireita páginas
  tortas e gira as de cabeça para baixo (no Windows, o modo *Máxima qualidade* usa modelos mais precisos).
  O **Pandoc** exporta para **21** formatos (Word, PDF, EPUB, ODT, PowerPoint, LaTeX, RTF…). Tem ainda
  correção de caracteres, pedaços e skills para IA, servidor MCP e o menu do botão direito no Windows.
- **COMPLETA — PADRÃO + IA de layout.** O **Docling** entende a página como uma pessoa: ordem de leitura
  em layouts complexos, tabelas com células mescladas, fórmulas e código. Funciona **sem internet**
  (os modelos vêm no instalador — por isso o tamanho). Traz também o MarkItDown (Microsoft) e o RapidOCR
  (OCR reserva; o Tesseract continua o principal). É mais lenta em PDFs: a IA usa muito o processador.

Até 27/11/2026 havia também uma edição LEVE (sem OCR nem Pandoc); como a diferença de tamanho era
pequena e a falta de OCR confundia, ela foi juntada à PADRÃO.

Para mudar de edição, instale a outra **por cima**: ela substitui a atual e as configurações
são mantidas. Todas as edições são **gratuitas**. Os componentes incluídos têm licenças
permissivas (MIT, BSD, Apache, LGPL…; veja [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)).

## Instalação

Baixe o arquivo da edição e do sistema na página
[**Releases**](https://github.com/dontstopbelieve/markinho/releases). `<Edição>` é `Padrao` ou
`Completa`:

| Sistema | Arquivo | Para quem |
|---|---|---|
| **Windows** | `Markinho-<Edição>-…-windows-x64-setup.exe` | **Recomendado.** Instalador com atalhos, menu **Markinho** no botão direito (“Converter para Markdown aqui” e “Abrir no Markinho”) e desinstalador. Não precisa de senha de administrador |
| Windows | `Markinho-<Edição>-…-windows-x64.msi` | Empresas e implantação em várias máquinas (GPO, Intune) |
| Windows | `Markinho-<Edição>-…-windows-x64-portatil.zip` | Pasta portátil: descompacte e abra `Markinho.exe` |
| Windows | `Markinho-<Edição>-…-windows-x64-portatil.exe` | Um arquivo só, sem instalar (PADRÃO). Abre mais devagar |
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

No **Windows**, o OCR (Tesseract) já vem dentro do instalador. No **Linux**, o `.deb` instala o Tesseract do sistema automaticamente. No
**macOS** (e no AppImage/tar.gz), instale o Tesseract à parte. As duas edições trazem também o **PP-OCR latino**
(PaddleOCR pelo RapidOCR, Apache-2.0), que funciona sem instalar nada, mantém acentos e lê melhor **letra
miúda**: no modo automático do OCR, o Markinho usa o Tesseract e troca para o PP-OCR em páginas limpas com letra
pequena (medido no olmOCR-bench). Pelo código-fonte, baixe o modelo uma vez com
`markinho --download-models ppocr`. Para o Tesseract no Mac:

```bash
brew install tesseract tesseract-lang
```

### Pelo código-fonte

Precisa do Python 3.10 ou mais recente. Escolha a edição pelo arquivo de dependências
(`requirements-padrao.txt` ou `requirements-completa.txt`):

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
| **Só as tabelas → Excel** | **Exportar** > “Excel — só as tabelas” (ou CSV): tira todas as tabelas do documento (PDF, Word, página da web…) para uma planilha — uma aba por tabela e uma aba **Índice** com o título (a legenda “Tabela 3 – …” ou o título da seção) e a página. Números viram números de verdade (“1.234,56”, “12,5%”, “R$ 10,00”), códigos com zero à esquerda ficam como texto, células mescladas continuam mescladas. No terminal: `markinho relatorio.pdf -t xlsx -o tabelas.xlsx` |
| **Word no padrão ABNT** | **Exportar** > DOCX > Modelo do Word: **ABNT** — Times New Roman 12, margens 3/2 cm, espaçamento 1,5, recuo de parágrafo, citações longas recuadas, seções numeradas e número de página |
| **PDFs de tribunais e órgãos públicos** | Remove a faixa vertical “Assinado eletronicamente por…”, códigos verificadores e endereços de conferência do PJe, SEI, eproc, e-SAJ (também a faixa lateral dos artigos do arXiv). Pode ser desligado nas opções do motor Nativo |
| **Páginas a revisar** | Quando o OCR tem baixa confiança ou uma página fica sem texto, aparece uma faixa amarela com as páginas; clique numa delas para ver o original ao lado |
| **Retomar lotes interrompidos** | Fechou ou travou no meio? Ao abrir, o Markinho oferece continuar de onde parou; botão direito, pasta monitorada e terminal pulam o que já está pronto. Veja [Retomar lotes interrompidos](#retomar-lotes-interrompidos) |
| **Progresso e Parar** | PDFs grandes mostram “página 12 de 80” na lista; **Parar** (Esc) interrompe na próxima página |
| **Pasta monitorada** | Ferramentas > Pasta monitorada: todo arquivo novo que cair na pasta (Downloads, scanner…) é convertido sozinho enquanto o Markinho estiver aberto |
| **Exportar como skill para IA** | Ferramentas > Exportar como skill para IA: o documento vira um índice + um arquivo por capítulo que o assistente consulta só onde precisa (veja [Skills para assistentes de IA](#skills-para-assistentes-de-ia)) |
| **Idioma da interface** | Configurações > Aparência > Idioma: português, inglês ou espanhol (ou o do sistema). Veja [Idiomas](#idiomas) |
| **Juntar e dividir** | Arquivo > Juntar todos em um .md; Ferramentas > Dividir por títulos (um arquivo por capítulo) |
| **Relatório do lote** | Ferramentas > Relatório do lote: planilha (CSV, abre no Excel) ou página HTML com o que deu certo, avisos e erros |
| **Relatório de erro** | Ajuda > Gerar relatório de erro: texto para mandar ao suporte, **sem o conteúdo dos documentos** (você confere antes de salvar) |
| **Modos Simples e Completo** | Como a calculadora do Windows: o Markinho abre no **Simples** — arrastar os documentos (a conversão começa sozinha), ver o texto formatado e usar 4 botões grandes: **Salvar, Copiar, Copiar para IA, Exportar** (Word, Word ABNT, PDF, Excel só com as tabelas, página web). O **Completo** tem tudo (motores, opções, abas, ferramentas). A troca fica sempre no alto da janela (Ctrl+1 / Ctrl+2); o Markinho lembra o último modo, e a fila e os textos são os mesmos nos dois. Avisos importantes aparecem no Simples com um link para conferir no Completo |
| **Assistente inicial** | Na primeira abertura, o Markinho pergunta para que você vai usá-lo (IA, Obsidian, documentação), ajusta as opções e oferece começar no modo simples |

**Como saber se há versão nova:** o Markinho **não acessa a internet** (é isso que protege os seus
documentos), então ele não sabe sozinho quando sai uma versão nova. Em vez disso, a cada 2 meses ele
lembra você de conferir a página [Releases](https://github.com/dontstopbelieve/markinho/releases) — a
página só abre se você clicar, e o lembrete pode ser desligado. A qualquer momento: **Ajuda > Procurar
atualizações…** (ou `markinho --version` no terminal).

**Atualizar ou trocar de edição:** basta rodar o instalador novo. Ele substitui a versão instalada no
mesmo lugar (não fica um programa duplicado), apaga antes os arquivos internos da versão anterior e
mantém as suas configurações. Vale para atualizar (3.0 → 3.1) e para subir ou descer de edição
(PADRÃO ↔ COMPLETA). No `.msi` e no `.deb` funciona do mesmo jeito.

## Problemas comuns e como o Markinho resolve

| Problema | Solução no Markinho |
|---|---|
| **Tabela que continua na página seguinte** | Uma tabela longa que quebra entre páginas do PDF vira **uma tabela só**, sem repetir o cabeçalho — inteira também nos pedaços para IA (RAG). Pode ser desligado nas opções do motor Nativo |
| **Tabelas quebradas** | Tabelas com linhas desenhadas no PDF são reconstruídas. Células **mescladas** (DOCX, PPTX, XLSX) viram tabela HTML com `rowspan`/`colspan`, que o Markdown aceita. Docling (IA) para tabelas difíceis |
| **Imagens perdidas** | Extraídas de DOCX, PPTX e PDF: numa pasta `<nome>_assets/` ao lado do `.md`, **embutidas** (base64) ou removidas. Opcional: descrição automática (texto alternativo) com IA local via **Ollama** |
| **Escaneados e prints** | **OCR local** automático nas páginas sem texto e em imagens (Tesseract, que mantém os acentos; ou RapidOCR). Docling e Marker têm OCR próprio |
| **Fotos de celular e cópias ruins** | Antes do OCR a imagem é tratada: tons de cinza, contraste automático, página torta endireitada e página de lado ou de cabeça para baixo girada. No modo **Máxima qualidade**, o Windows (PADRÃO/COMPLETA) usa os modelos *best* do Tesseract, mais precisos |
| **Várias colunas** | O leitor de PDF acha o espaço entre as colunas e lê uma coluna inteira antes da outra |
| **Cabeçalhos e rodapés** | Remove linhas repetidas no topo/rodapé das páginas e/ou corta uma margem fixa (%) |
| **Código e fórmulas** | Texto em fonte monoespaçada vira bloco de código com a indentação preservada. Fórmulas em LaTeX: Docling (opção “fórmulas”) ou Marker |
| **Palavras grudadas** | PDFs gerados pelo LaTeX (artigos científicos) e jornais usam espaços muito estreitos; o Markinho mede o espaço pelo tamanho da letra e separa as palavras certo |
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
| **Marker** | PDF de alta precisão com OCR e equações | Apache-2.0 (código) + modelos com restrição comercial | não incluído (o usuário pode instalar) |
| **PyMuPDF4LLM** | PDF muito rápido em CPU | **AGPL-3.0** | não incluído (o usuário pode instalar) |

**Uso offline:** a edição COMPLETA já traz os modelos do Docling de layout e de tabelas e funciona sem
internet.

### Pacotes extras

Recursos que poucas pessoas usam vêm **à parte**, para o instalador ficar menor (o GitHub aceita no
máximo 2 GB por arquivo). Instale só se for usar; depois de instalado, o pacote fica no computador e
funciona sem internet.

| Pacote | Tamanho | Para que serve | Vale a pena para | Dispensável para |
|---|---|---|---|---|
| **Idiomas extras do OCR** (`Markinho-Pacote-Idiomas-OCR-….zip`), PADRÃO e COMPLETA | ~95 MB | Lê escaneados, fotos e prints em espanhol (`spa`), francês (`fra`), alemão (`deu`), russo (`rus`), chinês simplificado (`chi_sim`, vertical: `chi_sim_vert`) e árabe (`ara`); versões rápida e precisa | Documentos escaneados nesses idiomas (contratos internacionais, imigração, traduções) | Documentos digitais (PDF com texto, Word…), que não usam OCR, e escaneados em português/inglês |
| **Fórmulas e código** (`Markinho-Pacote-Formulas-….zip`), só COMPLETA | ~640 MB | Converte equações em texto editável (LaTeX) e reconhece código de programação | Artigos científicos, teses, apostilas de exatas, documentação técnica | Contratos, processos, relatórios, documentos de escritório |

Como instalar:

- **No instalador do Windows** (`…-setup.exe`): na tela “Selecionar componentes”, marque o pacote. O
  instalador baixa o pacote da página [Pacotes extras](https://github.com/dontstopbelieve/markinho/releases/tag/pacotes-1) e confere a soma SHA-256. **Sem internet?** Coloque o `.zip`
  na mesma pasta do instalador: ele é usado direto.
- **Depois, em qualquer sistema**: baixe o `.zip` na página
  [Pacotes extras](https://github.com/dontstopbelieve/markinho/releases/tag/pacotes-1) e use *Ferramentas* > **Pacotes extras** >
  *Instalar de um arquivo…* (ou `markinho --instalar-pacote Markinho-Pacote-Formulas-….zip`;
  `markinho --pacotes` mostra o que está instalado).

O Markinho **não baixa nada sozinho**: quem baixa é o navegador ou o instalador, e só o pacote. Ao instalar,
o Markinho confere cada arquivo (SHA-256 e tamanho) e recusa pacotes danificados ou adulterados. Sem o
pacote de fórmulas, elas saem como texto simples ou imagem, e o Markinho avisa qual pacote resolve.

Depois de instalar os idiomas, o Markinho **reconhece sozinho** o idioma de cada página escaneada (idioma do
OCR em `auto`, o padrão): lê em português e inglês e, se a escrita for cirílica, árabe ou chinesa — ou o texto
for claramente espanhol, francês ou alemão —, lê de novo no idioma certo. Sem o pacote, ele avisa qual instalar.
Para fixar um idioma: *Configurações* › **Idiomas do OCR**, juntando com `+` (ex.: `por+spa`); no terminal,
`--opt ocr_lang=por+spa`. No Mac e no Linux o pacote de idiomas precisa do
Tesseract do sistema (que lá também pode receber idiomas pelo próprio gerenciador de pacotes).
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
- Tabelas que continuam na página seguinte do PDF são juntadas antes, então não viram dois pedaços soltos.
- **Tabelas e código nunca são cortados no meio**: tabelas grandes são divididas por linhas,
  repetindo o cabeçalho.
- Cada pedaço traz `id`, `text`, `headings` (caminho de títulos, repetido no início do texto),
  `page_start`/`page_end`, `kinds`, `chars`, `tokens` (estimativa) e `source`, além dos
  metadados do documento.

Na interface: **Exportar…** > “Pedaços para RAG / IA”. No terminal:
`markinho manual.pdf --chunks -o manual.jsonl --chunk-size 1000 --chunk-overlap 100`.

## Retomar lotes interrompidos

Se o Markinho fechar, travar ou o computador desligar no meio de um lote, ele **continua de onde parou** —
sem refazer o que já estava pronto. Vale para tudo (Configurações > Desempenho > **Retomar lotes
interrompidos**, ligado por padrão):

| Onde | O que acontece |
|---|---|
| **Janela** | Ao abrir de novo, o Markinho avisa que o último lote não terminou e oferece colocar de volta na fila os arquivos que faltavam. **Salvar todos** numa pasta onde já salvou grava por cima do mesmo arquivo (sem criar `_2`) |
| **Botão direito** (vários arquivos) | Arquivos já convertidos para aquela pasta, com as mesmas configurações e sem mudanças, são pulados; o que ficou pela metade ou deu erro é refeito |
| **Pasta monitorada** | Ao abrir o Markinho, converte o que chegou na pasta enquanto ele estava fechado e o que ficou pela metade; os arquivos que já estavam lá quando a monitoração começou continuam ignorados |
| **Terminal** | `--retomar` (veja acima) |

Como funciona: na pasta de saída fica um registro (`.markinho-lote.json`) com a **impressão digital
(SHA-256)** de cada arquivo e das configurações usadas. Se o arquivo de origem ou as configurações mudarem,
ele é convertido de novo. Os arquivos são gravados de forma **atômica** (primeiro num temporário, depois
trocados): uma queda nunca deixa um arquivo pela metade. Por privacidade, o registro **não guarda o nome nem
o caminho dos arquivos originais** (só impressões digitais), então a pasta de saída pode ser compartilhada,
inclusive depois de anonimizar.

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

## Ensinar o assistente de IA a usar o Markinho

Assistentes que trabalham no terminal (Claude Code, Codex, Copilot…) podem usar o Markinho sozinhos, sem
configurar servidor: **Ferramentas > Assistentes de IA > Instalar skill no Claude Code** (ou
`markinho --instalar-skill`) grava em `~/.claude/skills/markinho/SKILL.md` um guia com o caminho do
Markinho neste computador e os comandos mais úteis — converter, extrair tabelas para Excel, gerar pedaços
para IA, anonimizar, exportar para Word/PDF, lotes com `--retomar`. Depois é só pedir: “converta o
relatorio.pdf com o Markinho e extraia as tabelas”. Para outro assistente, `markinho --mostrar-skill`
mostra o texto para colar. A skill pede ao assistente que trate o conteúdo dos documentos como dado, não
como ordem. Ideia inspirada no Marker; texto próprio.

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
MediaWiki, Org, Textile, Jira, DocBook, Jupyter, texto puro, outros dialetos de Markdown e **só as tabelas em
Excel ou CSV**,
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

**Lotes que retomam de onde pararam:** veja [Retomar lotes interrompidos](#retomar-lotes-interrompidos).

```bash
markinho documentos/*.pdf -o saida/ --retomar
```

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

`--edition` aceita `padrao` ou `completa`; instale antes as dependências da
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
  batch.py        lotes que retomam de onde pararam (--retomar)
  tables.py       só as tabelas → Excel (uma aba por tabela + índice) ou CSV
  updates.py      lembrete de atualização a cada 2 meses (sem internet)
  agent_skill.py  skill que ensina assistentes de IA a usar o Markinho (--instalar-skill)
  aitools.py      Copiar para IA: tokens e divisão em partes
  skillpack.py    Exportar como skill para IA (SKILL.md + capítulos)
  anonymize.py    anonimização de dados pessoais
  compare.py      comparar duas versões
  naming.py       padrões de nome dos arquivos de saída
  presets.py      modos Rápido / Equilibrado / Máxima qualidade
  exporter.py     Markdown → DOCX/PDF/HTML/… (Pandoc ou nativo)
  models.py       modelos de IA para uso offline
  edition.py      edições PADRÃO / COMPLETA
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
- **Outros dados**: e-mail, telefone, CEP, **endereço** (Rua/Av./Travessa… com número), **data de nascimento**
  (depois de “nascido em”, “data de nascimento”; opção de manter **só o ano**), número de processo (CNJ),
  OAB, RG/CNH (com “RG”/“CNH” antes), placa (com “placa” antes), endereço IP.
- **O que ainda identifica**: depois de anonimizar, o Markinho avisa o que ficou no texto e ainda pode
  apontar a pessoa (endereço, CEP, data de nascimento, idade, telefone… de tipos que você desmarcou).
  Tirar só o nome não basta.
- **Tabela de correspondência** (opcional, desligada): grava `<nome>.correspondencia.csv` ao lado do arquivo,
  com `[PESSOA 1]` = nome original, para poder desfazer depois — é a “informação adicional” da
  pseudonimização da LGPD (art. 13, § 4º): **guarde em local seguro, separada do documento**.
- **Nomes**: assinaturas eletrônicas (“Assinado eletronicamente por…”) e nomes depois de pistas como
  Sr., Dra., réu, autor, paciente, nome: — cada nome encontrado é trocado no texto todo.
- **Sua lista** de nomes, empresas e lugares (sem diferenciar maiúsculas e acentos; `termo = substituto`).
- **Metadados e imagens**: tira autor, datas, assunto e nome do arquivo do frontmatter; tira GPS/câmera
  das imagens sem recompactar; opção de não incluir imagens.
- **Como trocar**: pseudônimo numerado (`[PESSOA 1]`, o mesmo dado sempre com o mesmo número),
  marcador (`[CPF]`) ou máscara parcial (`***.982.247-**`, `J. S.`).

No terminal: `markinho contrato.pdf --anonimizar` (ou `--anonimizar-lista nomes.txt`; `--anonimizar-ano` mantém só o
ano de nascimento; `--anonimizar-tabela` grava a tabela de correspondência).

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
