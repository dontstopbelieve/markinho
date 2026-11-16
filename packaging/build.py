"""Gera os pacotes de instalação do Markinho, por edição.

Uso:  python packaging/build.py [--edition leve|padrao|completa] <alvo> [<alvo> ...]

Edições (padrão: padrao):
  leve       motor nativo, correção, exportação DOCX/PDF/HTML/TXT
  padrao     leve + Pandoc + OCR (Tesseract: português e inglês)
  completa   padrao + Docling (IA de layout, modelos incluídos) + MarkItDown + RapidOCR

Alvos:
  app        pasta do programa (PyInstaller)            -> build/dist-<edição>/Markinho/
  onefile    executável único portátil (leve/padrão)    -> release/Markinho-<Edição>-<v>-<so>-<arq>-portatil(.exe)
  zip        pasta do programa compactada (portátil)    -> release/…-portatil.zip / .tar.gz / macOS .zip
  inno       instalador .exe para Windows (Inno Setup)  -> release/…-windows-x64-setup.exe
  msi        instalador .msi para Windows (WiX 4/5)     -> release/…-windows-x64.msi
  dmg        imagem de disco para macOS                 -> release/…-macos-<arq>.dmg
  deb        pacote Debian/Ubuntu                       -> release/markinho-<edição>_<v>_amd64.deb
  appimage   AppImage para qualquer Linux               -> release/…-x86_64.AppImage
  tessdata   baixa os idiomas do OCR da edição para packaging/vendor/tesseract/tessdata
  models     baixa os modelos do Docling (usado pela edição completa)
  wheel      pacote Python (pip/pipx; a edição é escolhida pelos extras)
  all        tudo o que dá para gerar neste sistema para a edição
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "packaging"
BUILD = ROOT / "build"
RELEASE = ROOT / "release"
sys.path.insert(0, str(ROOT))
from markinho import __version__ as VERSION  # noqa: E402

# O console do Windows (cp1252) não mostra "→" nem acentos: força UTF-8 na saída
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

OS = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
ARCH = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(platform.machine().lower(),
                                                                                   platform.machine().lower())
EDITION = "padrao"
EDITION_FILE = {"leve": "Leve", "padrao": "Padrao", "completa": "Completa"}     # nomes de arquivo sem acento
EDITION_TITLE = {"leve": "LEVE", "padrao": "PADRÃO", "completa": "COMPLETA"}
OCR_LANGS = {"leve": [], "padrao": ["por", "eng"], "completa": ["por", "eng"]}   # português (Brasil) e inglês
DEB_LANG = {"por": "por", "eng": "eng", "spa": "spa", "fra": "fra", "deu": "deu", "ita": "ita"}


def run(cmd: list, **kw) -> None:
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def dist() -> Path:
    return BUILD / f"dist-{EDITION}"


def app_dir() -> Path:
    return dist() / ("Markinho.app" if OS == "macos" else "Markinho")


def exe_dir() -> Path:
    """Pasta onde fica o executável (dentro do .app no macOS)."""
    return app_dir() / "Contents" / "MacOS" if OS == "macos" else app_dir()


def base_name() -> str:
    return f"Markinho-{EDITION_FILE[EDITION]}-{VERSION}-{OS}-{ARCH}"


def ensure_app() -> None:
    if not app_dir().exists():
        build_app()


# --------------------------------------------------------------------------- #
def collect_licenses() -> Path:
    """Copia LICENSE/COPYING/NOTICE de todas as bibliotecas da edição para o pacote
    (exigência das licenças MIT, BSD, Apache, LGPL…)."""
    from importlib.metadata import PackageNotFoundError, distribution

    from packaging.requirements import Requirement

    target = BUILD / f"licenses-{EDITION}" / "third_party"
    shutil.rmtree(target.parent, ignore_errors=True)
    target.mkdir(parents=True)
    roots = []
    for line in (ROOT / f"requirements-{EDITION}.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line.startswith("-r"):
            inner = (ROOT / line[2:].strip()).read_text(encoding="utf-8").splitlines()
            roots += [x.split("#")[0].strip() for x in inner if x.split("#")[0].strip() and not x.startswith("-r")]
        elif line:
            roots.append(line)
    seen: set[str] = set()

    def walk(name: str, extras=frozenset()):
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

    for spec in roots:
        r = Requirement(spec)
        walk(r.name, frozenset(r.extras))
    names = sorted({k for k, _ in seen})
    count = 0
    for name in names:
        try:
            dist = distribution(name)
        except PackageNotFoundError:
            continue
        for f in dist.files or []:
            low = Path(str(f)).name.lower()
            if any(k in low for k in ("licen", "copying", "notice", "copyright")) and not low.endswith((".py", ".pyc")):
                src = Path(f.locate())
                if src.is_file() and src.stat().st_size < 2_000_000:
                    dest = target / (dist.metadata.get("Name") or name) / src.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
                    count += 1
    # pacotes sem arquivo de licença na instalação: ficha com a licença declarada nos metadados
    for name in names:
        try:
            dist = distribution(name)
        except PackageNotFoundError:
            continue
        folder = target / (dist.metadata.get("Name") or name)
        if folder.exists():
            continue
        lic = dist.metadata.get("License-Expression") or (dist.metadata.get("License") or "").split("\n")[0]
        home = dist.metadata.get("Home-page") or next((u.split(",", 1)[-1].strip() for u in
                                                       dist.metadata.get_all("Project-URL") or []), "")
        folder.mkdir(parents=True)
        (folder / "LICENSE-INFO.txt").write_text(
            f"{dist.metadata.get('Name')} {dist.version}\nLicença: {lic or 'ver o projeto'}\nProjeto: {home}\n"
            "Os textos completos das licenças MIT, BSD-3-Clause, Apache-2.0, LGPL-3.0 e GPL-3.0 estão na "
            "pasta licenses/.\n", encoding="utf-8")
        count += 1
    # Pandoc (GPL): aviso e oferta do código-fonte da versão exata incluída
    if EDITION != "leve":
        try:
            sys.path.insert(0, str(ROOT))
            from markinho.engines import pandoc_version

            ver = pandoc_version() or "?"
        except Exception:  # noqa: BLE001
            ver = "?"
        (target / "Pandoc").mkdir(exist_ok=True)
        (target / "Pandoc" / "LEIA-ME.txt").write_text(
            f"O Markinho inclui o Pandoc {ver}, um programa separado de John MacFarlane e colaboradores,\n"
            "distribuído sem modificações sob a GNU General Public License, versão 2 ou posterior.\n\n"
            f"Código-fonte desta versão: https://github.com/jgm/pandoc/releases/tag/{ver}\n"
            "Texto da licença: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html\n", encoding="utf-8")
    if (PKG / "vendor" / "tesseract").is_dir():
        (target / "Tesseract").mkdir(exist_ok=True)
        (target / "Tesseract" / "LEIA-ME.txt").write_text(
            "O Markinho para Windows inclui o Tesseract OCR (Apache-2.0) e os dados de idioma tessdata_fast\n"
            "(Apache-2.0). Código-fonte: https://github.com/tesseract-ocr/tesseract\n", encoding="utf-8")
    print(f"licenças de terceiros: {count} arquivo(s) de {len(names)} pacote(s) -> {target}")
    return target


def build_app(onefile: bool = False) -> Path:
    collect_licenses()
    env = dict(os.environ, MARKINHO_VERSION=VERSION, MARKINHO_EDITION=EDITION)
    if onefile:
        env["MARKINHO_ONEFILE"] = "1"
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", dist(),
         "--workpath", BUILD / f"work-{EDITION}{'-onefile' if onefile else ''}", PKG / "markinho.spec"], env=env)
    if onefile:
        out = dist() / ("Markinho.exe" if OS == "windows" else "Markinho")
    else:
        out = app_dir()
        if EDITION == "completa":
            embed_models()
    print("→", out)
    return out


def build_models() -> Path:
    """Baixa os modelos do Docling para build/models/docling (precisa de internet)."""
    target = BUILD / "models" / "docling"
    if target.is_dir() and any(target.iterdir()):
        return target
    target.mkdir(parents=True, exist_ok=True)
    print(f"Baixando modelos do Docling para {target} …", flush=True)
    from docling.utils.model_downloader import download_models

    try:
        download_models(output_dir=target, progress=False)
    except TypeError:
        download_models(output_dir=target)
    return target


def embed_models() -> None:
    """COMPLETA: coloca os modelos ao lado do executável, para funcionar sem internet."""
    if os.environ.get("MARKINHO_SKIP_MODELS") == "1":       # só para testes locais sem internet
        print("aviso: modelos do Docling NÃO embutidos (MARKINHO_SKIP_MODELS=1)")
        return
    src = build_models()
    dest = exe_dir() / "models" / "docling"
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)
    size = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file()) / 1e6
    print(f"modelos do Docling embutidos ({size:.0f} MB) em {dest}")


def build_onefile() -> Path:
    if EDITION == "completa":
        raise SystemExit("A edição COMPLETA é grande demais para um executável único; use zip/inno/msi.")
    exe = build_app(onefile=True)
    RELEASE.mkdir(exist_ok=True)
    target = RELEASE / f"{base_name()}-portatil{'.exe' if OS == 'windows' else ''}"
    shutil.copy2(exe, target)
    print("→", target)
    return target


def build_zip() -> Path:
    ensure_app()
    src = app_dir()
    RELEASE.mkdir(exist_ok=True)
    folder = f"Markinho-{EDITION_FILE[EDITION]}-{VERSION}"
    if OS == "linux":
        target = RELEASE / f"{base_name()}.tar.gz"
        with tarfile.open(target, "w:gz") as tar:
            tar.add(src, arcname=folder)
    elif OS == "macos":
        target = RELEASE / f"{base_name()}.zip"
        run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", src, target])   # preserva o .app
    else:
        target = RELEASE / f"{base_name()}-portatil.zip"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as z:
            for f in src.rglob("*"):
                z.write(f, Path(folder) / f.relative_to(src))
    print("→", target)
    return target


# --------------------------------------------------------------------------- #
# OCR: idiomas do Tesseract
# --------------------------------------------------------------------------- #
def build_tessdata() -> Path:
    """Baixa os idiomas da edição (tessdata_fast, Apache-2.0) para o Tesseract embutido."""
    tessdata = PKG / "vendor" / "tesseract" / "tessdata"
    tessdata.mkdir(parents=True, exist_ok=True)
    for lang in OCR_LANGS[EDITION]:
        dest = tessdata / f"{lang}.traineddata"
        if dest.exists():
            continue
        url = f"https://github.com/tesseract-ocr/tessdata_fast/raw/main/{lang}.traineddata"
        print("baixando", url, flush=True)
        urllib.request.urlretrieve(url, dest)
    # remove idiomas que não pertencem à edição (mantém osd, usado para detectar orientação)
    keep = set(OCR_LANGS[EDITION]) | {"osd"}
    for f in tessdata.glob("*.traineddata"):
        if f.stem not in keep:
            f.unlink()
    print("idiomas do OCR:", sorted(f.stem for f in tessdata.glob("*.traineddata")))
    # modelos "best" (mais precisos, usados no modo Máxima qualidade), também Apache-2.0
    best = tessdata.parent / "tessdata_best"
    best.mkdir(exist_ok=True)
    for lang in OCR_LANGS[EDITION]:
        dest = best / f"{lang}.traineddata"
        if not dest.exists():
            url = f"https://github.com/tesseract-ocr/tessdata_best/raw/main/{lang}.traineddata"
            print("baixando", url, flush=True)
            urllib.request.urlretrieve(url, dest)
    print("modelos best:", sorted(f.stem for f in best.glob("*.traineddata")))
    return tessdata


# --------------------------------------------------------------------------- #
# Windows
# --------------------------------------------------------------------------- #
def _find_iscc() -> str:
    for c in [shutil.which("iscc"), r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
              r"C:\Program Files\Inno Setup 6\ISCC.exe"]:
        if c and Path(c).exists():
            return c
    raise SystemExit("Inno Setup não encontrado. Instale com: choco install innosetup  (ou winget install JRSoftware.InnoSetup)")


def build_inno() -> Path:
    ensure_app()
    RELEASE.mkdir(exist_ok=True)
    out_name = f"{base_name()}-setup"
    run([_find_iscc(), f"/DAppVersion={VERSION}", f"/DEdition={EDITION_TITLE[EDITION]}", f"/DSourceDir={app_dir()}",
         f"/DOutputDir={RELEASE}", f"/DOutputName={out_name}", f"/DIconFile={PKG / 'icons' / 'markinho.ico'}",
         PKG / "windows" / "markinho.iss"])
    target = RELEASE / f"{out_name}.exe"
    print("→", target)
    return target


def build_msi() -> Path:
    ensure_app()
    RELEASE.mkdir(exist_ok=True)
    wxs = BUILD / f"Markinho-{EDITION}.wxs"
    sys.path.insert(0, str(PKG / "windows"))
    from make_wxs import write_wxs

    write_wxs(app_dir(), wxs, VERSION, PKG / "icons" / "markinho.ico", PKG / "windows" / "termos.rtf",
              EDITION_TITLE[EDITION])
    wix = shutil.which("wix") or str(Path.home() / ".dotnet" / "tools" / "wix.exe")
    target = RELEASE / f"{base_name()}.msi"
    run([wix, "build", "-arch", "x64", "-culture", "pt-BR", "-ext", "WixToolset.UI.wixext", "-o", target, wxs])
    print("→", target)
    return target


# --------------------------------------------------------------------------- #
# macOS
# --------------------------------------------------------------------------- #
def build_dmg() -> Path:
    ensure_app()
    RELEASE.mkdir(exist_ok=True)
    stage = BUILD / f"dmg-{EDITION}"
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True)
    run(["ditto", app_dir(), stage / "Markinho.app"])
    (stage / "Applications").symlink_to("/Applications")    # arraste o app para cá
    target = RELEASE / f"{base_name()}.dmg"
    target.unlink(missing_ok=True)
    run(["hdiutil", "create", "-volname", f"Markinho {EDITION_TITLE[EDITION]} {VERSION}", "-srcfolder", stage,
         "-ov", "-format", "UDZO", target])
    print("→", target)
    return target


# --------------------------------------------------------------------------- #
# Linux
# --------------------------------------------------------------------------- #
DESKTOP = """[Desktop Entry]
Type=Application
Name=Markinho
GenericName=Conversor Markdown
Comment=Converte documentos para Markdown e Markdown para outros formatos
Exec={exec} %F
Icon=markinho
Terminal=false
Categories=Office;Utility;TextTools;
MimeType=application/pdf;application/vnd.openxmlformats-officedocument.wordprocessingml.document;application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;application/vnd.openxmlformats-officedocument.presentationml.presentation;text/html;text/markdown;image/png;image/jpeg;
Keywords=markdown;pdf;docx;ocr;converter;
"""


def build_deb() -> Path:
    ensure_app()
    RELEASE.mkdir(exist_ok=True)
    arch = "amd64" if ARCH == "x64" else ARCH
    pkg = f"markinho-{EDITION}"
    root = BUILD / f"deb-{EDITION}" / f"{pkg}_{VERSION}_{arch}"
    shutil.rmtree(root.parent, ignore_errors=True)
    (root / "DEBIAN").mkdir(parents=True)
    shutil.copytree(app_dir(), root / "opt" / "markinho", symlinks=True)
    (root / "usr" / "bin").mkdir(parents=True)
    (root / "usr" / "bin" / "markinho").symlink_to("/opt/markinho/markinho-cli")
    (root / "usr" / "bin" / "markinho-gui").symlink_to("/opt/markinho/Markinho")
    apps = root / "usr" / "share" / "applications"
    apps.mkdir(parents=True)
    (apps / "markinho.desktop").write_text(DESKTOP.format(exec="/opt/markinho/Markinho"), encoding="utf-8")
    icons = root / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
    icons.mkdir(parents=True)
    shutil.copy2(PKG / "icons" / "markinho.png", icons / "markinho.png")
    size_kb = sum(f.stat().st_size for f in root.rglob("*") if f.is_file() and not f.is_symlink()) // 1024
    depends = "libegl1, libgl1, libxkbcommon0, libfontconfig1, libdbus-1-3, libxcb-cursor0"
    recommends = ""
    langs = OCR_LANGS[EDITION]
    if langs:   # OCR do sistema (Tesseract), com os idiomas da edição
        depends += ", tesseract-ocr, tesseract-ocr-por"
        recommends = "Recommends: " + ", ".join(f"tesseract-ocr-{DEB_LANG[x]}" for x in langs if x != "por") + "\n"
    others = [f"markinho-{e}" for e in ("leve", "padrao", "completa") if e != EDITION]
    (root / "DEBIAN" / "control").write_text(f"""Package: {pkg}
Version: {VERSION}
Section: text
Priority: optional
Architecture: {arch}
Installed-Size: {size_kb}
Depends: {depends}
{recommends}Provides: markinho
Conflicts: {", ".join(others)}
Replaces: {", ".join(others)}
Maintainer: dontstopbelieve <dontstopbelieve@users.noreply.github.com>
Homepage: https://github.com/dontstopbelieve/markinho
Description: Markinho {EDITION_TITLE[EDITION]} - Conversor Markdown
 Interface gráfica e linha de comando. PDF, DOCX, XLSX, PPTX, HTML, EPUB, imagens
 e mais, com correção de caracteres, extração de imagens e exportação.
""", encoding="utf-8")
    for d in root.rglob("*"):
        if d.is_dir():
            d.chmod(0o755)
    target = RELEASE / f"{pkg}_{VERSION}_{arch}.deb"
    run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", root, target])
    print("→", target)
    return target


def build_appimage() -> Path:
    ensure_app()
    RELEASE.mkdir(exist_ok=True)
    appdir = BUILD / f"Markinho-{EDITION}.AppDir"
    shutil.rmtree(appdir, ignore_errors=True)
    shutil.copytree(app_dir(), appdir / "usr" / "lib" / "markinho", symlinks=True)
    (appdir / "AppRun").write_text('#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\n'
                                   'case "$1" in -*) exec "$HERE/usr/lib/markinho/markinho-cli" "$@";; esac\n'
                                   'if [ -n "$MARKINHO_CLI" ]; then exec "$HERE/usr/lib/markinho/markinho-cli" "$@"; fi\n'
                                   'exec "$HERE/usr/lib/markinho/Markinho" "$@"\n', encoding="utf-8")
    (appdir / "AppRun").chmod(0o755)
    (appdir / "markinho.desktop").write_text(DESKTOP.format(exec="Markinho"), encoding="utf-8")
    shutil.copy2(PKG / "icons" / "markinho.png", appdir / "markinho.png")
    tool = shutil.which("appimagetool") or str(BUILD / "appimagetool")
    if not Path(tool).exists():
        raise SystemExit("appimagetool não encontrado (o CI baixa automaticamente; veja .github/workflows/release.yml)")
    machine = "x86_64" if ARCH == "x64" else ARCH
    target = RELEASE / f"Markinho-{EDITION_FILE[EDITION]}-{VERSION}-{machine}.AppImage"
    run([tool, "--no-appstream", appdir, target], env=dict(os.environ, ARCH=machine))
    print("→", target)
    return target


# --------------------------------------------------------------------------- #
def build_wheel() -> list[Path]:
    RELEASE.mkdir(exist_ok=True)
    run([sys.executable, "-m", "build", "--outdir", RELEASE, ROOT])
    return list(RELEASE.glob(f"markinho-{VERSION}*"))


TARGETS = {
    "app": build_app, "onefile": build_onefile, "zip": build_zip, "inno": build_inno, "msi": build_msi,
    "dmg": build_dmg, "deb": build_deb, "appimage": build_appimage, "wheel": build_wheel,
    "tessdata": build_tessdata, "models": build_models,
}


def all_targets() -> list[str]:
    base = {"windows": ["app", "zip", "inno", "msi"], "macos": ["app", "zip", "dmg"],
            "linux": ["app", "zip", "deb", "appimage"]}[OS]
    if OS == "windows" and EDITION != "completa":
        base.append("onefile")
    return base


def main(argv: list[str]) -> int:
    global EDITION
    if argv[:1] in (["-h"], ["--help"]) or not argv:
        print(__doc__)
        return 0
    if argv[0] == "--edition":
        if len(argv) < 2 or argv[1] not in EDITION_FILE:
            print("edição inválida. Use: leve, padrao ou completa")
            return 2
        EDITION, argv = argv[1], argv[2:]
    targets = all_targets() if argv == ["all"] else argv
    print(f"== Markinho {VERSION} — edição {EDITION_TITLE[EDITION]} — {OS}/{ARCH}: {', '.join(targets)}")
    for t in targets:
        if t not in TARGETS:
            print(f"alvo desconhecido: {t}\n{__doc__}")
            return 2
        TARGETS[t]()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
