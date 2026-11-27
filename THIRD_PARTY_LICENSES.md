# Componentes de terceiros

O Markinho — Conversor Markdown é distribuído em três edições. Todos os componentes incluídos têm licenças
que **permitem uso e venda comercial**. Esta lista atende às exigências de atribuição
dessas licenças. Os **textos completos** das licenças acompanham o programa: na pasta
`licenses/` da instalação (textos gerais MIT, BSD-3-Clause, Apache-2.0, LGPL-3.0, GPL-3.0,
CDLA-Permissive-2.0) e em `licenses/third_party/`, com o arquivo de licença de cada biblioteca
incluída. Também podem ser lidos no programa, em **Ajuda > Licenças de terceiros**.

O Markinho é um projeto independente: não é afiliado, patrocinado nem endossado pelos projetos e
empresas citados, cujos nomes e marcas pertencem aos respectivos donos. Projetos que apenas
inspiraram ideias (markitdown, Marker, PyMuPDF4LLM, Unstructured, file2markdown) estão em
**Ajuda > Créditos**; nenhum código deles foi copiado.

## Todas as edições (PADRÃO e COMPLETA)

| Componente | Licença | Observação |
|---|---|---|
| Python | PSF License | https://docs.python.org/3/license.html |
| Fonte Raleway (letras “MD” do ícone) | SIL Open Font License 1.1 | https://github.com/impallari/Raleway — as letras foram convertidas em desenho no ícone; a fonte em si não é distribuída. Texto da licença em `licenses/Raleway-OFL-1.1.txt` |
| Qt 6 / PySide6 / Shiboken6 | **LGPL-3.0** | Usado por ligação dinâmica: as bibliotecas do Qt ficam como arquivos separados na pasta do programa e podem ser substituídas pelo usuário. Código-fonte: https://code.qt.io |
| pypdf | BSD-3-Clause | https://github.com/py-pdf/pypdf |
| pdfplumber, pdfminer.six | MIT | https://github.com/jsvine/pdfplumber |
| pypdfium2 / PDFium | Apache-2.0 / BSD-3-Clause | https://github.com/pypdfium2-team/pypdfium2 |
| python-docx, python-pptx | MIT | https://github.com/python-openxml |
| openpyxl | MIT | https://openpyxl.readthedocs.io |
| xlrd | BSD | https://github.com/python-excel/xlrd |
| Beautiful Soup | MIT | https://www.crummy.com/software/BeautifulSoup |
| markdownify | MIT | https://github.com/matthewwithanm/python-markdownify |
| Python-Markdown | BSD-3-Clause | https://github.com/Python-Markdown/markdown |
| Pygments | BSD-2-Clause | https://pygments.org — código colorido na visualização e no HTML exportado |
| mdformat, mdformat-gfm | MIT | https://github.com/hukkin/mdformat |
| ftfy | Apache-2.0 | https://github.com/rspeer/python-ftfy |
| Pillow | MIT-CMU (HPND) | https://python-pillow.org |
| lxml | BSD-3-Clause | https://lxml.de |
| cryptography | Apache-2.0 / BSD | https://github.com/pyca/cryptography |
| AnyDoc (firecrawl-anydoc) | MIT | https://github.com/firecrawl/anydoc. O Markinho usa só a conversão local (funções nativas em Rust); o “OCR hospedado” do AnyDoc, que enviaria o arquivo à Firecrawl, nunca é chamado |
| Bibliotecas Rust do AnyDoc: pdf-inspector, cfb, csv, flate2, encoding_rs, quick-xml, zip, log | MIT / Apache-2.0 | crates.io |
| MCP Python SDK (mcp, mcp-types) | MIT | https://github.com/modelcontextprotocol/python-sdk |
| Dependências do MCP: pydantic, anyio, jsonschema, pyjwt, h11, attrs, truststore | MIT | PyPI |
| Dependências do MCP: starlette, sse-starlette, uvicorn, httpx2, httpcore2, click, idna | BSD-3-Clause | PyPI |
| Dependências do MCP: opentelemetry-api, python-multipart | Apache-2.0 | PyPI |

## Pandoc e OCR (todas as edições)

| Componente | Licença | Observação |
|---|---|---|
| **Pandoc** | **GPL-2.0 ou posterior** | Incluído como **programa separado** (executável próprio, chamado pelo Markinho), o que a GPL permite como “agregação”. Exigência: oferecer o código-fonte do Pandoc. Ele está em https://github.com/jgm/pandoc (a versão incluída aparece em *Motores*) |
| pypandoc | MIT | https://github.com/JessicaTegner/pypandoc |
| Tesseract OCR | Apache-2.0 | https://github.com/tesseract-ocr/tesseract (incluído no instalador do Windows) |
| Dados de idioma do Tesseract (tessdata_fast e tessdata_best) | Apache-2.0 | https://github.com/tesseract-ocr/tessdata_fast · https://github.com/tesseract-ocr/tessdata_best |
| pytesseract | Apache-2.0 | https://github.com/madmaze/pytesseract |

## Somente COMPLETA

| Componente | Licença | Observação |
|---|---|---|
| Docling, docling-core, docling-parse, docling-ibm-models | MIT | https://github.com/docling-project |
| Modelo de layout `docling-layout-heron` (e versão ONNX) | Apache-2.0 | https://huggingface.co/docling-project/docling-layout-heron |
| Modelos de tabela `docling-models` (TableFormer) | CDLA-Permissive-2.0 / Apache-2.0 | https://huggingface.co/docling-project/docling-models — texto da CDLA em `licenses/CDLA-Permissive-2.0.txt` |
| Modelo de código e fórmulas `CodeFormulaV2` | CDLA-Permissive-2.0 | https://huggingface.co/docling-project/CodeFormulaV2 |
| Classificador de figuras `DocumentFigureClassifier-v2.5` | MIT (base: EfficientNet-B0, Apache-2.0) | https://huggingface.co/docling-project/DocumentFigureClassifier-v2.5 |
| Modelos do RapidOCR (OCR reserva do Docling) | Apache-2.0 | https://github.com/RapidAI/RapidOCR |

Licenças conferidas na API do Hugging Face em 13/11/2026. Cada pasta de modelo inclui o README
(cartão do modelo) com a licença; a CDLA-Permissive-2.0 exige que o seu texto acompanhe os modelos
redistribuídos, o que é feito pelo arquivo em `licenses/`.
| PyTorch | BSD-3-Clause | https://github.com/pytorch/pytorch (versão para processador, sem bibliotecas da NVIDIA) |
| Transformers, Tokenizers, Safetensors, huggingface_hub | Apache-2.0 | https://github.com/huggingface |
| MarkItDown | MIT | https://github.com/microsoft/markitdown |
| Magika | Apache-2.0 | https://github.com/google/magika |
| RapidOCR (e modelos PaddleOCR) | Apache-2.0 | https://github.com/RapidAI/RapidOCR |
| ONNX Runtime | MIT | https://github.com/microsoft/onnxruntime |
| OpenCV | Apache-2.0 | https://opencv.org |
| NumPy, SciPy, pandas | BSD-3-Clause | https://numpy.org · https://scipy.org · https://pandas.pydata.org |

## Não incluídos (por causa da licença)

O Markinho sabe usar estes motores se o usuário os instalar por conta própria. Eles
**não** fazem parte de nenhuma edição, porque as licenças restringem o uso comercial:

| Componente | Motivo |
|---|---|
| Marker / Surya | Os pesos dos modelos têm licença própria, com restrições comerciais |
| PyMuPDF / PyMuPDF4LLM | AGPL-3.0: distribuir junto obrigaria a abrir o código do programa inteiro (ou comprar licença comercial da Artifex) |
