from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / 'software.html'

# Values are deliberately source-specific: a Bioconda total is not combined with
# GitHub release-asset downloads. This keeps every displayed number interpretable.
SOURCES: dict[str, tuple[str, str]] = {
    'lotus3': ('bioconda', 'bioconda/lotus3'),
    'matafiler4': ('github', 'hildebra/MATAFILER4'),
    'protal': ('bioconda', 'bioconda/protal'),
    'rtk': ('bioconda', 'bioconda/rtk'),
    'clustermags': ('github', 'hildebra/clusterMAGs'),
    'cvanmf': ('bioconda', 'bioconda/cvanmf'),
    'adhesiomer': ('github', 'ksidorczuk/adhesiomeR'),
    'sdm': ('bioconda', 'bioconda/sdm'),
    'lca': ('bioconda', 'bioconda/lca'),
    'msafix': ('github', 'hildebra/MSAfix'),
    'canopy2': ('github', 'hildebra/canopy2'),
    'bmtk': ('github', 'apduncan/bm-tk'),
    'vcf2fna': ('github', 'hildebra/vcf2fna'),
    'metamage': ('github', '4less/meta-mage'),
    'benchpro': ('github', '4less/benchpro'),
    'newvu': ('github', '4less/newvu'),
    'enterosig': ('github', 'apduncan/enterosig_sl'),
    'lotus2': ('bioconda', 'bioconda/lotus2'),
    'matafiler': ('github', 'hildebra/MATAFILER'),
    'mgtk': ('github', 'hildebra/mg-tk'),
}


def read_json(url: str) -> tuple[object, object]:
    request = Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Hildebrand-Lab-site-updater'})
    with urlopen(request, timeout=25) as response:
        return json.load(response), response.headers


def bioconda_downloads(package: str) -> int:
    payload, _ = read_json(f'https://api.anaconda.org/package/{package}')
    total = payload.get('ndownloads')
    if not isinstance(total, int):
        raise ValueError(f'No download total returned for {package}')
    return total


def github_release_downloads(repository: str) -> int:
    # GitHub counts release assets only; it does not provide clone or source-archive totals.
    page = 1
    total = 0
    while True:
        payload, headers = read_json(f'https://api.github.com/repos/{repository}/releases?per_page=100&page={page}')
        if not isinstance(payload, list):
            raise ValueError(f'Unexpected GitHub release response for {repository}')
        total += sum(asset.get('download_count', 0) for release in payload for asset in release.get('assets', []))
        if len(payload) < 100 or 'rel="next"' not in headers.get('Link', ''):
            return total
        page += 1


def fetch_total(source: str, reference: str) -> int:
    if source == 'bioconda':
        return bioconda_downloads(reference)
    if source == 'github':
        return github_release_downloads(reference)
    raise ValueError(f'Unknown download source: {source}')


def main() -> int:
    html = PAGE.read_text(encoding='utf-8')
    updated = 0
    failures: list[str] = []
    for name, (source, reference) in SOURCES.items():
        try:
            total = fetch_total(source, reference)
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            failures.append(f'{name}: {error}')
            continue
        pattern = rf'<p class="tool-stat(?: tool-stat-low)?"><span data-download-stat="{re.escape(name)}">[\d,]+</span> ([^<]+)</p>'
        class_name = 'tool-stat' if total >= 5 else 'tool-stat tool-stat-low'
        replacement = f'<p class="{class_name}"><span data-download-stat="{name}">{total:,}</span> \\g<1></p>'
        html, count = re.subn(pattern, replacement, html, count=1)
        if count != 1:
            failures.append(f'{name}: statistic marker not found')
        else:
            updated += 1
    if updated:
        PAGE.write_text(html, encoding='utf-8')
        print(f'Updated {updated} public download counters on {date.today().isoformat()}.')
    if failures:
        print('Could not update: ' + '; '.join(failures), file=sys.stderr)
    return 0 if updated else 1


if __name__ == '__main__':
    raise SystemExit(main())
