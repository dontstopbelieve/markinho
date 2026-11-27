# Segurança do Markinho

Registro das verificações e proteções de segurança pelas quais o Markinho passou, por data.
Cada nova verificação ganha uma entrada aqui.

## Como relatar uma falha de segurança

**Não abra uma issue pública** para falhas de segurança. Use o relato privado do GitHub:
aba **Security** do repositório > **Report a vulnerability**. Descreva o problema e, se possível,
um arquivo de exemplo que o reproduza (sem dados pessoais reais).

É um projeto pessoal, mantido quando possível: não há prazo garantido de resposta ou correção.

## O que o Markinho garante e o que não garante

**Garante (por projeto e por testes automáticos):**

- **Nenhum documento sai do computador.** A conversão, o OCR, a anonimização e a exportação rodam
  localmente. A descrição de imagens usa apenas o Ollama instalado na própria máquina
  (`localhost`). Não há telemetria nem busca automática de atualizações.
- **Arquivos maliciosos são recusados ou contidos:** bombas de ZIP, partes gigantes dentro de
  documentos do Office, páginas de PDF enormes, extensões de imagem perigosas, textos preparados
  para travar o programa.
- **Exportação limpa:** o Markdown exportado para HTML/Word/PDF não executa scripts e não baixa nada
  da internet.
- **Servidor para assistentes de IA (MCP):** só enxerga as pastas autorizadas pelo usuário; gravar
  exige permissão explícita; nunca sobrescreve um arquivo sem pedido.
- **Relatório de erro sem conteúdo:** não inclui o conteúdo dos documentos, omite pastas e o nome do
  usuário do computador, e nunca é enviado sozinho.

**Não garante:**

- **Anonimização perfeita.** É uma ajuda automática baseada em regras; o usuário deve revisar o
  resultado antes de qualquer uso (veja [PRIVACIDADE.md](PRIVACIDADE.md)).
- **Segurança de programas de terceiros** instalados à parte (Ollama, Pandoc do sistema, motores
  opcionais como Marker e PyMuPDF4LLM).
- **Instalador assinado.** O Markinho não tem assinatura digital paga; por isso o Windows mostra
  um aviso. Confira o arquivo baixado com o `SHA256SUMS.txt` publicado em cada versão.

O programa é fornecido “como está”, sem garantia de qualquer tipo (licença AGPL-3.0).

## Registro de verificações

### 14/11/2026 — Auditoria do código e da automação

- **Arquivos maliciosos:** documentos do Office são ZIPs; o Markinho confere tamanho e taxa de
  compressão **antes de abrir** (bomba de ZIP) e lê cada parte com limite de tamanho.
  Páginas de PDF gigantes têm a resolução limitada. A extensão de imagens vinda do documento é
  saneada (nunca grava `.exe`, `.bat`…). Campos de modelo aninhados são rejeitados.
- **Expressões regulares que travavam:** três padrões podiam congelar o programa com um texto
  preparado (ataque de lentidão). Foram reescritos; um teste mede o tempo com texto hostil.
- **Exportação:** scripts e atributos de evento removidos (fora de blocos de código); imagens
  remotas viram links (nada é baixado); no MCP, imagens só das pastas autorizadas.
- **Servidor MCP:** caminhos resolvidos (incluindo `..` e atalhos/links simbólicos) **antes** de
  conferir a pasta autorizada; filtro de listagem não aceita pastas nem `..`; gravação só com
  permissão; testes de acesso negado.
- **Descrição de imagens:** só aceita o Ollama em `localhost`.
- **Instância única:** o canal entre janelas do programa é local e restrito ao mesmo usuário.
- **GitHub Actions:** ações fixadas por SHA (não por versão “solta”), permissões mínimas
  (`contents: read`; escrita só ao publicar uma versão), entradas do “Run workflow” validadas,
  limite de tempo em todos os jobs.
- **Bibliotecas:** `pip-audit` sem falhas conhecidas; versões mínimas elevadas onde havia falha
  corrigida (pypdf, Pillow, soupsieve, opentelemetry).

### 15/11/2026 — Edição COMPLETA e relatório de erro

- **COMPLETA:** 213 pacotes auditados (Docling, PyTorch, Transformers, ONNX Runtime, RapidOCR,
  MarkItDown) sem falhas conhecidas. Docling roda em modo offline quando os modelos estão no
  computador e sem serviços remotos.
- **Relatório de erro:** o nome do usuário do Windows passou a ser omitido também em caminhos com
  barras duplicadas ou espaços (antes podia aparecer).
- **Riscos aceitos:** `appimagetool` (versão “continuous”) e pacotes do Chocolatey sem versão fixa,
  usados só para montar os instaladores no GitHub.

### 16/11/2026 — Privacidade, testes e preparação para abrir o código

- **Privacidade documentada** ([PRIVACIDADE.md](PRIVACIDADE.md) e Ajuda > Privacidade): o que o
  relatório de erro contém, o que nunca contém, e que nada é enviado automaticamente.
- **Anonimização** de dados pessoais com avisos de responsabilidade sempre visíveis; números com
  dígito verificador conferido; nada da correspondência “[PESSOA 1] = nome” é guardado; dados
  escondidos das imagens (GPS, câmera) removidos sem recompactar.
- **Word exportado** sem nome de autor nos metadados.
- **Cobertura de testes** medida a cada envio ao GitHub (mínimo obrigatório); regras de negócio
  (anonimização, exportação, correção de caracteres, MCP) acima de 89%.
- **Busca de segredos** em todo o histórico do Git: nenhuma chave, senha ou token; e-mail de autor é
  o endereço “noreply” do GitHub. Um nome de usuário real usado como exemplo num teste foi trocado
  por um fictício.
- **Bibliotecas:** `pip-audit` sem falhas conhecidas nas três edições e nas ferramentas de
  desenvolvimento.
- **Somas SHA-256** publicadas junto de cada versão, para conferir os instaladores.
- **Histórico do Git recomeçado** antes de abrir o código: o repositório passou a ter um único commit
  inicial, sem os rascunhos antigos nem o nome de usuário que havia num teste. O histórico anterior
  foi guardado pelo dono, fora do GitHub.

### 26/11/2026 — Revisão de código (privacidade da anonimização)

Revisão do pacote inteiro com a ferramenta de revisão do Claude Code. Corrigido, com um teste para cada:

- **Descrição das imagens** (texto alternativo) não era anonimizada: nomes e CPF nela passavam
  intactos. Agora só o endereço da imagem é protegido; o texto é anonimizado como o resto.
- **“Nome Completo: Fulano”** escondia a palavra “Completo” e deixava o nome à vista; agora o nome
  depois dos dois-pontos é o escondido.
- Número na lista de palavras quebrava o link de imagens (marcador interno trocado por um que
  nenhuma regra alcança).
- Fotos JPEG em CMYK podiam mudar de cor ao tirar os dados escondidos (o segmento “Adobe”, que diz
  como ler as cores, agora é mantido).
- Intervalo de anos (“2019-2020”) deixou de ser confundido com telefone; lista de nomes salva como
  “UTF-8 com BOM” passou a funcionar no terminal; a janela de anonimizar não trava mais a cada letra.

### 26–27/11/2026 — Repositório público e proteções automáticas do GitHub

- Repositório aberto (público), com o histórico já recomeçado e sem segredos.
- **Relato privado de falhas** ligado (aba Security > Report a vulnerability).
- **Dependabot**: análise automática das bibliotecas do projeto.
- **Code scanning (CodeQL)**: análise automática do código a cada mudança; primeira análise completa
  concluída em 27/11/2026. Resultados em Security > Code scanning.
- **Secret scanning** com bloqueio de envio de senhas/chaves (push protection).
- **Contribuições de código não aceitas** (CONTRIBUTING.md): reduz o risco de código malicioso entrar
  por pull request.

### 27/11/2026 — Idiomas e “Exportar como skill para IA”

- **Idiomas (inglês e espanhol):** nenhuma decisão do programa depende de texto traduzido (motivo de
  nova tentativa com outro motor e situação do relatório do lote usam códigos internos); testes
  conferem que todo texto tem tradução e que códigos internos não passam pela tradução.
- **Skill para IA:** nome da skill e nomes dos capítulos só com letras, números e hífens (sem `..`
  nem barras: não dá para gravar fora da pasta escolhida, inclusive dentro do .zip). Títulos do
  documento entram no índice sem quebras de linha e com `|`, `[` e `]` escapados (não mudam a tabela,
  os links nem o cabeçalho YAML); a descrição vai entre aspas, sem quebras e sem `<` `>`.
- **Texto do documento não é instrução:** o `SKILL.md` avisa o assistente para não seguir ordens
  escritas dentro dos capítulos (proteção contra documentos preparados para enganar a IA).
- **Substituir uma skill antiga** apaga só a pasta `chapters/` dela, depois de perguntar; se essa
  pasta for um atalho (link), só o atalho é removido, nunca o que ele aponta. Testes em
  `tests/test_skillpack.py`.
- **Privacidade:** a janela e o texto de Privacidade avisam que, ao usar a skill ou o “Copiar para
  IA” num assistente on-line, o conteúdo vai para esse serviço.

### 27/11/2026 — Lotes que retomam (terminal, botão direito, pasta monitorada, janela) e tabelas entre páginas

- **Privacidade do registro:** as chaves são impressões digitais do caminho (não o caminho) e o texto dos
  erros não é guardado — a pasta de saída pode ser compartilhada (inclusive depois de anonimizar) sem levar o
  nome dos arquivos originais. Teste: `test_erro_fica_registrado_e_e_refeito`.
- Exportações (janela, botão direito, terminal) e “Salvar todos” também gravam de forma atômica.

- O registro do lote (`.markinho-lote.json`) fica na pasta de saída e pode ser mexido por qualquer um: o
  nome de saída guardado nele só é usado se for um nome de arquivo simples (sem barras, `..`, `:` nem ponto
  inicial); senão o Markinho escolhe o nome normalmente. Registro estragado = recomeça, sem apagar nada.
- Gravação atômica (temporário na mesma pasta + troca): queda no meio nunca deixa arquivo pela metade nem
  temporário largado. Testes em `tests/test_batch.py` (inclusive “computador desligou no 2º arquivo”).
- Página só com tabela não passa mais pelo OCR (antes o texto da tabela era repetido como texto solto).

### 27/11/2026 — Só as tabelas → Excel/CSV

- **Injeção de fórmula:** célula vinda de documento que começa com `=`, `+`, `-` ou `@` nunca vira fórmula —
  no Excel é gravada como texto (`data_type = "s"`); no CSV ganha um apóstrofo na frente (números negativos
  de verdade não). Teste: `test_excel` e `test_csv_com_varias_tabelas_e_protecao`.
- Tabela HTML com `rowspan`/`colspan` absurdos (documento preparado) é limitada (1.000 por célula, 200 mil
  células) e não trava o programa.

### 27/11/2026 — Sigilo verificado automaticamente

- `tests/test_offline.py`: converte todos os tipos de arquivo (PDF, escaneado com OCR, Word, Excel, CSV,
  Markdown, .doc/.xls/.ppt/.odt/.ods/.odp/.rtf), anonimiza, exporta para 9 formatos (com imagem remota no
  texto, que não pode ser baixada) e usa o botão direito, o lote com `--retomar`, só as tabelas e a skill —
  com toda conexão de rede bloqueada e anotada. Um teste confere que o próprio bloqueio funciona.
- No GitHub (workflow Testes), o mesmo arquivo roda com `unshare -rn`: a máquina fica sem rede nenhuma, o que
  cobre também os programas externos (Pandoc, Tesseract).

### 27/11/2026 — Pacotes extras (modelos opcionais em .zip)

- O .zip traz `markinho-pacote.json` com SHA-256 e tamanho de cada arquivo. Recusa: arquivo fora da lista,
  arquivo faltando, conteúdo diferente, arquivo maior que o declarado (lido aos poucos, parando no limite —
  os modelos têm centenas de MB e não cabem em `safety.read_zip_member`), nomes com `..`, `\`, `:` ou
  absolutos, pastas fora das do pacote, pacote desconhecido, formato novo, total acima de 6 GB.
- Instala numa pasta temporária e só troca no fim (pacote ruim não deixa nada pela metade).
- O instalador do Windows confere o SHA-256 do .zip (baixado ou ao lado do instalador) antes de usá-lo.
- O Markinho não baixa nada: o teste de sigilo continua valendo. Testes em `tests/test_packs.py`.
- Pacote de idiomas do OCR: só aceita `tessdata/<idioma>.traineddata` e `tessdata_best/<idioma>.traineddata`
  dos 7 idiomas da lista; a pasta do Tesseract do sistema nunca é alterada (o pacote fica na pasta do usuário,
  com atalhos para os idiomas do sistema).

## Rotina antes de cada versão

1. `pip install pip-audit` e `pip-audit -r requirements-padrao.txt` (e as outras edições).
2. Testes completos: `QT_QPA_PLATFORM=offscreen python -m pytest -q --cov`.
3. Conferir que nenhum segredo ou dado pessoal entrou no repositório.
4. Registrar aqui o que foi verificado.
