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

## Rotina antes de cada versão

1. `pip install pip-audit` e `pip-audit -r requirements-padrao.txt` (e as outras edições).
2. Testes completos: `QT_QPA_PLATFORM=offscreen python -m pytest -q --cov`.
3. Conferir que nenhum segredo ou dado pessoal entrou no repositório.
4. Registrar aqui o que foi verificado.
