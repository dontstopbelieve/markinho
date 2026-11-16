# Pendências do Markinho

Lista viva do que falta. Atualize ao concluir cada item. (Revisada em 15/11/2026.)

## Onde paramos (16/11/2026)

221 testes, cobertura 76% (mínimo 75% no CI). Desde 15/11: relatório de erro com configuração e
sistema, privacidade, anonimização (com avisos), cobertura de testes, decisão de projeto gratuito e
aberto e **licença AGPL-3.0 aplicada**. Instalador PADRÃO (Windows/Linux) gerado sem erros na execução
#10 (commit dfc39ec, ainda sem a licença).

**Próximos passos, em ordem:**
1. Dono testa no Windows o instalador PADRÃO (anonimização, relatório de erro, botão direito, pastas
   lembradas, Ver original ao lado) e relata o que achar.
2. Ícone (dono decide; começar do zero).
3. Antes de tornar público: revisar o histórico do Git, avisar que pull requests não são aceitos,
   modelo de relato de problema (issue).
4. Tornar o repositório público (o dono aperta o botão) → GitHub Actions passa a ser gratuito.
5. Publicar a v3.0.0 (Releases) com changelog; README com casos de uso e screenshots.

## Decisões que dependem do dono do projeto

- [x] **Nome do produto**: **Markinho — Conversor Markdown** (decidido em 13/11/2026).
      O nome provisório anterior já era usado por terceiros (um produto da Fraunhofer SIT e um
      projeto no GitHub), por isso foi trocado. Busca no INPI (13/11/2026): nenhuma marca
      “Markinho” e nenhum programa de computador “MARKINHO”.
- [x] **Busca por radical no INPI** (13/11/2026): 13 marcas contêm “Markinho” (Markinhos Moura,
      Markinho Duran, Markinhos Festas & Lanches, Markinhos Multi…), **nenhuma nas classes 9 ou 42**
      (software): são das classes 41 (entretenimento), 35, 37; a única antiga de classe 09 (1990) está
      arquivada. Pelo princípio da especialidade, marcas iguais convivem em classes diferentes.
      Busca de patente: nada (nomes não se patenteiam).
- [ ] **Busca opcional**: variação de som “Marquinho” nas classes 9 e 42.
- [ ] **Registro da marca “Markinho” no INPI** (opcional; tem taxa, com desconto para pessoa física
      e microempresa). O subtítulo “Conversor Markdown” é descritivo e não se registra.
- [x] **Repositório renomeado** para `dontstopbelieve/markinho` (13/11/2026).
- [ ] **Ícone**: a definir.
- [x] **Modelo do projeto** (decidido em 16/11/2026): **gratuito e de código aberto, “como está”**, sem
      venda e sem obrigação de atualizações ou suporte (projeto pessoal, versões quando o dono quiser).
      As três edições continuam, como tamanhos de download, todas grátis.
- [x] **Licença** (decidida em 16/11/2026): **AGPL-3.0** — ninguém pode fechar o código nem oferecer uma
      versão modificada como serviço on-line sem abrir as mudanças. **Aplicada** (era preciso o
      arquivo LICENSE e ajustar os textos — feito em 16/11/2026).
- [x] **Contribuições** (16/11/2026): **não aceitar código de terceiros** (só relatos de problema/issues),
      para o dono continuar único autor e poder, no futuro, oferecer licença comercial a quem pedir
      (licenciamento duplo). Ideias de outros projetos podem inspirar; código nunca é copiado.
      Dependências continuam **permissivas** (MIT/BSD/Apache/LGPL): uma dependência GPL/AGPL embutida
      impediria a licença comercial futura — por isso Marker e PyMuPDF continuam fora dos instaladores.
- [ ] **Repositório público**: decidido abrir, depois de aplicar a licença e revisar o histórico.

## Antes de publicar

- [x] **AGPL-3.0 aplicada** (16/11/2026): LICENSE (texto oficial), `pyproject.toml`, cabeçalho SPDX em
      todos os .py, README (Licença e manutenção), janela Sobre, termos do instalador, LICENSE nos
      instaladores.
- [x] **Busca de segredos e bibliotecas** (16/11/2026): nenhuma chave/senha/token em todo o histórico
      (73 commits); e-mail de autor é o “noreply” do GitHub; `pip-audit` sem falhas conhecidas nas três
      edições e nas ferramentas de desenvolvimento. Nome real trocado por fictício num teste.
- [x] **Histórico recomeçado** (16/11/2026): um único commit inicial; o histórico antigo (com rascunhos
      de ícone e um nome de usuário de teste) foi guardado pelo dono fora do GitHub
      (`markinho-historico-ate-2026-11-16.bundle`). Antes de tornar público: apagar as execuções antigas
      do GitHub Actions (cada execução > “…” > Delete workflow run), que apontam para commits antigos.
- [ ] **Antes de tornar público**: avisar que pull requests não são aceitos, modelo de issue simples.
- [ ] **Depois de público**: ligar os alertas do Dependabot (Settings > Code security > Dependabot
      alerts) — avisam sozinhos quando uma biblioteca ganha falha conhecida. Rodar `pip-audit` antes de
      cada release (`pip install pip-audit` e `pip-audit -r requirements-padrao.txt`).
- [ ] **Revisão jurídica dos avisos** (16/11/2026): o aviso “O Markinho não se responsabiliza…” da
      anonimização (janela, painel, termos de uso do instalador, PRIVACIDADE.md) e o “como está” dos
      termos; sem venda, o risco é menor, mas vale (opcional) um advogado revisar antes de divulgar.
      Também revisar PRIVACIDADE.md (LGPD).
- [x] **Instaladores LEVE no GitHub** (14/11/2026, execução #3): Windows completo (ZIP, EXE portátil,
      instalador .exe e .msi) e Linux (.deb, .tar.gz, teste do programa) ✓. Corrigidos: console do
      Windows sem UTF-8, coleta do MCP sem typer, caractere inválido no termos.rtf (WiX), ações do
      GitHub para Node.js 24, macOS 14/13 aposentados → macos-latest / macos-15-intel.
- [x] **Botão direito do Windows** (14/11/2026): submenu Markinho > “Converter para Markdown aqui”
      (sem abrir a janela) e “Abrir no Markinho”; instância única (vários arquivos = uma janela/um lote);
      mais formatos; dica da barra de tarefas no fim da instalação. **Testar num Windows real.**
      O .msi (WiX) não tem o menu do botão direito (só o instalador .exe).
- [x] **Instaladores PADRÃO no GitHub** (14/11/2026, execução #6, commit 6118499): Windows e Linux ✓,
      já com OCR melhorado e menu do botão direito.
- [ ] **Instaladores: falta** testar no computador do dono (Windows), rodar o macOS (`macos`) e a
      edição COMPLETA.
- [x] **Rodar os instaladores no GitHub** (só o dono consegue, o repositório é privado):
      Actions > Instaladores > Run workflow > “Edições”: `leve`, “Sistemas”: `linux,windows`
      (o macOS gasta 10× a cota; deixe para depois) > Run workflow. Ao terminar,
      os arquivos ficam em “Artifacts”, no fim da página da execução. Se falhar, abrir o job em
      vermelho e copiar a mensagem de erro.
      **Custo**: em repositório **privado** no plano gratuito são 2.000 min/mês de Actions, e o
      macOS conta 10× e o Windows 2×; o armazenamento de artefatos é de 500 MB. Uma execução com as
      3 edições pode consumir a maior parte da cota e a COMPLETA (1–2 GB) não cabe no armazenamento.
      Em repositório **público**, o Actions é gratuito e sem esse limite.
- [x] **Conferir os testes automáticos** (Actions > Testes; verdes em 14/11). Para economizar a cota, agora rodam só
      no Linux e só quando o código muda; o Windows é opcional (Run workflow > marcar “windows”).
- [ ] **Publicar a versão** (tag `v3.0.0` → Releases; a release já sai com `SHA256SUMS.txt`): depois de testar os instaladores e
      decidir a licença.
- [x] **Auditoria de segurança focada + verificação das bibliotecas** (14/11/2026): pip-audit sem falhas
      nas versões dos instaladores (mínimos elevados: pypdf, Pillow, soupsieve, opentelemetry); corrigidos
      ZIP-bomba, página de PDF gigante, extensão de imagem, listagem e exportação do MCP, downloads e
      scripts na exportação, 3 regex que travavam com texto preparado, Ollama só local, ações do GitHub
      fixadas por SHA, permissões mínimas e campos do Run workflow validados.
      COMPLETA (15/11): 213 pacotes auditados (Docling, PyTorch, Transformers, ONNX, RapidOCR, MarkItDown)
      sem falhas; Docling em modo offline quando os modelos estão no computador e sem serviços remotos.
      Riscos aceitos: appimagetool (versão “continuous”) e pacotes do Chocolatey sem versão fixa no CI.
- [ ] **Auditoria completa** com a skill da Cloudflare — opcional, antes do lançamento.
      https://github.com/cloudflare/security-audit-skill — focar em: servidor MCP (injeção de
      instruções vinda de documentos), arquivos maliciosos (ZIP-bomba, imagens gigantes, XML do
      EPUB, expressões regulares lentas), HTML exportado com `<script>`, cadeia de suprimentos do
      GitHub Actions. É a operação mais cara: muitos agentes.

## Decidido / feito em 13/11/2026

- [x] **Assinatura digital** dos instaladores: **não** (sem custo). Avisos do Windows (SmartScreen:
      “Mais informações” > “Executar assim mesmo”) e do macOS (botão direito > Abrir) documentados.
- [x] **Docling em PDF** testado (texto, tabelas, escaneado); OCR do Docling agora usa o Tesseract.
- [x] **Licenças dos modelos do Docling** conferidas: Apache-2.0, CDLA-Permissive-2.0, MIT
      (texto da CDLA em `licenses/`).
- [x] **Documentos reais**: 164 arquivos do acervo de testes do Docling → 163 convertidos (o outro é
      PDF com senha, com mensagem clara). Corrigidos: controles de conteúdo e caixas de texto no
      DOCX, EPUB, forma desconhecida no PPTX; tentativa automática com outro motor.
- [x] **MCP com assistente real**: testado com o Claude Code (listar, converter, acesso negado fora
      das pastas). Claude Desktop, Cursor e VS Code usam o mesmo protocolo.
- [x] **Comparar com o original** e ver arquivo exportado dentro do programa.
- [x] **Modos** Rápido / Equilibrado / Máxima qualidade e conversões simultâneas.
- [x] **OCR**: só português e inglês em todas as edições.
- [x] **OCR melhorado** (14/11/2026): imagem tratada antes (cinza, contraste, endireitar, girar página
      de lado/invertida) e modelos *best* no modo Máxima qualidade (Windows PADRÃO/COMPLETA; +~25 MB).
      Os modelos best não puderam ser baixados no ambiente de nuvem: confirmar no build do Windows.

## Mais tarde

- [ ] **Testes de regressão com réplicas falsas** (plano de 16/11): tabela que quebra entre páginas,
      DOCX com caixas de texto/notas/comentários, XLSX com várias abas e células mescladas, PPTX com
      tabelas, página escaneada torta/invertida gerada no teste. Regra: defeito corrigido = teste novo
      com uma réplica do arquivo (nunca o documento real de terceiros).
- [ ] **README**: casos de uso (advocacia/PJe + anonimização, pesquisa + RAG, Obsidian, IA/JSONL),
      screenshots e GIFs (depois do ícone).
- [ ] **Acessibilidade**: contraste, navegação por teclado, leitor de tela, fonte ampliada.
- [ ] **Assinatura digital gratuita** para código aberto (ex.: SignPath Foundation; tem requisitos),
      depois de o repositório ficar público.
- [ ] **Benchmark de qualidade** dos motores (texto, títulos e tabelas corretos, não só tempo).
- [ ] **Anonimização — nomes sem pista (COMPLETA)**: hoje (16/11/2026) a anonimização acha nomes só
      por pistas (Sr., réu, paciente, assinatura…) e pela lista do usuário. Detectar qualquer nome exige
      um modelo de IA de reconhecimento de nomes; antes, conferir a licença do modelo (venda permitida).
- [ ] **Tradução da interface** — só **português (Brasil) e inglês**; fazer depois de definir o nome:
      - Formato: arquivos **`.po`** (texto, um por idioma) numa pasta `lang/` ao lado do programa,
        lidos direto (sem compilar). Editável no Bloco de Notas ou no Poedit.
      - Tamanho: ~400–480 textos (~4–5 mil palavras), quase 40% na interface.
      - Custo: estrutura (uma vez) moderada a alta; inglês feito pelo Claude, com revisão antes do
        lançamento internacional; manutenção a cada função nova.

## Ferramentas para o Claude (avaliadas em 13/11/2026)

- Não instalar por enquanto: oh-my-claudecode (multiagentes, muito consumo), chrome-devtools-mcp e
  Vercel (só se houver site do produto — há Chromium/Playwright na sessão), Supabase (só se houver
  servidor/banco: contas, licenças online, anúncios), Cartographer e claude-code-setup (genéricos;
  substituídos pelo `CLAUDE.md`), claude-mem (memória se perde nas sessões em nuvem; grava tudo).
- Plugins de terceiros com hooks executam código: só de fontes confiáveis e depois da auditoria.
- [x] `CLAUDE.md` criado: memória do projeto lida em toda sessão nova.

## Limitações conhecidas

- No macOS e no AppImage/tar.gz do Linux, o OCR com acentos precisa do Tesseract instalado à parte.
- RTF convertido pelo AnyDoc pode perder o nível dos títulos.
- RapidOCR (só na COMPLETA, como reserva do Docling) perde acentos; o Tesseract é o OCR principal.
