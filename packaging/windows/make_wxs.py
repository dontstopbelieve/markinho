"""Gera o arquivo WiX (v4/v5) do instalador MSI a partir da pasta do programa.

Uso direto: python make_wxs.py <pasta Markinho> <saida.wxs> <versao> <icone.ico> <termos.rtf> [EDIÇÃO]
Normalmente é chamado por: python packaging/build.py msi
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from xml.sax.saxutils import quoteattr

# Fixo para sempre: é o que permite que uma versão nova substitua a anterior
UPGRADE_CODE = "8D3B6C1A-5E2F-4A7B-9D0C-1F2E3A4B5C6D"


def _msi_version(v: str) -> str:
    parts = [p for p in v.split(".") if p.isdigit()][:3]
    return ".".join((parts + ["0", "0", "0"])[:3])


def write_wxs(src: Path, out: Path, version: str, icon: Path, license_rtf: Path, edition: str = "PADRÃO") -> Path:
    src = Path(src).resolve()
    files = sorted(f for f in src.rglob("*") if f.is_file())
    comps = []
    for f in files:
        rel = f.relative_to(src)
        sub = str(rel.parent).replace("/", "\\")
        sub_attr = f" Subdirectory={quoteattr(sub)}" if sub != "." else ""
        # GUID estável por caminho: atualizações substituem os mesmos componentes
        guid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"markinho:{rel.as_posix()}")).upper()
        comps.append(f'      <Component Guid="{guid}"{sub_attr}><File Source={quoteattr(str(f))} /></Component>')
    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs" xmlns:ui="http://wixtoolset.org/schemas/v4/wxs/ui">
  <Package Name="Markinho {edition}" Manufacturer="dontstopbelieve" Version="{_msi_version(version)}"
           UpgradeCode="{UPGRADE_CODE}" Language="1046" Codepage="1252" Scope="perMachine">
    <SummaryInformation Description="Markinho {edition} {version} — Conversor Markdown" />
    <!-- mesmo UpgradeCode nas três edições: instalar outra edição (mesmo da mesma versão) substitui a atual -->
    <MajorUpgrade AllowSameVersionUpgrades="yes"
                  DowngradeErrorMessage="Uma versão mais nova do Markinho já está instalada." />
    <MediaTemplate EmbedCab="yes" CompressionLevel="high" />
    <Icon Id="MarkinhoIcon" SourceFile={quoteattr(str(Path(icon).resolve()))} />
    <Property Id="ARPPRODUCTICON" Value="MarkinhoIcon" />
    <Property Id="ARPURLINFOABOUT" Value="https://github.com/dontstopbelieve/markinho" />
    <WixVariable Id="WixUILicenseRtf" Value={quoteattr(str(Path(license_rtf).resolve()))} />
    <ui:WixUI Id="WixUI_InstallDir" InstallDirectory="INSTALLFOLDER" />

    <StandardDirectory Id="ProgramFiles6432Folder">
      <Directory Id="INSTALLFOLDER" Name="Markinho" />
    </StandardDirectory>
    <StandardDirectory Id="ProgramMenuFolder" />
    <StandardDirectory Id="DesktopFolder" />

    <ComponentGroup Id="AppFiles" Directory="INSTALLFOLDER">
{chr(10).join(comps)}
    </ComponentGroup>

    <Component Id="Shortcuts" Directory="ProgramMenuFolder" Guid="3A7C1E52-9B4D-4F6A-8E2C-5D1B0A9F7E63">
      <Shortcut Id="StartMenuShortcut" Name="Markinho" Description="Conversor Markdown"
                Target="[INSTALLFOLDER]Markinho.exe" WorkingDirectory="INSTALLFOLDER" Icon="MarkinhoIcon" />
      <Shortcut Id="DesktopShortcut" Directory="DesktopFolder" Name="Markinho"
                Target="[INSTALLFOLDER]Markinho.exe" WorkingDirectory="INSTALLFOLDER" Icon="MarkinhoIcon" />
      <RegistryValue Root="HKMU" Key="Software\\Markinho" Name="installed" Type="integer" Value="1" KeyPath="yes" />
    </Component>

    <Feature Id="Main" Title="Markinho" Level="1">
      <ComponentGroupRef Id="AppFiles" />
      <ComponentRef Id="Shortcuts" />
    </Feature>
  </Package>
</Wix>
'''
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(xml, encoding="utf-8")
    print(f"WiX: {len(files)} arquivos -> {out}")
    return Path(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) not in (5, 6):
        print(__doc__)
        sys.exit(2)
    write_wxs(Path(a[0]), Path(a[1]), a[2], Path(a[3]), Path(a[4]), *(a[5:]))
