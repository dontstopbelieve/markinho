# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Pacotes extras: recursos opcionais que a pessoa instala uma vez e ficam no computador.

* **Fórmulas e código** (COMPLETA, ~640 MB): modelo do Docling que poucas pessoas usam; fica fora do
  instalador para ele caber no limite de 2 GB por arquivo do GitHub.
* **Idiomas extras do OCR** (as duas edições, ~90 MB): espanhol, francês, alemão, russo, chinês e árabe
  para o Tesseract (versões rápida e precisa).

São publicados como ``Markinho-Pacote-<Nome>-<versão>.zip`` nas Releases. A pessoa escolhe:

* no instalador do Windows (marca a caixinha: ele baixa ou usa o .zip que estiver ao lado), ou
* depois, em Ferramentas › Pacotes extras › Instalar de um arquivo… (ou ``--instalar-pacote arquivo.zip``).

**O Markinho em si nunca baixa nada**: quem baixa é o navegador ou o instalador, antes de haver
documentos. Aqui só se confere e se descompacta um arquivo que já está no computador.

Os arquivos vão para a pasta de modelos do usuário. Docling e Tesseract só aceitam uma pasta: ela é
completada com atalhos para o que vem com o programa (ou com o sistema), sem copiar.

Segurança: o .zip traz ``markinho-pacote.json`` com o SHA-256 e o tamanho de cada arquivo; nada fora da
lista é aceito, os nomes não podem sair das partes do pacote e cada arquivo é conferido enquanto é copiado.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable

from .i18n import tr

MANIFEST = "markinho-pacote.json"
FORMAT = 1
RELEASES = "https://github.com/dontstopbelieve/markinho/releases"
# Os pacotes têm página própria nas Releases, separada das versões do programa: são publicados uma vez
# (workflow "Pacotes extras") e servem a várias versões do Markinho. Mudou o conteúdo → aumente o número.
PACKS_VERSION = "1"
PACKS_TAG = f"pacotes-{PACKS_VERSION}"
PACKS_PAGE = f"{RELEASES}/tag/{PACKS_TAG}"
PACKS_SUMS_URL = f"{RELEASES}/download/{PACKS_TAG}/SHA256SUMS.txt"
MAX_TOTAL = 6 * 1024 ** 3          # nenhum pacote passa de 6 GB descompactado
MAX_FILES = 2000


_TEXTS = {
    "formulas": lambda: dict(
        name=tr("Fórmulas e código"),
        what=tr("Converte equações em texto editável (LaTeX) e reconhece trechos de código de programação. Usado "
                "pelo motor Docling (IA de layout) quando as opções “Reconhecer fórmulas” ou “Reconhecer código” "
                "estão ligadas."),
        who=tr("Vale a pena para: artigos científicos, teses, apostilas de matemática, física, química e "
               "engenharia, documentação técnica."),
        skip=tr("Dispensável para: contratos, processos, relatórios, planilhas, documentos de escritório em geral. "
                "Sem ele, as fórmulas saem como texto simples ou imagem; o resto do documento não muda."),
        need=tr("Precisa da edição COMPLETA (motor Docling)."),
    ),
    "idiomas": lambda: dict(
        name=tr("Idiomas extras do OCR"),
        what=tr("Permite ler documentos escaneados, fotos e prints em espanhol (spa), francês (fra), alemão (deu), "
                "russo (rus), chinês simplificado (chi_sim; em colunas verticais: chi_sim_vert) e árabe (ara). "
                "Traz as versões rápida e precisa (modo Máxima qualidade). Depois de instalar, o Markinho reconhece "
                "sozinho o idioma da página; para fixar um, use Configurações › Idiomas do OCR (ex.: por+spa)."),
        who=tr("Vale a pena para: quem recebe documentos escaneados ou fotografados nesses idiomas (contratos "
               "internacionais, imigração, traduções, pesquisa)."),
        skip=tr("Dispensável para: documentos digitais (PDF com texto, Word, Excel…) em qualquer idioma, que não "
                "usam OCR, e para escaneados só em português ou inglês, que já vêm no Markinho."),
        need=tr("Precisa do Tesseract (OCR), que já vem no Markinho para Windows. No Mac e no Linux, instale o "
                "Tesseract do sistema (brew install tesseract ou apt install tesseract-ocr)."),
    ),
}


@dataclass(frozen=True)
class Pack:
    id: str
    file_title: str                  # parte do nome do arquivo: Markinho-Pacote-<file_title>-<versão>.zip
    units: tuple[str, ...]           # o que o pacote instala, relativo à pasta de modelos (pasta ou arquivo)
    size_mb: int
    requires: str                    # "docling" ou "tesseract"
    editions: tuple[str, ...]        # edições cujo instalador do Windows oferece o pacote

    def _t(self, key: str) -> str:
        return _TEXTS[self.id]()[key]

    name = property(lambda self: self._t("name"))
    what = property(lambda self: self._t("what"))
    who = property(lambda self: self._t("who"))
    skip = property(lambda self: self._t("skip"))
    need = property(lambda self: self._t("need"))

    def file_name(self, version: str = PACKS_VERSION) -> str:
        return f"Markinho-Pacote-{self.file_title}-{version}.zip"

    def url(self, version: str = PACKS_VERSION) -> str:
        return f"{RELEASES}/download/pacotes-{version}/{self.file_name(version)}"


OCR_LANGS = ("spa", "fra", "deu", "rus", "chi_sim", "chi_sim_vert", "ara")
PACKS: tuple[Pack, ...] = (
    Pack("formulas", "Formulas", ("docling/docling-project--CodeFormulaV2",), 640, "docling", ("completa",)),
    Pack("idiomas", "Idiomas-OCR",
         tuple(f"{d}/{x}.traineddata" for d in ("tessdata", "tessdata_best") for x in OCR_LANGS),
         95, "tesseract", ("padrao", "completa")),
)
PACKS_BY_ID = {p.id: p for p in PACKS}


class PackError(Exception):
    """Pacote inválido, corrompido ou que não pode ser instalado (mensagem já traduzida)."""


# ---------------------------------------------------------------- onde ficam os modelos
def models_root() -> Path:
    from .models import models_dir

    return models_dir()


def _bundled() -> Path | None:
    from .models import bundled_models_dir

    b = bundled_models_dir()
    p = b / "docling" if b is not None else None
    return p if p is not None and p.is_dir() else None


def user_docling_dir() -> Path:
    return models_root() / "docling"


def _has(folder: Path) -> bool:
    return folder.is_dir() and any(folder.iterdir())


def _is_link(p: Path) -> bool:
    try:
        return p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
    except OSError:
        return False


def _real(p: Path) -> bool:
    """Existe de verdade na pasta do usuário (não é atalho para o que vem com o programa)."""
    return p.exists() and not _is_link(p)


def _present_elsewhere(unit: str) -> bool:
    area, _, rest = unit.partition("/")
    if area == "docling":
        b = _bundled()
        return b is not None and _has(b / rest)
    try:
        from . import ocr

        if area == "tessdata":
            return Path(rest).stem in ocr.base_languages()
        if area == "tessdata_best":
            best = ocr.bundled_best_dir()
            return best is not None and (best / rest).is_file()
    except Exception:  # noqa: BLE001
        return False
    return False


def installed(pack: Pack) -> bool:
    root = models_root()
    return all((root / u).exists() or _present_elsewhere(u) for u in pack.units)


def removable(pack: Pack) -> bool:
    root = models_root()
    return any(_real(root / u) for u in pack.units)


def docling_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("docling") is not None


def tesseract_available() -> bool:
    from . import ocr

    return ocr.tesseract_cmd() is not None


def available(pack: Pack) -> bool:
    return docling_available() if pack.requires == "docling" else tesseract_available()


def _link(target: Path, link: Path) -> None:
    """Mostra algo que vem com o programa dentro da pasta do usuário, sem copiar quando possível."""
    is_dir = target.is_dir()
    try:
        os.symlink(target, link, target_is_directory=is_dir)
        return
    except (OSError, NotImplementedError):
        pass
    if is_dir and sys.platform == "win32":
        try:
            import _winapi

            _winapi.CreateJunction(str(target), str(link))     # não precisa de administrador
            return
        except (OSError, ImportError, AttributeError):
            pass
    if not is_dir:
        try:
            os.link(target, link)                              # mesmo disco: não ocupa espaço
            return
        except OSError:
            pass
        shutil.copy2(target, link)
        return
    shutil.copytree(target, link)                              # último recurso: copia


def merge_into(user: Path, base: Path) -> bool:
    """Completa a pasta do usuário com atalhos para o que está em `base` e falta nela.

    Docling e Tesseract só aceitam uma pasta de modelos: assim o pacote e o que vem com o programa (ou do
    sistema) aparecem juntos. Atalhos quebrados (programa reinstalado em outro lugar) são refeitos."""
    try:
        if base.resolve() == user.resolve():
            return True
        for item in base.iterdir():
            dest = user / item.name
            if _is_link(dest) and not dest.exists():
                try:
                    dest.unlink()
                except OSError:
                    os.rmdir(dest)
            if not dest.exists() and not dest.is_symlink():
                _link(item, dest)
    except OSError:
        return False
    return True


def merged_docling_dir() -> Path | None:
    """Pasta única de modelos para o Docling: a do programa ou, com pacote extra, a do usuário (juntada)."""
    bundled, user = _bundled(), user_docling_dir()
    if not _has(user):
        return bundled
    if bundled is None:
        return user
    return user if merge_into(user, bundled) else bundled


def merged_tessdata(base: Path | None, sub: str = "tessdata") -> Path | None:
    """Pasta de idiomas do Tesseract com o pacote extra junto; None se o pacote não estiver instalado."""
    user = models_root() / sub
    if not (user.is_dir() and any(_real(f) for f in user.glob("*.traineddata"))):
        return None
    if base is not None and base.is_dir() and not merge_into(user, base):
        return None
    return user


def _refresh_ocr() -> None:
    try:
        from . import ocr

        ocr.refresh()
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------- criar (usado pelo build)
def build_pack(pack: Pack, models: Path, out_dir: Path, version: str = PACKS_VERSION) -> Path:
    """Gera o .zip do pacote a partir de uma pasta de modelos (com docling/, tessdata/…). Sempre igual."""
    files: dict[str, dict] = {}
    entries: list[tuple[str, Path]] = []
    for unit in pack.units:
        src = models / unit
        if src.is_file():
            found = [src]
        elif _has(src):
            found = sorted(p for p in src.rglob("*") if p.is_file())
        else:
            raise PackError(tr("modelo não encontrado: {0}").format(src))
        for f in found:
            arc = f.relative_to(models).as_posix()
            files[arc] = {"sha256": _sha256(f), "tamanho": f.stat().st_size}
            entries.append((arc, f))
    manifest = {"formato": FORMAT, "pacote": pack.id, "versao": version, "arquivos": files}
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / pack.file_name(version)
    tmp = target.with_name(".~" + target.name)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:   # modelos não comprimem
        def add(name: str) -> zipfile.ZipInfo:
            zi = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            zi.external_attr = 0o644 << 16
            return zi
        zf.writestr(add(MANIFEST), json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False))
        for arc, f in entries:
            with f.open("rb") as src_fh, zf.open(add(arc), "w", force_zip64=True) as dst:
                shutil.copyfileobj(src_fh, dst, 1024 * 1024)
    os.replace(tmp, target)
    return target


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- conferir e instalar
def _unit_of(name: str, pack: Pack) -> str | None:
    """A qual parte do pacote o arquivo pertence (None = nome não permitido)."""
    if "\\" in name or ":" in name or name.startswith("/"):
        return None
    parts = PurePosixPath(name).parts
    if any(p in ("", ".", "..") for p in parts):
        return None
    for unit in pack.units:
        if name == unit or name.startswith(unit + "/"):
            return unit
    return None


def read_manifest(zf: zipfile.ZipFile) -> tuple[Pack, dict]:
    from .safety import read_zip_member

    try:
        data = json.loads(read_zip_member(zf, MANIFEST, 4 * 1024 * 1024).decode("utf-8"))
    except KeyError as exc:
        raise PackError(tr("este arquivo não é um pacote extra do Markinho")) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise PackError(tr("a lista de conteúdo do pacote está danificada")) from exc
    if not isinstance(data, dict) or data.get("formato") != FORMAT:
        raise PackError(tr("pacote de um formato que esta versão do Markinho não conhece; atualize o Markinho"))
    pack = PACKS_BY_ID.get(str(data.get("pacote")))
    if pack is None:
        raise PackError(tr("pacote desconhecido: {0}").format(data.get("pacote")))
    files = data.get("arquivos")
    if not isinstance(files, dict) or not files or len(files) > MAX_FILES:
        raise PackError(tr("a lista de conteúdo do pacote está danificada"))
    total = 0
    for name, info in files.items():
        if _unit_of(name, pack) is None or not isinstance(info, dict):
            raise PackError(tr("o pacote tem um nome de arquivo não permitido: {0}").format(name))
        size, sha = info.get("tamanho"), info.get("sha256")
        if not isinstance(size, int) or size < 0 or not isinstance(sha, str) or len(sha) != 64:
            raise PackError(tr("a lista de conteúdo do pacote está danificada"))
        total += size
    if total > MAX_TOTAL:
        raise PackError(tr("o pacote é grande demais"))
    return pack, data


def install_from_zip(path: Path | str, progress: Callable[[int, int], None] | None = None,
                     check_version: str | None = None) -> Pack:
    """Confere e instala um pacote .zip na pasta de modelos do usuário. Devolve o pacote instalado."""
    path = Path(path)
    try:
        zf = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise PackError(tr("não foi possível abrir o arquivo: {0}").format(exc)) from exc
    with zf:
        pack, data = read_manifest(zf)
        if not available(pack):
            raise PackError(pack.need)
        if check_version and data.get("versao") != check_version:
            raise PackError(tr("pacote da versão {0}; esta é a {1}").format(data.get("versao"), check_version))
        files = data["arquivos"]
        names = {i.filename for i in zf.infolist() if not i.is_dir()}
        if names - set(files) - {MANIFEST}:
            raise PackError(tr("o pacote tem arquivos fora da lista de conteúdo"))
        if set(files) - names:
            raise PackError(tr("faltam arquivos no pacote (download incompleto?)"))
        total = sum(v["tamanho"] for v in files.values())
        root = models_root()
        root.mkdir(parents=True, exist_ok=True)
        stage = root / f".instalando-{pack.id}"
        shutil.rmtree(stage, ignore_errors=True)
        done = 0
        try:
            for name in sorted(files):
                info = files[name]
                dest = stage.joinpath(*PurePosixPath(name).parts)
                dest.parent.mkdir(parents=True, exist_ok=True)
                h, n = hashlib.sha256(), 0
                with zf.open(name) as src, dest.open("wb") as out:
                    while chunk := src.read(1024 * 1024):
                        n += len(chunk)
                        if n > info["tamanho"]:
                            raise PackError(tr("arquivo do pacote maior do que o esperado: {0}").format(name))
                        h.update(chunk)
                        out.write(chunk)
                        done += len(chunk)
                        if progress:
                            progress(done, total)
                if n != info["tamanho"] or h.hexdigest() != info["sha256"]:
                    raise PackError(tr("o pacote está danificado (conferência falhou em {0}); baixe-o de novo")
                                    .format(name))
            for unit in sorted({_unit_of(n, pack) for n in files}):
                final = root / unit
                final.parent.mkdir(parents=True, exist_ok=True)
                if _is_link(final) or final.is_file():
                    final.unlink()
                elif final.exists():
                    shutil.rmtree(final)
                os.replace(stage / unit, final)
        except zipfile.BadZipFile as exc:
            raise PackError(tr("o pacote está danificado; baixe-o de novo")) from exc
        finally:
            shutil.rmtree(stage, ignore_errors=True)
    _refresh_ocr()
    return pack


def uninstall(pack: Pack) -> bool:
    """Remove um pacote da pasta do usuário (o que vem com o programa não é tocado)."""
    removed = False
    root = models_root()
    for unit in pack.units:
        p = root / unit
        if _real(p):
            shutil.rmtree(p) if p.is_dir() else p.unlink()
            removed = True
    _refresh_ocr()
    return removed
