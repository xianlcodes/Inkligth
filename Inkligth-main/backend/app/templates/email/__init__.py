import os
from string import Template

_TEMPLATE_DIR = os.path.dirname(__file__)


def render_template(name: str, **kwargs) -> str:
    path = os.path.join(_TEMPLATE_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        tmpl = Template(f.read())
    return tmpl.substitute(**kwargs)
