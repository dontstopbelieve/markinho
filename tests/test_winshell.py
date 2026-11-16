"""Menu do botão direito do Windows ligado pelo programa (com um registro de mentira)."""
import re
from pathlib import Path

from markinho import winshell


class FakeReg:
    def __init__(self):
        self.data = {}

    def set(self, key, name, value):
        self.data[(key, name)] = value

    def get(self, key, name):
        return self.data.get((key, name))

    def delete_tree(self, key):
        for k in [k for k in self.data if k[0] == key or k[0].startswith(key + "\\")]:
            del self.data[k]


def test_register_and_unregister():
    reg = FakeReg()
    assert not winshell.is_registered(reg)
    n = winshell.register(r"C:\Apps\Markinho\Markinho.exe", reg)
    assert n > 100 and winshell.is_registered(reg)
    cmd = reg.get(winshell.BASE.format(ext="pdf") + r"\shell\1perguntar\command", "")
    assert cmd == r'"C:\Apps\Markinho\Markinho.exe" --converter-para-md "%1"'
    assert reg.get(winshell.BASE.format(ext="md") + r"\shell\1exportar\command", "").endswith('--exportar "%1"')
    winshell.unregister(reg)
    assert not reg.data and not winshell.is_registered(reg)


def test_same_menu_as_installer():
    """O menu criado pelo programa é o mesmo do instalador (Inno Setup)."""
    iss = (Path(__file__).resolve().parent.parent / "packaging" / "windows" / "markinho.iss").read_text("utf-8-sig")
    from_iss = set(re.findall(r'SystemFileAssociations\\\.(\w+)\\shell\\Markinho\\shell\\(\w+)\\command', iss))
    from_app = {(k.split("\\.")[1].split("\\")[0], k.split("\\shell\\")[2].split("\\")[0])
                for k, _n, _v in winshell.entries("x.exe") if k.endswith("\\command")}
    assert from_iss == from_app
