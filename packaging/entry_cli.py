"""Executável de terminal: `markinho-cli arquivo.pdf -o saida.md` (sem argumentos abre a interface)."""
import sys

from markinho.__main__ import main

sys.exit(main())
