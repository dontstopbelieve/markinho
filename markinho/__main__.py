# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Ponto de entrada do Markinho.

    markinho                      abre a interface gráfica
    markinho arquivo.pdf [...]    converte no terminal (mesmas opções de `markinho --cli`)
    markinho --gui [arquivos]     força a interface gráfica
"""
from __future__ import annotations

from .i18n import tr

import argparse
import os
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    from .assets import IMAGE_MODES
    from .engines import AUTO, ENGINES
    from .exporter import FORMATS_BY_ID
    from .postprocess import PROFILES
    from .textfix import FixOptions

    ap = argparse.ArgumentParser(
        prog="markinho",
        description=tr("Converte documentos para Markdown (e Markdown para outros formatos). "
                    "Sem argumentos, abre a interface gráfica."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=tr("exemplos:\n"
               "  markinho relatorio.pdf -o relatorio.md\n"
               "  markinho scan.pdf --opt ocr=force\n"
               "  markinho artigo.pdf --images base64 --frontmatter\n"
               "  markinho tese.docx -e pandoc --opt flavor=commonmark_x\n"
               "  markinho notas.md -t docx -o notas.docx\n"
               "  markinho *.pdf -o saida/ --profile llm\n"
               "  markinho manual.pdf --chunks -o manual.jsonl --chunk-size 1000\n"
               "  markinho *.pdf -o saida/ --nome \"{n}_{nome}\" --nome-seguro\n  markinho manual.pdf --skill -o manual.zip\n"))
    ap.add_argument("arquivos", nargs="*", help=tr("arquivos a converter"))
    ap.add_argument("-o", "--output", help=tr("arquivo de saída (1 entrada) ou pasta (várias)"))
    ap.add_argument("-e", "--engine", default=AUTO, choices=[AUTO, *ENGINES], help=tr("motor de conversão (padrão: auto)"))
    ap.add_argument("--modo", choices=["rapido", "equilibrado", "qualidade"],
                    help=tr("desempenho × qualidade: rapido (sem OCR/imagens), equilibrado (padrão) ou "
                         "qualidade (IA de layout Docling, se instalada)"))
    ap.add_argument("--opt", action="append", default=[], metavar="CHAVE=VALOR",
                    help=tr("opção do motor, ex.: --opt ocr=force --opt pdf_columns=false --opt flavor=gfm"))
    ap.add_argument("--images", default=None, choices=[m for m, _ in IMAGE_MODES],
                    help=tr("imagens: pasta <nome>_assets (padrão), base64 ou none"))
    ap.add_argument("--profile", default="gfm", choices=[p for p, _ in PROFILES], help=tr("perfil/dialeto de saída"))
    ap.add_argument("--frontmatter", action="store_true", help=tr("metadados YAML no topo do .md"))
    ap.add_argument("--anonimizar", action="store_true",
                    help=tr("troca CPF, CNPJ, e-mails, telefones, nomes com pista etc. por marcadores ([PESSOA 1])"))
    ap.add_argument("--anonimizar-tabela", action="store_true",
                    help=tr("grava ao lado de cada .md a tabela de correspondência (<nome>.correspondencia.csv: "
                            "[PESSOA 1] = nome original); guarde-a em local seguro (liga --anonimizar)"))
    ap.add_argument("--anonimizar-ano", action="store_true",
                    help=tr("na data de nascimento, mantém só o ano (liga --anonimizar)"))
    ap.add_argument("--anonimizar-lista", metavar="ARQUIVO",
                    help=tr("arquivo .txt com nomes/termos a esconder (um por linha; liga --anonimizar)"))
    ap.add_argument("--describe", nargs="?", const="", default=None, metavar="MODELO",
                    help=tr("descreve as imagens com IA local (Ollama); MODELO opcional, ex.: qwen2.5vl:3b"))
    ap.add_argument("--no-fix", action="store_true", help=tr("não corrigir caracteres"))
    ap.add_argument("--fix-off", default="", metavar="LISTA",
                    help=tr('correções a desligar, separadas por vírgula: {0}').format(','.join(FixOptions.keys())))
    ap.add_argument("--report", action="store_true", help=tr("mostra o relatório de correções no stderr"))
    ap.add_argument("-t", "--to", metavar="FORMATO", choices=list(FORMATS_BY_ID),
                    help=tr("exporta o resultado para outro formato: ") + ", ".join(FORMATS_BY_ID))
    ap.add_argument("--chunks", nargs="?", const="jsonl", choices=["jsonl", "json"],
                    help=tr("gera pedaços para RAG/IA (padrão: jsonl) em vez de Markdown"))
    ap.add_argument("--skill", nargs="?", const="", default=None, metavar="NOME",
                    help=tr("cria uma skill para assistentes de IA (SKILL.md + capítulos) com todos os arquivos; "
                            "-o pasta ou -o arquivo.zip"))
    ap.add_argument("--retomar", action="store_true",
                    help=tr("lote que retoma de onde parou: guarda a impressão digital (SHA-256) de cada arquivo na "
                            "pasta de saída e, ao rodar de novo, pula o que já está pronto e não mudou"))
    ap.add_argument("--chunk-size", type=int, default=1500, metavar="N", help=tr("tamanho máximo do pedaço (caracteres)"))
    ap.add_argument("--chunk-overlap", type=int, default=150, metavar="N", help=tr("sobreposição entre pedaços"))
    ap.add_argument("--chunk-by", default="title", choices=["title", "page", "basic"],
                    help=tr("divisão: por título (padrão), por página ou só por tamanho"))
    ap.add_argument("--nome", default="{nome}", metavar="PADRÃO",
                    help=tr("padrão do nome dos arquivos gerados numa pasta: {nome} {n} {titulo} {data} {original} "
                         "{pasta} {motor}. Ex.: \"{n}_{nome}\""))
    ap.add_argument("--inicio", type=int, default=1, metavar="N", help=tr("primeiro número de {n} (padrão 1)"))
    ap.add_argument("--digitos", type=int, default=3, metavar="N", help=tr("dígitos de {n} (padrão 3: 001)"))
    ap.add_argument("--nome-seguro", action="store_true", help=tr("nomes sem acentos nem espaços, em minúsculas"))
    ap.add_argument("--ext", default=".md", choices=[".md", ".markdown", ".txt"], help=tr("extensão do Markdown"))
    ap.add_argument("--se-existir", default="suffix", choices=["suffix", "overwrite", "skip"],
                    help=tr("arquivo já existe: suffix (acrescenta _2), overwrite (substitui) ou skip (pula)"))
    ap.add_argument("--engines", action="store_true", help=tr("lista motores, OCR e formatos disponíveis"))
    ap.add_argument("--download-models", choices=["docling", "marker", "ppocr"],
                    help=tr("baixa os modelos de IA para uso offline"))
    ap.add_argument("--gui", action="store_true", help=tr("abre a interface gráfica"))
    ap.add_argument("--mcp", action="store_true",
                    help=tr("inicia o servidor MCP local (para Claude Desktop, Cursor, VS Code…)"))
    ap.add_argument("--mcp-config", choices=["claude", "cursor", "vscode", "install-claude"],
                    help=tr("mostra a configuração MCP para o assistente (ou instala no Claude Desktop)"))
    ap.add_argument("--instalar-skill", nargs="?", const="", default=None, metavar="PASTA",
                    help=tr("ensina assistentes de IA (Claude Code…) a usar o Markinho: grava a skill em "
                            "PASTA/markinho/SKILL.md (padrão: ~/.claude/skills)"))
    ap.add_argument("--mostrar-skill", action="store_true",
                    help=tr("mostra o texto dessa skill (para colar em outro assistente)"))
    ap.add_argument("--instalar-pacote", metavar="ARQUIVO.zip",
                    help=tr("instala um pacote extra (ex.: Fórmulas) a partir do .zip baixado das Releases"))
    ap.add_argument("--pacotes", action="store_true", help=tr("lista os pacotes extras e se estão instalados"))
    ap.add_argument("--version", action="store_true", help=tr("mostra a versão"))
    return ap


def cli(argv: list[str]) -> int:
    from . import __version__
    from .assets import write_assets
    from .core import ConversionError, convert
    from .engines import ENGINES
    from .exporter import FORMATS_BY_ID, available_formats, export
    from .postprocess import OutputOptions
    from .textfix import FixOptions

    ap = build_parser()
    args = ap.parse_args(argv)
    import os

    debug = os.environ.get("MARKINHO_DEBUG") == "1"
    if debug:   # diagnóstico: mostra os registros internos dos motores e o erro completo
        import logging

        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s", force=True)

    if args.version:
        from .updates import RELEASES_URL, build_date

        built = build_date()
        print(f"Markinho {__version__}" + (f" ({built.isoformat()})" if built else ""))
        print(tr("O Markinho não acessa a internet. Para ver se há versão nova: {0}").format(RELEASES_URL))
        return 0
    if args.pacotes:
        from .packs import PACKS, available, installed

        for pk in PACKS:
            state = tr("Instalado") if installed(pk) else tr("Não instalado")
            print(f"{pk.name} (~{pk.size_mb} MB): {state}")
            print("  " + pk.what)
            print("  " + pk.who)
            print("  " + pk.skip)
            if not available(pk):
                print("  " + pk.need)
            print("  " + tr("Baixar: {0}").format(pk.url()))
        return 0
    if args.instalar_pacote:
        from .packs import PackError, install_from_zip

        try:
            pk = install_from_zip(args.instalar_pacote)
        except (PackError, OSError) as exc:
            print(tr("erro: {0}").format(exc), file=sys.stderr)
            return 1
        print(tr("Pacote “{0}” instalado. Ele fica no computador e funciona sem internet.").format(pk.name))
        return 0
    if args.mostrar_skill:
        from .agent_skill import skill_text

        sys.stdout.write(skill_text())
        return 0
    if args.instalar_skill is not None:
        from .agent_skill import install

        try:
            path = install(args.instalar_skill or None)
        except OSError as exc:
            print(tr("erro: {0}").format(exc), file=sys.stderr)
            return 1
        print(tr("Skill instalada em {0}. Abra o assistente de novo e peça, por exemplo: “converta o "
                 "relatorio.pdf com o Markinho”.").format(path))
        return 0
    if args.mcp:
        from .mcp_server import run

        return run()
    if args.mcp_config:
        import json as _json

        from .mcp_server import client_config, install_claude_desktop

        if args.mcp_config == "install-claude":
            print(tr('Configuração gravada em {0} — reinicie o Claude Desktop.').format(install_claude_desktop()), file=sys.stderr)
        else:
            print(_json.dumps(client_config("vscode" if args.mcp_config == "vscode" else "claude"), indent=2))
        return 0
    if args.download_models:
        from .models import download_models

        try:
            download_models(args.download_models, progress=lambda m: print(m, file=sys.stderr))
        except Exception as exc:  # noqa: BLE001
            print(tr('erro: {0}').format(exc), file=sys.stderr)
            return 1
        return 0
    if args.engines:
        from . import ocr
        from .models import models_dir, status

        for eng in ENGINES.values():
            ok, why = eng.available()
            print(f"{eng.id:12} {'OK ' if ok else '-- '} {why}   [{eng.license or '-'}]")
            if ok:
                print("             entrada:", " ".join(sorted(eng.extensions())))
            else:
                print("             instalar:", eng.install_hint)
        print(ocr.describe_status())
        print(tr("exportar para:"), " ".join(f.id for f in available_formats()))
        print(tr('modelos de IA ({0}):').format(models_dir()), status())
        return 0
    if not args.arquivos:
        ap.error(tr("informe ao menos um arquivo"))

    opts = {}
    for item in args.opt:
        k, _, v = item.partition("=")
        v = v.strip()
        opts[k.strip()] = {"true": True, "false": False}.get(v.lower(), int(v) if v.isdigit() else v)
    fix = None
    if not args.no_fix:
        fix = FixOptions()
        for k in filter(None, (s.strip() for s in args.fix_off.split(","))):
            if k not in FixOptions.keys():
                ap.error(tr('correção desconhecida: {0}').format(k))
            setattr(fix, k, False)
    preset_engine, preset_opts, preset_images = None, {}, None
    if args.modo:
        from .presets import resolve

        preset_engine, preset_opts, preset_images = resolve(args.modo)
    output = OutputOptions(images=args.images or preset_images or "folder", profile=args.profile, frontmatter=args.frontmatter,
                           describe_images=args.describe is not None, ollama_model=args.describe or "")
    if args.anonimizar or args.anonimizar_lista or args.anonimizar_tabela or args.anonimizar_ano:
        from .anonymize import AnonOptions

        words = Path(args.anonimizar_lista).read_text(encoding="utf-8-sig") if args.anonimizar_lista else ""
        output.anon = AnonOptions(words=words, save_mapping=args.anonimizar_tabela, birth_year=args.anonimizar_ano)
        from .anonymize import DISCLAIMER

        print(tr("Anonimização: ") + DISCLAIMER, file=sys.stderr)

    if args.skill is not None and (args.chunks or args.to):
        ap.error(tr("use --skill sozinho (sem --chunks ou --to)"))
    if args.chunks:
        if args.to:
            ap.error(tr("use --chunks ou --to, não os dois"))
        args.to = f"chunks_{args.chunks}"
    export_opts = {"chunk_size": args.chunk_size, "chunk_overlap": args.chunk_overlap, "chunk_by": args.chunk_by}
    from .naming import NameContext, NamingOptions, rename_assets, render, validate

    if err := validate(args.nome):
        ap.error(err)
    naming = NamingOptions(args.nome, args.ext, args.inicio, args.digitos, args.nome_seguro, args.se_existir)
    ext = FORMATS_BY_ID[args.to].ext if args.to else args.ext
    used_names: set[str] = set()
    status = 0
    out = Path(args.output) if args.output else None
    multi = len(args.arquivos) > 1 or (out is not None and (out.is_dir() or str(args.output).endswith(("/", "\\"))))
    if args.to and out is None and not args.chunks:
        multi, out = True, Path(".")
    skill_docs: list[tuple[str, str]] = []
    if args.skill is not None:
        multi = False
    manifest = cfg = None
    counts = {"ok": 0, "pulados": 0, "erro": 0}
    if args.retomar:
        if args.skill is not None or not multi or out is None or (args.chunks and not args.output):
            ap.error(tr("--retomar precisa de uma pasta de saída (-o pasta/) e não funciona com --skill"))
        from .batch import Manifest, config_key, file_hash

        out.mkdir(parents=True, exist_ok=True)
        manifest = Manifest(out)
        if manifest.corrupt:
            print(tr("aviso: o registro do lote estava estragado; começando de novo"), file=sys.stderr)
        anon_list = ""
        if args.anonimizar_lista:
            anon_list = file_hash(args.anonimizar_lista)
        cfg = config_key({k: v for k, v in vars(args).items()
                          if k not in ("arquivos", "output", "retomar", "report", "gui", "version")}
                         | {"anon_list": anon_list})
    if multi and out:
        out.mkdir(parents=True, exist_ok=True)
    for index, f in enumerate(args.arquivos):
        sha = ""
        if manifest is not None:
            try:
                sha = file_hash(f)
            except OSError as exc:
                print(tr('erro: {0}').format(exc), file=sys.stderr)
                status = 1
                counts["erro"] += 1
                continue
            if manifest.is_done(f, sha, cfg):
                print(tr("{0}: já convertido e sem mudanças — pulado").format(f), file=sys.stderr)
                counts["pulados"] += 1
                continue
        engine, eng_opts = args.engine, dict(opts)
        if args.modo and args.engine == "auto":      # o modo escolhe o motor, a menos que -e seja dado
            from .engines import ENGINES, pick_engine

            engine = preset_engine
            if engine != "auto" and not ENGINES[engine].supports(Path(f)):
                engine = pick_engine(Path(f)).id
            chosen = engine if engine != "auto" else pick_engine(Path(f)).id
            eng_opts = {**preset_opts.get(chosen, {}), **opts}
        try:
            res = convert(f, engine, eng_opts, fix, output, fallback=args.engine == "auto")
        except ConversionError as exc:
            print(tr('erro: {0}').format(exc), file=sys.stderr)
            if manifest is not None:
                manifest.fail(f, sha, cfg, str(exc))
                counts["erro"] += 1
            if debug:
                import traceback

                traceback.print_exception(exc)
            status = 1
            continue
        for w in res.warnings:
            print(tr('aviso: {0}').format(w), file=sys.stderr)
        if args.report and res.fix_report is not None:
            print(f"--- {f} ({res.converter})\n{res.fix_report.to_markdown()}\n", file=sys.stderr)
        if args.skill is not None:
            skill_docs.append((res.metadata.get("title") or res.title or Path(f).stem, res.markdown))
            continue
        if out is None and args.chunks:      # pedaços direto na tela
            from .chunker import chunk_markdown, to_json, to_jsonl

            chunks = chunk_markdown(res.markdown, args.chunk_size, args.chunk_overlap, args.chunk_by,
                                    source=Path(f).name)
            meta = {**res.metadata, "source": Path(f).name}
            sys.stdout.write(to_jsonl(chunks, meta) if args.chunks == "jsonl" else to_json(chunks, meta))
            continue
        if out is None:
            sys.stdout.write(res.markdown)
            if res.assets and output.images == "folder":
                n = write_assets(res.markdown, res.assets, Path.cwd())
                if n:
                    print(tr('{0} imagem(ns) salva(s) em ./{1}/').format(n, next(iter(res.assets)).split('/')[0]), file=sys.stderr)
            continue
        if multi:   # vários arquivos numa pasta: nome pelo padrão (--nome), na ordem da linha de comando
            ctx = NameContext.from_result(Path(f), title=res.metadata.get("title") or res.title, engine=res.engine)
            stem = render(ctx, index, naming)
            name, k = stem + ext, 2
            reserved = manifest.output_name(f, cfg) if manifest is not None else None
            if reserved and reserved.lower() not in used_names:
                name = reserved                  # retomando: grava por cima do que ficou pela metade
            else:
                while name.lower() in used_names or ((out / name).exists() and naming.conflict == "suffix"):
                    name, k = f"{stem}_{k}{ext}", k + 1
            used_names.add(name.lower())
            target = out / name
            if manifest is not None:
                manifest.start(f, sha, cfg, name)
            elif target.exists() and naming.conflict == "skip":
                print(tr('{0}: {1} já existe — pulado').format(f, target), file=sys.stderr)
                continue
        else:
            target = out
        target.parent.mkdir(parents=True, exist_ok=True)      # -o pasta_nova/arquivo.md
        if args.to:
            import tempfile

            partial = target.with_name(f".~{target.stem}{target.suffix}")    # trocado no fim: nunca fica pela metade
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    base = tmp if write_assets(res.markdown, res.assets, Path(tmp)) else Path(f).parent
                    via = export(res.markdown, partial, args.to,
                                 {**export_opts, "source": Path(f).name, "metadata": res.metadata}, base_dir=base)
                os.replace(partial, target)
            except Exception as exc:  # noqa: BLE001
                partial.unlink(missing_ok=True)
                print(tr('erro ao exportar {0}: {1}').format(f, exc), file=sys.stderr)
                status = 1
                if manifest is not None:
                    manifest.finish(f, False, str(exc))
                    counts["erro"] += 1
                continue
            print(f"{f} -> {target} ({res.converter} → {via})", file=sys.stderr)
        else:
            from .batch import atomic_write

            md, files = rename_assets(res.markdown, res.assets, target.stem)   # pasta de imagens acompanha o nome
            atomic_write(target, md)
            n = write_assets(md, files, target.parent)
            if args.anonimizar_tabela and res.anon_report is not None:
                from .anonymize import write_mapping

                table = write_mapping(target, res.anon_report)
                if table:
                    print(tr("tabela de correspondência: {0} (guarde em local seguro, separada do documento)")
                          .format(table), file=sys.stderr)
            extra = tr(', {0} imagem(ns)').format(n) if n else ""
            print(f"{f} -> {target} ({res.converter}{extra})", file=sys.stderr)
        if manifest is not None:
            manifest.finish(f, True)
            counts["ok"] += 1
    if manifest is not None:
        print(tr("lote: {0} convertido(s), {1} pulado(s) sem mudanças, {2} com erro").format(
            counts["ok"], counts["pulados"], counts["erro"]), file=sys.stderr)
        if not manifest.close():                  # terminou sem erro: o registro é apagado
            print(tr("o registro do lote ficou guardado para retomar: rode o mesmo comando de novo"),
                  file=sys.stderr)
    if args.skill is not None and skill_docs:
        status = max(status, _write_skill(skill_docs, args.skill, out))
    return status


def _write_skill(docs: list[tuple[str, str]], name: str, out: Path | None) -> int:
    """--skill: grava a skill numa pasta (ou .zip) e diz onde ficou."""
    from .skillpack import build_skill, summary, to_zip, write_folder

    try:
        pack = build_skill(docs, name)
        if out is not None and out.suffix.lower() == ".zip":
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(to_zip(pack))
            target = out
        else:
            target = write_folder(pack, out or Path("."))
    except (OSError, ValueError) as exc:
        print(tr("erro: {0}").format(exc), file=sys.stderr)
        return 1
    print(tr("skill “{0}” criada em {1} — {2}").format(pack.name, target, summary(pack)), file=sys.stderr)
    return 0


QUICK_FLAG = "--converter-aqui"          # botão direito > Converter para Markdown aqui (sem perguntar)
QUICK_FLAGS = {QUICK_FLAG: "aqui",
               "--converter-para-md": "perguntar",   # > Converter para Markdown… (escolher onde salvar)
               "--exportar": "exportar"}             # > Converter Markdown para… (Word, PDF, HTML…)


def main() -> int:
    from .models import setup_environment

    setup_environment()
    # console do Windows (cp1252): acentos e "→" não podem derrubar o programa
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    argv = sys.argv[1:]
    if argv and argv[0] == "--cli":      # compatibilidade com a versão anterior
        argv = argv[1:]
        return cli(argv) if argv else cli(["--help"])
    if argv and argv[0] in QUICK_FLAGS:  # botão direito do Windows
        from .quick import main as quick_main

        return quick_main([a for a in argv[1:] if not a.startswith("-")], QUICK_FLAGS[argv[0]])
    if argv and argv[0] == "--mcp":      # servidor MCP: nunca abre a interface
        from .mcp_server import run

        return run()
    if not argv or "--gui" in argv:
        return start_gui([a for a in argv if a != "--gui"])
    return cli(argv)


def gui_entry() -> int:
    """Ponto de entrada `markinho-gui` (sem console no Windows)."""
    from .models import setup_environment

    setup_environment()
    if len(sys.argv) > 1 and sys.argv[1] in QUICK_FLAGS:
        from .quick import main as quick_main

        return quick_main([a for a in sys.argv[2:] if not a.startswith("-")], QUICK_FLAGS[sys.argv[1]])
    return start_gui(sys.argv[1:])


def start_gui(argv: list[str]) -> int:
    """Abre a janela com o mínimo carregado primeiro: (1) toma a “vaga” de instância única — um segundo clique
    enquanto o Markinho ainda carrega só traz esta janela para a frente, em vez de abrir outra; (2) mostra na
    hora uma telinha “Abrindo o Markinho…”; (3) só então carrega o resto do programa."""
    import os
    from pathlib import Path

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([sys.argv[0], *argv])
    app.setApplicationName("Markinho")
    app.setOrganizationName("Markinho")
    paths = [a for a in argv if not a.startswith("-")]
    early: dict = {"cb": None, "pending": []}

    def on_paths(new: list[str]) -> None:
        if early["cb"] is not None:
            early["cb"](new)
        else:
            early["pending"].extend(new)

    listener = None
    if os.environ.get("MARKINHO_MULTI") != "1":
        from .single import claim

        listener = claim("gui", paths, on_paths)
        if listener is None:          # já estava abrindo/aberto: os arquivos (ou só o clique) foram para lá
            return 0
    splash = None
    if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QSplashScreen

        icon = Path(__file__).resolve().parent / "resources" / "markinho.png"
        pix = QPixmap(str(icon)) if icon.is_file() else QPixmap(256, 256)
        if not pix.isNull():
            pix = pix.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        splash = QSplashScreen(pix)
        splash.showMessage(tr("Abrindo o Markinho…"), Qt.AlignBottom | Qt.AlignHCenter)
        splash.show()
        app.processEvents()
    from .gui import main as gui_main

    sys.argv = [sys.argv[0], *argv]
    return gui_main(listener=listener, early=early, splash=splash, claimed=True)


if __name__ == "__main__":
    sys.exit(main())
