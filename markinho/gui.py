# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Interface gráfica do Markinho (PySide6)."""
from __future__ import annotations

from .i18n import tr

import difflib
import html
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QPointF, QRunnable, QSettings, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import (QAction, QColor, QFont, QGuiApplication, QIcon, QImage, QKeySequence, QPainter,
                           QPalette, QTextDocument)
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDockWidget, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QRadioButton, QScrollArea, QSpinBox, QSplitter, QStyle, QTableWidget, QTableWidgetItem, QTabWidget,
    QTextBrowser, QToolBar, QVBoxLayout, QWidget,
)

from . import __version__
from .assets import IMAGE_MODES, write_assets
from .core import ConversionError, ConversionResult, convert, finalize_result
from .engines import AUTO, ENGINES, all_input_extensions, pandoc_version
from .exporter import FORMATS_BY_ID, available_formats, available_pdf_engines, export, format_backends
from .postprocess import PROFILES, OutputOptions
from .textfix import FixOptions, fix_text

ROLE_PATH = Qt.UserRole


@dataclass
class Entry:
    path: str
    result: ConversionResult | None = None
    error: str = ""
    edited: bool = False
    text: str = ""          # texto exibido/salvo (pode ter edições do usuário)
    busy: bool = False
    queued: bool = False    # na fila, aguardando o botão "Converter"
    custom: str = ""        # nome dado pelo usuário (Renomear / F2)
    progress: tuple[int, int] | None = None   # páginas feitas / total (PDF)
    partial: list | None = None               # prévia: [(página, texto provisório)] enquanto converte


# --------------------------------------------------------------------------- #
# Conversão em segundo plano
# --------------------------------------------------------------------------- #
class _Signals(QObject):
    done = Signal(str, int, object)    # caminho, geração, ConversionResult
    failed = Signal(str, int, str)     # caminho, geração, mensagem
    progress = Signal(str, int, int, int)   # caminho, geração, feitas, total
    partial = Signal(str, int, int, str)    # caminho, geração, página, texto provisório


class _ConvertTask(QRunnable):
    def __init__(self, path: str, gen: int, engine: str, opts: dict, fix: FixOptions | None,
                 output: OutputOptions | None = None, fallback: bool = False):
        super().__init__()
        self.path, self.gen, self.engine, self.opts, self.fix = path, gen, engine, opts, fix
        self.output, self.fallback = output, fallback
        self.signals = _Signals()
        import threading

        self.cancel = threading.Event()          # “Parar”: interrompe na próxima página

    def run(self) -> None:
        def prog(done, total):
            self.signals.progress.emit(self.path, self.gen, done, total)

        def part(page, text):
            self.signals.partial.emit(self.path, self.gen, page, text)

        try:
            res = convert(self.path, self.engine, self.opts, self.fix, self.output, fallback=self.fallback,
                          progress=prog, cancel=self.cancel, partial=part)
            self.signals.done.emit(self.path, self.gen, res)
        except ConversionError as exc:
            from .core import CANCELLED

            if str(exc) != CANCELLED:
                self._record(str(exc))
            self.signals.failed.emit(self.path, self.gen, str(exc))
        except Exception as exc:  # noqa: BLE001
            import traceback

            self._record(tr('Erro inesperado: {0}').format(exc), traceback.format_exc())
            self.signals.failed.emit(self.path, self.gen, tr('Erro inesperado: {0}').format(exc))

    def _record(self, message: str, tb: str = "") -> None:
        """Guarda o erro com a configuração usada nesta conversão (para o relatório de erro)."""
        from .diagnostics import record_error

        out = self.output
        record_error(self.path, message, tb, {
            "motor": self.engine, "tentar outro motor se falhar": self.fallback,
            "opções do motor": dict(self.opts or {}),
            "correção de caracteres": "ligada" if self.fix is not None else "desligada",
            "imagens": getattr(out, "images", None), "perfil": getattr(out, "profile", None),
            "metadados (frontmatter)": getattr(out, "frontmatter", None),
            "descrever imagens (Ollama)": getattr(out, "describe_images", None)})


# --------------------------------------------------------------------------- #
# Lista de arquivos com arrastar-e-soltar
# --------------------------------------------------------------------------- #
class FileList(QListWidget):
    """Fila de arquivos: aceita arquivos/pastas arrastados de fora e reordenação arrastando
    os próprios itens (a ordem define a numeração dos nomes de saída)."""
    files_dropped = Signal(list)
    order_changed = Signal()

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setContextMenuPolicy(Qt.ActionsContextMenu)

    @staticmethod
    def _external(e) -> bool:
        return e.mimeData().hasUrls() and e.source() is None

    def dragEnterEvent(self, e):
        if self._external(e):
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if self._external(e):
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if self._external(e):
            paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
            if paths:
                self.files_dropped.emit(paths)
                e.acceptProposedAction()
            return
        super().dropEvent(e)
        self.order_changed.emit()

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.count() == 0:
            p = QPainter(self.viewport())
            p.setPen(self.palette().placeholderText().color())
            p.drawText(self.viewport().rect(), Qt.AlignCenter | Qt.TextWordWrap,
                       tr("Arraste arquivos ou pastas para cá\n(ou para qualquer lugar da janela)\n\n"
                       "Eles ficam na fila; clique em “Converter” (F5)\nquando terminar de adicionar"))


class PreviewBrowser(QTextBrowser):
    """Visualização que encontra as imagens extraídas (guardadas em memória)."""

    def __init__(self):
        super().__init__()
        self.assets: dict[str, bytes] = {}

    def loadResource(self, rtype, url):
        if rtype == QTextDocument.ImageResource:
            data = self.assets.get(url.toString())
            if data:
                img = QImage.fromData(data)
                if not img.isNull() and img.width() > 900:
                    img = img.scaledToWidth(900, Qt.SmoothTransformation)
                return img
        return super().loadResource(rtype, url)


# --------------------------------------------------------------------------- #
# Visualizador do arquivo original / exportado
# --------------------------------------------------------------------------- #
class FileViewer(QWidget):
    """Mostra um arquivo dentro do programa: PDF de verdade (páginas), imagens, HTML e texto;
    DOCX, ODT, PPTX, XLSX, EPUB, RTF… aparecem como prévia convertida."""

    page_changed = Signal(int)          # página do PDF que o usuário está vendo (1, 2…)

    TEXT_EXTS = {".md", ".markdown", ".txt", ".csv", ".tsv", ".json", ".xml", ".rst", ".tex", ".log", ".yaml",
                 ".yml", ".py", ".js", ".ts", ".sql", ".ini", ".toml", ".jsonl", ".typ", ".adoc", ".org", ".wiki",
                 ".textile", ".jira"}
    IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}

    def __init__(self, parent=None):
        from PySide6.QtWidgets import QStackedWidget

        super().__init__(parent)
        self.path: Path | None = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.title = QLabel(tr("Nenhum arquivo"))
        self.title.setStyleSheet("color: palette(window-text);")
        self.title.setMinimumWidth(40)
        from PySide6.QtWidgets import QSizePolicy

        self.title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)   # não força a largura mínima
        self.open_btn = QPushButton(tr("Abrir"))
        self.open_btn.setToolTip(tr("Abrir no aplicativo padrão do computador"))
        self.open_btn.clicked.connect(self._open_external)
        self.folder_btn = QPushButton(tr("Pasta"))
        self.folder_btn.setToolTip(tr("Abrir a pasta do arquivo"))
        self.folder_btn.clicked.connect(self._open_folder)
        self.zoom_out_btn = QPushButton("−")
        self.zoom_in_btn = QPushButton("+")
        self.zoom_label = QLabel("")
        self.fit_btn = QPushButton(tr("Largura"))
        for b, tip in ((self.zoom_out_btn, tr("Afastar (Ctrl + rodinha do mouse)")),
                       (self.zoom_in_btn, tr("Aproximar (Ctrl + rodinha do mouse)")),
                       (self.fit_btn, tr("Ajustar a página à largura"))):
            b.setToolTip(tip)
        self.zoom_out_btn.setFixedWidth(28)
        self.zoom_in_btn.setFixedWidth(28)
        self.zoom_out_btn.clicked.connect(lambda: self.zoom(1 / 1.2))
        self.zoom_in_btn.clicked.connect(lambda: self.zoom(1.2))
        self.fit_btn.clicked.connect(self.fit_width)
        bar.addWidget(self.title, 1)
        for w in (self.zoom_out_btn, self.zoom_label, self.zoom_in_btn, self.fit_btn):
            bar.addWidget(w)
        bar.addWidget(self.open_btn)
        bar.addWidget(self.folder_btn)
        lay.addLayout(bar)
        self.stack = QStackedWidget()
        self.msg = QLabel()
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setWordWrap(True)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.html = QTextBrowser()
        self.html.setOpenLinks(False)                # arquivos não confiáveis: links não são abertos
        img_scroll = QScrollArea()
        self.img = QLabel()
        self.img.setAlignment(Qt.AlignCenter)
        img_scroll.setWidget(self.img)
        img_scroll.setWidgetResizable(True)
        self.pdf_view = None
        try:
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtPdfWidgets import QPdfView

            self.pdf_doc = QPdfDocument(self)
            self.pdf_view = QPdfView(self)
            self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            self.pdf_view.setDocument(self.pdf_doc)
            self.pdf_view.pageNavigator().currentPageChanged.connect(lambda p: self.page_changed.emit(p + 1))
            self.pdf_view.viewport().installEventFilter(self)       # Ctrl + rodinha = zoom
        except Exception:  # noqa: BLE001  - QtPdf ausente: PDFs aparecem como texto extraído
            self.pdf_doc = None
        for w in (self.msg, self.text, self.html, img_scroll) + ((self.pdf_view,) if self.pdf_view else ()):
            self.stack.addWidget(w)
        self._img_scroll = img_scroll
        lay.addWidget(self.stack, 1)
        self.show_message(tr("Selecione um arquivo."))

    def eventFilter(self, obj, ev):
        from PySide6.QtCore import QEvent

        if ev.type() == QEvent.Wheel and ev.modifiers() & Qt.ControlModifier and self.is_pdf():
            self.zoom(1.1 if ev.angleDelta().y() > 0 else 1 / 1.1)
            return True
        return super().eventFilter(obj, ev)

    def _keep_page(self):
        """Depois do zoom, volta para a página que estava à vista (o zoom mantém a rolagem em pixels)."""
        page = self.current_page()
        if page:
            self.pdf_view.setUpdatesEnabled(False)

            def back():
                self.pdf_view.pageNavigator().jump(page - 1, QPointF(), 0)
                self.pdf_view.setUpdatesEnabled(True)

            QTimer.singleShot(60, back)            # depois de o PDF refazer o layout com o novo zoom

    def zoom(self, factor: float) -> None:
        """Aproxima/afasta o PDF (ou a imagem)."""
        if self.is_pdf():
            self._keep_page()
            from PySide6.QtPdfWidgets import QPdfView

            cur = self.pdf_view.zoomFactor()
            if self.pdf_view.zoomMode() != QPdfView.ZoomMode.Custom:
                # partindo de “ajustar à largura”: estima o fator atual pela largura da página
                doc = self.pdf_doc
                pw = doc.pagePointSize(0).width() if doc and doc.pageCount() else 0
                cur = (self.pdf_view.viewport().width() / (pw * self.logicalDpiX() / 72)) if pw else 1.0
                self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
            self.pdf_view.setZoomFactor(max(0.2, min(cur * factor, 6.0)))
        elif self.stack.currentWidget() is self._img_scroll and self.img.pixmap() is not None:
            self._img_zoom = max(0.1, min(getattr(self, "_img_zoom", 1.0) * factor, 8.0))
            self._show_image()
        self._update_zoom_label()

    def fit_width(self) -> None:
        if self.is_pdf():
            self._keep_page()
            from PySide6.QtPdfWidgets import QPdfView

            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        elif self.stack.currentWidget() is self._img_scroll:
            self._img_zoom = None
            self._show_image()
        self._update_zoom_label()

    def _update_zoom_label(self) -> None:
        if self.is_pdf():
            from PySide6.QtPdfWidgets import QPdfView

            custom = self.pdf_view.zoomMode() == QPdfView.ZoomMode.Custom
            self.zoom_label.setText(f"{self.pdf_view.zoomFactor() * 100:.0f}%" if custom else tr("Largura"))
        else:
            z = getattr(self, "_img_zoom", None)
            self.zoom_label.setText(f"{z * 100:.0f}%" if z else "")

    def _show_image(self) -> None:
        pm = getattr(self, "_img_full", None)
        if pm is None:
            return
        z = getattr(self, "_img_zoom", None)
        if z:
            self.img.setPixmap(pm.scaledToWidth(max(20, int(pm.width() * z)), Qt.SmoothTransformation))
        else:
            w = max(200, self._img_scroll.viewport().width() - 10)
            self.img.setPixmap(pm if pm.width() <= w else pm.scaledToWidth(w, Qt.SmoothTransformation))

    def is_pdf(self) -> bool:
        return self.pdf_view is not None and self.stack.currentWidget() is self.pdf_view

    def current_page(self) -> int:
        return self.pdf_view.pageNavigator().currentPage() + 1 if self.is_pdf() else 0

    def go_to_page(self, page: int) -> None:
        """Mostra a página `page` (1, 2…) de um PDF aberto."""
        if self.is_pdf() and page != self.current_page():
            from PySide6.QtCore import QPointF

            self.pdf_view.pageNavigator().jump(max(0, page - 1), QPointF(), 0)

    def show_message(self, text: str) -> None:
        self.msg.setText(text)
        self.stack.setCurrentWidget(self.msg)
        self.open_btn.setEnabled(False)
        self.folder_btn.setEnabled(False)

    def load(self, path: str | Path, note: str = "") -> None:
        p = Path(path)
        self.path = p
        if not p.is_file():
            self.title.setText(html.escape(p.name))
            self.show_message(tr("Documento sem arquivo de origem (escrito no programa)."))
            return
        self.open_btn.setEnabled(True)
        self.folder_btn.setEnabled(True)
        ext = p.suffix.lower()
        label = f"<b>{html.escape(p.name)}</b>"
        try:
            if ext == ".pdf" and self.pdf_doc is not None:
                self.pdf_doc.load(str(p))
                pages = self.pdf_doc.pageCount()
                if pages > 0:
                    self.stack.setCurrentWidget(self.pdf_view)
                    self._update_zoom_label()
                    self.title.setText(tr('{0} · {1} página(s)').format(label, pages))
                    return
                self.title.setText(label)
                self.show_message(tr("Não foi possível abrir este PDF (protegido por senha ou corrompido)."))
                self.open_btn.setEnabled(True)
                return
            if ext in self.IMG_EXTS:
                img = QImage(str(p))
                if not img.isNull():
                    from PySide6.QtGui import QPixmap

                    w = max(200, self._img_scroll.viewport().width() - 10)
                    pm = QPixmap.fromImage(img)
                    self._img_full, self._img_zoom = pm, None
                    self.img.setPixmap(pm if pm.width() <= w else pm.scaledToWidth(w, Qt.SmoothTransformation))
                    self.stack.setCurrentWidget(self._img_scroll)
                    self._update_zoom_label()
                    self.title.setText(f"{label} · {img.width()}×{img.height()} px")
                    return
            if ext in (".html", ".htm", ".xhtml"):
                self.html.setHtml(p.read_text(encoding="utf-8", errors="replace"))
                self.stack.setCurrentWidget(self.html)
                self.title.setText(label)
                return
            if ext in self.TEXT_EXTS:
                data = p.read_bytes()[:3_000_000].decode("utf-8", errors="replace")
                self.text.setPlainText(data)
                self.stack.setCurrentWidget(self.text)
                self.title.setText(label)
                return
            # DOCX, ODT, PPTX, XLSX, EPUB, RTF, DOC…: prévia convertida
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                self.html.setHtml(self._preview_html(p))
            finally:
                QApplication.restoreOverrideCursor()
            self.stack.setCurrentWidget(self.html)
            self.title.setText(tr('{0} · prévia (o aspecto exato aparece no aplicativo padrão)').format(label)
                               + (f" · {html.escape(note)}" if note else ""))
        except Exception as exc:  # noqa: BLE001
            self.title.setText(label)
            self.show_message(tr('Não foi possível mostrar o arquivo aqui: {0}').format(exc))
            self.open_btn.setEnabled(True)

    @staticmethod
    def _preview_html(p: Path) -> str:
        from .engines import ENGINES, PANDOC_READERS, run_pandoc

        ext = p.suffix.lower()
        if ext in PANDOC_READERS and ENGINES["pandoc"].available()[0] and ext not in (".md", ".markdown"):
            try:
                return run_pandoc([str(p), "-f", PANDOC_READERS[ext], "-t", "html5"], timeout=60)
            except Exception:  # noqa: BLE001
                pass
        from .core import convert
        from .exporter import markdown_to_html
        from .postprocess import OutputOptions

        r = convert(p, output=OutputOptions(images="none"))
        return markdown_to_html(r.markdown)

    def _open_external(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        if self.path and self.path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path)))

    def _open_folder(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        if self.path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path.parent)))


class FileViewerDialog(QDialog):
    def __init__(self, parent, path: Path, title: str = tr("Arquivo exportado")):
        super().__init__(parent)
        self.setWindowTitle(f"{title} — {path.name}")
        self.resize(900, 760)
        lay = QVBoxLayout(self)
        v = FileViewer(self)
        lay.addWidget(v)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText(tr("Fechar"))
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        QTimer.singleShot(0, lambda: v.load(path))


# --------------------------------------------------------------------------- #
# Painel de configurações (motor + correção de caracteres)
# --------------------------------------------------------------------------- #
class _OllamaSignals(QObject):
    found = Signal(list, str)          # modelos, erro


class SettingsPanel(QWidget):
    engine_changed = Signal()
    reconvert_needed = Signal()       # motor, modo, opções do motor ou descrição de imagens mudaram
    fix_changed = Signal()
    output_changed = Signal()
    theme_changed = Signal(str)
    threads_changed = Signal(int)
    reconvert = Signal(bool)          # True = todos, False = selecionados

    def __init__(self, settings: QSettings):
        super().__init__()
        self.settings = settings
        self._opt_widgets: dict[str, QWidget] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)

        # ---- modo: desempenho × qualidade ----
        from .presets import PRESETS

        mbox = QGroupBox(tr("Principal"))
        mf = QFormLayout(mbox)
        self.mode = QComboBox()
        for pid, pr in PRESETS.items():
            self.mode.addItem(pr.label, pid)
            self.mode.setItemData(self.mode.count() - 1, pr.description, Qt.ToolTipRole)
        self.mode.addItem(tr("Personalizado"), "custom")
        self.mode.setItemData(self.mode.count() - 1, tr("Ajustes feitos à mão no motor e nas opções abaixo."),
                              Qt.ToolTipRole)
        self.mode.setCurrentIndex(max(0, self.mode.findData(self.settings.value("mode", "equilibrado"))))
        self.mode.setToolTip(tr("Rápido: lotes grandes de arquivos digitais. Equilibrado: o melhor para a maioria. "
                             "Máxima qualidade: PDFs difíceis e escaneados (mais lento)."))
        mf.addRow(tr("Velocidade:"), self.mode)
        self.mode_info = QLabel()
        self.mode_info.setWordWrap(True)
        self.mode_info.setStyleSheet("color: palette(window-text); font-size: 12px;")
        mf.addRow(self.mode_info)
        import os as _os

        self.threads = QSpinBox()
        self.threads.setRange(1, max(2, (_os.cpu_count() or 2)))
        self.threads.setValue(int(self.settings.value("queue/threads", min(4, _os.cpu_count() or 2))))
        self.threads.setToolTip(tr("Quantos arquivos convertem ao mesmo tempo. Menos = usa menos memória e "
                                "processador; mais = termina lotes mais rápido. A IA de layout sempre usa 1."))
        self.threads.valueChanged.connect(lambda v: (self.settings.setValue("queue/threads", v),
                                                     self.threads_changed.emit(v)))
        self._mode_form = mf
        lay.addWidget(mbox)

        # ---- opções avançadas (abre e fecha; fica fechado de início) ----
        from PySide6.QtWidgets import QToolButton as _QTB

        self.adv_toggle = _QTB()
        self.adv_toggle.setText(tr("Opções avançadas"))
        self.adv_toggle.setCheckable(True)
        self.adv_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.adv_toggle.setStyleSheet("QToolButton { border: none; font-weight: bold; padding: 4px 0; }")
        self.adv_toggle.setToolTip(tr("Motor de conversão, correção de caracteres, formato do Markdown, "
                                   "metadados, descrição de imagens, aparência"))
        lay.addWidget(self.adv_toggle)
        self.advanced = QWidget()
        adv = QVBoxLayout(self.advanced)
        adv.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.advanced)
        perf = QGroupBox(tr("Desempenho"))
        pf = QFormLayout(perf)
        pf.addRow(tr("Conversões ao mesmo tempo:"), self.threads)
        self.resume = QCheckBox(tr("Retomar lotes interrompidos"))
        self.resume.setChecked(self.settings.value("batch/resume", True, type=bool))
        self.resume.setToolTip(tr("Se o Markinho fechar ou o computador desligar no meio de um lote, ele continua de "
                                  "onde parou: oferece a fila que faltou ao abrir de novo e, no botão direito, na "
                                  "pasta monitorada e no terminal, pula o que já foi convertido e não mudou "
                                  "(confere a impressão digital SHA-256 de cada arquivo)."))
        self.resume.toggled.connect(lambda v: self.settings.setValue("batch/resume", v))
        pf.addRow(self.resume)
        self._perf_form = pf
        adv.addWidget(perf)

        def _adv(on: bool) -> None:
            self.advanced.setVisible(on)
            self.adv_toggle.setArrowType(Qt.DownArrow if on else Qt.RightArrow)
            self.settings.setValue("ui/advanced", on)
        self.adv_toggle.toggled.connect(_adv)
        self.adv_toggle.setChecked(self.settings.value("ui/advanced", False, type=bool))
        _adv(self.adv_toggle.isChecked())

        # ---- motor ----
        box = QGroupBox(tr("Motor de conversão"))
        self.engine_box = box
        bl = QVBoxLayout(box)
        self.engine = QComboBox()
        self.engine.addItem(tr("Automático (melhor disponível)"), AUTO)
        for eng in ENGINES.values():
            ok, why = eng.available()
            self.engine.addItem(eng.name + ("" if ok else tr("  (não instalado)")), eng.id)
            idx = self.engine.count() - 1
            self.engine.setItemData(idx, eng.description + ("" if ok else tr('\n\nInstalar: {0}').format(eng.install_hint)),
                                    Qt.ToolTipRole)
            if not ok:                      # aparece (para saber que existe), mas não pode ser escolhido
                item = self.engine.model().item(idx)
                if item is not None:
                    item.setEnabled(False)
        bl.addWidget(self.engine)
        self.engine_info = QLabel()
        self.engine_info.setWordWrap(True)
        self.engine_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.engine_info.setStyleSheet("color: palette(window-text); font-size: 12px;")
        bl.addWidget(self.engine_info)
        self.opt_form = QFormLayout()
        self.opt_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        bl.addLayout(self.opt_form)
        adv.addWidget(box)

        # ---- correção de caracteres ----
        self.fix_box = QGroupBox(tr("Correção de caracteres"))
        self.fix_box.setCheckable(True)
        self.fix_box.setToolTip(tr("Corrige caracteres perdidos ou trocados na extração "
                                "(codificação errada, acentos soltos, ligaduras…)."))
        fl_outer = QVBoxLayout(self.fix_box)
        frow = QHBoxLayout()
        self.fix_summary = QLabel()
        self.fix_summary.setStyleSheet("color: palette(window-text); font-size: 12px;")
        self.fix_more = _QTB()
        self.fix_more.setText(tr("Escolher quais"))
        self.fix_more.setCheckable(True)
        self.fix_more.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.fix_more.setArrowType(Qt.RightArrow)
        frow.addWidget(self.fix_summary, 1)
        frow.addWidget(self.fix_more)
        fl_outer.addLayout(frow)
        self.fix_details = QWidget()
        fl = QVBoxLayout(self.fix_details)
        fl.setContentsMargins(0, 0, 0, 0)
        fl_outer.addWidget(self.fix_details)
        self.fix_details.setVisible(False)
        self.fix_more.toggled.connect(lambda on: (self.fix_details.setVisible(on),
                                                  self.fix_more.setArrowType(Qt.DownArrow if on else Qt.RightArrow)))
        self.fix_checks: dict[str, QCheckBox] = {}
        defaults = FixOptions()
        for key in FixOptions.keys():
            label, tip = FixOptions.LABELS[key]
            cb = QCheckBox(label)
            cb.setToolTip(tip)
            cb.setChecked(self.settings.value(f"fix/{key}", getattr(defaults, key), type=bool))
            cb.toggled.connect(self._fix_toggled)
            fl.addWidget(cb)
            self.fix_checks[key] = cb
        row = QHBoxLayout()
        b_all = QPushButton(tr("Todas"))
        b_all.clicked.connect(lambda: self._set_all_fix(True))
        b_none = QPushButton(tr("Nenhuma"))
        b_none.clicked.connect(lambda: self._set_all_fix(False))
        row.addWidget(b_all)
        row.addWidget(b_none)
        row.addStretch()
        fl.addLayout(row)
        self.fix_box.setChecked(self.settings.value("fix/enabled", True, type=bool))
        self.fix_box.toggled.connect(self._fix_toggled)
        for cb in self.fix_checks.values():
            cb.toggled.connect(self._update_fix_summary)
        self._update_fix_summary()
        adv.addWidget(self.fix_box)

        # ---- saída ----
        obox = QGroupBox(tr("Formato e extras"))
        of = QFormLayout(obox)
        of.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.images = QComboBox()
        for val, lbl in IMAGE_MODES:
            self.images.addItem(lbl, val)
        self.images.setCurrentIndex(max(0, self.images.findData(self.settings.value("out/images", "folder"))))
        self.images.setToolTip(tr("Imagens extraídas dos documentos. A pasta é gravada ao lado do .md ao salvar."))
        mf.addRow(tr("Imagens:"), self.images)
        self.profile = QComboBox()
        for val, lbl in PROFILES:
            self.profile.addItem(lbl, val)
        self.profile.setCurrentIndex(max(0, self.profile.findData(self.settings.value("out/profile", "gfm"))))
        self.profile.setToolTip(tr("Dialeto do Markdown final: cada programa (GitHub, Obsidian, IAs) "
                                "entende o Markdown de um jeito um pouco diferente."))
        of.addRow(tr("Formato do Markdown:"), self.profile)
        self.frontmatter = QCheckBox(tr("Metadados no topo (frontmatter YAML)"))
        self.frontmatter.setToolTip(tr("Título, autor, datas e arquivo de origem em um bloco --- no início do .md."))
        self.frontmatter.setChecked(self.settings.value("out/frontmatter", False, type=bool))
        of.addRow(self.frontmatter)
        arow = QHBoxLayout()
        self.anon = QCheckBox(tr("Anonimizar dados pessoais"))
        self.anon.setToolTip(tr("Troca CPF, CNPJ, e-mails, telefones, nomes da sua lista e outros dados por marcadores "
                             "como [PESSOA 1]; tira autor e datas dos metadados e os dados escondidos das imagens. "
                             "Tudo no seu computador. Revise o resultado: nunca é 100%.\n\n")
                             + __import__("markinho.anonymize", fromlist=["DISCLAIMER"]).DISCLAIMER)
        self.anon.setChecked(self.settings.value("anon/enabled", False, type=bool))
        b_anon = QPushButton(tr("Opções…"))
        b_anon.setToolTip(tr("Escolher o que anonimizar e como"))
        b_anon.clicked.connect(self._anon_dialog)
        arow.addWidget(self.anon, 1)
        arow.addWidget(b_anon)
        mf.addRow(arow)
        from .gui_tools import anon_warning

        self.anon_warn = anon_warning(tr("Revise sempre o arquivo anonimizado antes de usar: o Markinho não se "
                                      "responsabiliza por dados não encontrados ou trocados por engano. Na sua "
                                      "lista, maiúsculas e acentos não importam, mas cada variação do nome "
                                      "precisa ser escrita."))
        self.anon_warn.setVisible(self.anon.isChecked())
        mf.addRow(self.anon_warn)
        self.anon.toggled.connect(self._anon_toggled)
        self.anon.toggled.connect(self._output_toggled)
        self.describe = QCheckBox(tr("Descrever imagens com IA local (Ollama)"))
        self.describe.setToolTip(tr("Gera o texto alternativo das imagens com um modelo de visão rodando no "
                                 "seu computador (ex.: ollama pull qwen2.5vl:3b). Nada é enviado à internet."))
        self.describe.setChecked(self.settings.value("out/describe", False, type=bool))
        of.addRow(self.describe)
        mrow = QHBoxLayout()
        self.ollama_model = QComboBox()
        self.ollama_model.setEditable(True)
        self.ollama_model.setToolTip(tr("Modelo de visão do Ollama. Vazio = o primeiro encontrado."))
        saved_model = self.settings.value("out/ollama_model", "")
        if saved_model:
            self.ollama_model.addItem(saved_model)
        b_ref = QPushButton("↻")
        b_ref.setFixedWidth(32)
        b_ref.setToolTip(tr("Procurar modelos no Ollama"))
        b_ref.clicked.connect(self._refresh_ollama)
        mrow.addWidget(self.ollama_model, 1)
        mrow.addWidget(b_ref)
        self.ollama_refresh_btn = b_ref
        self.ollama_label = QLabel(tr("Modelo:"))
        of.addRow(self.ollama_label, mrow)
        self.ollama_status = QLabel()
        self.ollama_status.setWordWrap(True)
        self.ollama_status.setTextFormat(Qt.RichText)
        self.ollama_status.setOpenExternalLinks(True)
        self.ollama_status.setStyleSheet("font-size: 12px;")
        of.addRow(self.ollama_status)
        self._ollama_sig = _OllamaSignals()
        self._ollama_sig.found.connect(self._ollama_found)
        self.describe.toggled.connect(self._describe_toggled)
        self.out_hint = QLabel()
        self.out_hint.setWordWrap(True)
        self.out_hint.setStyleSheet("color: palette(window-text); font-size: 12px;")
        of.addRow(self.out_hint)
        # alerta de opções que se anulam (ex.: descrever imagens com um perfil que remove as imagens)
        from PySide6.QtWidgets import QFrame

        self.conflict_box = QFrame()
        self.conflict_box.setStyleSheet("QFrame{background: #fff3cd; border: 1px solid #e0b100; border-radius: 4px;}"
                                        "QLabel{color: #3d2e00; border: none; background: transparent;}")
        cb = QVBoxLayout(self.conflict_box)
        cb.setContentsMargins(8, 6, 8, 6)
        self.conflict_label = QLabel()
        self.conflict_label.setWordWrap(True)
        self.conflict_fix = QPushButton()
        self.conflict_fix.clicked.connect(self._fix_conflict)
        cb.addWidget(self.conflict_label)
        cb.addWidget(self.conflict_fix)
        self.conflict_box.setVisible(False)
        mf.addRow(self.conflict_box)
        for w in (self.images, self.profile):
            w.currentIndexChanged.connect(self._output_toggled)
        self.frontmatter.toggled.connect(self._output_toggled)
        self.describe.toggled.connect(self._output_toggled)
        self.ollama_model.currentTextChanged.connect(self._output_toggled)
        for w in (self.ollama_model, self.ollama_refresh_btn, self.ollama_label):
            w.setEnabled(self.describe.isChecked())
        adv.addWidget(obox)

        # ---- aparência ----
        abox = QGroupBox(tr("Aparência"))
        af = QFormLayout(abox)
        self.theme = QComboBox()
        for val, lbl in (("system", tr("Do sistema")), ("light", tr("Claro")), ("dark", tr("Escuro"))):
            self.theme.addItem(lbl, val)
        self.theme.setCurrentIndex(max(0, self.theme.findData(self.settings.value("theme", "system"))))
        self.theme.currentIndexChanged.connect(
            lambda _i: (self.settings.setValue("theme", self.theme.currentData()),
                        self.theme_changed.emit(self.theme.currentData())))
        af.addRow(tr("Tema:"), self.theme)
        from .i18n import LANGUAGES

        self.lang = QComboBox()
        for val, lbl in LANGUAGES:
            self.lang.addItem(tr("Automático (idioma do sistema)") if val == "auto" else lbl, val)   # cada idioma no próprio nome
        self.lang.setCurrentIndex(max(0, self.lang.findData(str(self.settings.value("ui/lang", "auto")))))
        self.lang_note = QLabel(tr("Vale ao abrir o Markinho de novo."))
        self.lang_note.setStyleSheet("color:gray")
        self.lang_note.setVisible(False)
        self.lang.currentIndexChanged.connect(
            lambda _i: (self.settings.setValue("ui/lang", self.lang.currentData()), self.lang_note.setVisible(True)))
        af.addRow(tr("Idioma:"), self.lang)
        af.addRow("", self.lang_note)
        adv.addWidget(abox)

        # ---- reconverter ----
        rl = QHBoxLayout()
        b_sel = QPushButton(tr("Reconverter selecionados"))
        b_sel.clicked.connect(lambda: self.reconvert.emit(False))
        b_allc = QPushButton(tr("Reconverter todos"))
        b_allc.clicked.connect(lambda: self.reconvert.emit(True))
        rl.addWidget(b_sel)
        rl.addWidget(b_allc)
        adv.addLayout(rl)
        hint = QLabel(tr("Mudanças no motor valem para os próximos arquivos; use “Reconverter” para "
                      "aplicá-las aos que já estão na lista. Correções, perfil, metadados e o modo das "
                      "imagens são aplicados na hora."))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(window-text); font-size: 12px;")
        adv.addWidget(hint)
        lay.addStretch()

        saved = self.settings.value("engine", AUTO)
        if saved in ENGINES and not ENGINES[saved].available()[0]:
            saved = AUTO                    # motor de antes não está instalado nesta edição: volta ao automático
            self.settings.setValue("engine", AUTO)
        i = self.engine.findData(saved)
        self.engine.setCurrentIndex(max(i, 0))
        self.engine.currentIndexChanged.connect(self._engine_selected)
        self._build_options()
        self._update_out_hint()
        self._update_mode_info()
        self.mode.currentIndexChanged.connect(self._mode_selected)

    # --- motor ---
    def engine_id(self) -> str:
        return self.engine.currentData()

    def _engine_selected(self) -> None:
        self.settings.setValue("engine", self.engine_id())
        self._build_options()
        if not getattr(self, "_applying_mode", False):
            self._set_custom()
            self.reconvert_needed.emit()
        self.engine_changed.emit()

    # --- modos ---
    def _set_custom(self) -> None:
        if hasattr(self, "mode") and self.mode.currentData() != "custom":
            self.mode.blockSignals(True)
            self.mode.setCurrentIndex(self.mode.findData("custom"))
            self.mode.blockSignals(False)
            self.settings.setValue("mode", "custom")
            self._update_mode_info()

    def _update_mode_info(self) -> None:
        from .presets import PRESETS, resolve

        pid = self.mode.currentData()
        if pid == "custom":
            self.mode_info.setText(tr("Usando as escolhas feitas à mão abaixo."))
            return
        engine, _, _ = resolve(pid)
        text = PRESETS[pid].description
        if pid == "qualidade" and engine != "docling":
            text += tr(" — Docling não instalado (edição COMPLETA): usando o motor nativo com o OCR mais preciso nas páginas escaneadas.")
        self.mode_info.setText(text)

    def _mode_selected(self) -> None:
        from .engines import ENGINES
        from .presets import resolve

        pid = self.mode.currentData()
        self.settings.setValue("mode", pid)
        if pid != "custom":
            engine, per_engine, images = resolve(pid)
            for eid, opts in per_engine.items():
                for k, v in opts.items():
                    self.settings.setValue(f"opt/{eid}/{k}", v)
            self._applying_mode = True
            target = engine if engine in ENGINES and pid == "qualidade" else AUTO
            self.engine.setCurrentIndex(max(0, self.engine.findData(target)))
            self._build_options()
            self._applying_mode = False
            if images:
                self.images.setCurrentIndex(max(0, self.images.findData(images)))
        self._update_mode_info()
        self.engine_changed.emit()
        self.reconvert_needed.emit()

    def _build_options(self) -> None:
        while self.opt_form.rowCount():
            self.opt_form.removeRow(0)
        self._opt_widgets.clear()
        eid = self.engine_id()
        if eid == AUTO:
            avail = [e.name for e in ENGINES.values() if e.available()[0]]
            self.engine_info.setText(
                tr("Escolhe sozinho o melhor motor instalado para cada tipo de arquivo (sem IA por padrão, "
                "que é mais rápido). Instalados: ") + ", ".join(avail) + ".")
            return
        eng = ENGINES[eid]
        ok, why = eng.available()
        info = eng.description
        info += tr('\n✔ {0}').format(why) if ok else tr('\n✖ {0}\nInstalar: {1}').format(why, eng.install_hint)
        self.engine_info.setText(info)
        for opt in eng.options:
            key = f"opt/{eid}/{opt.key}"
            if opt.kind == "bool":
                w = QCheckBox(opt.label)
                w.setChecked(self.settings.value(key, opt.default, type=bool))
                w.toggled.connect(lambda v, k=key: (self.settings.setValue(k, v), self._set_custom(),
                                                    self.reconvert_needed.emit()))
                self.opt_form.addRow(w)
            elif opt.kind == "choice":
                w = QComboBox()
                for val, lbl in opt.choices:
                    w.addItem(lbl, val)
                w.setCurrentIndex(max(0, w.findData(self.settings.value(key, opt.default))))
                w.currentIndexChanged.connect(lambda _i, k=key, cw=w: (self.settings.setValue(k, cw.currentData()),
                                                                       self._set_custom(),
                                                                       self.reconvert_needed.emit()))
                self.opt_form.addRow(opt.label + ":", w)
            elif opt.kind == "int":
                w = QSpinBox()
                w.setRange(0, 40)
                w.setSuffix(" %")
                w.setValue(int(self.settings.value(key, opt.default) or 0))
                w.valueChanged.connect(lambda v, k=key: (self.settings.setValue(k, v), self.reconvert_needed.emit()))
                self.opt_form.addRow(opt.label + ":", w)
            else:
                w = QLineEdit(str(self.settings.value(key, opt.default)))
                w.textChanged.connect(lambda v, k=key: (self.settings.setValue(k, v), self.reconvert_needed.emit()))
                self.opt_form.addRow(opt.label + ":", w)
            if opt.help:
                w.setToolTip(opt.help)
            w.setEnabled(ok)
            self._opt_widgets[opt.key] = w

    def set_simple(self, on: bool) -> None:
        """Modo simples: só a parte Principal; as opções avançadas ficam escondidas."""
        self.engine_box.setVisible(not on)
        self.fix_box.setVisible(not on)
        self.adv_toggle.setVisible(not on)
        self.advanced.setVisible(not on and self.adv_toggle.isChecked())

    def _update_fix_summary(self, *_):
        on = sum(cb.isChecked() for cb in self.fix_checks.values())
        self.fix_summary.setText(tr('{0} de {1} correções ligadas').format(on, len(self.fix_checks)))

    def reload_output(self) -> None:
        """Relê as opções de saída salvas (ex.: depois do assistente inicial)."""
        for combo, key, default in ((self.images, "out/images", "folder"), (self.profile, "out/profile", "gfm")):
            combo.setCurrentIndex(max(0, combo.findData(self.settings.value(key, default))))
        self.frontmatter.setChecked(self.settings.value("out/frontmatter", False, type=bool))
        self.anon.setChecked(self.settings.value("anon/enabled", False, type=bool))

    def engine_options(self, eid: str | None = None) -> dict[str, Any]:
        eid = eid or self.engine_id()
        if eid == AUTO:
            # no modo automático, cada motor usa as opções salvas para ele
            return {}
        out = {}
        for opt in ENGINES[eid].options:
            key = f"opt/{eid}/{opt.key}"
            if opt.kind == "bool":
                out[opt.key] = self.settings.value(key, opt.default, type=bool)
            elif opt.kind == "int":
                out[opt.key] = int(self.settings.value(key, opt.default) or 0)
            else:
                out[opt.key] = self.settings.value(key, opt.default)
        return out

    def all_saved_options(self) -> dict[str, dict[str, Any]]:
        return {eid: self.engine_options(eid) for eid in ENGINES}

    # --- correção ---
    def fix_options(self) -> FixOptions | None:
        if not self.fix_box.isChecked():
            return None
        return FixOptions(**{k: cb.isChecked() for k, cb in self.fix_checks.items()})

    def _set_all_fix(self, value: bool) -> None:
        for cb in self.fix_checks.values():
            cb.blockSignals(True)
            cb.setChecked(value)
            cb.blockSignals(False)
        self._fix_toggled()

    # --- saída ---
    def output_options(self) -> OutputOptions:
        from .quick import anon_options

        return OutputOptions(images=self.images.currentData(), profile=self.profile.currentData(),
                             frontmatter=self.frontmatter.isChecked(), describe_images=self.describe.isChecked(),
                             ollama_model=self.ollama_model.currentText().strip(),
                             anon=anon_options(self.settings) if self.anon.isChecked() else None)

    def _anon_toggled(self, on: bool) -> None:
        """Na primeira vez, a pessoa precisa confirmar que leu o aviso de responsabilidade."""
        import os

        from .anonymize import DISCLAIMER, LIST_HELP

        if on and not self.settings.value("anon/ack", False, type=bool) and os.environ.get("MARKINHO_QUIET") != "1":
            box = QMessageBox(QMessageBox.Warning, "Anonimizar dados pessoais",
                              tr('<b>Antes de usar a anonimização, leia:</b><br><br>⚠ <b>{0}</b><br><br>A anonimização automática nunca é 100%: nomes sem pista (como “Rosa”) só são trocados se estiverem na sua lista.<br><br><b>Sua lista:</b> {1}').format(DISCLAIMER, LIST_HELP), parent=self)
            ok = box.addButton(tr("Li e entendi — anonimizar"), QMessageBox.AcceptRole)
            box.addButton(tr("Cancelar"), QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is not ok:
                self.anon.blockSignals(True)
                self.anon.setChecked(False)
                self.anon.blockSignals(False)
                self.anon_warn.setVisible(False)
                return
            self.settings.setValue("anon/ack", True)
        self.anon_warn.setVisible(on)

    def _anon_dialog(self) -> None:
        from .gui_tools import AnonDialog

        if AnonDialog(self, self.settings).exec() == QDialog.Accepted:
            if not self.anon.isChecked():
                self.anon.setChecked(True)          # já avisa a mudança
            else:
                self._output_toggled()

    def _output_toggled(self, *_):
        self.settings.setValue("out/images", self.images.currentData())
        self.settings.setValue("out/profile", self.profile.currentData())
        self.settings.setValue("out/frontmatter", self.frontmatter.isChecked())
        self.settings.setValue("anon/enabled", self.anon.isChecked())
        self.settings.setValue("out/describe", self.describe.isChecked())
        self.settings.setValue("out/ollama_model", self.ollama_model.currentText().strip())
        self._update_out_hint()
        self.output_changed.emit()

    def conflict(self) -> tuple[str, str, str] | None:
        """(mensagem, texto do botão, ação) quando duas opções de saída se anulam."""
        if self.describe.isChecked() and self.profile.currentData() == "llm":
            return (tr("⚠ <b>A descrição das imagens não vai aparecer:</b> o perfil “Texto para IA” remove as "
                    "imagens do resultado."), tr("Usar o perfil GitHub (GFM)"), "profile")
        if self.describe.isChecked() and self.images.currentData() == "none":
            return (tr("⚠ <b>A descrição das imagens não vai aparecer:</b> “Imagens: não incluir” descarta as "
                    "imagens antes de descrevê-las."), tr("Incluir as imagens (pasta ao lado do .md)"), "images")
        return None

    def _fix_conflict(self) -> None:
        c = self.conflict()
        if c and c[2] == "profile":
            self.profile.setCurrentIndex(max(0, self.profile.findData("gfm")))
        elif c and c[2] == "images":
            self.images.setCurrentIndex(max(0, self.images.findData("folder")))

    def _update_out_hint(self):
        notes = []
        if self.profile.currentData() == "llm" and not self.describe.isChecked():
            notes.append(tr("O perfil “Texto para IA” remove imagens e comentários para economizar tokens."))
        self.out_hint.setText(" ".join(notes))
        self.out_hint.setVisible(bool(notes))
        c = self.conflict()
        if hasattr(self, "conflict_box"):
            self.conflict_box.setVisible(c is not None)
            if c:
                self.conflict_label.setText(c[0])
                self.conflict_fix.setText(c[1])

    def _describe_toggled(self, on: bool) -> None:
        for w in (self.ollama_model, self.ollama_refresh_btn, self.ollama_label):
            w.setEnabled(on)
        self.reconvert_needed.emit()              # a descrição acontece durante a conversão
        if on:
            self._refresh_ollama()                 # procura sozinho, sem travar a janela
        else:
            self.ollama_status.clear()

    def _refresh_ollama(self):
        """Procura o Ollama em segundo plano (a janela não congela enquanto espera)."""
        self.ollama_refresh_btn.setEnabled(False)
        self.ollama_status.setText(tr("Procurando o Ollama neste computador…"))
        sig = self._ollama_sig

        class _Find(QRunnable):
            def run(self_inner):
                from .describe import list_models

                try:
                    sig.found.emit(list_models(), "")
                except Exception as exc:  # noqa: BLE001
                    sig.found.emit([], str(exc))

        QThreadPool.globalInstance().start(_Find())

    def _ollama_found(self, models: list, _error: str) -> None:
        from .describe import VISION_HINTS

        self.ollama_refresh_btn.setEnabled(self.describe.isChecked())
        cur = self.ollama_model.currentText()
        vis = [m for m in models if any(h in m.lower() for h in VISION_HINTS)]
        self.ollama_model.blockSignals(True)
        self.ollama_model.clear()
        for m in vis + [m for m in models if m not in vis]:
            self.ollama_model.addItem(m)
        if cur and (cur in models or not models):
            self.ollama_model.setCurrentText(cur)
        self.ollama_model.blockSignals(False)
        how = ("<code>ollama pull qwen2.5vl:3b</code>")
        if not models:
            self.ollama_model.lineEdit().setPlaceholderText(tr("nenhum modelo encontrado"))
            self.ollama_status.setText(
                tr("⚠ <b>O Ollama não foi encontrado neste computador.</b> A descrição de imagens precisa dele — é um programa gratuito que roda a IA aqui mesmo, sem internet. Para usar: 1) instale em <a href='https://ollama.com/download'>ollama.com</a>; 2) abra o Ollama; 3) no Prompt de Comando, baixe um modelo de visão: {0}; 4) clique em ↻. Sem o Ollama, as imagens ficam sem descrição (o resto da conversão funciona normalmente).").format(how))
        elif not vis:
            self.ollama_status.setText(tr('⚠ O Ollama está aberto, mas não há modelo de visão. No Prompt de Comando: {0} e depois clique em ↻.').format(how))
        else:
            self.ollama_status.setText(tr('✓ Ollama encontrado: {0} modelo(s) de visão.').format(len(vis)))

    def _fix_toggled(self, *_):
        self.settings.setValue("fix/enabled", self.fix_box.isChecked())
        for k, cb in self.fix_checks.items():
            self.settings.setValue(f"fix/{k}", cb.isChecked())
        self.fix_changed.emit()


# --------------------------------------------------------------------------- #
# Nomes dos arquivos de saída (padrão + prévia)
# --------------------------------------------------------------------------- #
class NamingWidget(QGroupBox):
    """Padrão de nome dos arquivos gerados, com prévia ao vivo."""

    def __init__(self, settings: QSettings, contexts: list, show_ext: bool = True, ext: str = ".md"):
        from .naming import CONFLICTS, EXTENSIONS, PRESETS, TOKENS

        super().__init__(tr("Nomes dos arquivos"))
        self.settings, self.contexts, self.fixed_ext, self.target_dir = settings, contexts, ext, None
        form = QFormLayout(self)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        row = QHBoxLayout()
        self.template = QLineEdit(settings.value("naming/template", "{nome}"))
        self.template.setToolTip(tr("Marcadores: ") + "  ".join("{" + t + "}" for t in TOKENS))
        self.presets = QComboBox()
        self.presets.addItem(tr("Modelos…"), "")
        for tpl, lbl in PRESETS:
            self.presets.addItem(f"{lbl}  —  {tpl}", tpl)
        self.presets.currentIndexChanged.connect(self._preset)
        row.addWidget(self.template, 1)
        row.addWidget(self.presets)
        form.addRow(tr("Padrão:"), row)
        tokens = QLabel(tr("{nome} nome original · {n} número na ordem da lista · {titulo} título do documento · "
                        "{data} data de hoje · {original} nome com extensão · {pasta} pasta de origem · "
                        "{motor} motor usado"))
        tokens.setWordWrap(True)
        tokens.setStyleSheet("color: palette(window-text); font-size: 12px;")
        form.addRow(tokens)
        nums = QHBoxLayout()
        self.start = QSpinBox()
        self.start.setRange(0, 999999)
        self.start.setValue(int(settings.value("naming/start", 1)))
        self.digits = QSpinBox()
        self.digits.setRange(1, 9)
        self.digits.setValue(int(settings.value("naming/digits", 3)))
        nums.addWidget(QLabel(tr("Começar em")))
        nums.addWidget(self.start)
        nums.addWidget(QLabel(tr("Dígitos")))
        nums.addWidget(self.digits)
        nums.addStretch()
        form.addRow(tr("Numeração {n}:"), nums)
        self.ext = QComboBox()
        for e in EXTENSIONS:
            self.ext.addItem(e, e)
        self.ext.setCurrentIndex(max(0, self.ext.findData(settings.value("naming/ext", ".md"))))
        self.ext_label = QLabel(tr("Extensão:"))
        form.addRow(self.ext_label, self.ext)
        self.ext.setVisible(show_ext)
        self.ext_label.setVisible(show_ext)
        self.safe = QCheckBox(tr("Nomes seguros: sem acentos nem espaços, em minúsculas (bom para indexação e servidores)"))
        self.safe.setChecked(settings.value("naming/safe", False, type=bool))
        form.addRow(self.safe)
        self.conflict = QComboBox()
        for val, lbl in CONFLICTS:
            self.conflict.addItem(lbl, val)
        self.conflict.setCurrentIndex(max(0, self.conflict.findData(settings.value("naming/conflict", "suffix"))))
        form.addRow(tr("Se já existir:"), self.conflict)
        self.error = QLabel()
        self.error.setStyleSheet("color: #c0392b;")
        form.addRow(self.error)
        self.preview = QListWidget()
        self.preview.setMinimumHeight(110)
        self.preview.setSelectionMode(QAbstractItemView.NoSelection)
        form.addRow(tr("Prévia:"), self.preview)
        for w in (self.template,):
            w.textChanged.connect(self.refresh)
        for w in (self.start, self.digits):
            w.valueChanged.connect(self.refresh)
        for w in (self.ext, self.conflict):
            w.currentIndexChanged.connect(self.refresh)
        self.safe.toggled.connect(self.refresh)
        self.refresh()

    def _preset(self):
        tpl = self.presets.currentData()
        if tpl:
            self.template.setText(tpl)
        self.presets.blockSignals(True)
        self.presets.setCurrentIndex(0)
        self.presets.blockSignals(False)

    def options(self):
        from .naming import NamingOptions

        return NamingOptions(self.template.text().strip() or "{nome}", self.ext.currentData() if self.ext.isVisible()
                             else self.fixed_ext, self.start.value(), self.digits.value(), self.safe.isChecked(),
                             self.conflict.currentData())

    def current_ext(self) -> str:
        return self.ext.currentData() if self.ext.isVisible() else self.fixed_ext

    def set_target(self, folder: str | None, ext: str | None = None):
        self.target_dir = Path(folder) if folder else None
        if ext:
            self.fixed_ext = ext
        self.refresh()

    def refresh(self, *_):
        from .naming import plan, validate

        err = validate(self.template.text())
        self.error.setText(f"⚠ {err}" if err else "")
        self.error.setVisible(bool(err))
        self.preview.clear()
        planned = plan(self.contexts, self.options(), self.target_dir, self.current_ext())
        marks = {"skip": tr("  (já existe: será pulado)"), "overwrite": tr("  (já existe: será substituído)")}
        for ctx, p in list(zip(self.contexts, planned))[:50]:
            self.preview.addItem(f"{ctx.original or ctx.stem}  →  {p.name}{marks.get(p.action, '')}")
        if len(self.contexts) > 50:
            self.preview.addItem(tr('… e mais {0}').format(len(self.contexts) - 50))

    def save(self):
        o = self.options()
        for k, v in (("template", o.template), ("start", o.start), ("digits", o.digits), ("safe", o.safe),
                     ("conflict", o.conflict)):
            self.settings.setValue(f"naming/{k}", v)
        if self.ext.isVisible():
            self.settings.setValue("naming/ext", o.ext)


def saved_naming(settings: QSettings):
    from .naming import NamingOptions

    return NamingOptions(settings.value("naming/template", "{nome}"), settings.value("naming/ext", ".md"),
                         int(settings.value("naming/start", 1)), int(settings.value("naming/digits", 3)),
                         settings.value("naming/safe", False, type=bool), settings.value("naming/conflict", "suffix"))


class SaveAllDialog(QDialog):
    """Salvar um .md para cada documento numa pasta, com padrão de nomes."""

    def __init__(self, parent, settings: QSettings, contexts: list):
        super().__init__(parent)
        self.setWindowTitle(tr("Salvar todos como Markdown"))
        self.resize(640, 560)
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.folder = QLineEdit(recall_dir(settings, "save"))
        b = QPushButton(tr("Escolher…"))
        b.clicked.connect(self._pick)
        row.addWidget(QLabel(tr("Pasta de destino:")))
        row.addWidget(self.folder, 1)
        row.addWidget(b)
        lay.addLayout(row)
        self.naming = NamingWidget(settings, contexts, show_ext=True)
        self.naming.set_target(self.folder.text())
        self.folder.textChanged.connect(lambda t: self.naming.set_target(t))
        lay.addWidget(self.naming)
        note = QLabel(tr("As imagens de cada documento vão para a pasta <i>&lt;nome&gt;_assets</i>, acompanhando o "
                      "novo nome, e os links dentro do .md são corrigidos."))
        note.setWordWrap(True)
        note.setStyleSheet("color: palette(window-text); font-size: 12px;")
        lay.addWidget(note)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Save).setText(tr("Salvar"))
        bb.button(QDialogButtonBox.Cancel).setText(tr("Cancelar"))
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.settings = settings

    def _pick(self):
        f = QFileDialog.getExistingDirectory(self, tr("Pasta de destino"), self.folder.text() or recall_dir(self.settings))
        if f:
            self.folder.setText(f)

    def _accept(self):
        from .naming import validate

        if err := validate(self.naming.template.text()):
            QMessageBox.warning(self, tr("Nomes"), err)
            return
        if not self.folder.text().strip():
            return
        self.naming.save()
        self.settings.setValue("out_dir", self.folder.text())
        remember_dir(self.settings, self.folder.text(), "save")
        self.accept()


# --------------------------------------------------------------------------- #
# Diálogo de exportação (Markdown -> outros formatos)
# --------------------------------------------------------------------------- #
class ExportDialog(QDialog):
    def __init__(self, parent, settings: QSettings, n_current: int, n_all: int, contexts: list | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Exportar Markdown para outro formato"))
        self.contexts = contexts or []
        self.settings = settings
        lay = QVBoxLayout(self)
        form = QFormLayout()

        self.fmt = QComboBox()
        for f in available_formats():
            backs = format_backends(f)
            self.fmt.addItem(f"{f.label}   [{' / '.join('Pandoc' if b == 'pandoc' else tr('Nativo') for b in backs)}]", f.id)
        self.fmt.setCurrentIndex(max(0, self.fmt.findData(settings.value("export/fmt", "docx"))))
        form.addRow(tr("Formato:"), self.fmt)

        self.backend = QComboBox()
        form.addRow(tr("Exportador:"), self.backend)

        self.title = QLineEdit()
        self.title.setPlaceholderText(tr("(opcional) título do documento"))
        form.addRow(tr("Título:"), self.title)

        self.template = QComboBox()
        self.template.addItem(tr("Padrão"), "")
        self.template.addItem(tr("ABNT (trabalhos acadêmicos)"), "abnt")
        self.template.setItemData(1, tr("Times New Roman 12, margens 3/2 cm, espaçamento 1,5, recuo de parágrafo, "
                                     "citações longas recuadas, seções numeradas e número de página."),
                                  Qt.ToolTipRole)
        self.template.setCurrentIndex(max(0, self.template.findData(settings.value("export/template", ""))))
        self.template_label = QLabel(tr("Modelo do Word:"))
        form.addRow(self.template_label, self.template)
        self.toc = QCheckBox(tr("Incluir sumário"))
        self.numbers = QCheckBox(tr("Numerar seções"))
        form.addRow(self.toc)
        form.addRow(self.numbers)
        self.template.currentIndexChanged.connect(
            lambda _i: (self.numbers.setChecked(True) if self.template.currentData() == "abnt" else None,
                        self._update_visibility()))

        ref_row = QHBoxLayout()
        self.ref = QLineEdit(settings.value("export/ref", ""))
        self.ref.setPlaceholderText(tr("modelo .docx/.odt/.pptx com seus estilos (opcional)"))
        b = QPushButton("…")
        b.setFixedWidth(32)
        b.clicked.connect(self._pick_ref)
        ref_row.addWidget(self.ref)
        ref_row.addWidget(b)
        self.ref_label = QLabel(tr("Modelo de estilos:"))
        form.addRow(self.ref_label, ref_row)

        self.pdf_engine = QComboBox()
        for e in available_pdf_engines():
            self.pdf_engine.addItem(e, e)
        self.pdf_label = QLabel(tr("Motor de PDF:"))
        form.addRow(self.pdf_label, self.pdf_engine)
        lay.addLayout(form)

        # opções dos pedaços para RAG
        from .chunker import STRATEGIES

        self.chunk_box = QGroupBox(tr("Pedaços para RAG / IA"))
        cf = QFormLayout(self.chunk_box)
        self.chunk_by = QComboBox()
        for val, lbl in STRATEGIES:
            self.chunk_by.addItem(lbl, val)
        self.chunk_by.setCurrentIndex(max(0, self.chunk_by.findData(settings.value("export/chunk_by", "title"))))
        self.chunk_by.setToolTip(tr("“Por página” precisa das marcas de página (opção do motor Nativo para PDF); "
                                 "sem elas, divide por título."))
        cf.addRow(tr("Dividir:"), self.chunk_by)
        self.chunk_size = QSpinBox()
        self.chunk_size.setRange(200, 20000)
        self.chunk_size.setSingleStep(100)
        self.chunk_size.setSuffix(tr(" caracteres"))
        self.chunk_size.setValue(int(settings.value("export/chunk_size", 1500)))
        self.chunk_size.setToolTip(tr("Tamanho máximo de cada pedaço. 1500 caracteres ≈ 375 tokens."))
        cf.addRow(tr("Tamanho máximo:"), self.chunk_size)
        self.chunk_overlap = QSpinBox()
        self.chunk_overlap.setRange(0, 5000)
        self.chunk_overlap.setSingleStep(50)
        self.chunk_overlap.setSuffix(tr(" caracteres"))
        self.chunk_overlap.setValue(int(settings.value("export/chunk_overlap", 150)))
        self.chunk_overlap.setToolTip(tr("Quanto do fim de um pedaço é repetido no início do seguinte, "
                                      "quando um texto longo é dividido."))
        cf.addRow(tr("Sobreposição:"), self.chunk_overlap)
        self.chunk_headings = QCheckBox(tr("Repetir o caminho de títulos em cada pedaço"))
        self.chunk_headings.setChecked(settings.value("export/chunk_headings", True, type=bool))
        cf.addRow(self.chunk_headings)
        lay.addWidget(self.chunk_box)

        scope = QGroupBox(tr("O que exportar"))
        sl = QVBoxLayout(scope)
        self.scope = QButtonGroup(self)
        for i, (txt, enabled) in enumerate([
            (tr("Documento atual"), n_current > 0),
            (tr('Todos os documentos — um arquivo para cada ({0})').format(n_all), n_all > 0),
            (tr('Todos juntos em um único arquivo ({0})').format(n_all), n_all > 1),
        ]):
            rb = QRadioButton(txt)
            rb.setEnabled(enabled)
            self.scope.addButton(rb, i)
            sl.addWidget(rb)
        first = next((b for b in self.scope.buttons() if b.isEnabled()), None)
        if first:
            first.setChecked(True)
        lay.addWidget(scope)
        self.naming = NamingWidget(settings, self.contexts, show_ext=False)
        lay.addWidget(self.naming)
        self.scope.idToggled.connect(lambda *_: self._update_visibility())

        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setStyleSheet("color: palette(window-text); font-size: 12px;")
        lay.addWidget(self.note)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(tr("Exportar…"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.fmt.currentIndexChanged.connect(self._fmt_changed)
        self.backend.currentIndexChanged.connect(self._update_visibility)
        self._fmt_changed()

    def _pick_ref(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("Modelo de estilos"), recall_dir(self.settings, "ref"),
                                           tr("Documentos (*.docx *.odt *.pptx)"))
        if f:
            remember_dir(self.settings, f, "ref")
        if f:
            self.ref.setText(f)

    def _fmt_changed(self):
        fid = self.fmt.currentData()
        self.backend.blockSignals(True)
        self.backend.clear()
        for b in format_backends(FORMATS_BY_ID[fid]):
            self.backend.addItem(tr("Pandoc") if b == "pandoc" else tr("Nativo (sem Pandoc)"), b)
        self.backend.blockSignals(False)
        self._update_visibility()

    def _update_visibility(self):
        fid = self.fmt.currentData()
        be = self.backend.currentData()
        pandoc = be == "pandoc"
        self.ref.setEnabled(fid in ("docx", "odt", "pptx") and (pandoc or fid == "docx"))
        self.ref_label.setEnabled(self.ref.isEnabled())
        show_pdf = fid == "pdf" and pandoc
        self.pdf_engine.setVisible(show_pdf)
        self.pdf_label.setVisible(show_pdf)
        is_docx = fid == "docx"
        self.template.setVisible(is_docx)
        self.template_label.setVisible(is_docx)
        abnt = is_docx and self.template.currentData() == "abnt"
        self.numbers.setEnabled(pandoc or abnt)
        is_chunks = fid.startswith("chunks_")
        is_tables = fid in ("xlsx", "csv")
        if hasattr(self, "naming"):
            self.naming.setVisible(self.scope.checkedId() == 1)
            self.naming.set_target(None, FORMATS_BY_ID[fid].ext)
        self.chunk_box.setVisible(is_chunks)
        self.title.setEnabled(not is_chunks and not is_tables)
        self.toc.setEnabled(not is_chunks and not is_tables)
        if is_chunks or is_tables:
            self.numbers.setEnabled(False)
        notes = {
            ("chunks_jsonl", "native"): tr("Um pedaço por linha (JSON Lines), com títulos, página e origem — "
                                        "pronto para bancos vetoriais (LangChain, LlamaIndex, Chroma…)."),
            ("chunks_json", "native"): tr("Um único JSON com os metadados do documento e a lista de pedaços."),
            ("pdf", "native"): tr("PDF gerado pelo motor de texto do Qt — não precisa de LaTeX."),
            ("pptx", "pandoc"): tr("Cada título de nível 1/2 vira um slide."),
            ("xlsx", "native"): tr("Só as tabelas do documento: uma aba por tabela e uma aba “Índice” com o título e a "
                                "página de cada uma. Números viram números (dá para somar); células mescladas continuam "
                                "mescladas."),
            ("csv", "native"): tr("Só as tabelas do documento, separadas por “;” (abre direto no Excel). Com várias "
                               "tabelas, elas vêm uma depois da outra, cada uma com o seu título."),
        }
        self.note.setText(notes.get((fid, be), ""))

    def values(self) -> tuple[str, str, dict, int]:
        fid = self.fmt.currentData()
        self.settings.setValue("export/fmt", fid)
        self.settings.setValue("export/ref", self.ref.text())
        opts = {"title": self.title.text().strip(), "toc": self.toc.isChecked(),
                "number_sections": self.numbers.isChecked() and self.numbers.isEnabled(),
                "pdf_engine": self.pdf_engine.currentData() or ""}
        if self.ref.isEnabled() and self.ref.text().strip():
            opts["reference_doc"] = self.ref.text().strip()
        if fid == "docx" and self.template.currentData():
            opts["template"] = self.template.currentData()
        self.settings.setValue("export/template", self.template.currentData() or "")
        if self.scope.checkedId() == 1:
            self.naming.save()
        if fid.startswith("chunks_"):
            opts.update(chunk_by=self.chunk_by.currentData(), chunk_size=self.chunk_size.value(),
                        chunk_overlap=self.chunk_overlap.value(), chunk_headings=self.chunk_headings.isChecked())
            for k in ("chunk_by", "chunk_size", "chunk_overlap", "chunk_headings"):
                self.settings.setValue(f"export/{k}", opts[k])
        return fid, self.backend.currentData(), opts, self.scope.checkedId()


# --------------------------------------------------------------------------- #
# Diálogo "Motores"
# --------------------------------------------------------------------------- #
class _ModelSignals(QObject):
    done = Signal(str, str)     # nome, mensagem


class _ModelTask(QRunnable):
    def __init__(self, which: str):
        super().__init__()
        self.which = which
        self.signals = _ModelSignals()

    def run(self):
        from .models import download_models

        try:
            target = download_models(self.which, progress=lambda *_: None)
            self.signals.done.emit(self.which, tr('Modelos baixados em {0}').format(target))
        except Exception as exc:  # noqa: BLE001
            self.signals.done.emit(self.which, tr('Erro: {0}').format(exc))


class EnginesDialog(QDialog):
    """Lista os motores e deixa escolher qual usar (botão “Usar”)."""

    def __init__(self, parent):
        super().__init__(parent)
        from . import ocr
        from .edition import EDITIONS, current
        from .models import models_dir, status

        self.setWindowTitle(tr("Motores de conversão"))
        self.resize(900, 560)
        self.main = parent
        lay = QVBoxLayout(self)
        ed = current()
        if ed is not None:
            nxt = {"padrao": EDITIONS["completa"]}.get(ed.id)
            more = ""
            if nxt is not None:
                extra_feats = [f for f in nxt.features if f not in ed.features]
                more = (tr('<br><b>A edição {0} acrescenta:</b> ').format(nxt.name) + "; ".join(html.escape(f) for f in extra_feats)
                        + tr(". Basta instalá-la por cima desta."))
            head = QLabel(tr('<b>Sua edição: {0}</b> — {1}{2}').format(ed.name, html.escape(ed.summary), more))
            head.setWordWrap(True)
            lay.addWidget(head)
        how = QLabel(tr("<b>Escolha o motor:</b> clique em <b>Usar</b> na linha desejada. <b>Automático</b> escolhe "
                     "sozinho o melhor para cada tipo de arquivo (recomendado). A escolha também fica no painel "
                     "Configurações › Motor de conversão."))
        how.setWordWrap(True)
        lay.addWidget(how)
        rows = [(AUTO, tr("Automático (recomendado)"), tr("Escolhe o melhor motor instalado para cada arquivo."), True, "")]
        for eng in ENGINES.values():
            ok, why = eng.available()
            desc = eng.description.split(". ")[0].rstrip(".") + "."
            rows.append((eng.id, eng.name, desc, ok, "" if ok else why))
        t = QTableWidget(len(rows), 4)
        t.setHorizontalHeaderLabels(["", tr("Motor"), tr("O que faz"), tr("Licença / situação")])
        t.verticalHeader().setVisible(False)
        self.use_btns: dict[str, QPushButton] = {}
        for r, (eid, name, desc, ok, why) in enumerate(rows):
            if ok:
                b = QPushButton(tr("Usar"))
                b.clicked.connect(lambda _c=False, e=eid: self._use(e))
                t.setCellWidget(r, 0, b)
                self.use_btns[eid] = b
            name_it = QTableWidgetItem(name)
            f = name_it.font()
            f.setBold(True)
            name_it.setFont(f)
            t.setItem(r, 1, name_it)
            d = QTableWidgetItem(desc)
            if eid != AUTO and ok:
                d.setToolTip(tr("Formatos de entrada: ") + " ".join(sorted(ENGINES[eid].extensions())))
            t.setItem(r, 2, d)
            lic = "" if eid == AUTO else (ENGINES[eid].license or "—")
            t.setItem(r, 3, QTableWidgetItem(lic if ok else f"{lic} — {why}"))
        t.resizeColumnsToContents()
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(2, QHeaderView.Stretch)          # descrição ocupa o espaço que sobra
        hh.setSectionResizeMode(3, QHeaderView.Interactive)
        t.setColumnWidth(3, 230)
        t.setWordWrap(True)
        t.resizeRowsToContents()
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.NoSelection)
        lay.addWidget(t)
        self._refresh_use()
        pdfs = available_pdf_engines()
        lines = [f"<b>OCR</b>: {html.escape(ocr.describe_status())}",
                 tr("<b>Exportação</b>: {0} formatos. Pandoc: {1}.").format(len(available_formats()), pandoc_version() or tr("não incluído"))
                 + (tr(' Motores de PDF: {0}.').format(', '.join(pdfs)) if pdfs else "")]
        ai = [w for w in ("docling", "marker") if ENGINES[w].available()[0]]
        if ai:
            st = status()
            lines.append(tr('<b>Modelos de IA</b> (pasta: {0}): ').format(html.escape(str(models_dir())))
                         + "; ".join(f"{w.capitalize()} — {html.escape(st[w])}" for w in ai)
                         + tr(". Para usar <b>sem internet</b>, baixe-os aqui uma vez."))
        extra = QLabel("<br>".join(lines))
        extra.setWordWrap(True)
        extra.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(extra)
        row = QHBoxLayout()
        self.btns = {}
        for which in ai:                       # só aparece o que dá para usar nesta edição
            b = QPushButton(tr('Baixar modelos do {0}').format(which.capitalize()))
            b.clicked.connect(lambda _c=False, w=which: self._download(w))
            row.addWidget(b)
            self.btns[which] = b
        row.addStretch()
        lay.addLayout(row)
        self.msg = QLabel()
        self.msg.setWordWrap(True)
        lay.addWidget(self.msg)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText(tr("Fechar"))
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._task = None

    def _current_engine(self) -> str:
        panel = getattr(self.main, "panel", None)
        return panel.engine_id() if panel is not None else AUTO

    def _refresh_use(self) -> None:
        cur = self._current_engine()
        for eid, b in self.use_btns.items():
            b.setText(tr("✓ Em uso") if eid == cur else tr("Usar"))
            f = b.font()
            f.setBold(eid == cur)                 # destacado em negrito (desativado ficaria cinza e ilegível)
            b.setFont(f)

    def _use(self, eid: str) -> None:
        panel = getattr(self.main, "panel", None)
        if panel is None or eid == self._current_engine():
            return
        panel.engine.setCurrentIndex(max(0, panel.engine.findData(eid)))
        self._refresh_use()
        name = tr("Automático") if eid == AUTO else ENGINES[eid].name
        self.msg.setText(tr('Motor escolhido: <b>{0}</b>. Vale para as próximas conversões; use “Reconverter” para aplicar aos arquivos já convertidos.').format(html.escape(name)))

    def _download(self, which: str):
        self.btns[which].setEnabled(False)
        self.msg.setText(tr('Baixando modelos do {0}… isso pode levar vários minutos.').format(which.capitalize()))
        self._task = _ModelTask(which)
        self._task.setAutoDelete(False)
        self._task.signals.done.connect(self._downloaded)
        QThreadPool.globalInstance().start(self._task)

    def _downloaded(self, which: str, message: str):
        if which in self.btns:
            self.btns[which].setEnabled(True)
        self.msg.setText(message)


# --------------------------------------------------------------------------- #
# Diálogo "Assistentes de IA" (servidor MCP local)
# --------------------------------------------------------------------------- #
class McpDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        from . import mcp_server as ms

        self.ms = ms
        self.setWindowTitle(tr("Assistentes de IA (MCP)"))
        self.resize(720, 560)
        lay = QVBoxLayout(self)
        intro = QLabel(
            tr("Deixe assistentes de IA como <b>Claude Desktop</b>, <b>Cursor</b> e <b>VS Code</b> converterem "
            "documentos usando o Markinho instalado. <b>Tudo roda no seu computador</b>: o assistente pede a "
            "conversão e o Markinho devolve o Markdown.<br><br>"
            "Por segurança, o assistente <b>só lê arquivos dentro das pastas abaixo</b>."))
        intro.setWordWrap(True)
        lay.addWidget(intro)

        box = QGroupBox(tr("Pastas autorizadas"))
        bl = QVBoxLayout(box)
        self.folders = QListWidget()
        cfg = ms.load_config()
        for f in cfg.get("folders", []):
            self.folders.addItem(f)
        bl.addWidget(self.folders)
        row = QHBoxLayout()
        b_add = QPushButton(tr("Adicionar pasta…"))
        b_add.clicked.connect(self._add)
        b_rem = QPushButton(tr("Remover"))
        b_rem.clicked.connect(lambda: [self.folders.takeItem(self.folders.row(i)) for i in self.folders.selectedItems()])
        row.addWidget(b_add)
        row.addWidget(b_rem)
        row.addStretch()
        bl.addLayout(row)
        self.allow_write = QCheckBox(tr("Permitir que o assistente salve arquivos nessas pastas (.md, DOCX, PDF…)"))
        self.allow_write.setToolTip(tr("Sem isso, o assistente só lê e converte. Arquivos existentes nunca são "
                                    "substituídos sem um pedido explícito."))
        self.allow_write.setChecked(bool(cfg.get("allow_write")))
        bl.addWidget(self.allow_write)
        lay.addWidget(box)

        cbox = QGroupBox(tr("Conectar a um assistente"))
        cl = QVBoxLayout(cbox)
        b_claude = QPushButton(tr("Configurar no Claude Desktop"))
        b_claude.clicked.connect(self._install_claude)
        b_copy = QPushButton(tr("Copiar configuração (Claude Desktop / Cursor)"))
        b_copy.clicked.connect(lambda: self._copy("claude"))
        b_vscode = QPushButton(tr("Copiar configuração (VS Code)"))
        b_vscode.clicked.connect(lambda: self._copy("vscode"))
        b_skill = QPushButton(tr("Instalar skill no Claude Code (usar o Markinho pelo terminal)"))
        b_skill.setToolTip(tr("Ensina o Claude Code (e outros assistentes que leem skills) a chamar o Markinho "
                              "sozinho: converter, extrair tabelas, gerar pedaços para IA, anonimizar. Não precisa "
                              "configurar servidor."))
        b_skill.clicked.connect(self._install_skill)
        for b in (b_claude, b_copy, b_vscode, b_skill):
            cl.addWidget(b)
        cmd, args = ms.server_command()
        how = QLabel(tr('Comando do servidor: <code>{0} {1}</code><br>No Cursor, cole a configuração em <code>.cursor/mcp.json</code>; no VS Code, em <code>.vscode/mcp.json</code>. Depois de configurar, reinicie o assistente.').format(html.escape(cmd), html.escape(' '.join(args))))
        how.setWordWrap(True)
        how.setTextInteractionFlags(Qt.TextSelectableByMouse)
        how.setStyleSheet("color: palette(window-text); font-size: 12px;")
        cl.addWidget(how)
        lay.addWidget(cbox)

        self.msg = QLabel()
        self.msg.setWordWrap(True)
        lay.addWidget(self.msg)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Save).setText(tr("Salvar"))
        bb.button(QDialogButtonBox.Close).setText(tr("Fechar"))
        bb.accepted.connect(self._save_and_close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        try:
            import mcp  # noqa: F401
        except ImportError:
            self.msg.setText(tr("⚠ O pacote do MCP não está instalado (pip install mcp). A configuração é salva, "
                             "mas o servidor não vai iniciar."))

    def _install_skill(self) -> None:
        from .agent_skill import install

        try:
            path = install()
        except OSError as exc:
            self.msg.setText(tr("Não foi possível salvar:\n{0}").format(exc))
            return
        self.msg.setText(tr("✔ Skill instalada em {0}. <b>Abra o Claude Code de novo</b> e peça, por exemplo: "
                            "“converta o relatorio.pdf com o Markinho e extraia as tabelas”.").format(html.escape(str(path))))

    def _add(self):
        f = QFileDialog.getExistingDirectory(self, tr("Pasta que o assistente pode usar"),
                                             recall_dir(QSettings("Markinho", "Markinho")))
        if f:
            remember_dir(QSettings("Markinho", "Markinho"), f)
        if f and not self.folders.findItems(f, Qt.MatchExactly):
            if Path(f).resolve() == Path.home().resolve() or len(Path(f).resolve().parts) <= 1:
                if QMessageBox.question(self, tr("Pasta ampla"), tr("Autorizar a pasta inteira do usuário (ou a raiz) dá "
                                        "ao assistente acesso a todos os seus arquivos. Continuar?")) != QMessageBox.Yes:
                    return
            self.folders.addItem(f)

    def _save(self) -> list[str]:
        folders = [self.folders.item(i).text() for i in range(self.folders.count())]
        self.ms.save_config(folders, self.allow_write.isChecked())
        return folders

    def _save_and_close(self):
        self._save()
        self.accept()

    def _install_claude(self):
        if not self._save():
            QMessageBox.warning(self, tr("Assistentes de IA"), tr("Adicione ao menos uma pasta autorizada antes."))
            return
        try:
            path = self.ms.install_claude_desktop()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, tr("Claude Desktop"), str(exc))
            return
        self.msg.setText(tr('✔ Configurado em {0}. <b>Feche e abra o Claude Desktop</b> para ativar. Pergunte, por exemplo: “Liste os documentos que o Markinho pode ler”.').format(html.escape(str(path))))

    def _copy(self, kind: str):
        import json as _json

        self._save()
        QGuiApplication.clipboard().setText(_json.dumps(self.ms.client_config(kind), indent=2, ensure_ascii=False))
        self.msg.setText(tr("✔ Configuração copiada para a área de transferência."))


# --------------------------------------------------------------------------- #
# Sobre: créditos e licenças
# --------------------------------------------------------------------------- #
class AboutDialog(QDialog):
    def __init__(self, parent, tab: int = 0):
        from .credits import DISCLAIMER, INSPIRED_BY, included_here, license_files
        from .edition import label as edition_label

        super().__init__(parent)
        self.setWindowTitle(tr("Sobre o Markinho"))
        self.resize(820, 640)
        lay = QVBoxLayout(self)
        tabs = QTabWidget()
        lay.addWidget(tabs)

        # --- Sobre ---
        about = QTextBrowser()
        about.setOpenExternalLinks(True)
        ip = icon_path()
        logo = f'<img src="{ip.as_uri()}" width="96" height="96">' if ip else ""
        engines = ", ".join(e.name for e in ENGINES.values() if e.available()[0])
        about.setHtml(
            tr('<table><tr><td>{0}</td><td style="padding-left:16px"><h1 style="margin:0">Markinho</h1><h3 style="margin:2px 0 8px 0;color:gray">Conversor Markdown</h3>Versão {1} · edição {2}</td></tr></table><p>Converte documentos <b>para Markdown</b> (PDF, Word, Excel, PowerPoint, OpenDocument, HTML, EPUB, imagens com OCR, Office antigo…) e Markdown <b>para outros formatos</b>. <b>Tudo roda no seu computador</b>: nenhum documento é enviado para a internet.</p><p><b>Motores disponíveis:</b> {3}<br><b>Formatos de exportação:</b> {4}</p><p><a href="https://github.com/dontstopbelieve/markinho">github.com/dontstopbelieve/markinho</a></p><p><b>Software livre e gratuito</b>, sob a licença GNU AGPL-3.0, fornecido “como está”, sem garantia de qualquer tipo. Projeto pessoal, sem garantia de atualizações ou suporte. Copyright © 2026 dontstopbelieve.</p><p>Feito com a ajuda de muitos projetos de código aberto — veja a aba <b>Créditos</b>. Obrigado a todos os desenvolvedores e desenvolvedoras!</p><p style="color:gray;font-size:small">{5}</p>').format(logo, __version__, html.escape(edition_label()), html.escape(engines), len(available_formats()), html.escape(DISCLAIMER)))
        tabs.addTab(about, tr("Sobre"))

        # --- Créditos ---
        cred = QTextBrowser()
        cred.setOpenExternalLinks(True)
        rows = []
        for c, here in included_here():
            mark = "✔" if here else "—"
            rows.append(f'<tr><td>{mark}</td><td><a href="{c.url}">{html.escape(c.name)}</a></td>'
                        f"<td>{html.escape(c.author)}</td><td>{html.escape(c.license)}</td>"
                        f"<td>{html.escape(c.role)}</td></tr>")
        insp = "".join(f'<tr><td><a href="{c.url}">{html.escape(c.name)}</a></td><td>{html.escape(c.author)}</td>'
                       f"<td>{html.escape(c.role)}</td></tr>" for c in INSPIRED_BY)
        cred.setHtml(
            tr("<h3>Obrigado!</h3><p>O Markinho existe graças ao trabalho generoso destas pessoas e projetos.</p>"
            "<h4>Componentes incluídos</h4>"
            "<p style='color:gray'>✔ = presente nesta edição. Usados conforme suas licenças (textos na aba "
            "<b>Licenças</b>).</p>"
            "<table cellspacing='0' cellpadding='4' border='1' style='border-collapse:collapse'>"
            "<tr><th></th><th>Projeto</th><th>Autores</th><th>Licença</th><th>Para quê</th></tr>")
            + "".join(rows) + tr("</table>"
            "<h4>Projetos que inspiraram ideias</h4>"
            "<p style='color:gray'>Ideias e funcionalidades que estudamos; o código do Markinho foi escrito do zero, "
            "sem copiar código destes projetos.</p>"
            "<table cellspacing='0' cellpadding='4' border='1' style='border-collapse:collapse'>"
            "<tr><th>Projeto</th><th>Autores</th><th>Ideia</th></tr>") + insp + "</table>"
            f'<p style="color:gray;font-size:small">{html.escape(DISCLAIMER)}</p>')
        tabs.addTab(cred, tr("Créditos"))

        # --- Licenças (textos completos) ---
        lic = QWidget()
        ll = QHBoxLayout(lic)
        self._files = license_files()
        self._list = QListWidget()
        for comp, rel, _text in self._files:
            self._list.addItem(f"{comp} — {Path(rel).name}")
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._list.currentRowChanged.connect(
            lambda i: self._text.setPlainText(self._files[i][2] if 0 <= i < len(self._files) else ""))
        split = QSplitter()
        split.addWidget(self._list)
        split.addWidget(self._text)
        split.setSizes([260, 540])
        ll.addWidget(split)
        if self._files:
            self._list.setCurrentRow(0)
        tabs.addTab(lic, tr('Licenças ({0})').format(len(self._files)))
        tabs.setCurrentIndex(tab)

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText(tr("Fechar"))
        b_sup = bb.addButton(tr("Gostou? Apoie o Markinho ❤"), QDialogButtonBox.ActionRole)
        b_sup.clicked.connect(lambda: __import__("markinho.gui_tools", fromlist=["SupportDialog"])
                              .SupportDialog(self).exec())
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


# --------------------------------------------------------------------------- #
# Janela principal
# --------------------------------------------------------------------------- #
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        from .edition import current

        ed = current()
        self.setWindowTitle(tr('Markinho {0}{1} — Conversor Markdown').format(__version__, ' ' + ed.name if ed else ''))
        self.resize(1320, 800)
        self.settings = QSettings("Markinho", "Markinho")
        self.pool = QThreadPool.globalInstance()
        self.heavy_pool = QThreadPool(self)
        self.heavy_pool.setMaxThreadCount(1)   # modelos de IA: um arquivo por vez
        import os as _os

        self.pool = QThreadPool(self)          # conversões leves: limite definido pelo usuário
        self.pool.setMaxThreadCount(int(self.settings.value("queue/threads", min(4, _os.cpu_count() or 2))))
        self.entries: dict[str, Entry] = {}
        self._image_mode: dict[str, str] = {}   # “Ler esta imagem como…” escolhido por arquivo
        self.gen: dict[str, int] = {}
        self._tasks: dict[str, _ConvertTask] = {}
        self._loading = False
        self._build_ui()
        self._update_buttons()

    DEFAULT_MODE = "simple"          # modo da primeira abertura (os testes antigos usam o Completo)
    DEFAULT_AUTO_CONVERT = True        # “Converter ao adicionar” na primeira vez

    # ---------------- construção da interface ----------------
    def _build_ui(self) -> None:
        st = self.style()
        tb = QToolBar("Principal")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        def action(text, icon, slot, shortcut=None, tip=""):
            a = QAction(st.standardIcon(icon), text, self)
            a.triggered.connect(slot)
            if shortcut:
                a.setShortcut(shortcut)
            if tip:
                a.setToolTip(tip)
            tb.addAction(a)
            return a

        self.act_add = action(tr("Adicionar"), QStyle.SP_FileIcon, self.add_files_dialog, QKeySequence.Open,
                              tip=tr("Adicionar arquivos à fila (Ctrl+O) — também dá para arrastá-los para a janela. "
                                  "A setinha ao lado tem: adicionar uma pasta inteira e escrever do zero."))
        self.act_folder = QAction(st.standardIcon(QStyle.SP_DirIcon), tr("Adicionar pasta…"), self)
        self.act_folder.triggered.connect(self.add_folder_dialog)
        self.act_new = QAction(draw_icon("write"), tr("Escrever do zero (novo .md)"), self)
        self.act_new.setShortcut(QKeySequence.New)
        self.act_new.setToolTip(tr("Escrever ou colar Markdown para exportar a outro formato"))
        self.act_new.triggered.connect(self.new_document)
        self.addAction(self.act_new)
        from PySide6.QtWidgets import QMenu as _QMenu, QToolButton as _QToolButton

        add_menu = _QMenu(self)
        add_menu.addAction(st.standardIcon(QStyle.SP_FileIcon), tr("Adicionar arquivos…"), self.add_files_dialog)
        add_menu.addAction(self.act_folder)
        add_menu.addAction(self.act_new)
        add_btn_tb = tb.widgetForAction(self.act_add)
        if isinstance(add_btn_tb, _QToolButton):
            add_btn_tb.setMenu(add_menu)
            add_btn_tb.setPopupMode(_QToolButton.MenuButtonPopup)
        self.act_paste = action(tr("Colar"), QStyle.SP_DialogOpenButton, self.paste_as_markdown, tr("Ctrl+Shift+V"),
                                tip=tr("Colar e converter (Ctrl+Shift+V): texto de uma página da web, do Word ou de um "
                                    "e-mail vira Markdown; uma imagem copiada passa pelo OCR"))
        tb.addSeparator()
        self.act_convert = action(tr("Converter"), QStyle.SP_MediaPlay, lambda: self.convert_queue(False), "F5",
                                  tip=tr("Converter os arquivos da fila (F5). Com um arquivo já convertido (✔) "
                                      "selecionado, converte de novo — útil depois de mudar o modo ou as opções."))
        conv_sel = QAction(tr("Converter selecionados"), self)
        conv_sel.setShortcut("Shift+F5")
        conv_sel.triggered.connect(lambda: self.convert_queue(True))
        self.addAction(conv_sel)
        self.act_cancel = action(tr("Parar"), QStyle.SP_MediaStop, self.cancel_conversions, "Esc",
                                 tip=tr("Parar as conversões (Esc): as que estão em andamento param na próxima página "
                                     "e voltam para a fila"))
        self.act_auto = QCheckBox(tr("Converter ao adicionar"))
        # ligado por padrão: o arquivo converte assim que entra (como no modo Simples); dá para desligar
        self.act_auto.setChecked(self.settings.value("queue/auto", self.DEFAULT_AUTO_CONVERT, type=bool))
        self.act_auto.setToolTip(tr("Ligado: converte assim que o arquivo entra. Desligado: acumula na fila e "
                                 "converte quando você clicar em “Converter” (F5)."))
        self.act_auto.toggled.connect(lambda v: self.settings.setValue("queue/auto", v))
        tb.addSeparator()

        def menu_action(text, icon, slot, shortcut=None, tip=""):
            a = QAction(st.standardIcon(icon), text, self)    # fica nos menus (a barra já está cheia)
            a.triggered.connect(slot)
            if shortcut:
                a.setShortcut(shortcut)
            if tip:
                a.setToolTip(tip)
            self.addAction(a)
            return a

        self.act_remove = menu_action(tr("Remover da lista"), QStyle.SP_TrashIcon, self.remove_selected,
                                      QKeySequence.Delete)
        self.act_clear = menu_action(tr("Limpar a lista"), QStyle.SP_DialogResetButton, self.clear_all)
        self.act_copy = action(tr("Copiar"), QStyle.SP_DialogApplyButton, self.copy_current, tr("Ctrl+Shift+C"),
                               tip=tr("Copiar o Markdown do documento aberto (Ctrl+Shift+C)"))
        self.act_copy.setIcon(draw_icon("copy"))
        self.act_ai = action(tr("Para IA"), QStyle.SP_MessageBoxQuestion, self.copy_for_ai, tr("Ctrl+Alt+C"),
                             tip=tr("Copiar para IA: texto enxuto, contagem de tokens e divisão em partes para "
                                 "ChatGPT, Claude, Gemini…"))
        self.act_ai.setIcon(draw_icon("ai"))
        self.act_save = action(tr("Salvar .md"), QStyle.SP_DialogSaveButton, self.save_current, QKeySequence.Save,
                               tip=tr("Salvar o documento aberto como .md (Ctrl+S)"))
        self.act_save_all = action(tr("Salvar todos"), QStyle.SP_DriveHDIcon, self.save_all, tr("Ctrl+Shift+S"),
                                   tip=tr("Salvar um .md para cada documento numa pasta"))
        self.act_merge = menu_action(tr("Juntar todos em um .md…"), QStyle.SP_FileDialogDetailedView,
                                     self.save_merged, tip=tr("Juntar todos em um único .md"))
        tb.addSeparator()
        self.act_export = action(tr("Exportar…"), QStyle.SP_ArrowRight, self.export_dialog, tr("Ctrl+E"),
                                 tip=tr("Converter o Markdown para Word, PDF, HTML, ODT, EPUB, LaTeX… (Ctrl+E)"))
        self.act_export.setIcon(draw_icon("export"))
        self.act_convert.setIcon(draw_icon("convert"))
        self._toolbar = tb
        # botões principais em destaque (azul): “Converter” e, depois de converter, “Salvar”
        for a in (self.act_convert, self.act_save):
            w_ = tb.widgetForAction(a)
            if w_ is not None:
                w_.setObjectName("primaryButton")
        tb.setStyleSheet(
            "QToolButton#primaryButton:enabled { background: #1565C0; color: white; border-radius: 6px;"
            " padding: 3px 10px; font-weight: bold; }"
            "QToolButton#primaryButton:enabled:hover { background: #0D47A1; }")
        self._secondary = [self.act_paste, self.act_cancel, self.act_copy, self.act_ai, self.act_save_all]
        from PySide6.QtWidgets import QMenu, QToolButton

        tools = QMenu(self)
        tools.addAction(st.standardIcon(QStyle.SP_ComputerIcon), tr("Motores de conversão…"),
                        lambda: EnginesDialog(self).exec())
        a_mcp = tools.addAction(st.standardIcon(QStyle.SP_DriveNetIcon), tr("Assistentes de IA (MCP)…"),
                                lambda: McpDialog(self).exec())
        a_mcp.setToolTip(tr("Deixar Claude Desktop, Cursor ou VS Code converterem arquivos pelo Markinho"))
        tools.addSeparator()
        extra = [(tr("Pasta monitorada…"), self.watch_dialog), (tr("Dividir por títulos…"), self.split_current),
                 (tr("Exportar como skill para IA…"), self.skill_export),
                 (tr("Relatório do lote…"), self.batch_report)]
        tools.addAction(self.act_merge)
        for text, slot in extra:
            tools.addAction(text, slot)
        from . import winshell

        self.act_shell = QAction(tr("Botão direito do Windows (menu Markinho)"), self, checkable=True)
        self.act_shell.setToolTip(tr("Liga/desliga o menu “Markinho” ao clicar com o botão direito nos arquivos. "
                                  "Funciona também na versão ZIP, sem senha de administrador."))
        self.act_shell.setVisible(winshell.available())
        if winshell.available():
            self.act_shell.setChecked(winshell.is_registered())
        self.act_shell.toggled.connect(self._toggle_shell)
        tools.addAction(self.act_shell)
        tools.addAction(tr("Assistente inicial…"), self.first_run)
        tools.addSeparator()
        self._tools_menu = tools
        tools.addAction(st.standardIcon(QStyle.SP_MessageBoxInformation), tr("Sobre o Markinho"), self.about)
        # barra de menus: Ajuda > Sobre (no macOS, “Sobre” vai para o menu do app)
        help_menu = self.menuBar().addMenu(tr("Ajuda"))
        self._help_menu = help_menu
        a_about = help_menu.addAction(tr("Sobre o Markinho"), self.about)
        a_about.setMenuRole(QAction.AboutRole)
        help_menu.addAction(tr("Créditos"), lambda: self.about(1))
        help_menu.addAction(tr("Licenças de terceiros"), lambda: self.about(2))
        help_menu.addSeparator()
        help_menu.addAction(tr("Privacidade e relatório de erro"), self.privacy)
        help_menu.addAction(tr("Gerar relatório de erro…"), self.error_report)
        help_menu.addAction(tr("Página do projeto"), self.open_project_page)
        help_menu.addAction(tr("Procurar atualizações…"), self.check_updates)
        help_menu.addSeparator()
        help_menu.addAction(tr("Apoie o Markinho ❤…"), self.support)
        edit_menu = self.menuBar().addMenu(tr("Editar"))
        edit_menu.addAction(self.act_paste)
        edit_menu.addAction(self.act_copy)
        edit_menu.addAction(self.act_ai)
        edit_menu.addSeparator()
        edit_menu.addAction(self.act_remove)
        edit_menu.addAction(self.act_clear)
        self.menuBar().insertMenu(help_menu.menuAction(), edit_menu)
        tool_menu = self.menuBar().addMenu(tr("Ferramentas"))
        tool_menu.addAction(tr("Motores de conversão…"), lambda: EnginesDialog(self).exec())
        tool_menu.addAction(tr("Assistentes de IA (MCP)…"), lambda: McpDialog(self).exec())
        tool_menu.addAction(tr("Pacotes extras…"), self.open_packs)
        tool_menu.addSeparator()
        tool_menu.addAction(tr("Anonimizar um arquivo Markdown…"), self.anonymize_file)
        tool_menu.addAction(tr("Comparar duas versões…"), self.compare_versions)
        for text, slot in extra:
            tool_menu.addAction(text, slot)
        tool_menu.addSeparator()
        tool_menu.addAction(self.act_shell)
        tool_menu.addAction(tr("Assistente inicial…"), self.first_run)
        self.menuBar().insertMenu(help_menu.menuAction(), tool_menu)
        # menus Arquivo e Exibir (Arquivo é o primeiro, como em todo programa)
        file_menu = QMenu(tr("Arquivo"), self)
        a_addf = QAction(st.standardIcon(QStyle.SP_FileIcon), tr("Adicionar arquivos…"), self)
        a_addf.triggered.connect(self.add_files_dialog)
        file_menu.addAction(a_addf)
        file_menu.addAction(self.act_folder)
        file_menu.addAction(self.act_new)
        file_menu.addAction(self.act_paste)
        file_menu.addSeparator()
        file_menu.addAction(self.act_convert)
        file_menu.addAction(conv_sel)
        file_menu.addAction(self.act_cancel)
        file_menu.addSeparator()
        file_menu.addAction(self.act_save)
        file_menu.addAction(self.act_save_all)
        file_menu.addAction(self.act_merge)
        file_menu.addAction(self.act_export)
        file_menu.addSeparator()
        a_quit = QAction(tr("Sair"), self)
        a_quit.setShortcut(QKeySequence.Quit)
        a_quit.triggered.connect(self.close)
        a_quit.setMenuRole(QAction.QuitRole)
        file_menu.addAction(a_quit)
        self.menuBar().insertMenu(edit_menu.menuAction(), file_menu)
        self._view_menu = QMenu(tr("Exibir"), self)
        self.menuBar().insertMenu(tool_menu.menuAction(), self._view_menu)

        # ---- esquerda: arquivos ----
        self.list = FileList()
        self.list.files_dropped.connect(self.add_paths)
        self.list.order_changed.connect(lambda: self.statusBar().showMessage(
            tr("Ordem alterada — ela define a numeração dos nomes de saída."), 4000))
        for text, slot, key in ((tr("Converter selecionados"), lambda: self.convert_queue(True), None),
                                (tr("Converter de novo"), lambda: self.reconvert(False), None),
                                (tr("Renomear saída…"), self.rename_selected, "F2"),
                                (tr("Remover da lista"), self.remove_selected, None)):
            a = QAction(text, self.list)
            a.triggered.connect(slot)
            if key:
                a.setShortcut(key)
                a.setShortcutContext(Qt.WidgetWithChildrenShortcut)
            self.list.addAction(a)
        # imagens: “Ler esta imagem como…” (tabela, código, texto) — reconverte com essa escolha
        sep = QAction(self.list)
        sep.setSeparator(True)
        self.list.addAction(sep)
        for text, mode in ((tr("Ler esta imagem como tabela"), "table"), (tr("Ler esta imagem como código"), "code"),
                           (tr("Ler esta imagem como texto corrido"), "text"), (tr("Ler esta imagem automaticamente"), "auto")):
            a = QAction(text, self.list)
            a.triggered.connect(lambda _c=False, m=mode: self.read_image_as(m))
            self.list.addAction(a)
        self.list.itemDoubleClicked.connect(lambda _it: self.rename_selected())
        self.list.currentItemChanged.connect(self._show_item)
        self.list.itemSelectionChanged.connect(self._update_buttons)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(6, 6, 6, 6)
        head = QLabel(tr("<b>Arquivos</b> (arraste para reordenar · F2 renomeia)"))
        head.setWordWrap(True)                 # sem isso a coluna não encolhia
        lv.addWidget(head)
        lv.addWidget(self.list, 1)
        add_btn = QPushButton(tr("Adicionar arquivos…"))
        add_btn.clicked.connect(self.add_files_dialog)
        lv.addWidget(add_btn)
        lv.addWidget(self.act_auto)
        fmt = QLabel(tr('Lê {0} tipos de arquivo: PDF, Word, Excel, PowerPoint, páginas da web, e-books, fotos e escaneados…').format(len(all_input_extensions())))
        fmt.setWordWrap(True)
        fmt.setStyleSheet("color: palette(window-text); font-size: 12px;")
        lv.addWidget(fmt)

        # ---- centro: abas ----
        mono = QFont("Consolas" if sys.platform == "win32" else "Menlo" if sys.platform == "darwin" else "Monospace")
        mono.setStyleHint(QFont.Monospace)
        self.editor = QPlainTextEdit()
        self.editor.setFont(mono)
        self.editor.setPlaceholderText(tr("Para começar: arraste documentos para a janela ou clique em “Adicionar”. "
                                       "Depois clique em “Converter” — o texto aparece aqui, pronto para "
                                       "salvar, copiar ou exportar (você pode editá-lo antes)."))
        self.editor.textChanged.connect(self._editor_changed)
        self.editor.setAcceptDrops(False)       # arquivos soltos aqui vão para a fila, não para o texto
        self.preview = PreviewBrowser()
        self.preview.setOpenExternalLinks(True)
        self.fixes = QTextBrowser()
        self.fixes.setOpenLinks(False)
        self.fixes.anchorClicked.connect(self._fix_link)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.editor, tr("Markdown"))
        self.tabs.addTab(self.preview, tr("Visualização"))
        self.tabs.addTab(self.fixes, tr("Correções"))
        self.tabs.currentChanged.connect(lambda _: self._refresh_views())
        zoom_box = QWidget()
        zl = QHBoxLayout(zoom_box)
        zl.setContentsMargins(0, 0, 4, 0)
        for text, step, tip in (("A−", -1, tr("Diminuir o texto (Ctrl −)")), ("A+", 1, tr("Aumentar o texto (Ctrl +)"))):
            b = QPushButton(text)
            b.setObjectName("zoomBtn")
            b.setFixedWidth(34)
            b.setToolTip(tip + tr(" — também com Ctrl + rodinha do mouse"))
            b.clicked.connect(lambda _c=False, st=step: self.text_zoom(st))
            zl.addWidget(b)
        self.tabs.setCornerWidget(zoom_box, Qt.TopRightCorner)
        for keys, step in ((("Ctrl++", "Ctrl+="), 1), (("Ctrl+-",), -1), (("Ctrl+0",), 0)):
            for k in keys:
                a = QAction(self)
                a.setShortcut(k)
                a.triggered.connect(lambda _c=False, st=step: self.text_zoom(st))
                self.addAction(a)
        self._base_pt = {id(w): w.font().pointSizeF() for w in (self.editor, self.preview)}
        QTimer.singleShot(0, lambda: self.text_zoom(None))     # aplica o tamanho guardado
        # avisos da abertura: só com a janela na tela (nunca por trás nem depois de fechada)
        QTimer.singleShot(300, lambda: self.isVisible() and self.offer_resume())     # lote que não terminou
        QTimer.singleShot(2500, lambda: self.isVisible() and self.remind_updates())  # a cada 2 meses

        center = QWidget()
        cv = QVBoxLayout(center)
        cv.setContentsMargins(6, 6, 6, 6)
        top = QHBoxLayout()
        self.info = QLabel(tr("Nenhum arquivo selecionado"))
        self.info.setStyleSheet("color: palette(window-text);")
        self.info.setWordWrap(True)
        self.compare_btn = QPushButton(tr("Ver original ao lado"))
        self.compare_btn.setCheckable(True)
        self.compare_btn.setShortcut("Ctrl+D")
        self.compare_btn.setToolTip(tr("Mostra o arquivo original ao lado do texto convertido, para conferir (Ctrl+D). "
                                    "Em PDFs, as páginas acompanham a leitura: role o texto e o PDF vai junto "
                                    "(e vice-versa). Não é uma comparação palavra por palavra."))
        self.compare_btn.toggled.connect(self._toggle_compare)
        self.space_btn = QPushButton(tr("Mais espaço"))
        self.space_btn.setCheckable(True)
        self.space_btn.setToolTip(tr("Esconde a lista de arquivos e o painel de configurações enquanto confere"))
        self.space_btn.toggled.connect(self._toggle_space)
        self.space_btn.setVisible(False)
        self.follow_cb = QCheckBox(tr("Rolar junto"))
        self.follow_cb.setToolTip(tr("Ligado: rolar o texto leva o PDF à página do trecho que está no topo, e vice-versa. "
                                  "Ao ligar, os dois lados se alinham na hora (pela página, não pela posição da "
                                  "barra), mesmo que estejam desencontrados."))
        self.follow_cb.setChecked(self.settings.value("ui/follow", True, type=bool))
        self.follow_cb.toggled.connect(self._toggle_follow)
        self.follow_cb.setVisible(False)
        top.addWidget(self.info, 1)
        top.addWidget(self.follow_cb)
        top.addWidget(self.space_btn)
        top.addWidget(self.compare_btn)
        cv.addLayout(top)
        self.review = QLabel()
        self.review.setWordWrap(True)
        self.review.setTextFormat(Qt.RichText)
        self.review.setStyleSheet("background: rgba(241,196,15,0.18); border-radius: 4px; padding: 4px 8px;")
        self.review.linkActivated.connect(self._go_review_page)
        self.review.setVisible(False)
        cv.addWidget(self.review)
        # faixa “configurações mudaram: converter de novo?”
        from PySide6.QtWidgets import QFrame

        self.settings_bar = QFrame()
        self.settings_bar.setStyleSheet("QFrame{background: #dbeafe; border: 1px solid #7aa7e8; border-radius: 4px;}"
                                        "QLabel{color: #10243f; border: none; background: transparent;}")
        sb = QHBoxLayout(self.settings_bar)
        sb.setContentsMargins(8, 4, 8, 4)
        self.settings_bar_label = QLabel()
        self.settings_bar_label.setWordWrap(True)
        sb.addWidget(self.settings_bar_label, 1)
        self.btn_redo_one = QPushButton(tr("Converter de novo este arquivo"))
        self.btn_redo_one.clicked.connect(self._redo_current)
        self.btn_redo_all = QPushButton(tr("Todos"))
        self.btn_redo_all.clicked.connect(lambda: (self.settings_bar.setVisible(False), self.reconvert(True)))
        later = QPushButton(tr("Agora não"))
        later.clicked.connect(lambda: self.settings_bar.setVisible(False))
        for b in (self.btn_redo_one, self.btn_redo_all, later):
            sb.addWidget(b)
        self.settings_bar.setVisible(False)
        cv.addWidget(self.settings_bar)
        self.original = FileViewer()
        self.original.setMinimumWidth(220)
        self.tabs.setMinimumWidth(220)
        self.original.setVisible(False)
        self.original.page_changed.connect(self._sync_from_original)
        self._sync_timer = QTimer(self, singleShot=True, interval=120, timeout=self._sync_to_original)
        for w in (self.editor, self.preview):
            w.verticalScrollBar().valueChanged.connect(lambda _v: self._sync_timer.start())
        self.compare_split = QSplitter()
        self.compare_split.addWidget(self.original)
        self.compare_split.addWidget(self.tabs)
        self.compare_split.setStretchFactor(0, 1)
        self.compare_split.setStretchFactor(1, 1)
        # ---- sumário (títulos clicáveis) à esquerda do texto ----
        self.outline = QListWidget()
        self.outline.setToolTip(tr("Sumário: clique num título para ir até ele no texto"))
        self.outline.itemClicked.connect(self._go_heading)
        self.outline.setMinimumWidth(120)
        ow = QWidget()
        ol = QVBoxLayout(ow)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.addWidget(QLabel("<b>Sumário</b>"))
        ol.addWidget(self.outline, 1)
        self.outline_box = ow
        self.outline_split = QSplitter()
        self.outline_split.addWidget(ow)
        self.outline_split.addWidget(self.compare_split)
        self.outline_split.setStretchFactor(1, 1)
        self.outline_split.setSizes([200, 800])
        self.outline_split.setCollapsible(1, False)
        self._outline_timer = QTimer(self, singleShot=True, interval=400, timeout=self._refresh_outline)
        self.editor.textChanged.connect(lambda: self._outline_timer.start())
        ow.setVisible(False)
        cv.addWidget(self.outline_split, 1)

        split = QSplitter()
        split.addWidget(left)
        # ---- tela de boas-vindas (lista vazia) e barra de etapas ----
        from PySide6.QtWidgets import QStackedWidget

        welcome = QWidget()
        welcome.setObjectName("welcome")
        wl = QVBoxLayout(welcome)
        wl.addStretch(1)
        ip = icon_path()
        if ip:
            logo = QLabel()
            from PySide6.QtGui import QPixmap

            logo.setPixmap(QPixmap(str(ip)).scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logo.setAlignment(Qt.AlignCenter)
            wl.addWidget(logo)
        wt = QLabel(tr("<h2>Arraste seus documentos para cá</h2>"
                    "<p>PDF, Word, Excel, PowerPoint, páginas da web, e-books, fotos e escaneados.<br>"
                    "O Markinho transforma em texto limpo, pronto para salvar, copiar para a IA ou exportar.</p>"))
        wt.setAlignment(Qt.AlignCenter)
        wt.setWordWrap(True)
        wl.addWidget(wt)
        brow = QHBoxLayout()
        brow.addStretch(1)
        b_pick = QPushButton(tr("  Escolher arquivos…  "))
        b_pick.setStyleSheet("QPushButton { background: #1565C0; color: white; font-weight: bold; padding: 10px 18px;"
                             " border-radius: 6px; font-size: 14px; } QPushButton:hover { background: #0D47A1; }")
        b_pick.clicked.connect(self.add_files_dialog)
        brow.addWidget(b_pick)
        b_folder = QPushButton(tr("Uma pasta inteira…"))
        b_folder.clicked.connect(self.add_folder_dialog)
        brow.addWidget(b_folder)
        b_write = QPushButton(tr("Escrever do zero"))
        b_write.clicked.connect(self.new_document)
        brow.addWidget(b_write)
        brow.addStretch(1)
        wl.addLayout(brow)
        tips = QLabel(tr("Dicas: <b>Ctrl+Shift+V</b> cola e converte um texto ou imagem copiados · no Windows, clique "
                      "com o botão direito num arquivo › <b>Markinho</b> · 🔒 nada sai do seu computador"))
        tips.setAlignment(Qt.AlignCenter)
        tips.setWordWrap(True)
        tips.setStyleSheet("color: palette(window-text); font-size: 12px; margin-top: 18px;")
        wl.addWidget(tips)
        wl.addStretch(2)
        welcome.setStyleSheet("QWidget#welcome { border: 2px dashed palette(mid); border-radius: 12px; }")
        self.center_stack = QStackedWidget()
        self.center_stack.addWidget(welcome)
        self.center_stack.addWidget(center)
        self.steps = QLabel()
        self.steps.setTextFormat(Qt.RichText)
        self.steps.setAlignment(Qt.AlignCenter)
        self.steps.setStyleSheet("padding: 4px; font-size: 13px;")
        self.steps.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
        self.steps.linkActivated.connect(self._step_clicked)     # a etapa atual é um botão: faz o que ela diz
        cwrap = QWidget()
        cwl = QVBoxLayout(cwrap)
        cwl.setContentsMargins(6, 6, 6, 0)
        cwl.addWidget(self.steps)
        cwl.addWidget(self.center_stack, 1)
        split.addWidget(cwrap)
        split.setStretchFactor(1, 1)
        split.setSizes([290, 700])
        left.setMinimumWidth(120)
        split.setCollapsible(0, True)
        for sp in (split, self.compare_split):           # divisórias visíveis e fáceis de arrastar
            sp.setHandleWidth(8)
            sp.setStyleSheet("QSplitter::handle { background: palette(midlight); border-left: 1px solid palette(mid);"
                             " border-right: 1px solid palette(mid); margin: 0 2px; }"
                             "QSplitter::handle:hover { background: palette(highlight); }")
        self._main_split, self._left = split, left
        self.setCentralWidget(split)

        # ---- direita: configurações ----
        self.panel = SettingsPanel(self.settings)
        self.panel.fix_changed.connect(self._refix_all)
        self.panel.output_changed.connect(self._refix_all)
        self.panel.theme_changed.connect(apply_theme)
        self.panel.threads_changed.connect(self.pool.setMaxThreadCount)
        self.panel.reconvert.connect(self.reconvert)
        self.panel.reconvert_needed.connect(self._settings_changed)
        scroll = QScrollArea()
        scroll.setWidget(self.panel)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(240)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)   # o painel acompanha a largura da coluna
        for combo in self.panel.findChildren(QComboBox):             # listas encolhem em vez de alargar o painel
            combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(8)
        dock = QDockWidget(tr("Configurações"), self)
        self._dock = dock
        dock.setWidget(scroll)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        view_toggle = dock.toggleViewAction()
        view_toggle.setText(tr("Painel de configurações"))
        view_toggle.setShortcut("F9")
        vm = self._view_menu
        vm.addAction(view_toggle)
        a_cmp = QAction(tr("Ver original ao lado"), self, checkable=True)
        a_cmp.toggled.connect(self.compare_btn.setChecked)
        self.compare_btn.toggled.connect(a_cmp.setChecked)
        vm.addAction(a_cmp)
        self.act_outline = QAction(tr("Sumário"), self, checkable=True)
        self.act_outline.setShortcut("Ctrl+Shift+O")
        self.act_outline.setToolTip(tr("Mostra os títulos do documento; clique para ir até eles"))
        self.act_outline.setChecked(self.settings.value("ui/outline", True, type=bool))
        self.act_outline.toggled.connect(lambda v: (self.settings.setValue("ui/outline", v), self._refresh_outline()))
        vm.addAction(self.act_outline)
        vm.addSeparator()
        for text, step, key in ((tr("Aumentar o texto"), 1, "Ctrl++"), (tr("Diminuir o texto"), -1, "Ctrl+-"),
                                (tr("Tamanho normal do texto"), 0, "Ctrl+0")):
            a_z = QAction(text, self)
            a_z.triggered.connect(lambda _c=False, st_=step: self.text_zoom(st_))
            a_z.setShortcut(key)
            a_z.setShortcutContext(Qt.WidgetShortcut)      # o atalho de verdade já existe na janela
            vm.addAction(a_z)
        vm.addSeparator()
        for mode, text, key in (("simple", tr("Modo simples"), "Ctrl+1"), ("complete", tr("Modo completo"), "Ctrl+2")):
            a_m = QAction(text, self)
            a_m.setShortcut(key)
            a_m.triggered.connect(lambda _c=False, m=mode: self.set_mode(m))
            self.addAction(a_m)                       # funciona mesmo com a barra de menus escondida (Simples)
            vm.addAction(a_m)
        # painel aberto/fechado é lembrado; em telas pequenas começa fechado (o texto fica com o espaço)
        saved_panel = self.settings.value("ui/panel", None)
        if saved_panel is None:
            scr = QGuiApplication.primaryScreen()
            small = scr is not None and scr.availableGeometry().width() < 1280
            dock.setVisible(not small)
        else:
            dock.setVisible(saved_panel in (True, "true", "1"))
        dock.visibilityChanged.connect(lambda v: self.settings.setValue("ui/panel", v)
                                       if self.isVisible() and getattr(self, "mode", "complete") == "complete" else None)

        self.progress = QProgressBar()
        self.progress.setMaximumWidth(200)
        self.progress.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress)
        self.watch_label = QLabel()
        self.watch_label.setStyleSheet("color: palette(window-text);")
        self.statusBar().addPermanentWidget(self.watch_label)
        self.offline_label = QLabel(tr("🔒 Offline — seus documentos não saem do computador"))
        self.offline_label.setStyleSheet("color: #1b5e20; font-weight: bold; padding: 0 8px;")
        self.offline_label.setToolTip(tr("Toda a conversão, o OCR, a anonimização e a exportação acontecem aqui, no "
                                      "seu computador. O Markinho não envia documentos, textos nem nomes de "
                                      "arquivos para a internet. Detalhes em Ajuda > Privacidade."))
        self.statusBar().addPermanentWidget(self.offline_label)
        self.statusBar().showMessage(tr("Pronto"))
        self.setAcceptDrops(True)               # soltar arquivos em qualquer lugar da janela
        self._watcher = None
        self._start_watch()
        self._build_modes()

    # ---------------- arrastar e soltar na janela ----------------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.add_paths(paths)
            e.acceptProposedAction()

    # ---------------- adicionar arquivos ----------------
    def add_files_dialog(self) -> None:
        exts = " ".join(f"*{e}" for e in all_input_extensions())
        files, _ = QFileDialog.getOpenFileNames(
            self, tr("Escolher arquivos"), recall_dir(self.settings, "open"),
            tr('Documentos suportados ({0});;Todos os arquivos (*)').format(exts))
        if files:
            remember_dir(self.settings, files[0], "open")
            self.add_paths(files)

    def add_folder_dialog(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("Escolher pasta"), recall_dir(self.settings, "open"))
        if folder:
            remember_dir(self.settings, folder, "open")
            self.add_paths([folder])

    def add_paths(self, paths: list[str]) -> None:
        exts = set(all_input_extensions())
        files: list[Path] = []
        for p in map(Path, paths):
            if p.is_dir():
                files += sorted(f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in exts)
            elif p.is_file():
                files.append(p)
        added = 0
        for f in files:
            key = str(f.resolve())
            if key in self.entries:
                continue
            self.entries[key] = Entry(key, queued=True)
            item = QListWidgetItem(f.name)
            item.setData(ROLE_PATH, key)
            self.list.addItem(item)
            if self.act_auto.isChecked() or getattr(self, "mode", "complete") == "simple":
                self._start(key)                  # no modo Simples a conversão começa sozinha
            else:
                self._decorate(item)
            added += 1
        if added and self.list.currentItem() is None:
            self.list.setCurrentRow(self.list.count() - added)
        if not added and paths:
            self.statusBar().showMessage(tr("Nenhum arquivo novo compatível encontrado."), 4000)
        self._update_progress()
        self._update_buttons()

    def new_document(self) -> None:
        n = 1
        while f"<novo {n}>" in self.entries:
            n += 1
        key = f"<novo {n}>"
        md = tr("# Novo documento\n\nEscreva ou cole seu Markdown aqui e use **Exportar…**.\n")
        res = ConversionResult(Path(tr('novo_{0}.md').format(n)), md, tr("Editor"), raw_markdown=md, engine="editor")
        self.entries[key] = Entry(key, res, text=md, busy=False, edited=True)
        item = QListWidgetItem(tr('Novo documento {0}.md').format(n))
        item.setData(ROLE_PATH, key)
        self.list.addItem(item)
        self._decorate(item)
        self.list.setCurrentItem(item)
        self.tabs.setCurrentIndex(0)
        self.editor.setFocus()

    def _start(self, path: str) -> None:
        entry = self.entries[path]
        entry.busy, entry.error, entry.queued = True, "", False
        entry.partial = []
        self.gen[path] = self.gen.get(path, 0) + 1
        eid = self.panel.engine_id()
        opts = self.panel.engine_options()
        if eid != AUTO and not ENGINES[eid].supports(Path(path)):
            eid = AUTO      # o motor escolhido não lê este formato (ex.: Docling e .doc): usa o melhor disponível
        if eid == AUTO:
            from .engines import pick_engine
            try:
                chosen = pick_engine(Path(path))
                eid, opts = chosen.id, self.panel.engine_options(chosen.id)
            except RuntimeError:
                pass
        if path in self._image_mode:            # “Ler esta imagem como…”
            eid, opts = "native", {**self.panel.engine_options("native"), "image_mode": self._image_mode[path]}
        task = _ConvertTask(path, self.gen[path], eid, opts, self.panel.fix_options(), self.panel.output_options(),
                            fallback=self.panel.engine_id() == AUTO)
        task.setAutoDelete(False)
        task.signals.done.connect(self._on_done)
        task.signals.failed.connect(self._on_failed)
        task.signals.progress.connect(self._on_progress)
        task.signals.partial.connect(self._on_partial)
        self._tasks[path] = task
        heavy = eid in ENGINES and ENGINES[eid].heavy
        (self.heavy_pool if heavy else self.pool).start(task)
        item = self._find(path)
        if item:
            self._decorate(item)
        self._update_progress()

    def convert_queue(self, selected_only: bool = False) -> None:
        """Converte os arquivos da fila (e tenta de novo os que deram erro), na ordem da lista."""
        items = self.list.selectedItems() if selected_only else [self.list.item(i) for i in range(self.list.count())]
        items.sort(key=self.list.row)
        keys = [it.data(ROLE_PATH) for it in items
                if (e := self.entries.get(it.data(ROLE_PATH))) is not None and not e.busy
                and (e.queued or e.error or (selected_only and e.result is None))]
        if not keys:
            # nada na fila: converte de novo os arquivos selecionados que já foram convertidos
            done = [it for it in (self.list.selectedItems() or ([self.list.currentItem()] if self.list.currentItem()
                                                                  else []))
                    if not it.data(ROLE_PATH).startswith("<") and self.entries[it.data(ROLE_PATH)].result is not None]
            if done:
                self.reconvert(False)
                self.statusBar().showMessage(tr('Convertendo de novo {0} arquivo(s)…').format(len(done)), 3000)
                return
            self.statusBar().showMessage(tr("Nada na fila para converter. Adicione arquivos ou selecione um já "
                                         "convertido para converter de novo."), 4000)
            return
        for k in keys:
            self._start(k)
        self.statusBar().showMessage(tr('Convertendo {0} arquivo(s)…').format(len(keys)))

    def cancel_conversions(self) -> None:
        """Tira da fila do processador as conversões que ainda não começaram; elas voltam a aguardar.
        As que já estão em andamento terminam, mas o resultado é descartado."""
        n = 0
        for path, e in self.entries.items():
            if not e.busy:
                continue
            task = self._tasks.pop(path, None)
            if task is not None and not (self.pool.tryTake(task) or self.heavy_pool.tryTake(task)):
                task.cancel.set()                         # em andamento: para na próxima página
            self.gen[path] = self.gen.get(path, 0) + 1      # ignora um resultado que ainda chegue
            e.busy, e.queued, e.progress = False, e.result is None, None
            item = self._find(path)
            if item:
                self._decorate(item)
            n += 1
        self._update_progress()
        self._update_buttons()
        if n:
            self.statusBar().showMessage(tr('{0} conversão(ões) cancelada(s).').format(n), 4000)

    def rename_selected(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        item = self.list.currentItem()
        if item is None:
            return
        e = self.entries[item.data(ROLE_PATH)]
        current = e.custom or self._stem(e)
        text, ok = QInputDialog.getText(self, tr("Renomear saída"),
                                        tr("Nome do arquivo de saída (sem extensão).\n"
                                        "Deixe vazio para voltar ao nome original:"), text=current)
        if ok:
            e.custom = "" if text.strip() in ("", self._stem(e)) else text.strip()
            self._decorate(item)

    def read_image_as(self, mode: str) -> None:
        """Reconverte as imagens selecionadas dizendo ao OCR o que elas contêm."""
        from .converters import IMAGE_EXTS

        keys = [it.data(ROLE_PATH) for it in self.list.selectedItems()
                if Path(it.data(ROLE_PATH)).suffix.lower() in IMAGE_EXTS]
        if not keys:
            self.statusBar().showMessage(tr("Selecione uma imagem (foto ou print) na lista."), 4000)
            return
        for k in keys:
            self._image_mode[k] = mode
            if not self.entries[k].busy:
                self.entries[k].edited = False
                self._start(k)

    def reconvert(self, all_items: bool) -> None:
        items = [self.list.item(i) for i in range(self.list.count())] if all_items else self.list.selectedItems()
        keys = [it.data(ROLE_PATH) for it in items if not it.data(ROLE_PATH).startswith("<")
                and not self.entries[it.data(ROLE_PATH)].busy]
        edited = [k for k in keys if self.entries[k].edited]
        if edited and QMessageBox.question(
                self, tr("Reconverter"),
                tr('{0} documento(s) foram editados. Reconverter descarta as edições. Continuar?').format(len(edited))) \
                != QMessageBox.Yes:
            return
        for k in keys:
            self.entries[k].edited = False
            self._start(k)
        if not keys:
            self.statusBar().showMessage(tr("Selecione arquivos para reconverter."), 3000)
        else:
            self._show_item(self.list.currentItem())

    # ---------------- resultados ----------------
    def _find(self, path: str) -> QListWidgetItem | None:
        for i in range(self.list.count()):
            if self.list.item(i).data(ROLE_PATH) == path:
                return self.list.item(i)
        return None

    def _decorate(self, item: QListWidgetItem) -> None:
        e = self.entries[item.data(ROLE_PATH)]
        st = self.style()
        if e.queued and not e.busy:
            item.setIcon(st.standardIcon(QStyle.SP_MediaPause))
            item.setToolTip(tr('{0}\n\nNa fila — clique em “Converter” (F5)').format(e.path))
        elif e.busy:
            item.setIcon(st.standardIcon(QStyle.SP_BrowserReload))
            prog = tr(' — página {0} de {1}').format(e.progress[0], e.progress[1]) if e.progress and e.progress[1] > 1 else ""
            item.setToolTip(tr('{0}\n\nConvertendo{1}… (Esc para parar)').format(e.path, prog))
        elif e.error:
            item.setIcon(st.standardIcon(QStyle.SP_MessageBoxCritical))
            item.setToolTip(f"{e.path}\n\n{e.error}")
        else:
            rep = e.result.fix_report
            from .core import is_alert

            warn = (rep is not None and bool(rep.warnings())) or any(is_alert(w) for w in e.result.warnings) \
                or bool(e.result.review_pages)
            item.setIcon(st.standardIcon(QStyle.SP_MessageBoxWarning if warn else QStyle.SP_DialogApplyButton))
            secs = f"{e.result.seconds:.2f}".replace(".", ",")
            tip = tr("{0}\n\n{1} • {2} caracteres • {3} s").format(e.path, e.result.converter, num_br(len(e.text)), secs)
            if rep is not None:
                tip += tr('\n{0} correção(ões) de caracteres').format(rep.total)
                if warn:
                    tip += "\n⚠ " + "\n⚠ ".join(rep.warnings())
            if e.result.assets:
                tip += tr('\n{0} imagem(ns) extraída(s)').format(len(e.result.assets))
            if e.result.anon_report is not None:
                tip += tr('\nAnonimizado — {0}').format(e.result.anon_report.summary())
                if e.result.anon_report.residual:
                    tip += "\n⚠ " + e.result.anon_report.residual_summary()
            for w in e.result.warnings:
                tip += f"\n⚠ {w}"
            if e.edited:
                tip += "\n✎ editado"
            item.setToolTip(tip)
        if e.path.startswith("<"):
            name = item.data(Qt.UserRole + 1) or item.text().lstrip("✎ ")
            item.setData(Qt.UserRole + 1, name)
        else:
            name = Path(e.path).name
        if e.custom:
            name = f"{e.custom}   ← {name}"
            item.setToolTip(item.toolTip() + tr('\n\nNome de saída: {0}').format(e.custom))
        if e.busy and e.progress and e.progress[1] > 1:
            name += f"   ({e.progress[0]}/{e.progress[1]})"
        elif e.result is not None and not e.busy and e.result.review_pages:
            name += "   ⚠"
        item.setText(("✎ " if e.edited and e.result and e.result.engine != "editor" else "") + name)

    def _on_done(self, path: str, gen: int, result: ConversionResult) -> None:
        if path not in self.entries or gen != self.gen.get(path):
            return
        self._tasks.pop(path, None)
        e = self.entries[path]
        e.result, e.error, e.busy, e.edited, e.text = result, "", False, False, result.markdown
        e.progress = None
        e.partial = None
        from .support import count_conversion

        milestone = count_conversion(self.settings)
        if milestone:
            self._support_due = milestone          # mostra quando terminar o que está convertendo
        self._after_update(path)

    PARTIAL_HEADER = ("<!-- PRÉVIA: texto provisório das páginas já lidas. Títulos, tabelas e o texto final "
                      "aparecem quando a conversão terminar. -->")

    def _on_partial(self, path: str, gen: int, page: int, text: str) -> None:
        e = self.entries.get(path)
        if e is None or gen != self.gen.get(path) or not e.busy:
            return
        if e.partial is None:
            e.partial = []
        e.partial.append((page, text))
        item = self.list.currentItem()
        if item is not None and item.data(ROLE_PATH) == path:
            from PySide6.QtGui import QTextCursor

            self._loading = True
            if self.editor.document().isEmpty():
                self.editor.setPlainText(self.PARTIAL_HEADER)
            cur = self.editor.textCursor()
            cur.movePosition(QTextCursor.End)
            cur.insertText(f"\n\n<!-- página {page} -->\n\n{text}")
            self._loading = False

    def _on_progress(self, path: str, gen: int, done: int, total: int) -> None:
        e = self.entries.get(path)
        if e is None or gen != self.gen.get(path) or not e.busy:
            return
        e.progress = (done, total)
        item = self._find(path)
        if item is not None:
            self._decorate(item)
            if item is self.list.currentItem() and total > 1:
                self.info.setText(tr('Convertendo {0}… página {1} de {2} (Esc para parar)').format(html.escape(Path(path).name), done, total))

    def _on_failed(self, path: str, gen: int, message: str) -> None:
        if path not in self.entries or gen != self.gen.get(path):
            return
        self._tasks.pop(path, None)
        e = self.entries[path]
        e.error, e.busy, e.progress = message, False, None
        e.partial = None
        self._after_update(path)

    def _after_update(self, path: str) -> None:
        item = self._find(path)
        if item is not None:
            self._decorate(item)
            if item is self.list.currentItem():
                self._show_item(item)
        self._update_progress()
        self._update_buttons()

    def _save_pending(self) -> None:
        """Retomar: guarda a fila que ainda não foi convertida (some quando tudo termina)."""
        if not getattr(self, "_resume_checked", False):
            return                                    # ainda não ofereceu retomar o lote anterior
        pending = [k for k, e in self.entries.items()
                   if not k.startswith("<") and e.result is None and not e.error and (e.queued or e.busy)]
        if pending:
            self.settings.setValue("batch/pending", pending)
        else:
            self.settings.remove("batch/pending")

    def offer_resume(self) -> None:
        """Ao abrir: o último lote não terminou (fechou no meio, travou, faltou energia)? Oferece continuar."""
        from . import batch

        pending = self.settings.value("batch/pending", []) or []
        if isinstance(pending, str):
            pending = [pending]
        pending = [p for p in pending if Path(p).is_file()]
        self._resume_checked = True
        self.settings.remove("batch/pending")
        if not pending or not batch.enabled(self.settings):
            return
        ask = QMessageBox.question(self, tr("Retomar o lote"),
                                   tr("O último lote não terminou: {0} arquivo(s) ainda não tinham sido convertidos.\n\n"
                                      "Colocar de volta na fila e continuar?").format(len(pending)))
        if ask == QMessageBox.Yes:
            self.add_paths(pending)
            if not self.act_auto.isChecked():
                self.convert_queue(False)

    def _update_progress(self) -> None:
        self._save_pending()
        if getattr(self, "mode", "complete") == "simple" and hasattr(self, "simple"):
            self.simple.refresh()
        self._update_steps()
        if hasattr(self, "act_cancel"):
            self.act_cancel.setEnabled(any(x.busy for x in self.entries.values()))
        total = len(self.entries)
        pending = sum(1 for e in self.entries.values() if e.busy)
        queued = sum(1 for e in self.entries.values() if e.queued and not e.busy)
        if queued and not pending:
            self.progress.setVisible(False)
            done = sum(1 for e in self.entries.values() if e.result is not None and not e.busy)
            self.statusBar().showMessage(tr('{0} arquivo(s) na fila — clique em “Converter” (F5)').format(queued)
                                         + (tr(' • {0} pronto(s)').format(done) if done else ""))
            return
        if not pending and getattr(self, "_support_due", None):
            due, self._support_due = self._support_due, None
            QTimer.singleShot(1200, lambda: self.support(due))
        if pending:
            self.progress.setVisible(True)
            self.progress.setRange(0, max(total, 1))
            self.progress.setValue(total - pending)
            self.statusBar().showMessage(tr('Convertendo… ({0} restante(s))').format(pending))
        else:
            self.progress.setVisible(False)
            errors = sum(1 for e in self.entries.values() if e.error)
            fixes = sum(e.result.fix_report.total for e in self.entries.values()
                        if e.result and e.result.fix_report)
            msg = tr('{0} documento(s) prontos').format(total - errors)
            if errors:
                msg += tr(', {0} com erro').format(errors)
            if fixes:
                msg += tr(' • {0} caractere(s) corrigido(s)').format(fixes)
            anon = sum(e.result.anon_report.total for e in self.entries.values()
                       if e.result and e.result.anon_report)
            if any(e.result and e.result.anon_report is not None for e in self.entries.values()):
                msg += (tr(' • anonimizado: {0} dado(s) trocado(s) — revise o arquivo antes de qualquer uso (o Markinho não se responsabiliza por falhas)').format(anon))
            self.statusBar().showMessage(msg if total else tr("Pronto"))

    # ---------------- correção de caracteres ----------------
    def _refix_all(self) -> None:
        fix = self.panel.fix_options()
        out = self.panel.output_options()
        for path, e in self.entries.items():
            if e.result is None or e.busy or e.result.engine == "editor":
                continue
            finalize_result(e.result, fix, out)
            if not e.edited:
                e.text = e.result.markdown
            item = self._find(path)
            if item:
                self._decorate(item)
        self._show_item(self.list.currentItem())
        self._update_progress()

    def _fix_link(self, url) -> None:
        if url.toString() == "#aplicar":
            fix = self.panel.fix_options() or FixOptions()
            text, rep = fix_text(self.editor.toPlainText(), fix)
            self.editor.setPlainText(text)
            self.statusBar().showMessage(tr('{0} correção(ões) aplicada(s) ao texto editado.').format(rep.total), 5000)
            self._refresh_views()

    # ---------------- exibição ----------------
    def _current(self) -> Entry | None:
        item = self.list.currentItem()
        return self.entries.get(item.data(ROLE_PATH)) if item else None

    def _toggle_compare(self, on: bool) -> None:
        self.original.setVisible(on)
        self.space_btn.setVisible(on)
        self.follow_cb.setVisible(on)
        self.settings.setValue("compare", on)
        if on:
            self._load_original()
            # tela estreita (ex.: notebook 1366): abre já com mais espaço; “Mostrar painéis” volta
            if self.centralWidget().width() < 1000 and not self.space_btn.isChecked():
                self.space_btn.setChecked(True)
            QTimer.singleShot(0, self._split_half)       # depois de a janela se ajustar
            QTimer.singleShot(200, self._sync_to_original)
        elif self.space_btn.isChecked():
            self.space_btn.setChecked(False)

    def text_zoom(self, step: int | None) -> None:
        """Aumenta/diminui o texto do Markdown e da visualização (step None = só aplicar o guardado,
        0 = voltar ao normal)."""
        level = int(self.settings.value("ui/text_zoom", 0))
        if step == 0:
            level = 0
        elif step:
            level = max(-4, min(level + step, 12))
        self.settings.setValue("ui/text_zoom", level)
        for w in (self.editor, self.preview):
            f = w.font()
            f.setPointSizeF(max(6.0, self._base_pt[id(w)] * (1.1 ** level)))
            w.setFont(f)
        if step is not None:
            self.statusBar().showMessage(tr('Tamanho do texto: {0:.0f}%').format(100 * 1.1 ** level), 2000)

    def _toggle_follow(self, on: bool) -> None:
        self.settings.setValue("ui/follow", on)
        if on:
            self._syncing = False
            self._sync_to_original()          # alinha na hora: o PDF vai para a página do texto à vista
            self.statusBar().showMessage(tr("Rolar junto ligado: o original foi alinhado à página do texto."), 3000)

    def _split_half(self) -> None:
        w = max(self.compare_split.width(), 400)
        self.compare_split.setSizes([w // 2, w - w // 2])

    def _toggle_space(self, on: bool) -> None:
        self._left.setVisible(not on)
        if hasattr(self, "_dock"):
            self._dock.setVisible(not on)
        self.space_btn.setText(tr("Mostrar painéis") if on else tr("Mais espaço"))
        QTimer.singleShot(0, self._split_half)

    # ---------------- leitura acompanhada (texto ↔ páginas do original) ----------------
    def _sync_widgets(self):
        w = self.tabs.currentWidget()
        return w if w in (self.editor, self.preview) else None

    def _page_positions(self, widget):
        from .pagesync import page_positions

        e = self._current()
        if e is None or e.result is None or not e.result.page_starts:
            return []
        text = widget.toPlainText()
        key = (id(e), id(widget), len(text), hash(text[:200]))
        if getattr(self, "_pos_cache_key", None) != key:
            self._pos_cache_key = key
            self._pos_cache = page_positions(e.result.page_starts, text)
        return self._pos_cache

    def _sync_to_original(self) -> None:
        """Texto rolou: leva o original à página do trecho que está no topo."""
        if getattr(self, "_syncing", False) or not self.original.isVisible() or not self.original.is_pdf() \
                or not self.follow_cb.isChecked():
            return
        widget = self._sync_widgets()
        if widget is None:
            return
        from PySide6.QtCore import QPoint

        from .pagesync import page_at

        page = page_at(self._page_positions(widget), widget.cursorForPosition(QPoint(4, widget.fontMetrics().height())).position())
        if page:
            self._syncing = True
            self.original.go_to_page(page)
            QTimer.singleShot(250, lambda: setattr(self, "_syncing", False))

    def _sync_from_original(self, page: int) -> None:
        """PDF rolou: leva o texto ao começo da página que está à vista."""
        if getattr(self, "_syncing", False) or not self.follow_cb.isChecked():
            return
        widget = self._sync_widgets()
        if widget is None:
            return
        from PySide6.QtGui import QTextCursor

        from .pagesync import page_at, position_of

        positions = self._page_positions(widget)
        from PySide6.QtCore import QPoint

        if page_at(positions, widget.cursorForPosition(QPoint(4, widget.fontMetrics().height())).position()) == page:
            return
        pos = position_of(positions, page)
        if pos is None:
            return
        self._syncing = True
        scroll_text_to(widget, pos)
        QTimer.singleShot(250, lambda: setattr(self, "_syncing", False))

    def _load_original(self) -> None:
        if not self.original.isVisible():
            return
        e = self._current()
        if e is None:
            self.original.show_message(tr("Selecione um arquivo da lista."))
        else:
            self.original.load(e.path if not e.path.startswith("<") else "")

    def _show_item(self, item: QListWidgetItem | None, *_):
        self._load_original()
        self._loading = True
        e = self.entries.get(item.data(ROLE_PATH)) if item else None
        if e is None:
            self.editor.clear()
            self.info.setText(tr("Nenhum arquivo selecionado"))
            self.info.setToolTip("")
        elif e.queued and not e.busy:
            self.editor.clear()
            self.info.setText(tr('Na fila: <b>{0}</b>. Clique em <b>Converter</b> (F5) quando terminar de adicionar arquivos.').format(html.escape(Path(e.path).name)))
        elif e.busy:
            self.editor.clear()
            if e.partial:                        # prévia das páginas já lidas
                self.editor.setPlainText(self.PARTIAL_HEADER + "".join(
                    f"\n\n<!-- página {p} -->\n\n{t}" for p, t in e.partial))
            self.info.setText(tr('Convertendo {0}… (prévia: o texto final aparece ao terminar)').format(Path(e.path).name))
        elif e.error:
            self.editor.clear()
            self.info.setText(f"<span style='color:#c0392b'>⚠ {html.escape(e.error)}</span>")
        else:
            self.editor.setPlainText(e.text)
            if e.result.engine != "editor" and self.tabs.currentWidget() is self.fixes:
                self.tabs.setCurrentWidget(self.preview)
            where = Path(e.path).name if not e.path.startswith("<") else tr("Documento novo (não salvo)")
            self.info.setText(f"<b>{html.escape(where)}</b>  •  {html.escape(e.result.converter)}  •  "
                              + tr("{0} caracteres").format(num_br(len(e.text))) + (tr("  •  ✎ editado") if e.edited else ""))
            self.info.setToolTip(e.path if not e.path.startswith("<") else "")
        self.editor.setReadOnly(e is None or e.busy or e.queued or bool(e.error))
        self._update_review(e)
        self._loading = False
        self._refresh_views()
        self._update_buttons()

    def _refresh_outline(self) -> None:
        """Sumário com os títulos do texto; só aparece se ligado e se houver ao menos 2 títulos."""
        from .outline import headings

        heads = headings(self.editor.toPlainText())
        self.outline.clear()
        for level, title, line in heads:
            it = QListWidgetItem(("    " * (level - 1)) + title)
            it.setData(Qt.UserRole, line)
            it.setToolTip(title)
            if level == 1:
                f = it.font()
                f.setBold(True)
                it.setFont(f)
            self.outline.addItem(it)
        show = hasattr(self, "act_outline") and self.act_outline.isChecked() and len(heads) >= 2
        self.outline_box.setVisible(show)

    def _go_heading(self, item) -> None:
        line = item.data(Qt.UserRole)
        title = item.toolTip()
        if self.tabs.currentWidget() is self.preview:
            from PySide6.QtGui import QTextCursor

            self.preview.moveCursor(QTextCursor.Start)
            self.preview.find(title)
            return
        from PySide6.QtGui import QTextCursor

        block = self.editor.document().findBlockByNumber(int(line))
        cur = QTextCursor(block)
        self.editor.setTextCursor(cur)
        self.editor.verticalScrollBar().setValue(int(line))      # QPlainTextEdit rola em linhas
        self.editor.setFocus()

    def _editor_changed(self) -> None:
        if self._loading:
            return
        e = self._current()
        if e is not None and e.result is not None:
            e.text = self.editor.toPlainText()
            if not e.edited:
                e.edited = True
                self._decorate(self.list.currentItem())
            if e.result.engine == "editor":
                e.result.markdown = e.result.raw_markdown = e.text
            self._preview_timer()

    def _preview_timer(self):
        if not hasattr(self, "_ptimer"):
            self._ptimer = QTimer(self)
            self._ptimer.setSingleShot(True)
            self._ptimer.timeout.connect(self._refresh_views)
        self._ptimer.start(400)

    def _render_preview(self, view) -> None:
        """Texto formatado do documento atual (com as imagens em memória) — Completo e Simples."""
        e = self._current()
        view.assets = e.result.assets if e is not None and e.result is not None else {}
        text = self.editor.toPlainText()
        if "```" in text or "~~~" in text:          # código: colorido (Pygments)
            from .exporter import markdown_to_html

            dark = view.palette().color(QPalette.Base).lightness() < 128
            view.setHtml(markdown_to_html(text, highlight=True, dark=dark))
        else:
            view.setMarkdown(text)

    def _refresh_views(self) -> None:
        w = self.tabs.currentWidget()
        if getattr(self, "mode", "complete") == "simple" and hasattr(self, "simple"):
            self.simple.refresh()
        if w is self.preview:
            self._render_preview(self.preview)
        elif w is self.fixes:
            self.fixes.setHtml(self._fixes_html())

    def _fixes_html(self) -> str:
        e = self._current()
        css = ("<style>body{font-family:sans-serif} .del{background:#ffd7d5;color:#000;text-decoration:line-through}"
               ".ins{background:#ccf0d4;color:#000} td{vertical-align:top;padding:2px 8px;font-family:monospace;"
               "font-size:12px} .warn{color:#b9770e}</style>")
        if e is None or e.result is None:
            return css + tr("<p>Selecione um documento convertido.</p>")
        if e.result.engine == "editor":
            return css + (tr("<p>Documento escrito à mão.</p><p><a href='#aplicar'>Aplicar correção de "
                          "caracteres ao texto</a></p>"))
        rep = e.result.fix_report
        if rep is None:
            return css + (tr("<p>A correção de caracteres está <b>desligada</b>. Ative-a no painel "
                          "<i>Configurações</i> para ver e aplicar correções.</p>"))
        out = [css]
        if e.edited:
            out.append(tr("<p class='warn'>✎ O texto foi editado — as correções abaixo se referem ao texto "
                       "original convertido. <a href='#aplicar'>Aplicar correção ao texto editado</a></p>"))
        from .exporter import markdown_to_html
        out.append(markdown_to_html(rep.to_markdown()))
        # linhas alteradas (antes x depois)
        before = e.result.raw_markdown.splitlines()
        after = e.result.markdown.splitlines()
        rows = []
        sm = difflib.SequenceMatcher(None, before, after, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            for a, b in zip(before[i1:i2] + [""] * max(0, (j2 - j1) - (i2 - i1)),
                            after[j1:j2] + [""] * max(0, (i2 - i1) - (j2 - j1))):
                rows.append((i1 + 1, _inline_diff(a, b)))
                if len(rows) >= 300:
                    break
        if rows:
            out.append(tr("<h3>Linhas alteradas ({0})</h3>").format(f"{len(rows)}{'+' if len(rows) >= 300 else ''}")
                       + "<table cellspacing='0'>")
            for n, (a, b) in rows:
                out.append(f"<tr><td style='color:gray'>{n}</td><td>{a}</td></tr>"
                           f"<tr><td></td><td>{b}</td></tr><tr><td colspan=2><hr></td></tr>")
            out.append("</table>")
        return "".join(out)

    def _update_buttons(self) -> None:
        e = self._current()
        has_cur = e is not None and e.result is not None and not e.busy and not e.error
        any_done = bool(self._done_entries())
        self.act_copy.setEnabled(has_cur)
        self.act_ai.setEnabled(has_cur)
        self.act_save.setEnabled(has_cur)
        self.act_save_all.setEnabled(any_done)
        self.act_merge.setEnabled(any_done)
        self.act_export.setEnabled(any_done)
        self.act_remove.setEnabled(bool(self.list.selectedItems()))
        self.act_clear.setEnabled(self.list.count() > 0)
        entries = list(self.entries.values())
        sel_done = any(not it.data(ROLE_PATH).startswith("<") and (x := self.entries.get(it.data(ROLE_PATH)))
                       and x.result is not None and not x.busy for it in self.list.selectedItems())
        self.act_convert.setEnabled(any((x.queued or x.error) and not x.busy for x in entries) or sel_done)
        self.act_cancel.setEnabled(any(x.busy for x in entries))
        # destaque azul no próximo passo: “Converter” se há fila; senão “Salvar”
        pending = any(x.queued and not x.busy for x in entries)
        self._update_steps(pending)
        self._set_primary(self.act_convert, pending)
        self._set_primary(self.act_save, not pending and self.act_save.isEnabled())

    def _update_steps(self, pending: bool | None = None) -> None:
        """Barra ① Adicionar → ② Converter → ③ Salvar e tela de boas-vindas com a lista vazia."""
        if not hasattr(self, "steps"):
            return
        entries = list(self.entries.values())
        if pending is None:
            pending = any(x.queued and not x.busy for x in entries)
        busy = any(x.busy for x in entries)
        done = any(x.result is not None and not x.busy for x in entries)
        step = 1 if not entries else 2 if (pending or busy or not done) else 3
        names = [tr("① Adicionar documentos"), tr("② Converter") + (tr(" (em andamento…)") if busy else ""),
                 tr("③ Salvar, copiar ou exportar")]
        # o que fazer agora, escrito; na etapa atual, o nome vira botão (clique = faz a etapa)
        hint = {1: tr("Solte arquivos na janela ou clique aqui para escolher"),
                2: tr("Os arquivos estão na fila: clique aqui para converter (ou aperte F5)") if not busy
                else tr("Aguarde: convertendo…"),
                3: tr("Pronto! Clique aqui para salvar, ou use Copiar / Exportar na barra de cima")}[step]
        actions = {1: "add", 2: "convert", 3: "save"}
        parts = []
        for k, n in enumerate(names, 1):
            if k == step:
                label = ("▶ " + n) if (k == 2 and not busy) else n
                box = f"<span style='background:#1565C0;color:white;'><b>&nbsp;{label}&nbsp;</b></span>"
                if not (k == 2 and busy):
                    box = f"<a href='{actions[k]}' style='text-decoration:none;'>{box}</a>"
                parts.append(box)
            elif k < step:
                parts.append(f"<span style='color:#2e7d32'>✓ {n}</span>")
            else:
                parts.append(f"<span style='color:gray'>{n}</span>")
        self.steps.setText("&nbsp;&nbsp;→&nbsp;&nbsp;".join(parts)
                           + f"<br><span style='color:palette(window-text);font-size:12px;'>{hint}</span>")
        self.steps.setToolTip(hint)
        self.center_stack.setCurrentIndex(0 if not entries else 1)

    def _step_clicked(self, what: str) -> None:
        """Clique na etapa atual da barra ① → ② → ③."""
        if what == "add":
            self.add_files_dialog()
        elif what == "convert":
            self.convert_queue(False)
        elif what == "save":
            done = self._done_entries()
            (self.save_all if len(done) > 1 else self.save_current)()

    def _set_primary(self, act, on: bool) -> None:
        w_ = self._toolbar.widgetForAction(act) if hasattr(self, "_toolbar") else None
        if w_ is None or (w_.objectName() == "primaryButton") == on:
            return
        w_.setObjectName("primaryButton" if on else "")
        w_.style().unpolish(w_)
        w_.style().polish(w_)

    def resizeEvent(self, ev) -> None:
        """Janela estreita: botões secundários só com ícone (nenhum botão some atrás do “»”)."""
        super().resizeEvent(ev)
        if hasattr(self, "_toolbar"):
            narrow = self.width() < 1250
            for act in self._secondary:
                w_ = self._toolbar.widgetForAction(act)
                if w_ is not None:
                    w_.setToolButtonStyle(Qt.ToolButtonIconOnly if narrow else Qt.ToolButtonTextBesideIcon)

    def _done_entries(self) -> list[Entry]:
        out = []
        for i in range(self.list.count()):
            e = self.entries[self.list.item(i).data(ROLE_PATH)]
            if e.result is not None and not e.busy and not e.error:
                out.append(e)
        return out

    # ---------------- ações ----------------
    def remove_selected(self) -> None:
        for item in self.list.selectedItems():
            key = item.data(ROLE_PATH)
            self.entries.pop(key, None)
            self.gen.pop(key, None)
            self.list.takeItem(self.list.row(item))
        self._show_item(self.list.currentItem())
        self._update_progress()

    def clear_all(self) -> None:
        self.list.clear()
        self.entries.clear()
        self.gen.clear()
        self._show_item(None)
        self._update_progress()

    def copy_current(self) -> None:
        QGuiApplication.clipboard().setText(self.editor.toPlainText())
        self.statusBar().showMessage(tr("Markdown copiado para a área de transferência."), 3000)

    @staticmethod
    def _stem(e: Entry) -> str:
        return e.result.source.stem if e.result else Path(e.path).stem

    def _src_dir(self, e: Entry) -> str:
        return str(Path(e.path).parent) if not e.path.startswith("<") else str(Path.home())

    def _context(self, e: Entry):
        from .naming import NameContext

        title = (e.result.metadata.get("title") if e.result else "") or (e.result.title if e.result else "")
        src = e.result.source if e.result else Path(e.path)
        return NameContext.from_result(src, title=title, engine=e.result.engine if e.result else "", custom=e.custom)

    def _contexts(self, entries: list[Entry]) -> list:
        return [self._context(e) for e in entries]

    def save_current(self) -> None:
        from .naming import render

        e = self._current()
        if e is None or e.result is None:
            return
        opts = saved_naming(self.settings)
        row = max(0, self.list.row(self.list.currentItem()))     # {n} = posição na lista
        start = Path(recall_dir(self.settings, "save", self._src_dir(e))) / (render(self._context(e), row, opts) + opts.ext)
        target, _ = QFileDialog.getSaveFileName(self, tr("Salvar Markdown"), str(start),
                                                tr("Markdown (*.md *.markdown);;Texto (*.txt);;Todos (*)"))
        if target:
            if self._write(Path(target), e.text, e.result.assets, anon_report=e.result.anon_report):
                remember_dir(self.settings, target, "save")
                self.settings.setValue("out_dir", str(Path(target).parent))
                self.statusBar().showMessage(tr('Salvo em {0}').format(target), 5000)

    def save_all(self) -> None:
        from .naming import plan

        entries = self._done_entries()
        dlg = SaveAllDialog(self, self.settings, self._contexts(entries))
        if dlg.exec() != QDialog.Accepted:
            return
        folder = Path(dlg.folder.text())
        folder.mkdir(parents=True, exist_ok=True)
        planned = plan(self._contexts(entries), dlg.naming.options(), folder)
        from . import batch

        manifest = batch.Manifest(folder) if batch.enabled(self.settings) else None
        written = skipped = 0
        for e, p in zip(entries, planned):
            src = Path(e.path)
            sha = batch.file_hash(src) if manifest is not None and src.is_file() else ""
            reserved = manifest.output_name(src, "janela") if sha else None
            target = folder / reserved if reserved else p.path   # salvando de novo: mesmo arquivo, sem _2
            if p.action == "skip" and not reserved:
                skipped += 1
                continue
            if sha:
                manifest.start(src, sha, "janela", target.name)
            if self._write(target, e.text, e.result.assets, anon_report=e.result.anon_report):
                written += 1
                if sha:
                    manifest.finish(src, True)
        msg = tr('{0} arquivo(s) salvo(s) em:\n{1}').format(written, folder)
        if skipped:
            msg += tr('\n\n{0} pulado(s) porque já existiam.').format(skipped)
        QMessageBox.information(self, tr("Markinho"), msg)

    @staticmethod
    def _all_assets(entries: list[Entry]) -> dict[str, bytes]:
        files: dict[str, bytes] = {}
        for e in entries:
            if e.result:
                files.update(e.result.assets)
        return files

    def _merged_text(self, entries: list[Entry]) -> str:
        return "\n\n---\n\n".join(
            f"<!-- Fonte: {self._stem(e)} -->\n\n{e.text.strip()}" for e in entries) + "\n"

    def save_merged(self) -> None:
        entries = self._done_entries()
        start = Path(recall_dir(self.settings, "save")) / "documentos.md"
        target, _ = QFileDialog.getSaveFileName(self, tr("Salvar Markdown combinado"), str(start), tr("Markdown (*.md)"))
        if target:
            remember_dir(self.settings, target, "save")
        if target and self._write(Path(target), self._merged_text(entries), self._all_assets(entries), rename=False):
            self.statusBar().showMessage(tr('{0} documento(s) combinados em {1}').format(len(entries), target), 5000)

    def export_dialog(self) -> None:
        cur = self._current()
        n_cur = 1 if cur is not None and cur.result is not None and not cur.busy and not cur.error else 0
        entries = self._done_entries()
        dlg = ExportDialog(self, self.settings, n_cur, len(entries), self._contexts(entries))
        if dlg.exec() != QDialog.Accepted:
            return
        fid, backend, opts, scope = dlg.values()
        fmt = FORMATS_BY_ID[fid]
        out_dir = recall_dir(self.settings, "export")
        jobs: list[tuple[str, Path, str | None, dict, dict]] = []   # (markdown, destino, pasta base, imagens, extras)
        if scope == 1:
            folder = QFileDialog.getExistingDirectory(self, tr("Pasta de destino"), out_dir)
            if not folder:
                return
            remember_dir(self.settings, folder, "export")
            from .naming import plan

            dlg.naming.set_target(folder, fmt.ext)
            for e, p in zip(entries, plan(self._contexts(entries), dlg.naming.options(), Path(folder), fmt.ext)):
                if p.action == "skip":
                    continue
                jobs.append((e.text, p.path, self._src_dir(e), e.result.assets,
                             {"source": e.result.source.name, "metadata": e.result.metadata}))
        else:
            if scope == 0:
                md, stem, base, files = cur.text, self._stem(cur), self._src_dir(cur), cur.result.assets
            else:
                md, stem, base, files = self._merged_text(entries), "documentos", None, self._all_assets(entries)
            start = str(Path(out_dir) / (stem + fmt.ext))
            target, _ = QFileDialog.getSaveFileName(self, tr('Exportar como {0}').format(fmt.label), start, f"{fmt.label} (*{fmt.ext})")
            if not target:
                return
            if not target.lower().endswith(fmt.ext):
                target += fmt.ext
            remember_dir(self.settings, target, "export")
            extra = ({"source": cur.result.source.name, "metadata": cur.result.metadata} if scope == 0
                     else {"source": "documentos"})
            jobs.append((md, Path(target), base, files, extra))

        QApplication.setOverrideCursor(Qt.WaitCursor)
        errors, used = [], ""
        import tempfile

        try:
            for md, target, base, files, extra in jobs:
                try:
                    with tempfile.TemporaryDirectory(prefix="markinho_exp_") as tmp:
                        # as imagens extraídas ficam em memória: grava numa pasta temporária para o exportador
                        if files and write_assets(md, files, Path(tmp)):
                            base = tmp
                        partial = target.with_name(f".~{target.stem}{target.suffix}")   # nunca fica pela metade
                        try:
                            used = export(md, partial, fid, {**opts, **extra}, backend, base_dir=base)
                            os.replace(partial, target)
                        finally:
                            partial.unlink(missing_ok=True)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{target.name}: {exc}")
        finally:
            QApplication.restoreOverrideCursor()
        ok = len(jobs) - len(errors)
        if errors:
            QMessageBox.warning(self, tr("Exportar"), tr('{0} exportado(s), {1} com erro:\n\n').format(ok, len(errors)) + "\n".join(errors[:10]))
        else:
            via = "Pandoc" if used == "pandoc" else tr("exportador nativo")
            self.statusBar().showMessage(tr('{0} arquivo(s) exportado(s) como {1} via {2} → {3}').format(ok, fmt.label, via, jobs[0][1] if ok == 1 else jobs[0][1].parent), 8000)
            if ok >= 1:
                box = QMessageBox(self)
                box.setWindowTitle(tr("Exportado"))
                box.setText(tr('{0} arquivo(s) exportado(s) como {1}.').format(ok, fmt.label))
                b_here = box.addButton(tr("Ver aqui"), QMessageBox.AcceptRole)
                b_app = box.addButton(tr("Abrir no aplicativo padrão"), QMessageBox.ActionRole)
                box.addButton(tr("Fechar"), QMessageBox.RejectRole)
                box.exec()
                first = jobs[0][1]
                if box.clickedButton() is b_here:
                    FileViewerDialog(self, first).exec()
                elif box.clickedButton() is b_app:
                    from PySide6.QtCore import QUrl
                    from PySide6.QtGui import QDesktopServices

                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(first)))

    def _write(self, path: Path, text: str, assets: dict[str, bytes] | None = None, rename: bool = True,
               anon_report=None) -> bool:
        from .naming import rename_assets

        try:
            if assets and rename:
                # a pasta de imagens acompanha o nome do arquivo: <nome>_assets/
                text, assets = rename_assets(text, assets, path.stem)
            from .batch import atomic_write

            atomic_write(path, text)          # nunca fica um arquivo pela metade
            if assets:
                write_assets(text, assets, path.parent)
            if anon_report is not None:
                from .quick import anon_options

                if anon_options(self.settings).save_mapping:
                    from .anonymize import write_mapping

                    write_mapping(path, anon_report)      # “<nome>.correspondencia.csv”, ao lado
            return True
        except OSError as exc:
            QMessageBox.critical(self, tr("Erro ao salvar"), tr('Não foi possível salvar {0}:\n{1}').format(path, exc))
            return False

    # ---------------- configurações mudaram ----------------
    def _converted_files(self) -> list[str]:
        return [k for k, e in self.entries.items() if not k.startswith("<") and e.result is not None and not e.busy]

    def _settings_changed(self) -> None:
        """Motor, modo ou opções mudaram: oferece converter de novo os arquivos já convertidos."""
        done = self._converted_files()
        if not done:
            return
        self.settings_bar_label.setText(tr("<b>As configurações de conversão mudaram.</b> Os arquivos já convertidos "
                                        "continuam com as configurações anteriores. Converter de novo?"))
        self.btn_redo_all.setText(tr('Todos ({0})').format(len(done)))
        self.btn_redo_all.setVisible(len(done) > 1)
        cur = self._current()
        self.btn_redo_one.setVisible(cur is not None and cur.path in done)
        self.settings_bar.setVisible(True)

    def _redo_current(self) -> None:
        item = self.list.currentItem()
        self.settings_bar.setVisible(False)
        if item is None:
            return
        self.list.clearSelection()
        item.setSelected(True)
        self.reconvert(False)

    # ---------------- colar e converter ----------------
    def paste_as_markdown(self) -> None:
        from PySide6.QtCore import QBuffer, QIODevice

        from .paste import clipboard_to_markdown

        mime = QGuiApplication.clipboard().mimeData()
        html_text = mime.html() if mime is not None and mime.hasHtml() else None
        text = mime.text() if mime is not None and mime.hasText() else None
        png = None
        if mime is not None and mime.hasImage() and not html_text and not (text or "").strip():
            img = QGuiApplication.clipboard().image()
            if not img.isNull():
                buf = QBuffer()
                buf.open(QIODevice.WriteOnly)
                img.save(buf, "PNG")
                png = bytes(buf.data())
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            md, origin = clipboard_to_markdown(html_text, text, png)
        except Exception as exc:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, tr("Colar"), tr('Não foi possível converter o conteúdo colado:\n{0}').format(exc))
            return
        QApplication.restoreOverrideCursor()
        if not md.strip():
            self.statusBar().showMessage(tr("A área de transferência está vazia (copie um texto ou imagem antes)."), 5000)
            return
        n = 1
        while f"<colado {n}>" in self.entries:
            n += 1
        key = f"<colado {n}>"
        res = ConversionResult(Path(tr('colado_{0}.md').format(n)), md, tr('Colado ({0})').format(origin), raw_markdown=md, engine="editor")
        self.entries[key] = Entry(key, res, text=md, busy=False)
        item = QListWidgetItem(tr('Colado {0}.md').format(n))
        item.setData(ROLE_PATH, key)
        self.list.addItem(item)
        self._decorate(item)
        self.list.setCurrentItem(item)
        self.tabs.setCurrentIndex(0)
        self.statusBar().showMessage(tr('Conteúdo colado convertido ({0}).').format(origin), 4000)

    def copy_for_ai(self) -> None:
        from .gui_tools import AiCopyDialog

        e = self._current()
        if e is None or e.result is None:
            return
        AiCopyDialog(self, e.text, self.settings).exec()

    # ---------------- dividir, relatório, pasta monitorada ----------------
    def split_current(self) -> None:
        from .gui_tools import SplitDialog

        e = self._current()
        if e is None or e.result is None:
            QMessageBox.information(self, tr("Dividir por títulos"), tr("Selecione um documento já convertido."))
            return
        start = str(Path(self._src_dir(e)) / tr('{0}_partes').format(self._stem(e)))
        SplitDialog(self, e.text, e.result.assets, self.settings, start).exec()

    def open_packs(self) -> None:
        from .gui_tools import PacksDialog

        PacksDialog(self).exec()

    def skill_export(self) -> None:
        from .gui_tools import SkillDialog

        def doc(e) -> tuple[str, str]:
            return (e.result.metadata.get("title") or e.result.title or self._stem(e), e.text)

        entries = self._done_entries()
        cur = self._current()
        current = doc(cur) if cur is not None and cur in entries else None
        if current is None and not entries:
            QMessageBox.information(self, tr("Exportar como skill para IA"), tr("Adicione e converta arquivos primeiro."))
            return
        start = self._src_dir(cur if current else entries[0])
        SkillDialog(self, current, [doc(e) for e in entries], self.settings, start).exec()

    def batch_report(self) -> None:
        from . import report

        rows = []
        for i in range(self.list.count()):
            e = self.entries[self.list.item(i).data(ROLE_PATH)]
            if e.path.startswith("<"):
                continue
            rows.append(report.row(e.path, e.result if not e.busy else None, e.error, e.queued))
        if not rows:
            QMessageBox.information(self, tr("Relatório do lote"), tr("Adicione e converta arquivos primeiro."))
            return
        target, flt = QFileDialog.getSaveFileName(
            self, tr("Salvar relatório do lote"), str(Path(recall_dir(self.settings, "save")) / "relatorio-markinho.csv"),
            tr("Planilha (*.csv);;Página (*.html)"))
        if not target:
            return
        path = Path(target)
        remember_dir(self.settings, path, "save")
        try:
            if path.suffix.lower() in (".html", ".htm") or "html" in flt:
                report.to_html(rows, path.with_suffix(".html"))
            else:
                report.to_csv(rows, path.with_suffix(".csv"))
        except OSError as exc:
            QMessageBox.critical(self, tr("Relatório do lote"), tr('Não foi possível salvar:\n{0}').format(exc))
            return
        self.statusBar().showMessage(report.summary(rows) + tr(" Relatório salvo."), 6000)

    def watch_dialog(self) -> None:
        from .gui_tools import WatchDialog

        if WatchDialog(self, self.settings).exec() == QDialog.Accepted:
            self._start_watch()

    def _start_watch(self) -> None:
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher.deleteLater()
            self._watcher = None
        self.watch_label.clear()
        if not self.settings.value("watch/enabled", False, type=bool):
            return
        from .watch import FolderWatcher

        folder = self.settings.value("watch/folder", "")
        out = None if self.settings.value("watch/same", True, type=bool) else self.settings.value("watch/out", "")
        w = FolderWatcher(folder, out or None, self)
        if not w.start():
            self.watch_label.setText(tr("Pasta monitorada não encontrada"))
            return
        w.converted.connect(self._on_watch_result)
        self._watcher = w
        self.watch_label.setText(tr('Monitorando: {0}').format(Path(folder).name))
        self.watch_label.setToolTip(tr('Pasta monitorada: {0}\nArquivos novos são convertidos sozinhos.').format(folder))

    def _on_watch_result(self, r) -> None:
        if r.error:
            from .diagnostics import record_error

            record_error(str(r.source), r.error)
            self.statusBar().showMessage(tr('Pasta monitorada: erro em {0}: {1}').format(r.source.name, r.error), 8000)
        elif r.output:
            self.statusBar().showMessage(tr('Pasta monitorada: {0} → {1}').format(r.source.name, r.output.name), 6000)

    # ---------------- modo simples, assistente, relatório de erro ----------------
    def _toggle_shell(self, on: bool) -> None:
        from . import winshell

        try:
            if on:
                winshell.register()
                QMessageBox.information(self, tr("Botão direito do Windows"),
                                        tr("Pronto! Clique com o botão direito num PDF, Word, Excel ou imagem > Markinho.\n\n"
                                        "No Windows 11, o menu fica em “Mostrar mais opções”. Se você mover a pasta do "
                                        "Markinho de lugar, ligue esta opção de novo."))
            else:
                winshell.unregister()
                self.statusBar().showMessage(tr("Menu “Markinho” removido do botão direito."), 4000)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("Botão direito do Windows"), tr('Não foi possível alterar o menu:\n{0}').format(exc))

    def first_run(self) -> None:
        from .gui_tools import FirstRunDialog

        if FirstRunDialog(self, self.settings).exec() == QDialog.Accepted:
            self.panel.reload_output()
            self.set_mode(str(self.settings.value("ui/mode", "simple")))

    def anonymize_file(self) -> None:
        """Anonimiza um .md já salvo (ou o documento aberto, se for o caso) e salva uma cópia."""
        from .gui_tools import AnonDialog

        e = self._current()
        if e is not None and e.text and QMessageBox.question(
                self, tr("Anonimizar"), tr('Anonimizar o documento aberto ({0})?\n\n“Não” escolhe outro arquivo Markdown.').format(Path(e.path).name)) == QMessageBox.Yes:
            AnonDialog(self, self.settings, e.text, Path(e.path)).exec()
            return
        path, _ = QFileDialog.getOpenFileName(self, tr("Anonimizar um arquivo Markdown"),
                                              recall_dir(self.settings, "anon"), tr("Markdown (*.md *.markdown *.txt)"))
        if not path:
            return
        remember_dir(self.settings, path, "anon")
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            QMessageBox.warning(self, tr("Anonimizar"), tr('Não foi possível ler o arquivo: {0}').format(exc))
            return
        AnonDialog(self, self.settings, text, Path(path)).exec()

    def compare_versions(self) -> None:
        from .gui_tools import CompareDialog

        e = self._current()
        cur_path = e.path if e is not None and e.text and not e.path.startswith("<") else ""
        CompareDialog(self, self.settings, cur_path, e.text if cur_path else "").exec()

    def support(self, milestone: int | None = None) -> None:
        from .gui_tools import SupportDialog

        if milestone and any(e.busy for e in self.entries.values()):
            self._support_due = milestone          # nunca no meio de uma conversão
            return
        SupportDialog(self, milestone if isinstance(milestone, int) else None, self.settings).exec()

    def privacy(self) -> None:
        from .privacy import text

        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Privacidade e relatório de erro"))
        dlg.resize(640, 600)
        lay = QVBoxLayout(dlg)
        view = QTextBrowser()
        view.setMarkdown(text())
        lay.addWidget(view)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        dlg.exec()

    def error_report(self) -> None:
        from .gui_tools import ErrorReportDialog

        ErrorReportDialog(self, self.settings).exec()

    # ---------------- páginas a revisar ----------------
    def _update_review(self, e) -> None:
        if e is None or e.result is None or e.busy or e.error or not (e.result.review_pages or e.result.warnings):
            self.review.setVisible(False)
            return
        parts = []
        if e.result.review_pages:
            links = ", ".join(f"<a href='page:{p}'>{p}</a>" for p in e.result.review_pages[:30])
            more = "…" if len(e.result.review_pages) > 30 else ""
            parts.append(tr('⚠ <b>Revise a(s) página(s)</b> {0}{1} — clique para ver no original.').format(links, more))
        for w in e.result.warnings[:4]:
            parts.append("• " + html.escape(w))
        self.review.setText("<br>".join(parts))
        self.review.setVisible(True)

    def _go_review_page(self, link: str) -> None:
        if not link.startswith("page:"):
            return
        page = int(link.split(":", 1)[1])
        if not self.compare_btn.isChecked():
            self.compare_btn.setChecked(True)
        QTimer.singleShot(150, lambda: self.original.go_to_page(page))

    def about(self, tab: int = 0) -> None:
        AboutDialog(self, tab).exec()

    # ---------------- modos Simples e Completo ----------------
    def _build_modes(self) -> None:
        from PySide6.QtWidgets import QStackedWidget

        from .gui_simple import ModeHeader, SimpleView

        self.header = ModeHeader(self.set_mode, self._help_menu, icon_path())
        hb = QToolBar(tr("Modo"))
        hb.setObjectName("headerBar")
        hb.setMovable(False)
        hb.setFloatable(False)
        hb.toggleViewAction().setVisible(False)
        hb.addWidget(self.header)
        self.insertToolBar(self._toolbar, hb)
        self.insertToolBarBreak(self._toolbar)
        self._header_bar = hb
        self.simple = SimpleView(self)
        self.root_stack = QStackedWidget()
        self.takeCentralWidget()
        self.root_stack.addWidget(self._main_split)
        self.root_stack.addWidget(self.simple)
        self.setCentralWidget(self.root_stack)
        self._list_home = (self._left.layout(), self._left.layout().indexOf(self.list))
        mode = self.settings.value("ui/mode", None)
        self.mode = "complete"
        self.set_mode(str(mode) if mode in ("simple", "complete") else self.DEFAULT_MODE)   # 1ª vez: Simples

    def set_mode(self, mode: str) -> None:
        """Simples (só o essencial) ou Completo (tudo). Lembra o último; a fila e os textos são os mesmos."""
        mode = "simple" if mode == "simple" else "complete"
        self.header.set_mode(mode)
        if mode == self.mode and self.root_stack.currentWidget() is (self.simple if mode == "simple" else self._main_split):
            return
        self.settings.setValue("ui/mode", mode)
        simple = mode == "simple"
        if simple:
            self._dock_was = self._dock.isVisible()
        self.mode = mode
        self.menuBar().setVisible(not simple)
        self._toolbar.setVisible(not simple)
        self.offline_label.setVisible(not simple)       # o selo já está no cabeçalho
        if simple:
            self._dock.setVisible(False)
            self.simple.list_slot.addWidget(self.list)
            self.root_stack.setCurrentWidget(self.simple)
            self.simple.refresh()
        else:
            lay, idx = self._list_home
            lay.insertWidget(idx, self.list, 1)
            self.root_stack.setCurrentWidget(self._main_split)
            self._dock.setVisible(getattr(self, "_dock_was", self.settings.value("ui/panel", True) in (True, "true", "1")))
            self._show_item(self.list.currentItem())
        self.list.setVisible(True)

    def open_in_complete(self, review: bool = False) -> None:
        """Link dos avisos do Simples: vai para o Completo e, se houver páginas a revisar, mostra o original."""
        self.set_mode("complete")
        e = self._current()
        if review and e is not None and e.result is not None and e.result.review_pages:
            self._go_review_page(f"page:{e.result.review_pages[0]}")

    def quick_export(self, fid: str, template: str | None = None) -> None:
        """Exportar do modo Simples: um formato, o documento atual, sem janela de opções."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        e = self._current()
        if e is None or e.result is None or e.busy or e.error:
            return
        fmt = FORMATS_BY_ID[fid]
        start = Path(recall_dir(self.settings, "export")) / (self._stem(e) + fmt.ext)
        target, _ = QFileDialog.getSaveFileName(self, tr("Exportar como {0}").format(fmt.label), str(start),
                                                f"{fmt.label} (*{fmt.ext})")
        if not target:
            return
        target = Path(target)
        if target.suffix.lower() != fmt.ext:
            target = target.with_suffix(fmt.ext)
        remember_dir(self.settings, str(target), "export")
        opts = {"source": Path(e.path).name, "metadata": e.result.metadata}
        if template:
            opts["template"] = template
        import tempfile

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            with tempfile.TemporaryDirectory(prefix="markinho_exp_") as tmp:
                base = tmp if e.result.assets and write_assets(e.text, e.result.assets, Path(tmp)) else str(Path(e.path).parent)
                partial = target.with_name(f".~{target.stem}{target.suffix}")
                try:
                    export(e.text, partial, fid, opts, "auto", base_dir=base)
                    os.replace(partial, target)
                finally:
                    partial.unlink(missing_ok=True)
        except Exception as exc:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, tr("Exportar"), tr("Não foi possível exportar:\n{0}").format(exc))
            return
        QApplication.restoreOverrideCursor()
        box = QMessageBox(self)
        box.setWindowTitle(tr("Exportado"))
        box.setText(tr("{0} foi salvo em {1}").format(target.name, target.parent))
        b_open = box.addButton(tr("Abrir arquivo"), QMessageBox.AcceptRole)
        b_dir = box.addButton(tr("Abrir pasta"), QMessageBox.ActionRole)
        box.addButton(tr("Fechar"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is b_open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
        elif box.clickedButton() is b_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.parent)))

    def check_updates(self) -> None:
        from .gui_tools import UpdateDialog

        UpdateDialog(self, self.settings).exec()

    def remind_updates(self) -> None:
        """Lembrete sem internet: aparece a cada ~2 meses, nunca por cima de outra janela nem no meio de um lote."""
        from . import updates

        if QApplication.activeModalWidget() is not None or any(e.busy for e in self.entries.values()):
            return
        if updates.due(self.settings):
            from .gui_tools import UpdateDialog

            UpdateDialog(self, self.settings, reminder=True).exec()

    def open_project_page(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl("https://github.com/dontstopbelieve/markinho"))


def _inline_diff(a: str, b: str) -> tuple[str, str]:
    """Destaca, caractere a caractere, o que mudou entre duas linhas."""
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    ra, rb = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        sa, sb = html.escape(a[i1:i2]), html.escape(b[j1:j2])
        if tag == "equal":
            ra.append(sa)
            rb.append(sb)
        else:
            if sa:
                ra.append(f"<span class='del'>{_visible(a[i1:i2])}</span>")
            if sb:
                rb.append(f"<span class='ins'>{_visible(b[j1:j2])}</span>")
    return "− " + "".join(ra), "+ " + "".join(rb)


def _visible(s: str) -> str:
    import unicodedata

    out = []
    for c in s:
        if unicodedata.category(c) in ("Cf", "Cc") or (unicodedata.category(c) == "Zs" and c != " "):
            out.append(f"⟨U+{ord(c):04X}⟩")
        elif unicodedata.combining(c):
            out.append(f"◌{c}")
        else:
            out.append(html.escape(c))
    return "".join(out)


def num_br(n: int) -> str:
    """1023 → “1.023” em português, “1,023” em inglês (ver i18n.num)."""
    from .i18n import num

    return num(n)


def draw_icon(kind: str) -> QIcon:
    """Ícones simples desenhados no próprio programa (iguais em todos os sistemas)."""
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QBrush, QPainter, QPainterPath, QPen, QPixmap

    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    blue, green, dark = QColor("#1565C0"), QColor("#1DBF4E"), QColor("#37474F")
    if kind == "convert":                       # círculo azul com “play”
        p.setPen(Qt.NoPen)
        p.setBrush(blue)
        p.drawEllipse(QRectF(4, 4, 56, 56))
        tri = QPainterPath(QPointF(25, 18))
        tri.lineTo(46, 32)
        tri.lineTo(25, 46)
        tri.closeSubpath()
        p.setBrush(Qt.white)
        p.drawPath(tri)
    elif kind == "export":                      # folha com seta saindo
        p.setPen(QPen(dark, 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPolyline([QPointF(30, 10), QPointF(12, 10), QPointF(12, 54), QPointF(46, 54), QPointF(46, 36)])
        p.setPen(QPen(green, 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(QPointF(28, 36), QPointF(54, 10))
        p.drawPolyline([QPointF(38, 10), QPointF(54, 10), QPointF(54, 26)])
    elif kind == "copy":                        # duas folhas
        p.setPen(QPen(dark, 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.white)
        p.drawRoundedRect(QRectF(8, 8, 32, 38), 5, 5)
        p.drawRoundedRect(QRectF(24, 20, 32, 38), 5, 5)
    elif kind == "ai":                          # brilho (estrela de 4 pontas) — “IA”
        def star(cx, cy, r):
            path = QPainterPath(QPointF(cx, cy - r))
            for x, y in ((cx + r * .22, cy - r * .22), (cx + r, cy), (cx + r * .22, cy + r * .22), (cx, cy + r),
                         (cx - r * .22, cy + r * .22), (cx - r, cy), (cx - r * .22, cy - r * .22)):
                path.lineTo(x, y)
            path.closeSubpath()
            return path
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#7E57C2")))
        p.drawPath(star(28, 34, 24))
        p.setBrush(QBrush(QColor("#FFB300")))
        p.drawPath(star(50, 13, 10))
    elif kind == "write":                       # folha com lápis
        p.setPen(QPen(dark, 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline([QPointF(34, 54), QPointF(10, 54), QPointF(10, 10), QPointF(40, 10), QPointF(40, 22)])
        p.setPen(QPen(blue, 8, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(30, 48), QPointF(54, 24))
    p.end()
    return QIcon(pm)


def icon_path() -> Path | None:
    p = Path(__file__).resolve().parent / "resources" / "markinho.png"
    return p if p.is_file() else None


def recall_dir(settings, kind: str = "", fallback: str | None = None) -> str:
    """Pasta onde a janela de abrir/salvar deve começar: a última usada nesse tipo de janela ou,
    se não houver, a última pasta usada em qualquer janela do Markinho."""
    for key in ((f"dir/{kind}",) if kind else ()) + ("last_dir",):
        v = settings.value(key, "")
        if v and Path(v).is_dir():
            return str(v)
    return fallback if fallback and Path(fallback).is_dir() else str(Path.home())


def remember_dir(settings, path: str | Path, kind: str = "") -> None:
    """Guarda a pasta usada (de um arquivo ou de uma pasta) para as próximas janelas."""
    if not path:
        return
    p = Path(path)
    folder = p if p.is_dir() else p.parent
    if kind:
        settings.setValue(f"dir/{kind}", str(folder))
    settings.setValue("last_dir", str(folder))


def scroll_text_to(widget, pos: int) -> None:
    """Rola uma caixa de texto até a posição `pos` ficar no topo. No QPlainTextEdit a barra conta
    linhas; no QTextBrowser/QTextEdit, pixels."""
    from PySide6.QtGui import QTextCursor

    cur = QTextCursor(widget.document())
    cur.setPosition(max(0, min(pos, widget.document().characterCount() - 1)))
    bar = widget.verticalScrollBar()
    if isinstance(widget, QPlainTextEdit):
        layout = cur.block().layout()
        line = layout.lineForTextPosition(cur.positionInBlock()).lineNumber() if layout is not None else 0
        bar.setValue(cur.block().firstLineNumber() + max(line, 0))
    else:
        bar.setValue(bar.value() + widget.cursorRect(cur).top())


def install_translations(app) -> None:
    """Botões e janelas padrão do Qt (Fechar, Cancelar, Abrir/Salvar arquivo…) em português."""
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator

    if getattr(app, "_markinho_tr", None):
        return
    app._markinho_tr = []
    folder = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    for name in ("qtbase", "qt"):
        tr = QTranslator(app)
        if tr.load(QLocale("pt_BR"), name, "_", folder):
            app.installTranslator(tr)
            app._markinho_tr.append(tr)


def _light_palette(app) -> QPalette:
    """Paleta clara do Fusion com textos de apoio escuros (o cinza padrão é difícil de ler)."""
    p = app.style().standardPalette()
    p.setColor(QPalette.PlaceholderText, QColor(85, 85, 85))
    p.setColor(QPalette.Mid, QColor(70, 70, 70))
    return p


def apply_theme(theme: str) -> None:
    """Tema claro/escuro/do sistema com a paleta do estilo Fusion."""
    app = QApplication.instance()
    if app is None:
        return
    from .gui_simple import stylesheet

    if theme == "system":
        app.setPalette(_light_palette(app))
        app.setStyleSheet(stylesheet(False))
        try:
            hints = QGuiApplication.styleHints()
            if hints.colorScheme() == Qt.ColorScheme.Dark:
                theme = "dark"
        except AttributeError:
            pass
        if theme == "system":
            return
    if theme == "light":
        app.setPalette(_light_palette(app))
        app.setStyleSheet(stylesheet(False))
        return
    p = QPalette()
    dark, base, text, mid = QColor(37, 37, 38), QColor(30, 30, 30), QColor(225, 225, 225), QColor(128, 128, 128)
    for role, color in [(QPalette.Window, dark), (QPalette.WindowText, text), (QPalette.Base, base),
                        (QPalette.AlternateBase, QColor(45, 45, 48)), (QPalette.ToolTipBase, dark),
                        (QPalette.ToolTipText, text), (QPalette.Text, text), (QPalette.Button, QColor(50, 50, 52)),
                        (QPalette.ButtonText, text), (QPalette.BrightText, QColor(255, 80, 80)),
                        (QPalette.Highlight, QColor(42, 130, 218)), (QPalette.HighlightedText, QColor(255, 255, 255)),
                        (QPalette.Link, QColor(90, 160, 255)), (QPalette.PlaceholderText, mid), (QPalette.Mid, mid)]:
        p.setColor(role, color)
    for role in (QPalette.Text, QPalette.ButtonText, QPalette.WindowText):
        p.setColor(QPalette.Disabled, role, QColor(110, 110, 110))
    app.setPalette(p)
    app.setStyleSheet(stylesheet(True))


def main() -> int:
    from .models import setup_environment

    setup_environment()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Markinho")
    app.setOrganizationName("Markinho")
    app.setStyle("Fusion")
    ip = icon_path()
    if ip:
        app.setWindowIcon(QIcon(str(ip)))
    paths = [a for a in sys.argv[1:] if not a.startswith("-")]
    pending: list[str] = []
    holder: dict[str, MainWindow] = {}

    def receive(new: list[str]) -> None:
        """Arquivos vindos de outra instância (botão direito com vários arquivos selecionados)."""
        win = holder.get("win")
        if win is None:
            pending.extend(new)
            return
        if new:
            win.add_paths(new)
        win.showNormal()
        win.raise_()
        win.activateWindow()

    listener = None
    if os.environ.get("MARKINHO_MULTI") != "1":      # MARKINHO_MULTI=1 permite várias janelas
        from .single import claim

        listener = claim("gui", paths, receive)
        if listener is None:        # o Markinho já estava aberto: os arquivos foram para a fila dele
            return 0
    from .diagnostics import install as install_diagnostics

    install_diagnostics()
    install_translations(app)
    settings = QSettings("Markinho", "Markinho")
    apply_theme(settings.value("theme", "system"))
    if not settings.value("ui/first_run_done", False, type=bool) and os.environ.get("MARKINHO_SKIP_WELCOME") != "1":
        from .gui_tools import FirstRunDialog

        FirstRunDialog(None, settings).exec()          # antes da janela: o painel já abre com as escolhas
    win = MainWindow()
    holder["win"] = win
    win._single = listener
    win.show()
    if paths or pending:
        win.add_paths(paths + pending)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
