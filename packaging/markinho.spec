# -*- mode: python ; coding: utf-8 -*-
# Receita do PyInstaller. Gere com:  python packaging/build.py --edition padrao app
#   MARKINHO_EDITION = leve | padrao | completa   (padrão: padrao)
#   MARKINHO_ONEFILE = 1  -> um único executável portátil (só a interface)
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

ROOT = Path(SPECPATH).parent
EDITION = os.environ.get("MARKINHO_EDITION", "padrao")
ONEFILE = os.environ.get("MARKINHO_ONEFILE") == "1"
ICON = str(ROOT / "packaging" / "icons" / ("markinho.ico" if sys.platform == "win32" else "markinho.icns"))
assert EDITION in ("leve", "padrao", "completa"), EDITION

# marca da edição dentro do pacote (lida por markinho/edition.py)
marker_dir = ROOT / "build" / f"edition-{EDITION}"
marker_dir.mkdir(parents=True, exist_ok=True)
(marker_dir / "edition.txt").write_text(EDITION, encoding="utf-8")

datas = [(str(ROOT / "markinho" / "resources"), "markinho/resources"),
         (str(ROOT / "markinho" / "locale"), "markinho/locale"),
         (str(marker_dir / "edition.txt"), "markinho/resources"),
         (str(ROOT / "THIRD_PARTY_LICENSES.md"), "."),
         (str(ROOT / "THIRD_PARTY_LICENSES.md"), "licenses"),
         (str(ROOT / "PRIVACIDADE.md"), "."),
         (str(ROOT / "LICENSE"), "."),                       # licença do próprio Markinho (AGPL-3.0)
         (str(ROOT / "LICENSE"), "licenses/Markinho"),
         (str(ROOT / "licenses"), "licenses")]
_collected = ROOT / "build" / f"licenses-{EDITION}" / "third_party"   # gerado por build.py (collect_licenses)
if _collected.is_dir():
    datas.append((str(_collected), "licenses/third_party"))
binaries = []
hidden = (collect_submodules("markinho") + collect_submodules("mdformat") + collect_submodules("mdformat_gfm")
          + ["anydoc", "anydoc._anydoc", "markdown.extensions.extra", "markdown.extensions.toc", "markdown.extensions.sane_lists"])
datas += collect_data_files("mdformat_gfm") + collect_data_files("docx") + collect_data_files("pptx")
# servidor MCP local (todas as edições): SDK oficial e os tipos do protocolo
for _pkg in ("mcp", "mcp_types"):
    try:
        # mcp.cli exige "typer" (comando "mcp" de desenvolvimento): não é usado pelo Markinho
        _d, _b, _h = collect_all(_pkg, filter_submodules=lambda n: not n.startswith("mcp.cli"))
        datas += _d
        binaries += _b
        hidden += _h
    except Exception as _exc:  # noqa: BLE001
        print(f"aviso: não foi possível coletar {_pkg}: {_exc}")
# python-docx/python-pptx montam caminhos como "docx/parts/../templates/x.xml": a pasta intermediária
# precisa existir no disco, senão o arquivo "não existe" (ex.: DOCX com cabeçalho)
for sub in ("docx/parts", "docx/oxml", "pptx/parts", "pptx/opc", "pptx/oxml"):
    datas.append((str(ROOT / "packaging" / "pyinstaller" / "keep.txt"), sub))

# Nunca incluídos (licenças que impedem a venda sem custo/abrir o código, ou inúteis aqui)
excludes = ["marker", "surya", "pymupdf", "fitz", "pymupdf4llm", "tkinter", "IPython", "jupyter", "notebook",
            "pytest", "matplotlib", "mcp.cli", "typer",
            "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQml", "PySide6.QtQuick",
            # (QtPdf/QtPdfWidgets ficam: são o visualizador de PDF do "Comparar com o original")
            "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtCharts", "PySide6.QtDataVisualization"]
AI_STACK = ["torch", "torchvision", "transformers", "docling", "docling_core", "docling_ibm_models", "docling_parse",
            "easyocr", "scipy", "pandas", "markitdown", "magika", "rapidocr_onnxruntime", "rapidocr", "onnxruntime",
            "cv2", "shapely", "pyclipper", "cuda", "accelerate", "safetensors", "tokenizers", "huggingface_hub"]

if EDITION == "leve":
    excludes += AI_STACK + ["pypandoc", "pytesseract", "numpy"]
else:
    datas += collect_data_files("pypandoc")          # executável do Pandoc (pypandoc_binary)
    hidden += ["pypandoc", "pytesseract"]
    tess = ROOT / "packaging" / "vendor" / "tesseract"   # Tesseract embutido (o CI do Windows coloca aqui)
    if tess.is_dir():
        datas.append((str(tess), "tesseract"))
    if EDITION == "padrao":
        excludes += AI_STACK + ["numpy"]
    else:  # completa: IA de layout e motores extras
        for pkg in ("docling", "docling_core", "docling_parse", "docling_ibm_models", "markitdown", "magika",
                    "rapidocr_onnxruntime", "rapidocr", "transformers", "tokenizers", "safetensors", "huggingface_hub"):
            try:
                d, b, h = collect_all(pkg)
            except Exception as exc:  # noqa: BLE001
                print(f"aviso: não foi possível coletar {pkg}: {exc}")
                continue
            datas += d
            binaries += b
            hidden += h
        # Toda a árvore de dependências: arquivos de dados (ex.: tabelas do latex2mathml) e
        # metadados (várias bibliotecas conferem a versão das outras ao iniciar).
        from importlib.metadata import PackageNotFoundError, distribution, packages_distributions

        from packaging.requirements import Requirement
        from PyInstaller.utils.hooks import copy_metadata

        top_of = {}
        for top, dists in packages_distributions().items():
            for dname in dists:
                top_of.setdefault(dname.lower().replace("_", "-"), []).append(top)
        seen = set()

        def walk(name, extras=frozenset()):
            # segue também os "extras" (ex.: docling -> docling-slim[feat-ocr-rapidocr-onnx])
            key = (name.lower().replace("_", "-"), extras)
            if key in seen:
                return
            seen.add(key)
            try:
                dist = distribution(name)
            except PackageNotFoundError:
                return
            for req in dist.requires or []:
                r = Requirement(req)
                envs = [{"extra": ""}] + [{"extra": e} for e in extras]
                if r.marker is None or any(r.marker.evaluate(env) for env in envs):
                    walk(r.name, frozenset(r.extras))

        for root in ("docling", "markitdown", "rapidocr-onnxruntime"):
            walk(root)
        seen = {k for k, _ in seen}
        skip = {"torch", "nvidia", "triton", "PySide6", "shiboken6"}
        for dname in sorted(seen):
            try:
                datas += copy_metadata(dname)
            except Exception:  # noqa: BLE001
                pass
            for top in top_of.get(dname, []):
                if top in skip or top.startswith("_"):
                    continue
                try:
                    datas += collect_data_files(top)
                except Exception:  # noqa: BLE001
                    pass
        # bibliotecas da NVIDIA (GPU) ficam de fora: o instalador usa o PyTorch para processador.
        # MARKINHO_KEEP_GPU=1 mantém (só para testar localmente com um PyTorch de GPU instalado).
        if os.environ.get("MARKINHO_KEEP_GPU") != "1":
            excludes += ["nvidia", "triton"]


# Partes do Qt que o Markinho não usa, mas que entram por dependência de plugins (~20 MB)
import re  # noqa: E402

QT_UNUSED = re.compile(r"Qt6?(Quick|Qml|VirtualKeyboard|3D|Multimedia|ShaderTools|WebEngine|Charts)"
                       r"|virtualkeyboard|qtquick|qml", re.I)


def analysis(script):
    a = Analysis([str(ROOT / "packaging" / script)], pathex=[str(ROOT)], datas=datas, binaries=binaries,
                 hiddenimports=hidden, excludes=excludes, noarchive=False)
    a.binaries = [b for b in a.binaries if not QT_UNUSED.search(Path(b[0]).name)]
    a.datas = [d for d in a.datas if not (d[0].startswith("PySide6") and QT_UNUSED.search(d[0]))]
    return a


a_gui = analysis("entry_gui.py")
pyz_gui = PYZ(a_gui.pure)

if ONEFILE:
    exe = EXE(pyz_gui, a_gui.scripts, a_gui.binaries, a_gui.datas, [], name="Markinho", console=False,
              icon=ICON, upx=False, runtime_tmpdir=None)
else:
    exe_gui = EXE(pyz_gui, a_gui.scripts, [], exclude_binaries=True, name="Markinho", console=False,
                  icon=ICON, upx=False)
    a_cli = analysis("entry_cli.py")
    pyz_cli = PYZ(a_cli.pure)
    exe_cli = EXE(pyz_cli, a_cli.scripts, [], exclude_binaries=True, name="markinho-cli", console=True,
                  icon=ICON, upx=False)
    coll = COLLECT(exe_gui, a_gui.binaries, a_gui.datas, exe_cli, a_cli.binaries, a_cli.datas,
                   name="Markinho", upx=False)
    if sys.platform == "darwin":
        app = BUNDLE(coll, name="Markinho.app", icon=ICON, bundle_identifier="io.github.dontstopbelieve.markinho",
                     info_plist={"CFBundleShortVersionString": os.environ.get("MARKINHO_VERSION", "3.0.0"),
                                 "NSHighResolutionCapable": True,
                                 "CFBundleDocumentTypes": [{"CFBundleTypeName": "Documento",
                                                            "CFBundleTypeRole": "Viewer",
                                                            "LSItemContentTypes": ["public.data"]}]})
