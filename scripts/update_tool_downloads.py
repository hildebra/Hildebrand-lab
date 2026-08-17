from __future__ import annotations

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / 'software.html'

# Download values remain source-specific rather than being combined. GitHub stars
# are a separate popularity signal and are refreshed for every linked repository.
SOURCES: dict[str, tuple[str, str]] = {
    'lotus3': ('bioconda', 'bioconda/lotus3'),
    'matafiler4': ('github', 'hildebra/MATAFILER4'),
    'protal': ('bioconda', 'bioconda/protal'),
    'rtk': ('cran', 'rtk'),
    'clustermags': ('github', 'hildebra/clusterMAGs'),
    'cvanmf': ('bioconda', 'bioconda/cvanmf'),
    'adhesiomer': ('github', 'ksidorczuk/adhesiomeR'),
    'sdm': ('bioconda', 'bioconda/sdm'),
    'lca': ('bioconda', 'bioconda/lca'),
    'msafix': ('github', 'hildebra/MSAfix'),
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

REPOSITORIES: dict[str, str] = {
    'lotus3': 'hildebra/LotuS3',
    'matafiler4': 'hildebra/MATAFILER4',
    'protal': '4less/protal',
    'rtk': 'hildebra/Rarefaction',
    'clustermags': 'hildebra/clusterMAGs',
    'cvanmf': 'apduncan/cvanmf',
    'adhesiomer': 'ksidorczuk/adhesiomeR',
    'sdm': 'hildebra/sdm',
    'lca': 'hildebra/LCA',
    'msafix': 'hildebra/MSAfix',
    'canopy2': 'hildebra/canopy2',
    'bmtk': 'apduncan/bm-tk',
    'vcf2fna': 'hildebra/vcf2fna',
    'metamage': '4less/meta-mage',
    'benchpro': '4less/benchpro',
    'newvu': '4less/newvu',
    'enterosig': 'apduncan/enterosig_sl',
    'lotus2': 'hildebra/lotus2',
    'matafiler': 'hildebra/MATAFILER',
    'mgtk': 'hildebra/mg-tk',
}

CRANLOGS_START = '2012-10-01'
TAGGED_VERSION_REPOSITORIES: dict[str, str] = {
    'canopy2': 'hildebra/canopy2',
}


def read_json(url: str) -> tuple[object, object]:
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'Hildebrand-Lab-site-updater'}
    github_token = os.environ.get('GITHUB_TOKEN')
    if github_token and url.startswith('https://api.github.com/'):
        headers['Authorization'] = f'Bearer {github_token}'
    request = Request(url, headers=headers)
    with urlopen(request, timeout=25) as response:
        return json.load(response), response.headers


def bioconda_downloads(package: str) -> int:
    payload, _ = read_json(f'https://api.anaconda.org/package/{package}')
    total = payload.get('ndownloads')
    if not isinstance(total, int):
        raise ValueError(f'No download total returned for {package}')
    return total


def cran_downloads(package: str) -> int:
    end = date.today().isoformat()
    payload, _ = read_json(f'https://cranlogs.r-pkg.org/downloads/total/{CRANLOGS_START}:{end}/{package}')
    if not isinstance(payload, list) or not payload:
        raise ValueError(f'No CRAN download total returned for {package}')
    total = payload[0].get('downloads')
    if not isinstance(total, int):
        raise ValueError(f'Invalid CRAN download total returned for {package}')
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


def github_stars(repository: str) -> int:
    payload, _ = read_json(f'https://api.github.com/repos/{repository}')
    if not isinstance(payload, dict):
        raise ValueError(f'Unexpected GitHub repository response for {repository}')
    total = payload.get('stargazers_count')
    if not isinstance(total, int):
        raise ValueError(f'No GitHub star count returned for {repository}')
    return total


def github_tag_count(repository: str) -> int:
    page = 1
    total = 0
    while True:
        payload, headers = read_json(f'https://api.github.com/repos/{repository}/tags?per_page=100&page={page}')
        if not isinstance(payload, list):
            raise ValueError(f'Unexpected GitHub tag response for {repository}')
        total += len(payload)
        if len(payload) < 100 or 'rel="next"' not in headers.get('Link', ''):
            return total
        page += 1


def fetch_total(source: str, reference: str) -> int:
    if source == 'bioconda':
        return bioconda_downloads(reference)
    if source == 'cran':
        return cran_downloads(reference)
    if source == 'github':
        return github_release_downloads(reference)
    raise ValueError(f'Unknown download source: {source}')


def sort_current_tools(html: str) -> str:
    section_pattern = re.compile(
        r'(?P<prefix><section class="detail-section" aria-labelledby="tools-title">.*?<div class="shell tool-detail-grid">\n)'
        r'(?P<cards>.*?)'
        r'(?P<suffix>        </div>\n      </section>)',
        re.DOTALL,
    )

    def reorder(match: re.Match[str]) -> str:
        cards = re.findall(r'          <article class="tool-detail-card">.*?</article>\n', match.group('cards'), re.DOTALL)
        if len(cards) < 2:
            return match.group(0)

        def downloads(card: str) -> int:
            marker = re.search(r'data-download-stat="[^"]+">([\d,]+)</span>', card)
            return int(marker.group(1).replace(',', '')) if marker else -1

        cards.sort(key=downloads, reverse=True)
        return match.group('prefix') + ''.join(cards) + match.group('suffix')

    return section_pattern.sub(reorder, html, count=1)


def main() -> int:
    html = PAGE.read_text(encoding='utf-8')
    updated_downloads = 0
    updated_stars = 0
    updated_versions = 0
    failures: list[str] = []
    download_labels = {
        'bioconda': 'Bioconda downloads',
        'cran': 'CRAN downloads',
        'github': 'GitHub release downloads',
    }
    download_results: dict[str, tuple[str, int]] = {}
    star_results: dict[str, int] = {}
    version_results: dict[str, int] = {}

    # Every counter is independent, so parallel requests keep the refresh practical
    # even when one of the public services is slow.
    with ThreadPoolExecutor(max_workers=8) as executor:
        download_futures = {
            executor.submit(fetch_total, source, reference): (name, source)
            for name, (source, reference) in SOURCES.items()
        }
        star_futures = {
            executor.submit(github_stars, repository): name
            for name, repository in REPOSITORIES.items()
        }
        version_futures = {
            executor.submit(github_tag_count, repository): name
            for name, repository in TAGGED_VERSION_REPOSITORIES.items()
        }

        for future in as_completed(download_futures):
            name, source = download_futures[future]
            try:
                download_results[name] = (source, future.result())
            except (HTTPError, URLError, TimeoutError, ValueError) as error:
                failures.append(f'{name} downloads: {error}')

        for future in as_completed(star_futures):
            name = star_futures[future]
            try:
                star_results[name] = future.result()
            except (HTTPError, URLError, TimeoutError, ValueError) as error:
                failures.append(f'{name} stars: {error}')

        for future in as_completed(version_futures):
            name = version_futures[future]
            try:
                version_results[name] = future.result()
            except (HTTPError, URLError, TimeoutError, ValueError) as error:
                failures.append(f'{name} tagged versions: {error}')

    for name, (source, total) in download_results.items():
        pattern = rf'<p class="tool-stat(?: tool-stat-low)?"><span data-download-stat="{re.escape(name)}">[\d,]+</span> [^<]+</p>'
        class_name = 'tool-stat' if total >= 5 else 'tool-stat tool-stat-low'
        replacement = f'<p class="{class_name}"><span data-download-stat="{name}">{total:,}</span> {download_labels[source]}</p>'
        html, count = re.subn(pattern, replacement, html, count=1)
        if count != 1:
            failures.append(f'{name} downloads: statistic marker not found')
        else:
            updated_downloads += 1

    for name, total in star_results.items():
        pattern = rf'<b data-github-stars="{re.escape(name)}">[\d,]+</b> GitHub stars?'
        label = 'GitHub star' if total == 1 else 'GitHub stars'
        replacement = f'<b data-github-stars="{name}">{total:,}</b> {label}'
        html, count = re.subn(pattern, replacement, html, count=1)
        if count != 1:
            failures.append(f'{name} stars: statistic marker not found')
        else:
            updated_stars += 1

    for name, total in version_results.items():
        pattern = rf'<b data-github-versions="{re.escape(name)}">[\d,]+</b> tagged versions?'
        label = 'tagged version' if total == 1 else 'tagged versions'
        replacement = f'<b data-github-versions="{name}">{total:,}</b> {label}'
        html, count = re.subn(pattern, replacement, html, count=1)
        if count != 1:
            failures.append(f'{name} tagged versions: statistic marker not found')
        else:
            updated_versions += 1

    html = sort_current_tools(html)
    if updated_downloads or updated_stars or updated_versions:
        PAGE.write_text(html, encoding='utf-8')
        print(
            f'Updated {updated_downloads} download counters, {updated_stars} GitHub star counters, '
            f'and {updated_versions} tagged-version counters '
            f'on {date.today().isoformat()}.'
        )
    if failures:
        print('Could not update: ' + '; '.join(sorted(failures)), file=sys.stderr)
    return 0 if updated_downloads or updated_stars or updated_versions else 1


if __name__ == '__main__':
    raise SystemExit(main())
