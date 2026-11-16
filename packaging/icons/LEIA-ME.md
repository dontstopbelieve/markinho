# Ícone do Markinho

Definido em 16/11/2026: folha de documento formada por uma **seta verde** (sobe pela esquerda) e uma
**seta amarela** (topo, canto dobrado, desce pela direita), com **“MD”** branco no centro, sobre um
quadrado arredondado **azul da bandeira do Brasil**. Representa a conversão para Markdown e de volta.

| Arquivo | Uso |
|---|---|
| `markinho.svg` | **original em vetor** (fonte de todos os outros) |
| `markinho-16.svg` | versão simplificada para 16 px (só as setas, mais grossas; letras seriam ilegíveis) |
| `markinho.ico` | Windows (16, 24, 32, 48, 64, 128 e 256 px; o 16 px usa a versão simplificada) |
| `markinho.icns` | macOS |
| `markinho.png` | Linux (256 px) |
| `../../markinho/resources/markinho.png` | janela do programa e Sobre (512 px) |

**Cores:** azul `#002776` (degradê a partir de `#0B3A94`), verde `#1DBF4E` (mais claro que o da
bandeira, `#009C3B`, para ter contraste no azul), amarelo `#FFDF00`, branco `#FFFFFF`.
**Letras:** fonte Raleway ExtraBold (peso 800), SIL Open Font License 1.1, convertidas em desenho.

## Refazer os arquivos

Requisitos: `pip install fonttools Pillow PySide6`.

1. (Só se for mudar o desenho) recriar os SVG a partir da fonte Raleway (`Raleway[wght].ttf`, do
   Google Fonts, pasta `ofl/raleway`); o número é a altura do “MD” (104 em 512):

   ```bash
   cd packaging/icons && python ferramentas/gera_svg.py 104 "Raleway[wght].ttf"
   ```

2. Gerar PNG, `.ico` e `.icns` a partir dos SVG e copiar para os lugares acima:

   ```bash
   python packaging/icons/ferramentas/gera_icones.py packaging/icons/markinho.svg packaging/icons/markinho-16.svg /tmp/icones
   ```

   Copie `markinho.ico` e `markinho.icns` para `packaging/icons/`, `markinho-256.png` como
   `packaging/icons/markinho.png` e `markinho-512.png` como `markinho/resources/markinho.png`.

O histórico completo do estudo (opções avaliadas, versões anteriores, conversa sobre o uso de “MD”)
fica no pacote de identidade visual guardado pelo dono, fora do repositório.
