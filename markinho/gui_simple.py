# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Modos Simples e Completo (como a calculadora do Windows) e o visual comum dos dois.

- ``ModeHeader``: faixa do alto com o nome, a troca **Simples | Completo** (sempre à vista, Ctrl+1/Ctrl+2),
  o menu Ajuda (no Simples, que não tem barra de menus) e o selo “nada sai do seu computador”.
- ``SimpleView``: o modo Simples — soltar/escolher arquivos (a conversão começa sozinha), depois o texto
  formatado com 4 ações grandes (Salvar, Copiar, Copiar para IA, Exportar) e avisos que levam ao Completo.
  A lista de arquivos é a mesma do Completo (o widget é emprestado), então nada se perde ao trocar.
- ``stylesheet``: a mesma aparência (cartões arredondados, botões, abas, lista) nos dois modos, clara e escura.
"""
from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QSizePolicy, QStackedWidget,
    QToolButton, QVBoxLayout, QWidget,
)

from .i18n import num, tr

LIGHT = {"bg": "#f3f4f6", "card": "#ffffff", "line": "#d0d4da", "text": "#1f2328", "muted": "#5f6670",
         "blue": "#1565c0", "blue2": "#0d47a1", "sel": "#e8f0fe", "ok": "#2e7d32", "hover": "#eef3fb",
         "warn_bg": "#fff3cd", "warn_line": "#e0b100", "warn_text": "#3d2e00", "drop": "#9fb3c8"}
DARK = {"bg": "#1e1f22", "card": "#2a2b2f", "line": "#3d4046", "text": "#e4e6ea", "muted": "#a3a8b0",
        "blue": "#2f80e0", "blue2": "#1d6cc9", "sel": "#26384f", "ok": "#66bb6a", "hover": "#30343b",
        "warn_bg": "#3a3214", "warn_line": "#a8861a", "warn_text": "#f5e6b3", "drop": "#56657a"}


def stylesheet(dark: bool = False) -> str:
    """Folha de estilo comum (Simples e Completo). Só mexe em bordas, cantos, espaços e cores de destaque."""
    c = DARK if dark else LIGHT
    return f"""
QMainWindow, QDialog {{ background: {c['bg']}; }}
QToolBar {{ background: {c['card']}; border: none; border-bottom: 1px solid {c['line']}; spacing: 4px; padding: 4px 6px; }}
QToolBar QToolButton {{ padding: 5px 9px; border-radius: 6px; border: 1px solid transparent; }}
QToolBar QToolButton:hover {{ background: {c['hover']}; border-color: {c['line']}; }}
QToolBar#headerBar {{ padding: 0; border-bottom: 1px solid {c['line']}; }}
QMenuBar {{ background: {c['card']}; }}
QStatusBar {{ background: {c['card']}; border-top: 1px solid {c['line']}; }}
QListWidget, QPlainTextEdit, QTextBrowser, QTextEdit {{ background: {c['card']}; border: 1px solid {c['line']};
    border-radius: 9px; padding: 4px; }}
QListWidget::item {{ padding: 6px 6px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {c['sel']}; color: {c['text']}; }}
QListWidget::item:hover:!selected {{ background: {c['hover']}; }}
QPushButton {{ background: {c['card']}; border: 1px solid {c['line']}; border-radius: 7px; padding: 6px 14px; }}
QPushButton:hover {{ border-color: {c['blue']}; }}
QPushButton:pressed, QPushButton:checked {{ background: {c['sel']}; }}
QPushButton:disabled {{ color: {c['muted']}; }}
QPushButton[primary="true"] {{ background: {c['blue']}; border-color: {c['blue2']}; color: white; font-weight: bold; }}
QPushButton[primary="true"]:hover {{ background: {c['blue2']}; }}
QLineEdit, QComboBox, QSpinBox {{ background: {c['card']}; border: 1px solid {c['line']}; border-radius: 6px; padding: 4px 6px; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {c['blue']}; }}
QTabWidget::pane {{ border: 1px solid {c['line']}; border-radius: 9px; top: -1px; background: {c['card']}; }}
QTabBar::tab {{ padding: 7px 16px; border: 1px solid transparent; border-bottom: 2px solid transparent; }}
QTabBar::tab:selected {{ color: {c['blue']}; font-weight: bold; border-bottom: 2px solid {c['blue']}; }}
QTabBar::tab:hover:!selected {{ background: {c['hover']}; border-radius: 6px; }}
QGroupBox {{ border: 1px solid {c['line']}; border-radius: 9px; margin-top: 16px; padding: 10px 8px 8px 8px;
    background: {c['card']}; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; font-weight: bold; }}
QDockWidget::title {{ background: {c['card']}; padding: 7px 10px; border-bottom: 1px solid {c['line']}; }}
QScrollArea {{ border: none; background: transparent; }}
#modeHeader {{ background: {c['card']}; }}
#appName {{ font-size: 17px; font-weight: bold; }}
#appSub, #muted {{ color: {c['muted']}; }}
#lockLabel {{ color: {c['ok']}; font-weight: bold; }}
QPushButton#zoomBtn {{ padding: 3px 0; }}
QPushButton#segLeft, QPushButton#segRight {{ padding: 6px 18px; font-weight: bold; color: {c['muted']};
    background: {c['bg']}; border: 1px solid {c['line']}; border-radius: 15px; min-height: 18px; }}
QPushButton#segLeft:checked, QPushButton#segRight:checked {{ background: {c['blue']}; color: white; border-color: {c['blue2']}; }}
#dropZone {{ border: 2px dashed {c['drop']}; border-radius: 16px; background: {c['card']}; }}
#dropTitle {{ font-size: 24px; font-weight: bold; }}
#card {{ background: {c['card']}; border: 1px solid {c['line']}; border-radius: 12px; }}
#cardTitle {{ font-weight: bold; padding: 2px 2px 6px 2px; }}
QPushButton#bigAction, QToolButton#bigAction {{ font-size: 15px; font-weight: bold; padding: 11px 20px; border-radius: 9px;
    background: {c['card']}; border: 1px solid {c['line']}; }}
QToolButton#bigAction:hover {{ border-color: {c['blue']}; }}
QToolButton#bigAction::menu-indicator {{ subcontrol-position: right center; right: 8px; }}
QPushButton#bigAction[primary="true"] {{ background: {c['blue']}; border-color: {c['blue2']}; color: white; }}
QPushButton#bigAction[primary="true"]:hover {{ background: {c['blue2']}; }}
#warnBar {{ background: {c['warn_bg']}; border: 1px solid {c['warn_line']}; color: {c['warn_text']}; border-radius: 9px;
    padding: 8px 12px; }}
"""


def _primary(button: QPushButton) -> QPushButton:
    button.setProperty("primary", True)
    return button


class ModeHeader(QWidget):
    """Nome do programa, troca de modo (sempre à vista), Ajuda (no Simples) e o selo offline."""

    def __init__(self, on_mode, help_menu: QMenu, icon: Path | None):
        super().__init__()
        self.setObjectName("modeHeader")
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(10)
        if icon:
            logo = QLabel()
            logo.setPixmap(QPixmap(str(icon)).scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            lay.addWidget(logo)
        names = QVBoxLayout()
        names.setSpacing(0)
        name = QLabel("Markinho")
        name.setObjectName("appName")
        sub = QLabel(tr("Conversor Markdown"))
        sub.setObjectName("appSub")
        names.addWidget(name)
        names.addWidget(sub)
        lay.addLayout(names)
        lay.addStretch(1)
        self.simple_btn = QPushButton(tr("Simples"))
        self.simple_btn.setObjectName("segLeft")
        self.full_btn = QPushButton(tr("Completo"))
        self.full_btn.setObjectName("segRight")
        group = QButtonGroup(self)
        group.setExclusive(True)
        seg = QHBoxLayout()
        seg.setSpacing(4)
        for b, mode, tip in ((self.simple_btn, "simple", tr("Modo simples: só o essencial — arrastar, converter e "
                                                              "salvar, copiar ou exportar (Ctrl+1)")),
                             (self.full_btn, "complete", tr("Modo completo: todas as ferramentas, motores e "
                                                            "opções (Ctrl+2)"))):
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(tip)
            group.addButton(b)
            b.clicked.connect(lambda _c=False, m=mode: on_mode(m))
            seg.addWidget(b)
        lay.addLayout(seg)
        self.help_btn = QToolButton()
        self.help_btn.setText(tr("Ajuda"))
        self.help_btn.setPopupMode(QToolButton.InstantPopup)
        self.help_btn.setMenu(help_menu)
        lay.addWidget(self.help_btn)
        lock = QLabel(tr("🔒 Nada sai do seu computador"))
        lock.setObjectName("lockLabel")
        lock.setToolTip(tr("Toda a conversão, o OCR, a anonimização e a exportação acontecem aqui, no "
                           "seu computador. O Markinho não envia documentos, textos nem nomes de "
                           "arquivos para a internet. Detalhes em Ajuda > Privacidade."))
        lay.addWidget(lock)

    def set_mode(self, mode: str) -> None:
        self.simple_btn.setChecked(mode == "simple")
        self.full_btn.setChecked(mode != "simple")
        self.help_btn.setVisible(mode == "simple")          # no Completo, a Ajuda está na barra de menus


class SimpleView(QWidget):
    """O modo Simples. ``mw`` é a janela principal (MainWindow)."""

    QUICK_FORMATS = (("docx", None), ("docx", "abnt"), ("pdf", None), ("xlsx", None), ("html", None))

    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 4, 18, 14)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
        self.stack.addWidget(self._drop_page())
        self.stack.addWidget(self._result_page())

    # ---- antes: soltar ou escolher arquivos ----
    def _drop_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("dropZone")
        v = QVBoxLayout(page)
        v.addStretch(2)
        icon = QLabel("📄")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 54px;")
        v.addWidget(icon)
        title = QLabel(tr("Arraste seus documentos para cá"))
        title.setObjectName("dropTitle")
        title.setAlignment(Qt.AlignCenter)
        v.addWidget(title)
        sub = QLabel(tr("PDF, Word, Excel, PowerPoint, páginas da web, e-books, fotos e escaneados"))
        sub.setObjectName("muted")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        v.addWidget(sub)
        row = QHBoxLayout()
        row.addStretch(1)
        pick = _primary(QPushButton(tr("Escolher arquivos…")))
        pick.setObjectName("bigAction")
        pick.clicked.connect(self.mw.add_files_dialog)
        paste = QPushButton(tr("📋 Colar"))
        paste.setObjectName("bigAction")
        paste.setToolTip(tr("Cola e converte um texto ou imagem copiados (Ctrl+Shift+V)"))
        paste.clicked.connect(self.mw.act_paste.trigger)
        row.addWidget(pick)
        row.addWidget(paste)
        row.addStretch(1)
        v.addSpacing(14)
        v.addLayout(row)
        self.anon = QCheckBox(tr("Esconder dados pessoais (CPF, e-mails, nomes…)"))
        self.anon.setToolTip(tr("Anonimiza o texto convertido: troca CPF, CNPJ, e-mails, telefones e nomes com pista "
                                "por marcadores. Revise sempre o resultado — nunca é 100%."))
        self.anon.toggled.connect(self._anon_toggled)
        arow = QHBoxLayout()
        arow.addStretch(1)
        arow.addWidget(self.anon)
        arow.addStretch(1)
        v.addSpacing(10)
        v.addLayout(arow)
        hint = QLabel(tr("Dica: no Windows, clique com o botão direito num arquivo › <b>Markinho</b> › "
                         "Converter para Markdown aqui"))
        hint.setObjectName("muted")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        v.addSpacing(12)
        v.addWidget(hint)
        v.addStretch(3)
        return page

    # ---- depois: lista + texto + 4 ações ----
    def _result_page(self) -> QWidget:
        page = QWidget()
        h = QHBoxLayout(page)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(14)
        side = QFrame()
        side.setObjectName("card")
        side.setFixedWidth(280)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(10, 10, 10, 10)
        self.count = QLabel()
        self.count.setObjectName("cardTitle")
        sv.addWidget(self.count)
        self.list_slot = QVBoxLayout()           # a lista de arquivos do Completo é emprestada aqui
        sv.addLayout(self.list_slot, 1)
        more = QPushButton(tr("＋ Adicionar mais"))
        more.clicked.connect(self.mw.add_files_dialog)
        save_all = QPushButton(tr("💾 Salvar todos"))
        save_all.clicked.connect(self.mw.save_all)
        sv.addWidget(more)
        sv.addWidget(save_all)
        h.addWidget(side)

        right = QVBoxLayout()
        right.setSpacing(10)
        acts = QHBoxLayout()
        acts.setSpacing(10)
        self.save_btn = _primary(QPushButton(tr("💾 Salvar")))
        self.save_btn.setToolTip(tr("Salvar o documento aberto como .md (Ctrl+S)"))
        self.save_btn.clicked.connect(self.mw.save_current)
        self.copy_btn = QPushButton(tr("📋 Copiar"))
        self.copy_btn.setToolTip(tr("Copiar o texto (Markdown) para colar em outro programa"))
        self.copy_btn.clicked.connect(self.mw.copy_current)
        self.ai_btn = QPushButton(tr("✨ Copiar para IA"))
        self.ai_btn.setToolTip(tr("Texto enxuto, contagem de tokens e divisão em partes para ChatGPT, Claude, Gemini…"))
        self.ai_btn.clicked.connect(self.mw.copy_for_ai)
        self.export_btn = QToolButton()
        self.export_btn.setText(tr("⤴ Exportar"))
        self.export_btn.setPopupMode(QToolButton.InstantPopup)
        self.export_btn.setMenu(self._export_menu())
        for b in (self.save_btn, self.copy_btn, self.ai_btn, self.export_btn):
            b.setObjectName("bigAction")
            b.setCursor(Qt.PointingHandCursor)
            acts.addWidget(b)
        acts.addStretch(1)
        self.words = QLabel()
        self.words.setObjectName("muted")
        acts.addWidget(self.words)
        right.addLayout(acts)
        self.warn = QLabel()
        self.warn.setObjectName("warnBar")
        self.warn.setWordWrap(True)
        self.warn.setTextFormat(Qt.RichText)
        self.warn.linkActivated.connect(lambda _l: self.mw.open_in_complete(review=True))
        self.warn.setVisible(False)
        right.addWidget(self.warn)
        from .gui import PreviewBrowser

        self.preview = PreviewBrowser()
        self.preview.setOpenExternalLinks(True)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.status = QLabel()
        self.status.setObjectName("muted")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setWordWrap(True)
        self.status.setVisible(False)
        right.addWidget(self.status)
        right.addWidget(self.preview, 1)
        h.addLayout(right, 1)
        return page

    def _export_menu(self) -> QMenu:
        from .exporter import FORMATS_BY_ID, format_backends

        menu = QMenu(self)
        labels = {("docx", None): tr("Word (.docx) — para editar e imprimir"),
                  ("docx", "abnt"): tr("Word no padrão ABNT (trabalhos acadêmicos)"),
                  ("pdf", None): tr("PDF"),
                  ("xlsx", None): tr("Excel — só as tabelas (.xlsx)"),
                  ("html", None): tr("Página web (.html)")}
        for fid, template in self.QUICK_FORMATS:
            if fid in FORMATS_BY_ID and format_backends(FORMATS_BY_ID[fid]):
                a = menu.addAction(labels[(fid, template)])
                a.triggered.connect(lambda _c=False, f=fid, t=template: self.mw.quick_export(f, t))
        menu.addSeparator()
        more = menu.addAction(tr("Mais formatos… (EPUB, ODT, PowerPoint, LaTeX, pedaços para IA)"))
        more.triggered.connect(lambda: (self.mw.set_mode("complete"), self.mw.export_dialog()))
        return menu

    # ---- anonimizar: a mesma opção do painel de configurações ----
    def _anon_toggled(self, on: bool) -> None:
        box = self.mw.panel.anon
        if box.isChecked() != on:
            box.setChecked(on)
        if box.isChecked() != on:                 # o painel recusou (aviso não aceito)
            self.anon.blockSignals(True)
            self.anon.setChecked(box.isChecked())
            self.anon.blockSignals(False)

    # ---- atualizar com o estado da janela ----
    def refresh(self) -> None:
        mw = self.mw
        n = len(mw.entries)
        self.anon.blockSignals(True)
        self.anon.setChecked(mw.panel.anon.isChecked())
        self.anon.blockSignals(False)
        if not n:
            self.stack.setCurrentIndex(0)
            return
        self.stack.setCurrentIndex(1)
        self.count.setText(tr("Seus documentos ({0})").format(n))
        e = mw._current()
        ready = e is not None and e.result is not None and not e.busy and not e.error
        for b in (self.save_btn, self.copy_btn, self.ai_btn, self.export_btn):
            b.setEnabled(ready)
        self.preview.setVisible(ready)
        self.status.setVisible(not ready)
        self.warn.setVisible(False)
        if e is None:
            self.status.setText(tr("Selecione um documento na lista."))
            self.words.clear()
            return
        if e.error:
            self.status.setText(tr("⚠ Não foi possível converter {0}:\n{1}").format(Path(e.path).name, e.error))
            self.words.clear()
            return
        if not ready:
            done = f" — {e.progress[0]}/{e.progress[1]}" if e.progress else ""
            self.status.setText(tr("Convertendo {0}…").format(Path(e.path).name) + done)
            self.words.clear()
            return
        self.words.setText(tr("≈ {0} palavras").format(num(len(e.text.split()))))
        mw._render_preview(self.preview)
        from .core import is_alert

        notes = [w for w in e.result.warnings if w and is_alert(w)]
        if e.result.review_pages:
            pages = ", ".join(str(p) for p in e.result.review_pages[:12]) + ("…" if len(e.result.review_pages) > 12 else "")
            notes.insert(0, tr("Revise a(s) página(s) {0}: podem ter erros de leitura.").format(pages))
        if notes:
            more = tr(" (e mais {0})").format(len(notes) - 1) if len(notes) > 1 else ""
            self.warn.setText("⚠ " + html.escape(notes[0]) + more
                              + " &nbsp;<a href='#completo'>" + tr("Conferir no modo completo →") + "</a>")
            self.warn.setVisible(True)
