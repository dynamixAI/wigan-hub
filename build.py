import shutil
import sys
from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape

from sections.food import build as food

OUT = Path("public")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree("site/static", OUT / "static")
    env = Environment(
        loader=ChoiceLoader([FileSystemLoader("sections/food/templates"), FileSystemLoader("site/templates")]),
        autoescape=select_autoescape(["html"]),
    )
    count = food.build(env, OUT)
    print(f"Built food section: {count} places")


if __name__ == "__main__":
    sys.exit(main())
