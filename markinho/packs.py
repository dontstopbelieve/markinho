# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Pacotes extras: modelos de IA opcionais que a pessoa instala uma vez e ficam no computador.

A COMPLETA já traz os modelos de layout e de tabelas. Os que poucas pessoas usam (ex.: fórmulas, ~600 MB)
são publicados à parte como ``Markinho-Pacote-<Nome>-<versão>.zip`` nas Releases do GitHub, para o
instalador caber no limite de 2 GB por arquivo. A pessoa escolhe:

* no instalador do Windows (marca a caixinha: ele baixa ou usa o .zip que estiver ao lado), ou
* depois, em Ferramentas › Pacotes extras › Instalar de um arquivo… (ou ``--instalar-pacote arquivo.zip``).

**O Markinho em si nunca baixa nada**: quem baixa é o navegador ou o instalador, antes de haver
documentos. Aqui só se confere e se descompacta um arquivo que já está no computador.

Segurança: o .zip traz ``markinho-pacote.json`` com o SHA-256 e o tamanho de cada arquivo; nada fora da
lista é aceito, os nomes não podem sair da pasta do pacote e cada arquivo é conferido enquanto é copiado.
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
MAX_TOTAL = 6 * 1024 ** 3          # nenhum pacote passa de 6 GB descompactado
MAX_FILES = 2000


@dataclass(frozen=True)
class Pack:
    id: str
    file_title: str                  # parte do nome do arquivo: Markinho-Pacote-<file_title>-<versão>.zip
    folders: tuple[str, ...]         # pastas dentro de models/docling
    size_mb: int

    @property
    def name(self) -> str:
        return {"formulas": tr("Fórmulas e código")}[self.id]

    @property
    def what(self) -> str:
        return {"formulas": tr("Converte equações em texto editável (LaTeX) e reconhece trechos de código de "
                               "programação. Usado pelo motor Docling (IA de layout) quando as opções "
                               "“Reconhecer fórmulas” ou “Reconhecer código” estão ligadas.")}[self.id]

    @property
    def who(self) -> str:
        return {"formulas": tr("Vale a pena para: artigos científicos, teses, apostilas de matemática, física, "
                               "química e engenharia, documentação técnica.")}[self.id]

    @property
    def skip(self) -> str:
        return {"formulas": tr("Dispensável para: contratos, processos, relatórios, planilhas, documentos de "
                               "escritório em geral. Sem ele, as fórmulas saem como texto simples ou imagem; "
                               "o resto do documento não muda.")}[self.id]

    def file_name(self, version: str) -> str:
        return f"Markinho-Pacote-{self.file_title}-{version}.zip"

    def url(self, version: str) -> str:
        return f"{RELEASES}/download/v{version}/{self.file_name(version)}"


PACKS: tuple[Pack, ...] = (
    Pack("formulas", "Formulas", ("docling-project--CodeFormulaV2",), 600),
)
PACKS_BY_ID = {p.id: p for p in PACKS}


class PackError(Exception):
    """Pacote inválido, corrompido ou que não pode ser instalado (mensagem já traduzida)."""


# ---------------------------------------------------------------- onde ficam os modelos
def _bundled() -> Path | None:
    from .models import bundled_models_dir

    b = bundled_models_dir()
    p = b / "docling" if b is not None else None
    return p if p is not None and p.is_dir() else None


def user_docling_dir() -> Path:
    from .models import models_dir

    return models_dir() / "docling"


def _has(folder: Path) -> bool:
    return folder.is_dir() and any(folder.iterdir())


def installed(pack: Pack) -> bool:
    bases = [b for b in (_bundled(), user_docling_dir()) if b is not None]
    return all(any(_has(b / f) for b in bases) for f in pack.folders)


def docling_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("docling") is not None


def _is_link(p: Path) -> bool:
    try:
        return p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
    except OSError:
        return False


def _link_dir(target: Path, link: Path) -> None:
    """Liga uma pasta embutida dentro da pasta do usuário, sem copiar (atalho; no Windows, junção)."""
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        pass
    if sys.platform == "win32":
        try:
            import _winapi

            _winapi.CreateJunction(str(target), str(link))     # não precisa de administrador
            return
        except (OSError, ImportError, AttributeError):
            pass
    shutil.copytree(target, link)                                # último recurso: copia


def merged_docling_dir() -> Path | None:
    """Pasta única de modelos para o Docling (ele só aceita uma).

    Só embutidos → a pasta do programa. Com pacote extra na pasta do usuário → a pasta do usuário, com
    atalhos para os modelos embutidos que faltam nela (refeitos se o programa mudou de lugar).
    """
    bundled, user = _bundled(), user_docling_dir()
    if not _has(user):
        return bundled
    if bundled is None:
        return user
    for item in bundled.iterdir():
        if not item.is_dir():
            continue
        dest = user / item.name
        if _is_link(dest) and not dest.exists():         # atalho quebrado (programa reinstalado em outro lugar)
            try:
                dest.unlink()
            except OSError:
                os.rmdir(dest)
        if not dest.exists():
            try:
                _link_dir(item, dest)
            except OSError:
                return bundled                           # sem como juntar: ao menos o básico funciona
    return user


# ---------------------------------------------------------------- criar (usado pelo build)
def build_pack(pack: Pack, docling_models: Path, out_dir: Path, version: str) -> Path:
    """Gera o .zip do pacote a partir de uma pasta de modelos do Docling. Sempre igual para o mesmo conteúdo."""
    files: dict[str, dict] = {}
    entries: list[tuple[str, Path]] = []
    for folder in pack.folders:
        src = docling_models / folder
        if not _has(src):
            raise PackError(tr("modelo não encontrado: {0}").format(src))
        for f in sorted(p for p in src.rglob("*") if p.is_file()):
            arc = "docling/" + f.relative_to(docling_models).as_posix()
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
def _safe_name(name: str, pack: Pack) -> bool:
    if "\\" in name or ":" in name or name.startswith("/"):
        return False
    parts = PurePosixPath(name).parts
    return (len(parts) >= 3 and parts[0] == "docling" and parts[1] in pack.folders
            and all(p not in ("", ".", "..") for p in parts))


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
        if not _safe_name(name, pack) or not isinstance(info, dict):
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
        if not docling_available():
            raise PackError(tr("os pacotes extras são para a edição COMPLETA (com o motor Docling)"))
        if check_version and data.get("versao") != check_version:
            raise PackError(tr("pacote da versão {0}; esta é a {1}").format(data.get("versao"), check_version))
        files = data["arquivos"]
        names = {i.filename for i in zf.infolist() if not i.is_dir()}
        if names - set(files) - {MANIFEST}:
            raise PackError(tr("o pacote tem arquivos fora da lista de conteúdo"))
        if set(files) - names:
            raise PackError(tr("faltam arquivos no pacote (download incompleto?)"))
        total = sum(v["tamanho"] for v in files.values())
        root = user_docling_dir()
        root.mkdir(parents=True, exist_ok=True)
        stage = root / f".instalando-{pack.id}"
        shutil.rmtree(stage, ignore_errors=True)
        done = 0
        try:
            for name in sorted(files):
                info = files[name]
                dest = stage.joinpath(*PurePosixPath(name).parts[1:])
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
            for folder in pack.folders:
                final = root / folder
                if _is_link(final):
                    final.unlink()
                elif final.exists():
                    shutil.rmtree(final)
                os.replace(stage / folder, final)
        except zipfile.BadZipFile as exc:
            raise PackError(tr("o pacote está danificado; baixe-o de novo")) from exc
        finally:
            shutil.rmtree(stage, ignore_errors=True)
    return pack


def uninstall(pack: Pack) -> bool:
    """Remove um pacote da pasta do usuário (os modelos que vêm com o programa não são tocados)."""
    removed = False
    for folder in pack.folders:
        p = user_docling_dir() / folder
        if p.exists() and not _is_link(p):
            shutil.rmtree(p)
            removed = True
    return removed
