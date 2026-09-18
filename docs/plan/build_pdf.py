"""docs/plan/albertitos_plan.md → dist/entrega/albertitos_plan.pdf sin dependencias del sistema (PyMuPDF Story)."""

from __future__ import annotations

import sys
from pathlib import Path

import markdown
import pymupdf

ORIGEN = Path("docs/plan/albertitos_plan.md")
DESTINO = Path("dist/entrega/albertitos_plan.pdf")
CSS = """
body { font-family: sans-serif; font-size: 10.5pt; line-height: 1.35; color: #111; }
h1 { font-size: 20pt; margin: 0 0 8pt 0; } h2 { font-size: 15pt; margin: 16pt 0 6pt 0; border-bottom: 1px solid #999; }
h3 { font-size: 12pt; margin: 12pt 0 4pt 0; } p, li { margin: 3pt 0; }
code { font-family: monospace; font-size: 9pt; background: #eee; } pre { background: #f3f3f3; padding: 6pt; font-size: 8.5pt; }
table { border-collapse: collapse; } td, th { border: 1px solid #999; padding: 3pt 6pt; font-size: 9.5pt; }
em { color: #555; }
"""


def main(origen: Path = ORIGEN, destino: Path = DESTINO) -> None:
    html = markdown.markdown(
        origen.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"]
    )
    story = pymupdf.Story(html=html, user_css=CSS)
    destino.parent.mkdir(parents=True, exist_ok=True)
    escritor = pymupdf.DocumentWriter(str(destino))
    pagina = pymupdf.paper_rect("a4")
    zona = pagina + (40, 40, -40, -48)
    mas = True
    n = 0
    while mas:
        dev = escritor.begin_page(pagina)
        mas, _ = story.place(zona)
        story.draw(dev)
        escritor.end_page()
        n += 1
    escritor.close()
    print(f"{destino}: {n} páginas")


if __name__ == "__main__":
    main(*(Path(a) for a in sys.argv[1:3]))
