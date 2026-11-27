# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Janelas das ferramentas: Copiar para IA, Exportar como skill, Dividir por títulos, Pasta monitorada,
Relatório de erro e Primeira abertura."""
from __future__ import annotations

from .i18n import num, tr

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton,
    QRadioButton, QSpinBox, QVBoxLayout,
)


WARN_STYLE = ("QLabel{background: #fff3cd; color: #3d2e00; border: 1px solid #e0b100; border-radius: 4px; "
              "padding: 6px; font-size: 12px;}")


def anon_warning(text: str | None = None) -> QLabel:
    """Quadro amarelo com o aviso de responsabilidade da anonimização (sempre visível, não é dica)."""
    from .anonymize import DISCLAIMER

    lb = QLabel("⚠ <b>" + (text or DISCLAIMER) + "</b>")
    lb.setWordWrap(True)
    lb.setStyleSheet(WARN_STYLE)
    return lb


def _hint(text: str) -> QLabel:
    lb = QLabel(text)
    lb.setWordWrap(True)
    lb.setStyleSheet("color: palette(window-text); font-size: 11px;")
    return lb


# --------------------------------------------------------------------------- #
# Copiar para IA
# --------------------------------------------------------------------------- #
class AiCopyDialog(QDialog):
    """Texto enxuto para colar no ChatGPT, Claude, Gemini…, com tokens e divisão em partes."""

    def __init__(self, parent, markdown: str, settings: QSettings):
        from .aitools import LIMITS, estimate_tokens, prepare

        super().__init__(parent)
        self.setWindowTitle(tr("Copiar para IA"))
        self.resize(580, 480)
        self.settings = settings
        self.text = prepare(markdown)
        lay = QVBoxLayout(self)
        tokens = estimate_tokens(self.text)
        lay.addWidget(QLabel(tr("<b>Copiar o texto para colar no ChatGPT, Claude, Gemini…</b>")))
        lay.addWidget(_hint(tr("O Markinho <b>não usa IA nem gasta tokens</b> aqui: ele só prepara o texto (tira "
                            "imagens, comentários e marcas de página) e copia para a área de transferência. "
                            "Nada é enviado para a internet.")))
        size = QLabel(tr('Tamanho do texto: <b>{0} caracteres ≈ {1} tokens</b>').format(num(len(self.text)), num(tokens)))
        lay.addWidget(size)
        lay.addWidget(_hint(tr("“Tokens” são a medida de tamanho que os assistentes de IA usam. Cada assistente tem um "
                            "limite por mensagem; se o texto passar do limite, divida em partes e cole uma por vez. "
                            "A contagem é uma estimativa.")))
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Se for grande demais, dividir em partes de até:")))
        self.limit = QComboBox()
        for label, val in LIMITS:
            self.limit.addItem(label, val)
        self.limit.addItem(tr("Outro valor…"), -1)
        self.custom = QSpinBox()
        self.custom.setRange(1_000, 2_000_000)
        self.custom.setSingleStep(1_000)
        self.custom.setSuffix(tr(" tokens"))
        self.custom.setValue(int(settings.value("ai/custom", 50_000)))
        saved = int(settings.value("ai/limit", 0))
        i = self.limit.findData(saved)
        self.limit.setCurrentIndex(i if i >= 0 else self.limit.count() - 1)
        row.addWidget(self.limit, 1)
        row.addWidget(self.custom)
        lay.addLayout(row)
        self.parts_list = QListWidget()
        lay.addWidget(self.parts_list, 1)
        self.status = _hint("")
        lay.addWidget(self.status)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText(tr("Fechar"))
        self.copy_btn = bb.addButton(tr("Copiar parte selecionada"), QDialogButtonBox.ActionRole)
        self.copy_btn.clicked.connect(self._copy_selected)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.limit.currentIndexChanged.connect(self._refresh)
        self.custom.valueChanged.connect(self._refresh)
        self.parts_list.itemDoubleClicked.connect(lambda _i: self._copy_selected())
        self._refresh()

    def _max_tokens(self) -> int:
        v = self.limit.currentData()
        return self.custom.value() if v == -1 else int(v)

    def _refresh(self) -> None:
        from .aitools import estimate_tokens, split_for_ai

        self.custom.setVisible(self.limit.currentData() == -1)
        self.settings.setValue("ai/limit", self.limit.currentData())
        self.settings.setValue("ai/custom", self.custom.value())
        self.parts = split_for_ai(self.text, self._max_tokens())
        self.parts_list.clear()
        for k, p in enumerate(self.parts, 1):
            label = tr("Texto inteiro") if len(self.parts) == 1 else tr('Parte {0} de {1}').format(k, len(self.parts))
            it = QListWidgetItem(tr('{0} — ≈ {1} tokens').format(label, num(estimate_tokens(p))))
            it.setData(Qt.UserRole, k - 1)
            self.parts_list.addItem(it)
        self.parts_list.setCurrentRow(0)
        self.copy_btn.setText(tr("Copiar texto") if len(self.parts) == 1 else tr("Copiar parte selecionada"))
        if len(self.parts) == 1:
            limit = self._max_tokens()
            self.status.setText(tr("O texto cabe inteiro numa mensagem: não precisa dividir.") if limit else
                                tr("Texto inteiro, sem divisão."))
        else:
            self.status.setText(tr('O texto foi dividido em {0} partes. Cole em ordem, uma por mensagem; cada parte avisa o assistente para esperar a última antes de responder. Duplo clique copia.').format(len(self.parts)))

    def _copy_selected(self) -> None:
        it = self.parts_list.currentItem()
        k = it.data(Qt.UserRole) if it else 0
        QGuiApplication.clipboard().setText(self.parts[k])
        what = tr("Texto copiado") if len(self.parts) == 1 else tr("Parte {0} copiada").format(k + 1)
        self.status.setText(tr("✓ {0}. Cole no assistente com Ctrl+V.").format(what))
        if k + 1 < len(self.parts):
            self.parts_list.setCurrentRow(k + 1)


# --------------------------------------------------------------------------- #
# Exportar como skill para IA
# --------------------------------------------------------------------------- #
class SkillDialog(QDialog):
    """Pacote “skill” (SKILL.md + capítulos) para assistentes consultarem o documento sob demanda."""

    DEST_FOLDER, DEST_ZIP, DEST_CLAUDE = 0, 1, 2

    def __init__(self, parent, current: tuple[str, str] | None, all_docs: list[tuple[str, str]],
                 settings: QSettings, start_dir: str):
        super().__init__(parent)
        self.setWindowTitle(tr("Exportar como skill para IA"))
        self.resize(640, 560)
        self.current, self.all_docs, self.settings = current, all_docs, settings
        self.pack = None
        self._name_edited = self._desc_edited = False
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr("<b>Transformar o documento numa skill que o assistente de IA consulta quando precisa</b>")))
        lay.addWidget(_hint(tr("Cria um índice (SKILL.md) e um arquivo por capítulo. O assistente (Claude Code, "
                               "Claude.ai, Codex, Copilot…) lê o índice e abre só o capítulo de que precisa, em vez de "
                               "carregar o documento inteiro — gasta bem menos tokens e responde pelo texto real. "
                               "Feito aqui, sem IA e sem internet: os capítulos vêm dos títulos do documento.")))
        lay.addWidget(_hint(tr("🔒 O Markinho só cria os arquivos aqui. Se você usar a skill num assistente on-line "
                               "(Claude.ai, por exemplo), o texto dos capítulos vai para esse serviço — em documentos "
                               "sigilosos, anonimize antes.")))
        form = QFormLayout()
        self.scope = QComboBox()
        if current is not None:
            self.scope.addItem(tr("Documento atual"), "current")
        if len(all_docs) > 1:
            self.scope.addItem(tr("Todos os documentos convertidos ({0}) numa skill só").format(len(all_docs)), "all")
        form.addRow(tr("O que exportar"), self.scope)
        self.name = QLineEdit()
        self.name.setToolTip(tr("Letras minúsculas sem acento, números e hífens. Vira o comando no assistente (ex.: /manual-do-produto)."))
        self.name.textEdited.connect(lambda _t: setattr(self, "_name_edited", True))
        form.addRow(tr("Nome da skill:"), self.name)
        self.desc = QPlainTextEdit()
        self.desc.setFixedHeight(70)
        self.desc.setToolTip(tr("O assistente lê esta frase para decidir quando usar a skill: diga do que o documento trata."))
        self.desc.textChanged.connect(self._desc_changed)
        form.addRow(tr("Descrição:"), self.desc)
        lay.addLayout(form)
        self.preview = _hint("")
        lay.addWidget(self.preview)
        box = QGroupBox(tr("Onde salvar"))
        bl = QVBoxLayout(box)
        self.dest = QButtonGroup(self)
        opts = [(self.DEST_FOLDER, tr("Numa pasta (para copiar para a pasta de skills do seu assistente)")),
                (self.DEST_ZIP, tr("Arquivo .zip (para enviar nas configurações do Claude.ai, na parte de Skills)")),
                (self.DEST_CLAUDE, tr("Instalar direto no Claude Code deste computador ({0})").format(
                    self._claude_dir_label()))]
        for val, text in opts:
            rb = QRadioButton(text)
            self.dest.addButton(rb, val)
            bl.addWidget(rb)
        saved = int(settings.value("skill/dest", self.DEST_FOLDER) or 0)
        (self.dest.button(saved) or self.dest.button(self.DEST_FOLDER)).setChecked(True)
        row = QHBoxLayout()
        self.folder = QLineEdit(start_dir)
        b = QPushButton("…")
        b.setFixedWidth(32)
        b.clicked.connect(self._pick)
        row.addWidget(self.folder)
        row.addWidget(b)
        bl.addLayout(row)
        lay.addWidget(box)
        self.dest.idToggled.connect(lambda _i, _on: self._dest_changed())
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok = bb.button(QDialogButtonBox.Ok)
        self.ok.setText(tr("Criar skill"))
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.scope.currentIndexChanged.connect(lambda _i: self._rebuild(reset=True))
        self._dest_changed()
        self._rebuild(reset=True)

    @staticmethod
    def _claude_dir_label() -> str:
        from .skillpack import claude_code_dir

        p = claude_code_dir()
        try:
            return "~/" + p.relative_to(Path.home()).as_posix()
        except ValueError:
            return str(p)

    def _docs(self) -> list[tuple[str, str]]:
        if self.scope.currentData() == "current" and self.current is not None:
            return [self.current]
        return self.all_docs

    def _desc_changed(self) -> None:
        if not getattr(self, "_filling", False):
            self._desc_edited = True

    def _rebuild(self, reset: bool = False) -> None:
        from .skillpack import build_skill, summary

        if reset:
            self._name_edited = self._desc_edited = False
        try:
            self.pack = build_skill(self._docs(), self.name.text() if self._name_edited else "",
                                    description=self.desc.toPlainText() if self._desc_edited else "")
        except ValueError as exc:
            self.pack = None
            self.preview.setText(str(exc))
            self.ok.setEnabled(False)
            return
        self.ok.setEnabled(True)
        if not self._name_edited:
            self.name.setText(self.pack.name)
        if not self._desc_edited:
            self._filling = True
            self.desc.setPlainText(self.pack.description)
            self._filling = False
        self.preview.setText(summary(self.pack))

    def _dest_changed(self) -> None:
        self.folder.setEnabled(self.dest.checkedId() != self.DEST_CLAUDE)

    def _pick(self) -> None:
        d = QFileDialog.getExistingDirectory(self, tr("Pasta de destino"), self.folder.text())
        if d:
            from .gui import remember_dir

            remember_dir(self.settings, d, "save")
            self.folder.setText(d)

    def target(self) -> Path:
        """Pasta da skill (ou arquivo .zip) que será gravado."""
        from .skillpack import claude_code_dir, skill_name

        name = skill_name(self.name.text())
        dest = self.dest.checkedId()
        if dest == self.DEST_CLAUDE:
            return claude_code_dir() / name
        if dest == self.DEST_ZIP:
            return Path(self.folder.text()) / f"{name}.zip"
        return Path(self.folder.text()) / name

    def _save(self) -> None:
        from .skillpack import to_zip, write_folder

        self._rebuild()                       # pega o nome e a descrição como estão agora
        if self.pack is None:
            return
        target = self.target()
        if target.exists():
            ask = QMessageBox.question(self, tr("Exportar como skill para IA"),
                                       tr("{0} já existe. Substituir os arquivos da skill?").format(target))
            if ask != QMessageBox.Yes:
                return
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if self.dest.checkedId() == self.DEST_ZIP:
                target.write_bytes(to_zip(self.pack))
            else:
                write_folder(self.pack, target.parent, replace=True)
        except OSError as exc:
            QMessageBox.critical(self, tr("Exportar como skill para IA"), tr("Não foi possível salvar:\n{0}").format(exc))
            return
        self.settings.setValue("skill/dest", self.dest.checkedId())
        how = {self.DEST_FOLDER: tr("Copie a pasta para a pasta de skills do seu assistente (no Claude Code: "
                                    "~/.claude/skills; em outros: veja a documentação dele)."),
               self.DEST_ZIP: tr("No Claude.ai, envie o .zip nas configurações, na parte de Skills."),
               self.DEST_CLAUDE: tr("Abra o Claude Code de novo e peça, por exemplo: “/{0} do que trata o capítulo 2?”").format(
                   self.pack.name)}[self.dest.checkedId()]
        QMessageBox.information(self, tr("Exportar como skill para IA"),
                                tr("Skill criada em:\n{0}\n\n{1}").format(target, how))
        self.accept()


# --------------------------------------------------------------------------- #
# Atualizações (sem internet: só lembra e abre a página se a pessoa clicar)
# --------------------------------------------------------------------------- #
class UpdateDialog(QDialog):
    """Ajuda > Procurar atualizações… e o lembrete a cada 2 meses."""

    def __init__(self, parent, settings: QSettings, reminder: bool = False):
        from . import __version__
        from .edition import label
        from .updates import RELEASES_URL, build_date

        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(tr("Atualizações do Markinho"))
        self.resize(520, 300)
        lay = QVBoxLayout(self)
        built = build_date()
        from .i18n import language

        when = (built.strftime("%d/%m/%Y") if language() in ("pt", "es") else built.isoformat()) if built else ""
        version = tr("Versão instalada: <b>{0}</b> · edição {1}").format(__version__, label())
        if when:
            version += tr(" · de {0}").format(when)
        head = tr("<h3>Hora de conferir se há uma versão nova</h3>") if reminder else tr("<h3>Procurar atualizações</h3>")
        lay.addWidget(QLabel(head + version))
        lay.addWidget(_hint(tr("Para proteger a sua privacidade, o Markinho <b>não acessa a internet</b> — por isso ele "
                               "não sabe sozinho se saiu uma versão nova (com correções e melhorias). Confira de vez em "
                               "quando a página de versões do projeto no GitHub; para atualizar, baixe o instalador da "
                               "mesma edição e instale por cima: as suas configurações são mantidas.")))
        link = QLabel(f"<a href='{RELEASES_URL}'>{RELEASES_URL}</a>")
        link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link.linkActivated.connect(lambda _u: self.open_page())
        lay.addWidget(link)
        self.remind = QCheckBox(tr("Lembrar a cada 2 meses"))
        self.remind.setChecked(not settings.value("updates/never", False, type=bool))
        lay.addWidget(self.remind)
        bb = QDialogButtonBox()
        b_open = bb.addButton(tr("Abrir a página de versões"), QDialogButtonBox.AcceptRole)
        b_open.clicked.connect(self.open_page)
        bb.addButton(tr("Lembrar depois") if reminder else tr("Fechar"), QDialogButtonBox.RejectRole)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.finished.connect(lambda _r: self._save())

    def _save(self) -> None:
        from .updates import snooze

        self.settings.setValue("updates/never", not self.remind.isChecked())
        snooze(self.settings)                     # o próximo lembrete conta a partir de hoje

    def open_page(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from .updates import RELEASES_URL

        QDesktopServices.openUrl(QUrl(RELEASES_URL))     # só quando a pessoa clica
        self.accept()


# --------------------------------------------------------------------------- #
# Pacotes extras (modelos opcionais)
# --------------------------------------------------------------------------- #
class PacksDialog(QDialog):
    """Ferramentas > Pacotes extras: o que cada um faz, para quem serve e instalar a partir do .zip."""

    def __init__(self, parent):
        from . import __version__
        from .packs import PACKS, available

        super().__init__(parent)
        self.setWindowTitle(tr("Pacotes extras"))
        self.resize(640, 640)
        self.version = __version__
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr("<h3>Pacotes extras</h3>")))
        lay.addWidget(_hint(tr("Recursos de IA que poucas pessoas usam vêm à parte, para o instalador ficar menor. "
                               "Instale só se precisar: <b>baixe o arquivo .zip uma vez</b> na página de versões "
                               "(pelo navegador) e escolha “Instalar de um arquivo…”. Depois ele fica no "
                               "computador e funciona sem internet. O Markinho não baixa nada sozinho.")))
        self.status: dict[str, QLabel] = {}
        self.remove_btn: dict[str, QPushButton] = {}
        for pk in PACKS:
            box = QGroupBox(tr("{0} (~{1} MB)").format(pk.name, num(pk.size_mb)))
            bl = QVBoxLayout(box)
            st = QLabel()
            self.status[pk.id] = st
            bl.addWidget(st)
            for text in (pk.what, pk.who, pk.skip):
                bl.addWidget(_hint(text))
            if not available(pk):
                bl.addWidget(anon_warning(pk.need))
            row = QHBoxLayout()
            b_inst = QPushButton(tr("Instalar de um arquivo…"))
            b_inst.setEnabled(available(pk))
            b_inst.clicked.connect(lambda _c=False, p=pk: self.install(p))
            b_get = QPushButton(tr("Abrir a página de download"))
            b_get.clicked.connect(lambda _c=False, p=pk: self.open_page(p))
            b_rm = QPushButton(tr("Remover"))
            b_rm.clicked.connect(lambda _c=False, p=pk: self.remove(p))
            self.remove_btn[pk.id] = b_rm
            row.addWidget(b_inst)
            row.addWidget(b_get)
            row.addStretch(1)
            row.addWidget(b_rm)
            bl.addLayout(row)
            lay.addWidget(box)
        lay.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.refresh()

    def refresh(self) -> None:
        from .packs import PACKS, installed, removable

        for pk in PACKS:
            ok = installed(pk)
            self.status[pk.id].setText(tr("✔ <b>Instalado</b>") if ok else tr("Não instalado"))
            self.remove_btn[pk.id].setEnabled(removable(pk))

    def open_page(self, pk) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from .packs import PACKS_PAGE

        QDesktopServices.openUrl(QUrl(PACKS_PAGE))     # o navegador baixa, não o Markinho

    def install(self, pk, path: str | None = None) -> bool:
        from PySide6.QtWidgets import QApplication, QProgressDialog

        from .packs import PackError, install_from_zip

        if path is None:
            path, _f = QFileDialog.getOpenFileName(self, tr("Escolha o arquivo do pacote"), str(Path.home()),
                                                   tr("Pacote do Markinho (*.zip)"))
            if not path:
                return False
        prog = QProgressDialog(tr("Conferindo e instalando o pacote…"), "", 0, 1000, self)
        prog.setCancelButton(None)
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(0)
        last = [-1]

        def step(done: int, total: int) -> None:
            v = int(done * 1000 / max(total, 1))
            if v != last[0]:
                last[0] = v
                prog.setValue(v)
                QApplication.processEvents()

        try:
            got = install_from_zip(path, step)
        except (PackError, OSError) as exc:
            prog.close()
            QMessageBox.warning(self, tr("Pacotes extras"), tr("Não foi possível instalar: {0}").format(exc))
            return False
        prog.close()
        self.refresh()
        msg = tr("Pacote “{0}” instalado. Ele fica no computador e funciona sem internet.").format(got.name)
        if got.id != pk.id:
            msg += "\n" + tr("(O arquivo escolhido era de outro pacote.)")
        QMessageBox.information(self, tr("Pacotes extras"), msg)
        return True

    def remove(self, pk) -> None:
        from .packs import uninstall

        if QMessageBox.question(self, tr("Pacotes extras"),
                                tr("Remover o pacote “{0}”? Para usá-lo de novo, será preciso instalar o .zip "
                                   "outra vez.").format(pk.name)) != QMessageBox.Yes:
            return
        uninstall(pk)
        self.refresh()


# --------------------------------------------------------------------------- #
# Dividir por títulos
# --------------------------------------------------------------------------- #
class SplitDialog(QDialog):
    def __init__(self, parent, markdown: str, assets: dict[str, bytes], settings: QSettings, start_dir: str):
        super().__init__(parent)
        self.setWindowTitle(tr("Dividir por títulos"))
        self.md, self.assets, self.settings = markdown, assets, settings
        lay = QVBoxLayout(self)
        lay.addWidget(_hint(tr("Cria um arquivo .md para cada capítulo ou seção, numerados na ordem "
                            "(01_Introdução.md, 02_…). Útil para Obsidian, documentação e IA.")))
        form = QFormLayout()
        self.level = QComboBox()
        self.level.addItem(tr("Títulos de nível 1 (# Capítulo)"), 1)
        self.level.addItem(tr("Títulos de nível 1 e 2 (## Seção)"), 2)
        self.level.addItem(tr("Títulos de nível 1 a 3"), 3)
        form.addRow(tr("Cortar em:"), self.level)
        row = QHBoxLayout()
        self.folder = QLineEdit(start_dir)
        b = QPushButton("…")
        b.setFixedWidth(32)
        b.clicked.connect(self._pick)
        row.addWidget(self.folder)
        row.addWidget(b)
        form.addRow(tr("Pasta:"), row)
        lay.addLayout(form)
        self.preview = _hint("")
        lay.addWidget(self.preview)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(tr("Dividir e salvar"))
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.level.currentIndexChanged.connect(self._update)
        self._update()

    def _pick(self) -> None:
        d = QFileDialog.getExistingDirectory(self, tr("Pasta para os arquivos"), self.folder.text())
        if d:
            from .gui import remember_dir

            remember_dir(self.settings, d, "save")
            self.folder.setText(d)

    def _update(self) -> None:
        from .splitter import split_by_headings

        self.parts = split_by_headings(self.md, self.level.currentData())
        names = ", ".join(t for t, _ in self.parts[:6]) + ("…" if len(self.parts) > 6 else "")
        self.preview.setText(tr('{0} arquivo(s): {1}').format(len(self.parts), names))

    def _save(self) -> None:
        from .assets import write_assets
        from .naming import clean

        folder = Path(self.folder.text())
        try:
            folder.mkdir(parents=True, exist_ok=True)
            digits = max(2, len(str(len(self.parts))))
            written = 0
            for k, (title, text) in enumerate(self.parts, 1):
                name = f"{k:0{digits}d}_{clean(title) or 'parte'}.md"
                target = folder / name
                n = 2
                while target.exists():
                    target = folder / f"{Path(name).stem}_{n}.md"
                    n += 1
                target.write_text(text, encoding="utf-8")
                if self.assets:
                    write_assets(text, self.assets, folder)        # só as imagens usadas nesta parte
                written += 1
        except OSError as exc:
            QMessageBox.critical(self, tr("Dividir por títulos"), tr('Não foi possível salvar:\n{0}').format(exc))
            return
        QMessageBox.information(self, tr("Dividir por títulos"), tr('{0} arquivo(s) salvo(s) em:\n{1}').format(written, folder))
        self.accept()


# --------------------------------------------------------------------------- #
# Pasta monitorada
# --------------------------------------------------------------------------- #
class WatchDialog(QDialog):
    def __init__(self, parent, settings: QSettings):
        super().__init__(parent)
        self.setWindowTitle(tr("Pasta monitorada"))
        self.settings = settings
        lay = QVBoxLayout(self)
        lay.addWidget(_hint(tr("Enquanto o Markinho estiver aberto, todo arquivo novo que aparecer na pasta "
                            "(baixado, escaneado, copiado…) é convertido sozinho com as configurações atuais. "
                            "Os arquivos que já estavam lá não são convertidos.")))
        self.enabled = QCheckBox(tr("Monitorar a pasta"))
        self.enabled.setChecked(settings.value("watch/enabled", False, type=bool))
        lay.addWidget(self.enabled)
        form = QFormLayout()
        self.folder = self._row(form, tr("Pasta:"), settings.value("watch/folder", str(Path.home() / "Downloads")))
        self.same = QCheckBox(tr("Salvar o .md na mesma pasta"))
        self.same.setChecked(settings.value("watch/same", True, type=bool))
        form.addRow(self.same)
        self.out = self._row(form, tr("Salvar em:"), settings.value("watch/out", str(Path.home() / "Documents" / "Markinho")))
        self.same.toggled.connect(lambda v: self.out.setEnabled(not v))
        self.out.setEnabled(not self.same.isChecked())
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _row(self, form, label, value) -> QLineEdit:
        row = QHBoxLayout()
        edit = QLineEdit(value)
        b = QPushButton("…")
        b.setFixedWidth(32)
        b.clicked.connect(lambda: (d := QFileDialog.getExistingDirectory(self, label, edit.text())) and edit.setText(d))
        row.addWidget(edit)
        row.addWidget(b)
        form.addRow(label, row)
        return edit

    def _ok(self) -> None:
        if self.enabled.isChecked() and not Path(self.folder.text()).is_dir():
            QMessageBox.warning(self, tr("Pasta monitorada"), tr("A pasta escolhida não existe."))
            return
        s = self.settings
        s.setValue("watch/enabled", self.enabled.isChecked())
        s.setValue("watch/folder", self.folder.text())
        s.setValue("watch/same", self.same.isChecked())
        s.setValue("watch/out", self.out.text())
        self.accept()


# --------------------------------------------------------------------------- #
# Relatório de erro
# --------------------------------------------------------------------------- #
class ErrorReportDialog(QDialog):
    def __init__(self, parent, settings: QSettings):
        from .diagnostics import report_text

        super().__init__(parent)
        self.setWindowTitle(tr("Relatório de erro"))
        self.resize(720, 560)
        lay = QVBoxLayout(self)
        lay.addWidget(_hint(tr("<b>O que este relatório contém:</b> versão e edição do Markinho; sistema, processador, "
                            "memória, idioma e tela; motores disponíveis; suas configurações (sem pastas); e os erros "
                            "desde que o programa foi aberto — nome, tipo e tamanho do arquivo, a mensagem, detalhes "
                            "técnicos e a configuração usada naquela conversão. <b>Não contém o conteúdo dos "
                            "documentos</b>, e o nome do seu usuário do computador é omitido.<br>"
                            "<b>Nada é enviado:</b> você confere, salva e decide se manda ao suporte. "
                            "Veja Ajuda > Privacidade.")))
        self.settings = settings
        self.hide = QCheckBox(tr("Esconder os nomes dos arquivos (trocar por arquivo1.pdf, arquivo2.docx…)"))
        self.hide.toggled.connect(lambda v: self.text.setPlainText(report_text(self.settings, hide_names=v)))
        lay.addWidget(self.hide)
        self.text = QPlainTextEdit(report_text(settings))
        self.text.setReadOnly(True)
        lay.addWidget(self.text, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        save = bb.addButton(tr("Salvar…"), QDialogButtonBox.ActionRole)
        copy = bb.addButton(tr("Copiar"), QDialogButtonBox.ActionRole)
        save.clicked.connect(self._save)
        copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.text.toPlainText()))
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _save(self) -> None:
        import datetime as dt

        from .gui import recall_dir, remember_dir

        s = QSettings("Markinho", "Markinho")
        f, _ = QFileDialog.getSaveFileName(self, tr("Salvar relatório"),
                                           str(Path(recall_dir(s, "save")) / f"markinho-relatorio-{dt.date.today()}.txt"),
                                           tr("Texto (*.txt)"))
        if f:
            remember_dir(s, f, "save")
            Path(f).write_text(self.text.toPlainText(), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Primeira abertura
# --------------------------------------------------------------------------- #
PURPOSES = [
    ("ia", tr("Usar com IA (ChatGPT, Claude, Gemini, RAG)"),
     {"out/profile": "llm", "out/images": "none", "out/frontmatter": False}),
    ("obsidian", tr("Notas no Obsidian"),
     {"out/profile": "obsidian", "out/images": "folder", "out/frontmatter": True}),
    ("docs", tr("Documentação, sites ou GitHub"),
     {"out/profile": "gfm", "out/images": "folder", "out/frontmatter": False}),
    ("outro", tr("Outro / ainda não sei"), {"out/profile": "gfm", "out/images": "folder", "out/frontmatter": False}),
]


class FirstRunDialog(QDialog):
    def __init__(self, parent, settings: QSettings):
        super().__init__(parent)
        self.setWindowTitle(tr("Bem-vindo ao Markinho"))
        self.settings = settings
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr("<h3>Para que você vai usar o Markinho?</h3>")))
        lay.addWidget(_hint(tr("Isso só ajusta as opções iniciais. Dá para mudar depois no painel Configurações "
                            "ou em Ferramentas > Assistente inicial.")))
        box = QGroupBox()
        bl = QVBoxLayout(box)
        self.group = QButtonGroup(self)
        current = settings.value("ui/purpose", "outro")
        for k, (pid, label, _) in enumerate(PURPOSES):
            rb = QRadioButton(label)
            rb.setChecked(pid == current)
            self.group.addButton(rb, k)
            bl.addWidget(rb)
        if self.group.checkedId() < 0:
            self.group.button(len(PURPOSES) - 1).setChecked(True)
        lay.addWidget(box)
        self.simple = QCheckBox(tr("Começar no modo simples (dá para trocar a qualquer momento no alto da janela)"))
        self.simple.setChecked(str(settings.value("ui/mode", "simple")) == "simple")
        lay.addWidget(self.simple)
        from . import winshell

        self.shell = QCheckBox(tr("Adicionar o menu “Markinho” ao botão direito do Windows"))
        self.shell.setToolTip(tr("Converter arquivos clicando com o botão direito neles (no Windows 11: “Mostrar mais "
                              "opções”). Pode ser desligado em Ferramentas."))
        self.shell.setVisible(winshell.available())
        self.shell.setChecked(winshell.available() and not winshell.is_registered())
        lay.addWidget(self.shell)
        lay.addWidget(_hint(tr("Como usar: arraste arquivos para a janela e clique em Converter (F5). No Windows, "
                            "também dá para clicar com o botão direito num arquivo > Markinho > Converter para "
                            "Markdown aqui.")))
        bb = QDialogButtonBox(QDialogButtonBox.Ok)
        bb.button(QDialogButtonBox.Ok).setText(tr("Começar"))
        bb.accepted.connect(self._ok)
        lay.addWidget(bb)

    def _ok(self) -> None:
        pid, _, values = PURPOSES[max(0, self.group.checkedId())]
        for k, v in values.items():
            self.settings.setValue(k, v)
        self.settings.setValue("ui/purpose", pid)
        self.settings.setValue("ui/mode", "simple" if self.simple.isChecked() else "complete")
        self.settings.setValue("ui/first_run_done", True)
        if self.shell.isVisible() and self.shell.isChecked():
            try:
                from . import winshell

                winshell.register()
            except Exception:  # noqa: BLE001 — opcional: dá para ligar depois em Ferramentas
                pass
        self.accept()


# --------------------------------------------------------------------------- #
# Botão direito: andamento, escolha do formato e alerta de concluído
# --------------------------------------------------------------------------- #
class ProgressPopup(QDialog):
    """Janelinha com a porcentagem da tarefa. O usuário pode ocultá-la (e escolher não vê-la mais)."""

    def __init__(self, settings: QSettings, stop=None):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QProgressBar

        super().__init__(None, Qt.Window | Qt.WindowStaysOnTopHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle(tr("Markinho — convertendo"))
        self.settings, self._stop = settings, stop
        self.setMinimumWidth(380)
        lay = QVBoxLayout(self)
        self.label = QLabel(tr("Preparando…"))
        self.label.setWordWrap(True)
        lay.addWidget(self.label)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setFormat("%p%")
        lay.addWidget(self.bar)
        self.show_next = QCheckBox(tr("Mostrar esta janela nas próximas conversões"))
        self.show_next.setChecked(settings.value("quick/show_progress", True, type=bool))
        self.show_next.toggled.connect(lambda v: settings.setValue("quick/show_progress", v))
        lay.addWidget(self.show_next)
        row = QHBoxLayout()
        row.addWidget(_hint(tr("Ao terminar, aparece um aviso.")), 1)
        hide = QPushButton(tr("Ocultar"))
        hide.setToolTip(tr("Continua convertendo sem esta janela"))
        hide.clicked.connect(self.hide)
        stop_btn = QPushButton(tr("Parar"))
        stop_btn.clicked.connect(self._on_stop)
        row.addWidget(hide)
        row.addWidget(stop_btn)
        lay.addLayout(row)
        self._timer = QTimer(self, singleShot=True, interval=300, timeout=self._maybe_show)
        self._closed = False

    def start(self, total: int) -> None:
        self.set_total(total)
        if self.settings.value("quick/show_progress", True, type=bool):
            self._timer.start()             # tarefas muito rápidas nem mostram a janela

    def _maybe_show(self) -> None:
        if not self._closed:
            self.show()
            self.raise_()

    def set_total(self, total: int) -> None:
        self._total = max(1, total)

    def set_file(self, name: str, done: int, total: int) -> None:
        self._total = max(1, total)
        self.label.setText(tr('Convertendo <b>{0}</b>').format(name) + (f"  ({done + 1} de {total})" if total > 1 else ""))
        self.set_progress(done, total, 0.0)

    def set_progress(self, done: int, total: int, fraction: float) -> None:
        total = max(1, total)
        self.bar.setValue(int(round(100 * min(1.0, (done + max(0.0, min(fraction, 1.0))) / total))))

    def _on_stop(self) -> None:
        if self._stop:
            self._stop()
        self.label.setText(tr("Parando… (termina a página atual)"))

    def closeEvent(self, e):           # fechar no X = ocultar; a conversão continua
        e.ignore()
        self.hide()

    def close(self) -> bool:
        self._closed = True
        self._timer.stop()
        self.hide()
        return True


class ExportChoiceDialog(QDialog):
    """Escolher o formato para converter um .md (Word, PDF, HTML…)."""

    def __init__(self, parent, settings: QSettings):
        from .exporter import available_formats

        super().__init__(parent)
        self.setWindowTitle(tr("Converter Markdown para…"))
        self.settings = settings
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.fmt = QComboBox()
        for f in available_formats():
            if not f.id.startswith("chunks_"):
                self.fmt.addItem(f.label, f.id)
        self.fmt.setCurrentIndex(max(0, self.fmt.findData(settings.value("export/fmt", "docx"))))
        form.addRow(tr("Formato:"), self.fmt)
        self.abnt = QCheckBox(tr("Word no padrão ABNT (trabalhos acadêmicos)"))
        self.abnt.setChecked(settings.value("export/template", "") == "abnt")
        form.addRow(self.abnt)
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(tr("Continuar"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.fmt.currentIndexChanged.connect(lambda _i: self.abnt.setVisible(self.fmt.currentData() == "docx"))
        self.abnt.setVisible(self.fmt.currentData() == "docx")

    def values(self) -> tuple[str, dict, str]:
        from .exporter import FORMATS_BY_ID

        fid = self.fmt.currentData()
        self.settings.setValue("export/fmt", fid)
        opts: dict = {}
        if fid == "docx":
            self.settings.setValue("export/template", "abnt" if self.abnt.isChecked() else "")
            if self.abnt.isChecked():
                opts.update(template="abnt", number_sections=True)
        return fid, opts, FORMATS_BY_ID[fid].ext


class DoneDialog(QDialog):
    """Alerta de concluído, com atalhos para abrir o arquivo ou a pasta."""

    def __init__(self, results: list, stopped: bool = False, skipped: int = 0):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtWidgets import QStyle

        from .quick import summary

        super().__init__(None, Qt.Window | Qt.WindowStaysOnTopHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        title, text = summary(results) if results else (tr("Markinho"), tr("Nenhum arquivo convertido."))
        if stopped:
            title = tr("Markinho: conversão interrompida")
            text += tr(' {0} arquivo(s) não foram convertidos.').format(skipped) if skipped > 0 else ""
        self.setWindowTitle(title.replace("Markinho: ", "Markinho — "))
        lay = QVBoxLayout(self)
        head = QHBoxLayout()
        bad = [r for r in results if r.error]
        icon = QLabel()
        icon.setPixmap(self.style().standardIcon(
            QStyle.SP_MessageBoxWarning if (bad or stopped) else QStyle.SP_DialogApplyButton).pixmap(40, 40))
        head.addWidget(icon)
        msg = QLabel(f"<b>{title.replace('Markinho: ', '').capitalize()}</b><br>{text}")
        msg.setWordWrap(True)
        head.addWidget(msg, 1)
        lay.addLayout(head)
        try:
            from .quick import settings as _settings

            if results and _settings().value("anon/enabled", False, type=bool):
                lay.addWidget(anon_warning(tr("Os arquivos foram anonimizados. ") + __import__(
                    "markinho.anonymize", fromlist=["DISCLAIMER"]).DISCLAIMER))
        except Exception:  # noqa: BLE001
            pass
        if bad:
            det = QPlainTextEdit("\n".join(f"• {r.source.name}: {r.error}" for r in bad))
            det.setReadOnly(True)
            det.setMaximumHeight(140)
            lay.addWidget(det)
            lay.addWidget(_hint(tr("Dica: use “Abrir no Markinho” para ver os detalhes e testar outro motor.")))
        ok = [r for r in results if r.output and not r.error]
        bb = QDialogButtonBox(QDialogButtonBox.Ok)
        if len(ok) == 1 and ok[0].output.is_file():
            b = bb.addButton(tr("Abrir arquivo"), QDialogButtonBox.ActionRole)
            b.clicked.connect(lambda: (QDesktopServices.openUrl(QUrl.fromLocalFile(str(ok[0].output))), self.accept()))
        if ok:
            folder = ok[0].output.parent
            b = bb.addButton(tr("Abrir pasta"), QDialogButtonBox.ActionRole)
            b.clicked.connect(lambda: (QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))), self.accept()))
        bb.accepted.connect(self.accept)
        lay.addWidget(bb)
        self.setMinimumWidth(420)


# --------------------------------------------------------------------------- #
# Anonimizar
# --------------------------------------------------------------------------- #
class AnonDialog(QDialog):
    """O que anonimizar e como. Com `markdown`, mostra quanto foi encontrado e permite salvar uma cópia
    anonimizada (Ferramentas > Anonimizar um arquivo Markdown…)."""

    def __init__(self, parent, settings: QSettings, markdown: str | None = None, source: Path | None = None):
        from .anonymize import DISCLAIMER, KINDS, LIST_HELP, MODES
        from .quick import anon_options

        super().__init__(parent)
        self.settings, self.markdown, self.source = settings, markdown, source
        self.setWindowTitle(tr("Anonimizar dados pessoais") + (f" — {source.name}" if source else ""))
        self.resize(680, 640)
        o = anon_options(settings)
        lay = QVBoxLayout(self)
        lay.addWidget(_hint(tr("Troca dados pessoais do <b>Markdown convertido</b> (o arquivo original não muda). "
                            "Tudo acontece no seu computador, só com regras — nada vai para a internet. "
                            "<b>Revise sempre o resultado:</b> a anonimização automática nunca é 100% "
                            "(nomes sem pista, como “Rosa”, só saem pela sua lista).")))
        lay.addWidget(anon_warning(DISCLAIMER))
        from PySide6.QtWidgets import QFrame, QGridLayout, QScrollArea, QWidget

        body = QWidget()
        blay = QVBoxLayout(body)
        blay.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(body)
        lay.addWidget(scroll, 1)
        kinds = QGroupBox(tr("O que procurar no texto"))
        kl = QGridLayout(kinds)
        self.kind_boxes: dict[str, QCheckBox] = {}
        half = (len(KINDS) + 1) // 2
        for i, (kid, label, _, _) in enumerate(KINDS):
            cb = QCheckBox(label.split(" (")[0])
            cb.setToolTip(label)
            cb.setChecked(kid in o.kinds)
            self.kind_boxes[kid] = cb
            kl.addWidget(cb, i % half, i // half)
        blay.addWidget(kinds)
        words = QGroupBox(tr("Sua lista: nomes, empresas, lugares… (um por linha)"))
        wl = QVBoxLayout(words)
        self.words = QPlainTextEdit(o.words)
        self.words.setPlaceholderText(tr("João da Silva\nJoão = [PESSOA A]\nSr. Silva = [PESSOA A]\n"
                                      "Empresa Exemplo Ltda\nExemplo Ltda\nSão Paulo = [CIDADE]"))
        self.words.setFixedHeight(90)
        wl.addWidget(self.words)
        rules = QLabel(tr("<b>Como a lista funciona:</b> ") + LIST_HELP)
        rules.setWordWrap(True)
        rules.setStyleSheet("color: palette(window-text); font-size: 12px;")
        wl.addWidget(rules)
        blay.addWidget(words)
        mode = QGroupBox(tr("Como substituir"))
        ml = QVBoxLayout(mode)
        self.modes = QButtonGroup(self)
        for mid, label in MODES:
            rb = QRadioButton(label)
            rb.setProperty("mode", mid)
            rb.setChecked(mid == o.mode)
            self.modes.addButton(rb)
            ml.addWidget(rb)
        blay.addWidget(mode)
        extra = QGroupBox(tr("Metadados e imagens"))
        el = QVBoxLayout(extra)
        self.meta = QCheckBox(tr("Tirar autor, datas, assunto e nome do arquivo dos metadados (frontmatter)"))
        self.meta.setChecked(o.metadata)
        self.exif = QCheckBox(tr("Tirar dados escondidos das imagens (GPS, câmera, data) — sem perder qualidade"))
        self.exif.setChecked(o.image_metadata)
        self.noimg = QCheckBox(tr("Não incluir imagens (fotos, assinaturas e documentos escaneados)"))
        self.noimg.setChecked(o.remove_images)
        for w in (self.meta, self.exif, self.noimg):
            el.addWidget(w)
        el.addWidget(_hint(tr("O nome do arquivo .md segue o padrão de nomes das configurações: se o nome do "
                           "original identificar alguém, use um padrão como “documento_{n}”.")))
        blay.addWidget(extra)
        self.found = QLabel()
        self.found.setWordWrap(True)
        lay.addWidget(self.found)
        bb = QDialogButtonBox()
        if markdown is not None:
            b_prev = bb.addButton(tr("Ver resultado…"), QDialogButtonBox.ActionRole)
            b_prev.clicked.connect(self._preview)
            bb.addButton(tr("Salvar cópia anonimizada…"), QDialogButtonBox.AcceptRole)
            bb.addButton(QDialogButtonBox.Cancel)
            # recontagem só depois de uma pausa na digitação (documentos grandes travariam a janela)
            self._recount = QTimer(self)
            self._recount.setSingleShot(True)
            self._recount.setInterval(400)
            self._recount.timeout.connect(self._count)
            for w in list(self.kind_boxes.values()) + [self.words] + self.modes.buttons():
                (w.textChanged if w is self.words else w.toggled).connect(lambda *_: self._recount.start())
            self._count()
        else:
            bb.addButton(QDialogButtonBox.Ok)
            bb.addButton(QDialogButtonBox.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def options(self):
        from .anonymize import AnonOptions

        mode = next((b.property("mode") for b in self.modes.buttons() if b.isChecked()), "pseudonimo")
        return AnonOptions(kinds=[k for k, cb in self.kind_boxes.items() if cb.isChecked()], mode=mode,
                           words=self.words.toPlainText(), metadata=self.meta.isChecked(),
                           image_metadata=self.exif.isChecked(), remove_images=self.noimg.isChecked())

    def result_text(self) -> tuple[str, object]:
        from .anonymize import anonymize, strip_frontmatter_private

        o = self.options()
        md = self.markdown or ""
        if o.metadata:
            md = strip_frontmatter_private(md)
        if o.remove_images:
            import re

            md = re.sub(r"!\[[^\]\n]{0,500}\]\([^)\n]{0,2000}\)", "", md)
        return anonymize(md, o)

    def _count(self, *_):
        _, rep = self.result_text()
        self.found.setText(tr('<b>Encontrado neste texto:</b> {0}.').format(rep.summary()))

    def _preview(self) -> None:
        text, _ = self.result_text()
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Resultado da anonimização"))
        dlg.resize(700, 600)
        lay = QVBoxLayout(dlg)
        view = QPlainTextEdit(text)
        view.setReadOnly(True)
        lay.addWidget(view)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        dlg.exec()

    def _accept(self) -> None:
        from .anonymize import DISCLAIMER
        from .quick import save_anon_options

        save_anon_options(self.settings, self.options())
        self.settings.setValue("anon/ack", True)        # o aviso estava à vista nesta janela
        if self.markdown is None:
            self.accept()
            return
        from .gui import recall_dir, remember_dir

        stem = self.source.stem if self.source else "documento"
        start = str(Path(recall_dir(self.settings, "anon", str(self.source.parent if self.source else Path.home())))
                    / tr('{0}_anonimizado.md').format(stem))
        path, _ = QFileDialog.getSaveFileName(self, tr("Salvar cópia anonimizada"), start, tr("Markdown (*.md)"))
        if not path:
            return
        remember_dir(self.settings, path, "anon")
        text, rep = self.result_text()
        Path(path).write_text(text, encoding="utf-8")
        QMessageBox.information(self, tr("Anonimizar"), tr('Cópia anonimizada salva.\n\n{0}\n\n').format(rep.summary())
                                + DISCLAIMER)
        self.accept()


# --------------------------------------------------------------------------- #
# Apoie o Markinho
# --------------------------------------------------------------------------- #
class SupportDialog(QDialog):
    """Doação opcional por Pix (QR Code, chave e copia e cola). `milestone`: agradecimento de marco de uso."""

    def __init__(self, parent=None, milestone: int | None = None, settings: QSettings | None = None):
        from PySide6.QtGui import QPixmap

        from .support import PIX_KEY, PIX_PAYLOAD

        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(tr("Apoie o Markinho"))
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        if milestone:
            head = QLabel(tr('<h3>🎉 Você já converteu {0} documentos com o Markinho!</h3>').format(num(milestone)))
            head.setWordWrap(True)
            lay.addWidget(head)
        txt = QLabel(tr("O Markinho é gratuito e continuará sendo. Se ele foi útil e você quiser agradecer, "
                     "pode fazer uma doação de qualquer valor por <b>Pix</b>.<br><br>É totalmente "
                     "<b>opcional</b> e não cria nenhuma obrigação de suporte, correções ou novas versões."))
        txt.setWordWrap(True)
        lay.addWidget(txt)
        img = Path(__file__).resolve().parent / "resources" / "apoie-pix.png"
        if img.exists():
            qr = QLabel()
            qr.setPixmap(QPixmap(str(img)).scaledToWidth(200, Qt.SmoothTransformation))
            qr.setAlignment(Qt.AlignCenter)
            lay.addWidget(qr)
        lay.addWidget(QLabel(tr("<b>Chave Pix (aleatória):</b>")))
        key = QLabel(PIX_KEY)                  # por extenso, inteira e fácil de selecionar
        key.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        key.setAlignment(Qt.AlignCenter)
        key.setStyleSheet("QLabel { font-family: Consolas, Menlo, monospace; font-size: 14px; padding: 6px;"
                          " border: 1px solid palette(mid); border-radius: 4px; background: palette(base); }")
        lay.addWidget(key)
        self.key_label = key
        row = QHBoxLayout()
        b_key = QPushButton(tr("Copiar chave"))
        b_key.clicked.connect(lambda: (QGuiApplication.clipboard().setText(PIX_KEY), b_key.setText(tr("Chave copiada ✓"))))
        row.addWidget(b_key)
        b_cc = QPushButton(tr("Copiar “Pix copia e cola”"))
        b_cc.clicked.connect(lambda: (QGuiApplication.clipboard().setText(PIX_PAYLOAD),
                                      b_cc.setText(tr("Pix copia e cola copiado ✓"))))
        row.addWidget(b_cc)
        lay.addLayout(row)
        lay.addWidget(_hint(tr("No aplicativo do banco aparece o nome do mantenedor como recebedor (padrão do Pix). "
                            "Outras formas de ajudar: relatar problemas e sugerir funções no GitHub, e indicar o "
                            "Markinho a quem precisa.")))
        bb = QDialogButtonBox()
        if milestone and settings is not None:
            never = bb.addButton(tr("Não mostrar de novo"), QDialogButtonBox.RejectRole)
            never.clicked.connect(lambda: settings.setValue("support/never", True))
        bb.addButton(tr("Fechar"), QDialogButtonBox.AcceptRole)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


# --------------------------------------------------------------------------- #
# Comparar duas versões
# --------------------------------------------------------------------------- #
def _doc_text(path: str, settings: QSettings) -> str:
    """Texto em Markdown de um arquivo: lido direto (.md/.txt) ou convertido com as configurações salvas."""
    p = Path(path)
    if p.suffix.lower() in (".md", ".markdown", ".txt"):
        return p.read_text(encoding="utf-8", errors="replace")
    import threading

    from PySide6.QtWidgets import QApplication

    from .core import convert
    from .quick import SettingsSnapshot, saved_job

    snap = SettingsSnapshot(settings)            # nunca ler QSettings fora da thread da interface
    box: dict = {}

    def work():
        try:
            eid, opts, fix, output, fallback = saved_job(snap, p)
            output.images = "none"
            box["md"] = convert(p, eid, opts, fix, output, fallback=fallback).markdown
        except Exception as exc:  # noqa: BLE001
            box["err"] = str(exc)

    t = threading.Thread(target=work, daemon=True)
    t.start()
    while t.is_alive():
        QApplication.processEvents()
        t.join(0.05)
    if "err" in box:
        raise RuntimeError(box["err"])
    return box["md"]


class CompareDialog(QDialog):
    """Ferramentas > Comparar duas versões: o que entrou, saiu ou mudou entre dois documentos."""

    def __init__(self, parent, settings: QSettings, current_path: str = "", current_text: str = ""):
        from PySide6.QtWidgets import QTextBrowser

        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(tr("Comparar duas versões"))
        self.resize(900, 700)
        self._texts: dict[str, str] = {}
        self._html = ""
        lay = QVBoxLayout(self)
        lay.addWidget(_hint(tr("Escolha a versão <b>antiga</b> e a <b>nova</b> (PDF, Word, Markdown…). O Markinho converte "
                            "as duas e mostra o que <b>saiu</b> (riscado em vermelho), o que <b>entrou</b> (em verde) "
                            "e os trechos alterados, palavra por palavra. Tudo no seu computador.")))
        form = QFormLayout()
        self.path_a, self.path_b = QLineEdit(), QLineEdit()
        for edit, label, key in ((self.path_a, tr("Versão antiga:"), "a"), (self.path_b, tr("Versão nova:"), "b")):
            row = QHBoxLayout()
            edit.setPlaceholderText(tr("Escolha um arquivo…"))
            b = QPushButton(tr("Escolher…"))
            b.clicked.connect(lambda _c=False, e=edit: self._pick(e))
            row.addWidget(edit, 1)
            row.addWidget(b)
            form.addRow(label, row)
        lay.addLayout(form)
        if current_text:
            self.path_a.setText(current_path or tr("(documento aberto)"))
            self._texts[self.path_a.text()] = current_text
        top = QHBoxLayout()
        self.b_go = QPushButton(tr("Comparar"))
        self.b_go.setDefault(True)
        self.b_go.clicked.connect(self.run)
        self.show_equal = QCheckBox(tr("Mostrar também os trechos iguais"))
        self.show_equal.toggled.connect(self._render)
        top.addWidget(self.b_go)
        top.addWidget(self.show_equal)
        top.addStretch()
        lay.addLayout(top)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        lay.addWidget(self.summary)
        self.view = QTextBrowser()
        lay.addWidget(self.view, 1)
        bb = QDialogButtonBox()
        self.b_save = bb.addButton(tr("Salvar relatório (HTML)…"), QDialogButtonBox.ActionRole)
        self.b_save.setEnabled(False)
        self.b_save.clicked.connect(self._save)
        bb.addButton(tr("Fechar"), QDialogButtonBox.RejectRole)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.comparison = None

    def _pick(self, edit: QLineEdit) -> None:
        from .gui import recall_dir, remember_dir

        path, _ = QFileDialog.getOpenFileName(self, tr("Escolher versão"), recall_dir(self.settings, "compare"))
        if path:
            remember_dir(self.settings, path, "compare")
            edit.setText(path)

    def _text(self, path: str) -> str:
        if path in self._texts:
            return self._texts[path]
        self._texts[path] = _doc_text(path, self.settings)
        return self._texts[path]

    def run(self) -> None:
        from PySide6.QtCore import Qt as _Qt
        from PySide6.QtWidgets import QApplication

        from .compare import compare

        a, b = self.path_a.text().strip(), self.path_b.text().strip()
        if not a or not b:
            QMessageBox.information(self, tr("Comparar"), tr("Escolha as duas versões."))
            return
        self.summary.setText(tr("Convertendo e comparando…"))
        self.b_go.setEnabled(False)
        QApplication.setOverrideCursor(_Qt.WaitCursor)
        try:
            self.comparison = compare(self._text(a), self._text(b))
        except Exception as exc:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            self.b_go.setEnabled(True)
            self.summary.setText("")
            QMessageBox.warning(self, tr("Comparar"), tr('Não foi possível ler um dos arquivos:\n\n{0}').format(exc))
            return
        QApplication.restoreOverrideCursor()
        self.b_go.setEnabled(True)
        self._render()

    def _render(self, *_):
        from .compare import to_html

        if self.comparison is None:
            return
        self.summary.setText(f"<b>{self.comparison.summary()}</b>")
        self._html = to_html(self.comparison, Path(self.path_a.text()).name, Path(self.path_b.text()).name,
                             self.show_equal.isChecked())
        self.view.setHtml(self._html)
        self.b_save.setEnabled(True)

    def _save(self) -> None:
        from .gui import recall_dir, remember_dir

        start = str(Path(recall_dir(self.settings, "compare")) / "comparacao.html")
        path, _ = QFileDialog.getSaveFileName(self, tr("Salvar relatório"), start, tr("Página HTML (*.html)"))
        if path:
            remember_dir(self.settings, path, "compare")
            Path(path).write_text(self._html, encoding="utf-8")
