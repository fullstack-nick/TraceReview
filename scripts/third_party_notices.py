"""Collect notices from the locked, installed packages. No network or package edits."""
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LICENSE_NAME = re.compile(r'(^|[._-])(licen[cs]e|copying|notice)([._-]|$)', re.I)


def read(path):
    content = path.read_text(encoding='utf-8', errors='replace').replace('\r\n', '\n')
    return '\n'.join(line.rstrip(' \t') for line in content.split('\n')).strip()


def npm_licenses(directory):
    matches = []
    for current, folders, files in os.walk(directory):
        folders[:] = sorted(folder for folder in folders if folder != 'node_modules' and not folder.startswith('.'))
        for name in sorted(files):
            path = Path(current) / name
            if LICENSE_NAME.search(name) and path.stat().st_size < 5_000_000:
                matches.append((str(path.relative_to(directory)).replace('\\', '/'), read(path)))
    if not matches:
        for path in sorted(directory.glob('*')):
            if path.is_file() and path.name.lower().startswith('readme'):
                content = read(path)
                match = re.search(r'(?im)^(?:#{1,6}[^\n]*(?:license|copyright|credits)[^\n]*\n|(?:License|Copyright)[^\n]*\n[-=]+\n)', content)
                if match:
                    matches.append((path.name + ' (license section)', content[match.start():]))
        for name in ('index.js', 'main.js', 'isarray.js', 'imurmurhash.js', 'natural-compare.js', 'murmurhash3_gc.js', 'murmurhash2_gc.js'):
            path = directory / name
            if path.is_file():
                content = read(path)
                match = re.match(r'\s*(/\*[\s\S]*?\*/)', content)
                if match and re.search('license|copyright|public domain', match[0], re.I):
                    matches.append((name + ' (leading notice)', match[0]))
    return matches


def main():
    records = []
    for distribution in sorted(distributions(), key=lambda d: d.metadata['Name'].lower()):
        metadata = distribution.metadata
        licenses = [(str(path), read(Path(distribution.locate_file(path)))) for path in distribution.files or [] if LICENSE_NAME.search(path.name)]
        label = metadata.get('License-Expression') or metadata.get('License', 'See license text').split('\n')[0]
        records.append(('Python', metadata['Name'], distribution.version, label, licenses))
    packages = json.loads((ROOT / 'frontend/package-lock.json').read_text(encoding='utf-8'))['packages']
    for relative, entry in sorted(packages.items()):
        if not relative:
            continue
        directory = ROOT / 'frontend' / relative
        if not directory.is_dir():
            continue  # Other platforms' optional binaries are not installed or distributed.
        metadata = json.loads((directory / 'package.json').read_text(encoding='utf-8'))
        licenses = npm_licenses(directory)
        supplement = ROOT / 'docs/licenses' / f"{metadata['name']}@{metadata['version']}.txt"
        if not licenses and supplement.is_file():
            licenses.append(('upstream supplemental notice', read(supplement)))
        if metadata['name'].startswith('@rolldown/binding-') and not licenses:
            licenses.append(('rolldown/LICENSE (same upstream package version)', read(ROOT / 'frontend/node_modules/rolldown/LICENSE')))
        records.append(('npm', metadata['name'], metadata['version'], str(metadata.get('license', entry.get('license', 'See package'))), licenses))
    lines = ['# Third-party notices', '', 'TraceReview source and original synthetic fixtures use the [MIT license](LICENSE). Dependencies retain their own licenses.', '',
             'This inventory is generated from the locked packages installed on Windows using `uv run --locked python scripts/third_party_notices.py`. It includes development/test packages as well as runtime packages. Platform-specific packages not installed here are omitted; the lockfiles record them. No Python/Node runtime or browser executable is redistributed in this repository.', '',
             'Collected license, copyright, and notice texts are preserved in [THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt). NumPy’s wheel notices cover its bundled numerical libraries. Supplemental upstream notices and their source/blob identifiers are in `docs/licenses/`. The Rolldown binary uses the notice from its matching source package. Package metadata identifiers are descriptive; the complete upstream terms control.', '',
             '`glslify-deps` declares ISC in its package metadata, credits Hugh Kennedy, and supplies no standalone license text. Its upstream repository is https://github.com/stackgl/glslify-deps. It belongs to the full Plotly dependency tree; TraceReview imports the precompiled basic plotting bundle. No missing upstream copyright text has been invented.', '',
             '| Ecosystem | Package | Version | Declared license | Notice files |', '|---|---|---|---|---|']
    texts = ['TraceReview — third-party license and notice texts\nGenerated from installed locked packages.\nEach section remains under its upstream terms.\n']
    missing = []
    for ecosystem, name, version, license_id, licenses in records:
        lines.append(f'| {ecosystem} | `{name}` | {version} | {license_id.replace(chr(124), "/")} | {len(licenses)} |')
        texts.append('\n' + '=' * 78 + f'\n{ecosystem}: {name} {version}\nDeclared license: {license_id}\n' + '=' * 78)
        if not licenses:
            missing.append(f'{name}@{version}')
            texts.append('The installed package contains no standalone license/notice file. Consult its package metadata and upstream source.\n')
        for path, content in licenses:
            texts.append(f'\n--- {path} ---\n\n{content}\n')
    (ROOT / 'THIRD_PARTY_NOTICES.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    (ROOT / 'THIRD_PARTY_LICENSES.txt').write_text('\n'.join(texts), encoding='utf-8', newline='\n')
    print(f'Collected {len(records)} package entries and {sum(len(r[4]) for r in records)} notice files.')
    print('Packages without a standalone notice:', ', '.join(missing) or 'none')


if __name__ == '__main__':
    main()
