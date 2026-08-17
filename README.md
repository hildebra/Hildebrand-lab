# Hildebrand Lab website

A lightweight, dependency-free static website for the Hildebrand Lab. It is designed to publish directly on GitHub Pages: no CMS, database, build step, tracking code, or server-side runtime is needed.

## Edit the site

- Home-page content and structure: `index.html`
- Research detail page: `research.html`
- Software detail page: `software.html`
- People detail page: `people.html`
- Lab-led publication archive: `publications.html`
- Opportunities and collaboration page: `join-us.html`
- Design and responsive layout: `styles.css`
- Mobile navigation behaviour: `script.js`
- Local images: `assets/images/`

Update the People overview in `index.html` and maintain current/former member roles, biographies and portraits in `people.html`. Add or revise detailed publication cards in `publications.html`; each card should link to the publication record and use an original explanatory visual rather than a copied paper figure. Before publishing, review the **Join us**, **People**, and publication sections so they accurately reflect current opportunities, lab members and research output.

## Refresh tool statistics

The software page displays source-specific download totals and GitHub stars. The updater refreshes cumulative Bioconda totals, RTK’s exact CRAN Logs grand total, GitHub release-asset downloads, repository star counts, and canopy2's tagged-version count; it automatically hides download totals below five and re-sorts current tools by downloads. GitHub does not publish download counts for automatic tag archives, so canopy2's version count is kept separate from download statistics. Set `GITHUB_TOKEN` when available to avoid GitHub’s anonymous API rate limit, then run `python3 scripts/update_tool_downloads.py` before publishing. The original LotuS predates these public counters, so its historic count is explicitly marked unavailable rather than estimated.

## Publish with GitHub Pages

1. Create a new GitHub repository, such as `hildebrand-lab-site`.
2. Upload this folder’s contents to the repository’s default branch (usually `main`).
3. In the repository, open **Settings → Pages**.
4. Under **Build and deployment**, select **Deploy from a branch**, choose `main`, and select the `/ (root)` folder.
5. Save. GitHub will publish the site at the address shown on that page, usually within a few minutes.

For a custom domain, add the domain in **Settings → Pages**, then update its DNS records with the domain provider following GitHub’s instructions. Keep the existing site online until the new address is verified and tested.

## Image credits

The images in `assets/images/` were retained from the original Hildebrand Lab website. The site footer credits Quadram Institute and Earlham Institute as the original photography providers. Confirm continuing permission to reuse these images before public launch.
