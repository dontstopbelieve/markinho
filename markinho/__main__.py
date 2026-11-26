# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Ponto de entrada do Markinho.

    markinho                      abre a interface gráfica
    markinho arquivo.pdf [...]    converte no terminal (mesmas opções de `markinho --cli`)
    markinho --gui [arquivos]     força a interface gráfica
"""
from __future__ import annotations

import argparse
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
        description="Converte documentos para Markdown (e Markdown para outros formatos). "
                    "Sem argumentos, abre a interface gráfica.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="exemplos:\n"
               "  markinho relatorio.pdf -o relatorio.md\n"
               "  markinho scan.pdf --opt ocr=force\n"
               "  markinho artigo.pdf --images base64 --frontmatter\n"
               "  markinho tese.docx -e pandoc --opt flavor=commonmark_x\n"
               "  markinho notas.md -t docx -o notas.docx\n"
               "  markinho *.pdf -o saida/ --profile llm\n"
               "  markinho manual.pdf --chunks -o manual.jsonl --chunk-size 1000\n"
               "  markinho *.pdf -o saida/ --nome \"{n}_{nome}\" --nome-seguro\n")
    ap.add_argument("arquivos", nargs="*", help="arquivos a converter")
    ap.add_argument("-o", "--output", help="arquivo de saída (1 entrada) ou pasta (várias)")
    ap.add_argument("-e", "--engine", default=AUTO, choices=[AUTO, *ENGINES], help="motor de conversão (padrão: auto)")
    ap.add_argument("--modo", choices=["rapido", "equilibrado", "qualidade"],
                    help="desempenho × qualidade: rapido (sem OCR/imagens), equilibrado (padrão) ou "
                         "qualidade (IA de layout Docling, se instalada)")
    ap.add_argument("--opt", action="append", default=[], metavar="CHAVE=VALOR",
                    help="opção do motor, ex.: --opt ocr=force --opt pdf_columns=false --opt flavor=gfm")
    ap.add_argument("--images", default=None, choices=[m for m, _ in IMAGE_MODES],
                    help="imagens: pasta <nome>_assets (padrão), base64 ou none")
    ap.add_argument("--profile", default="gfm", choices=[p for p, _ in PROFILES], help="perfil/dialeto de saída")
    ap.add_argument("--frontmatter", action="store_true", help="metadados YAML no topo do .md")
    ap.add_argument("--anonimizar", action="store_true",
                    help="troca CPF, CNPJ, e-mails, telefones, nomes com pista etc. por marcadores ([PESSOA 1])")
    ap.add_argument("--anonimizar-lista", metavar="ARQUIVO",
                    help="arquivo .txt com nomes/termos a esconder (um por linha; liga --anonimizar)")
    ap.add_argument("--describe", nargs="?", const="", default=None, metavar="MODELO",
                    help="descreve as imagens com IA local (Ollama); MODELO opcional, ex.: qwen2.5vl:3b")
    ap.add_argument("--no-fix", action="store_true", help="não corrigir caracteres")
    ap.add_argument("--fix-off", default="", metavar="LISTA",
                    help=f"correções a desligar, separadas por vírgula: {','.join(FixOptions.keys())}")
    ap.add_argument("--report", action="store_true", help="mostra o relatório de correções no stderr")
    ap.add_argument("-t", "--to", metavar="FORMATO", choices=list(FORMATS_BY_ID),
                    help="exporta o resultado para outro formato: " + ", ".join(FORMATS_BY_ID))
    ap.add_argument("--chunks", nargs="?", const="jsonl", choices=["jsonl", "json"],
                    help="gera pedaços para RAG/IA (padrão: jsonl) em vez de Markdown")
    ap.add_argument("--chunk-size", type=int, default=1500, metavar="N", help="tamanho máximo do pedaço (caracteres)")
    ap.add_argument("--chunk-overlap", type=int, default=150, metavar="N", help="sobreposição entre pedaços")
    ap.add_argument("--chunk-by", default="title", choices=["title", "page", "basic"],
                    help="divisão: por título (padrão), por página ou só por tamanho")
    ap.add_argument("--nome", default="{nome}", metavar="PADRÃO",
                    help="padrão do nome dos arquivos gerados numa pasta: {nome} {n} {titulo} {data} {original} "
                         "{pasta} {motor}. Ex.: \"{n}_{nome}\"")
    ap.add_argument("--inicio", type=int, default=1, metavar="N", help="primeiro número de {n} (padrão 1)")
    ap.add_argument("--digitos", type=int, default=3, metavar="N", help="dígitos de {n} (padrão 3: 001)")
    ap.add_argument("--nome-seguro", action="store_true", help="nomes sem acentos nem espaços, em minúsculas")
    ap.add_argument("--ext", default=".md", choices=[".md", ".markdown", ".txt"], help="extensão do Markdown")
    ap.add_argument("--se-existir", default="suffix", choices=["suffix", "overwrite", "skip"],
                    help="arquivo já existe: suffix (acrescenta _2), overwrite (substitui) ou skip (pula)")
    ap.add_argument("--engines", action="store_true", help="lista motores, OCR e formatos disponíveis")
    ap.add_argument("--download-models", choices=["docling", "marker"],
                    help="baixa os modelos de IA para uso offline")
    ap.add_argument("--gui", action="store_true", help="abre a interface gráfica")
    ap.add_argument("--mcp", action="store_true",
                    help="inicia o servidor MCP local (para Claude Desktop, Cursor, VS Code…)")
    ap.add_argument("--mcp-config", choices=["claude", "cursor", "vscode", "install-claude"],
                    help="mostra a configuração MCP para o assistente (ou instala no Claude Desktop)")
    ap.add_argument("--version", action="store_true", help="mostra a versão")
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
        print(f"Markinho {__version__}")
        return 0
    if args.mcp:
        from .mcp_server import run

        return run()
    if args.mcp_config:
        import json as _json

        from .mcp_server import client_config, install_claude_desktop

        if args.mcp_config == "install-claude":
            print(f"Configuração gravada em {install_claude_desktop()} — reinicie o Claude Desktop.", file=sys.stderr)
        else:
            print(_json.dumps(client_config("vscode" if args.mcp_config == "vscode" else "claude"), indent=2))
        return 0
    if args.download_models:
        from .models import download_models

        try:
            download_models(args.download_models, progress=lambda m: print(m, file=sys.stderr))
        except Exception as exc:  # noqa: BLE001
            print(f"erro: {exc}", file=sys.stderr)
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
        print("exportar para:", " ".join(f.id for f in available_formats()))
        print(f"modelos de IA ({models_dir()}):", status())
        return 0
    if not args.arquivos:
        ap.error("informe ao menos um arquivo")

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
                ap.error(f"correção desconhecida: {k}")
            setattr(fix, k, False)
    preset_engine, preset_opts, preset_images = None, {}, None
    if args.modo:
        from .presets import resolve

        preset_engine, preset_opts, preset_images = resolve(args.modo)
    output = OutputOptions(images=args.images or preset_images or "folder", profile=args.profile, frontmatter=args.frontmatter,
                           describe_images=args.describe is not None, ollama_model=args.describe or "")
    if args.anonimizar or args.anonimizar_lista:
        from .anonymize import AnonOptions

        words = Path(args.anonimizar_lista).read_text(encoding="utf-8-sig") if args.anonimizar_lista else ""
        output.anon = AnonOptions(words=words)
        from .anonymize import DISCLAIMER

        print("Anonimização: " + DISCLAIMER, file=sys.stderr)

    if args.chunks:
        if args.to:
            ap.error("use --chunks ou --to, não os dois")
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
    if multi and out:
        out.mkdir(parents=True, exist_ok=True)
    for index, f in enumerate(args.arquivos):
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
            print(f"erro: {exc}", file=sys.stderr)
            if debug:
                import traceback

                traceback.print_exception(exc)
            status = 1
            continue
        for w in res.warnings:
            print(f"aviso: {w}", file=sys.stderr)
        if args.report and res.fix_report is not None:
            print(f"--- {f} ({res.converter})\n{res.fix_report.to_markdown()}\n", file=sys.stderr)
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
                    print(f"{n} imagem(ns) salva(s) em ./{next(iter(res.assets)).split('/')[0]}/", file=sys.stderr)
            continue
        if multi:   # vários arquivos numa pasta: nome pelo padrão (--nome), na ordem da linha de comando
            ctx = NameContext.from_result(Path(f), title=res.metadata.get("title") or res.title, engine=res.engine)
            stem = render(ctx, index, naming)
            name, k = stem + ext, 2
            while name.lower() in used_names or ((out / name).exists() and naming.conflict == "suffix"):
                name, k = f"{stem}_{k}{ext}", k + 1
            used_names.add(name.lower())
            target = out / name
            if target.exists() and naming.conflict == "skip":
                print(f"{f}: {target} já existe — pulado", file=sys.stderr)
                continue
        else:
            target = out
        target.parent.mkdir(parents=True, exist_ok=True)      # -o pasta_nova/arquivo.md
        if args.to:
            import tempfile

            try:
                with tempfile.TemporaryDirectory() as tmp:
                    base = tmp if write_assets(res.markdown, res.assets, Path(tmp)) else Path(f).parent
                    via = export(res.markdown, target, args.to,
                                 {**export_opts, "source": Path(f).name, "metadata": res.metadata}, base_dir=base)
            except Exception as exc:  # noqa: BLE001
                print(f"erro ao exportar {f}: {exc}", file=sys.stderr)
                status = 1
                continue
            print(f"{f} -> {target} ({res.converter} → {via})", file=sys.stderr)
        else:
            md, files = rename_assets(res.markdown, res.assets, target.stem)   # pasta de imagens acompanha o nome
            target.write_text(md, encoding="utf-8")
            n = write_assets(md, files, target.parent)
            extra = f", {n} imagem(ns)" if n else ""
            print(f"{f} -> {target} ({res.converter}{extra})", file=sys.stderr)
    return status


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
        from .gui import main as gui_main

        sys.argv = [sys.argv[0]] + [a for a in argv if a != "--gui"]
        return gui_main()
    return cli(argv)


def gui_entry() -> int:
    """Ponto de entrada `markinho-gui` (sem console no Windows)."""
    from .models import setup_environment

    setup_environment()
    if len(sys.argv) > 1 and sys.argv[1] in QUICK_FLAGS:
        from .quick import main as quick_main

        return quick_main([a for a in sys.argv[2:] if not a.startswith("-")], QUICK_FLAGS[sys.argv[1]])
    from .gui import main as gui_main

    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
