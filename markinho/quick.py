# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""“Converter para Markdown aqui” (botão direito do Windows): converte sem abrir a janela principal.

Usa as configurações salvas no programa (modo, motor, imagens, correção, padrão de nome) e grava
o `.md` ao lado do original. Mostra o progresso numa janelinha e avisa ao terminar; se algo falhar,
explica o motivo. Vários arquivos selecionados viram um lote só (veja `single.py`).
"""
from __future__ import annotations

from .i18n import tr

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings


@dataclass
class QuickResult:
    source: Path
    output: Path | None = None
    error: str = ""
    skipped: bool = False
    unchanged: bool = False      # retomar: já convertido antes e sem mudanças (não foi refeito)


def settings() -> QSettings:
    return QSettings("Markinho", "Markinho")


class SettingsSnapshot:
    """Cópia das configurações para usar fora da thread da interface (ler QSettings em duas threads
    ao mesmo tempo pode derrubar o programa). Imita `QSettings.value(chave, padrão, type=…)`."""

    def __init__(self, s: QSettings | None = None):
        s = s or settings()
        self._d = {k: s.value(k) for k in s.allKeys()}

    def allKeys(self) -> list[str]:  # noqa: N802 (mesmo nome do Qt)
        return list(self._d)

    def value(self, key: str, default=None, type=None):  # noqa: A002
        v = self._d.get(key, default)
        if type is bool:
            return v.strip().lower() in ("true", "1", "yes", "sim") if isinstance(v, str) else bool(v)
        if type is int:
            try:
                return int(v)
            except (TypeError, ValueError):
                return int(default or 0)
        return v


def _engine_options(s: QSettings, eid: str) -> dict[str, Any]:
    from .engines import ENGINES

    out: dict[str, Any] = {}
    for opt in ENGINES[eid].options:
        key = f"opt/{eid}/{opt.key}"
        if opt.kind == "bool":
            out[opt.key] = s.value(key, opt.default, type=bool)
        elif opt.kind == "int":
            out[opt.key] = int(s.value(key, opt.default) or 0)
        else:
            out[opt.key] = s.value(key, opt.default)
    return out


def saved_job(s: QSettings, path: Path) -> tuple[str, dict[str, Any], Any, Any, bool]:
    """(motor, opções, correção, saída, tentar outro motor) a partir das configurações salvas —
    as mesmas que a janela principal usaria."""
    from .engines import AUTO, ENGINES, pick_engine
    from .postprocess import OutputOptions
    from .textfix import FixOptions

    chosen = str(s.value("engine", AUTO))
    eid = chosen if chosen in ENGINES and ENGINES[chosen].supports(path) else AUTO
    opts: dict[str, Any] = {}
    if eid == AUTO:
        try:
            eid = pick_engine(path).id
        except RuntimeError:
            eid = AUTO
    if eid != AUTO:
        opts = _engine_options(s, eid)
    fix = None
    if s.value("fix/enabled", True, type=bool):
        defaults = FixOptions()
        fix = FixOptions(**{k: s.value(f"fix/{k}", getattr(defaults, k), type=bool)
                            for k in FixOptions.__dataclass_fields__})
    output = OutputOptions(images=s.value("out/images", "folder"), profile=s.value("out/profile", "gfm"),
                           frontmatter=s.value("out/frontmatter", False, type=bool),
                           describe_images=s.value("out/describe", False, type=bool),
                           ollama_model=str(s.value("out/ollama_model", "")),
                           anon=anon_options(s) if s.value("anon/enabled", False, type=bool) else None)
    return eid, opts, fix, output, chosen == AUTO


def anon_options(s):
    """Opções de anonimização salvas (iguais na janela, no botão direito e na pasta monitorada)."""
    from .anonymize import DEFAULT_KINDS, AnonOptions

    kinds = s.value("anon/kinds", None)
    if kinds is None:
        kinds = list(DEFAULT_KINDS)
    elif isinstance(kinds, str):
        kinds = [k for k in kinds.split(",") if k]
    return AnonOptions(kinds=list(kinds), mode=str(s.value("anon/mode", "pseudonimo")),
                       words=str(s.value("anon/words", "")),
                       metadata=s.value("anon/metadata", True, type=bool),
                       image_metadata=s.value("anon/image_metadata", True, type=bool),
                       remove_images=s.value("anon/remove_images", False, type=bool))


def save_anon_options(s, o) -> None:
    s.setValue("anon/kinds", ",".join(o.kinds))
    s.setValue("anon/mode", o.mode)
    s.setValue("anon/words", o.words)
    s.setValue("anon/metadata", o.metadata)
    s.setValue("anon/image_metadata", o.image_metadata)
    s.setValue("anon/remove_images", o.remove_images)


def naming_options(s: QSettings):
    from .naming import NamingOptions

    return NamingOptions(s.value("naming/template", "{nome}"), s.value("naming/ext", ".md"),
                         int(s.value("naming/start", 1)), int(s.value("naming/digits", 3)),
                         s.value("naming/safe", False, type=bool), s.value("naming/conflict", "suffix"))


def convert_here(path: str | Path, s: QSettings | None = None, index: int = 0,
                 out_dir: str | Path | None = None, target: str | Path | None = None,
                 progress=None, cancel=None) -> QuickResult:
    """Converte um arquivo para Markdown e grava ao lado do original (ou em `out_dir`, ou exatamente em
    `target`, quando o usuário escolheu nome e local). Nunca levanta exceção."""
    from . import batch
    from .assets import write_assets
    from .core import convert
    from .naming import NameContext, plan, rename_assets

    s = s or settings()
    src = Path(path)
    manifest = sha = cfg = None
    try:
        if not src.is_file():
            return QuickResult(src, error=tr("arquivo não encontrado"))
        eid, opts, fix, output, fallback = saved_job(s, src)
        folder = Path(out_dir) if out_dir else src.parent
        if not target and batch.enabled(s):
            # retomar: o que já foi convertido para esta pasta, com estas configurações, e não mudou, é pulado
            manifest = batch.Manifest(folder)
            sha = batch.file_hash(src)
            cfg = batch.job_key(eid, opts, fix, output, {"naming": vars(naming_options(s))})
            if manifest.is_done(src, sha, cfg):
                return QuickResult(src, folder / manifest.output_name(src, cfg), skipped=True, unchanged=True)
        ctx = {"origem": tr("botão direito / pasta monitorada"), "motor": eid, "opções do motor": dict(opts),
               "correção de caracteres": "ligada" if fix is not None else "desligada",
               "imagens": output.images, "perfil": output.profile}
        res = convert(src, eid, opts, fix, output, fallback=fallback, progress=progress, cancel=cancel)
        if target:
            dest = Path(target)
            dest.parent.mkdir(parents=True, exist_ok=True)
        else:
            title = res.metadata.get("title") or res.title or ""
            ctx = NameContext.from_result(src, title=title, engine=res.engine)
            nopts = naming_options(s)
            nopts.start = nopts.start + index            # {n} segue a ordem do lote
            folder.mkdir(parents=True, exist_ok=True)
            reserved = manifest.output_name(src, cfg) if manifest is not None else None
            if reserved:                                 # retomando: grava por cima do que ficou pela metade
                dest = folder / reserved
            else:
                planned = plan([ctx], nopts, folder)[0]
                if planned.action == "skip":
                    return QuickResult(src, planned.path, skipped=True)
                dest = planned.path
        if manifest is not None:
            manifest.start(src, sha, cfg, dest.name)
        text, assets = res.markdown, res.assets
        if assets:
            text, assets = rename_assets(text, assets, dest.stem)
        batch.atomic_write(dest, text)
        if assets:
            write_assets(text, assets, dest.parent)
        if manifest is not None:
            manifest.finish(src, True)
        return QuickResult(src, dest)
    except PermissionError:
        return QuickResult(src, error=tr("sem permissão para gravar nesta pasta"))
    except Exception as exc:  # noqa: BLE001
        if manifest is not None and sha:
            try:
                manifest.fail(src, sha, cfg, str(exc) or exc.__class__.__name__)
            except OSError:
                pass
        return _failed(src, exc, locals().get("ctx"))


def export_one(path: str | Path, fmt_id: str, target: str | Path, options: dict | None = None,
               cancel=None) -> QuickResult:
    """Markdown → outro formato (Word, PDF, HTML…). Nunca levanta exceção."""
    from .core import CANCELLED, ConversionError
    from .exporter import export

    src = Path(path)
    try:
        if cancel is not None and cancel.is_set():
            raise ConversionError(CANCELLED)
        if not src.is_file():
            return QuickResult(src, error=tr("arquivo não encontrado"))
        md = src.read_text(encoding="utf-8", errors="replace")
        dest = Path(target)
        dest.parent.mkdir(parents=True, exist_ok=True)
        partial = dest.with_name(f".~{dest.stem}{dest.suffix}")      # trocado no fim: nunca fica pela metade
        try:
            export(md, partial, fmt_id, options or {}, base_dir=src.parent)
            os.replace(partial, dest)
        finally:
            partial.unlink(missing_ok=True)
        return QuickResult(src, dest)
    except PermissionError:
        return QuickResult(src, error=tr("sem permissão para gravar nesta pasta"))
    except Exception as exc:  # noqa: BLE001
        return _failed(src, exc)


def _failed(src: Path, exc: Exception, ctx: dict | None = None) -> QuickResult:
    import traceback

    from .core import CANCELLED
    from .diagnostics import record_error

    if str(exc) != CANCELLED:
        record_error(str(src), str(exc) or exc.__class__.__name__,
                     "" if exc.__class__.__name__ == "ConversionError" else traceback.format_exc(), ctx)
    return QuickResult(src, error=str(exc) or exc.__class__.__name__)


def summary(results: list[QuickResult]) -> tuple[str, str]:
    """(título, texto) do aviso final."""
    ok = [r for r in results if r.output and not r.skipped and not r.error]
    unchanged = [r for r in results if r.unchanged]
    skipped = [r for r in results if r.skipped and not r.unchanged]
    bad = [r for r in results if r.error]
    if len(results) == 1 and unchanged:
        return tr("Markinho: concluído"), tr("{0} já tinha sido convertido e não mudou: {1}").format(
            unchanged[0].source.name, unchanged[0].output)
    if len(results) == 1 and ok:
        return tr("Markinho: concluído"), tr('{0} foi salvo em {1}').format(ok[0].output.name, ok[0].output.parent)
    parts = [tr('{0} arquivo(s) convertido(s)').format(len(ok))]
    if unchanged:
        parts.append(tr("{0} já convertido(s) antes e sem mudanças").format(len(unchanged)))
    if skipped:
        parts.append(tr('{0} pulado(s) (já existiam)').format(len(skipped)))
    if bad:
        parts.append(tr('{0} com erro').format(len(bad)))
    return (tr("Markinho: concluído") if not bad else tr("Markinho: terminou com erros")), ", ".join(parts) + "."


# --------------------------------------------------------------------------- #
# Botão direito: escolher destino, acompanhar o andamento, alerta de concluído
# --------------------------------------------------------------------------- #
MODES = {"aqui": "quick", "perguntar": "quick-ask", "exportar": "export"}   # modo → canal da instância única


def default_target(src: Path, s, ext: str = ".md") -> Path:
    """Nome sugerido na janela de salvar: o padrão de nomes das configurações, na pasta do original."""
    from .naming import NameContext, plan

    nopts = naming_options(s)
    return plan([NameContext.from_result(src)], nopts, src.parent, ext)[0].path


def main(paths: list[str], mode: str = "aqui") -> int:
    from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from .diagnostics import install as install_diagnostics
    from .single import claim

    install_diagnostics()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Markinho")
    app.setOrganizationName("Markinho")
    app.setQuitOnLastWindowClosed(False)
    state: dict = {"queue": [], "results": [], "busy": False, "stopped": False, "started": False,
                   "out_dir": None, "targets": {}, "fmt": "", "opts": {}, "page": 0.0}
    queue: list[str] = state["queue"]

    def add(new: list[str]) -> None:
        for p in new:
            if p not in queue:
                queue.append(p)
        if state["started"]:
            popup.set_total(len(queue))

    listener = claim(MODES.get(mode, "quick"), paths, add)
    if listener is None:            # outra instância já está cuidando da seleção: entregou os arquivos
        return 0

    from .gui import icon_path, install_translations
    from .gui_tools import DoneDialog, ExportChoiceDialog, ProgressPopup

    install_translations(app)

    ip = icon_path()
    app.setWindowIcon(QIcon(str(ip)) if ip else QIcon())
    s = settings()
    snapshot = SettingsSnapshot(s)
    add(paths)

    def ask_destination() -> bool:
        """Pergunta onde salvar (e o formato, ao exportar). False = o usuário desistiu."""
        from PySide6.QtWidgets import QFileDialog

        ext = ".md"
        if mode == "exportar":
            choice = ExportChoiceDialog(None, s)
            from PySide6.QtWidgets import QDialog

            if choice.exec() != QDialog.Accepted:
                return False
            state["fmt"], state["opts"], ext = choice.values()
        if mode == "aqui":
            return True
        from .gui import recall_dir, remember_dir

        last = s.value("dir/quick", "")              # última pasta escolhida no botão direito
        if len(queue) == 1:
            src = Path(queue[0])
            sug = default_target(src, snapshot, ext) if mode == "perguntar" else src.with_suffix(ext)
            if last and Path(last).is_dir():
                sug = Path(last) / sug.name
            filt = "Markdown (*.md)" if ext == ".md" else f"{ext[1:].upper()} (*{ext})"
            f, _ = QFileDialog.getSaveFileName(None, tr("Salvar como"), str(sug), filt)
            if not f:
                return False
            f = Path(f)
            if f.suffix.lower() != ext:
                f = f.with_suffix(ext)
            state["targets"][queue[0]] = f
            state["out_dir"] = f.parent            # arquivos que chegarem depois vão para a mesma pasta
            remember_dir(s, f, "quick")
            return True
        d = QFileDialog.getExistingDirectory(None, tr('Pasta para salvar os {0} arquivos').format(len(queue)),
                                             recall_dir(s, "quick", str(Path(queue[0]).parent)))
        if not d:
            return False
        state["out_dir"] = Path(d)
        remember_dir(s, d, "quick")
        return True

    class Worker(QObject):
        finished_one = Signal(object)
        progressed = Signal(int, int)

        def run_one(self, path: str, index: int) -> None:
            cancel = state["cancel"]
            if mode == "exportar":
                target = state["targets"].get(path) or _unique(
                    (state["out_dir"] or Path(path).parent) / (Path(path).stem + _ext(state["fmt"])))
                r = export_one(path, state["fmt"], target, state["opts"], cancel)
            else:
                r = convert_here(path, snapshot, index, state["out_dir"], state["targets"].get(path),
                                 progress=lambda d, t: self.progressed.emit(d, t), cancel=cancel)
            self.finished_one.emit(r)

    import threading

    state["cancel"] = threading.Event()
    thread = QThread()
    worker = Worker()
    worker.moveToThread(thread)
    thread.start()
    popup = ProgressPopup(s, stop=lambda: state["cancel"].set())

    def next_file() -> None:
        if state["busy"]:
            return
        done = len(state["results"])
        if state["cancel"].is_set() or done >= len(queue):
            finish()
            return
        state["busy"] = True
        state["page"] = 0.0
        popup.set_file(Path(queue[done]).name, done, len(queue))
        QTimer.singleShot(0, worker, lambda p=queue[done], i=done: worker.run_one(p, i))

    class Receiver(QObject):
        """Vive na thread da interface: os sinais da conversão chegam por fila."""

        @Slot(object)
        def done(self, r: QuickResult) -> None:
            state["results"].append(r)
            state["busy"] = False
            popup.set_progress(len(state["results"]), len(queue), 0.0)
            QTimer.singleShot(100, next_file)

        @Slot(int, int)
        def prog(self, d: int, t: int) -> None:
            if t > 0:
                popup.set_progress(len(state["results"]), len(queue), d / t)

    receiver = Receiver()
    worker.finished_one.connect(receiver.done)
    worker.progressed.connect(receiver.prog)

    def finish() -> None:
        listener.server.close()        # um clique novo depois daqui abre a sua própria janela
        if not state["cancel"].is_set() and len(state["results"]) < len(queue):
            next_file()                # chegou mais algum arquivo no último instante
            return
        popup.close()
        thread.quit()
        thread.wait(5000)
        results = state["results"]
        if state["cancel"].is_set():
            from .core import CANCELLED

            results = [r for r in results if r.error != CANCELLED]
        import os

        if (results or state["cancel"].is_set()) and os.environ.get("MARKINHO_QUIET") != "1":
            DoneDialog(results, stopped=state["cancel"].is_set(), skipped=len(queue) - len(results)).exec()
        app.quit()

    def begin() -> None:
        # espera um instante: os outros arquivos da seleção ainda estão chegando
        try:
            if not ask_destination():
                app.quit()
                return
            state["started"] = True
            popup.start(len(queue))
            next_file()
        except Exception as exc:  # noqa: BLE001 — nunca ficar aberto sem fazer nada
            import os
            import traceback

            from PySide6.QtWidgets import QMessageBox

            from .diagnostics import record_error

            record_error(tr("(botão direito)"), str(exc), traceback.format_exc())
            if os.environ.get("MARKINHO_QUIET") != "1":
                QMessageBox.critical(None, tr("Markinho"), tr('Não foi possível converter:\n{0}').format(exc))
            app.exit(1)

    QTimer.singleShot(500, begin)
    return app.exec()


def _ext(fmt_id: str) -> str:
    from .exporter import FORMATS_BY_ID

    return FORMATS_BY_ID[fmt_id].ext


def _unique(path: Path) -> Path:
    if not path.exists():
        return path
    n = 2
    while (cand := path.with_name(f"{path.stem}_{n}{path.suffix}")).exists():
        n += 1
    return cand
