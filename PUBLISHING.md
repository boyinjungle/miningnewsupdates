# Sakariya Mining & Graphite Daily — Publishing Contract

This is a public, static publication. **ChatGPT is the only intended content publisher.**
GitHub stores source-of-truth files. GitHub Actions validates and builds the website.
Never edit generated site output.

## Source-of-truth inputs

| File | Purpose |
| --- | --- |
| newspaper/YYYY-MM-DD.html | Full public-safe dated HTML edition, dated Asia/Kolkata |
| data/newspaper-index.json | Newest-first metadata for every published edition |
| data/sources.json | Public deduplicated directory records |
| data/people.json | Verified public professional profiles and cross-linked newspaper mentions |
| data/projects.json | Global public project, mine, battery and processing-plant register |
| data/funding.json | Funders, instruments, transaction status and amount linked to project IDs |
| index.html | Source directory website template |
| scripts/build.py | Source directory and newspaper build coordinator |
| scripts/archive_search.py | Cross-date article search, tags, navigation and UI |
| scripts/validate_publish.py | Pre-deployment checks, RSS, sitemap and manifest |

## Daily automated publishing procedure

1. Research material developments; verify publication dates, event dates, and original sources.
2. Write only public-safe material to newspaper/YYYY-MM-DD.html. Use semantic HTML article blocks and an h3 headline, with data-topics and data-tags attributes whenever possible. See TOPICS in scripts/archive_search.py for available slugs, including critical-minerals and global-opportunities.
3. Create or update the dated issue using the GitHub connector. Fetch its current SHA before updating an existing issue.
4. Fetch and update data/newspaper-index.json; preserve all existing dates, add the current issue exactly once, and keep newest first. Use the current blob SHA for updates.
5. Update data/sources.json only for actually verified public sources or corrected links; preserve its existing schema.
6. Maintain data/people.json for explicitly sourced named/quoted people, verified designation, organization, country and commodity, and linked article anchors. Do not infer identities or affiliations; preserve historic people records and deduplicate.

7. Allow GitHub Actions to build and validate; check the exact workflow result and published deployment before claiming success.
8. Keep authorized employee-only Sakariya research in the separately delivered internal edition. Never commit confidential notes, private deals, personal lead lists, licensed full text, credentials or restricted project data to this public repository, even temporarily.
9. Report successes, failures, source gaps and failed delivery attempts accurately. Do not claim Gmail sending or GitHub syncing succeeded without tool confirmation.

## Generated outputs, not source files

- Newspaper archive, full HTML editions with branded navigation, article tags, in-edition jump search and share actions.
- newspaper/article-index.json: article metadata for cross-date topic/tag search.
- newspaper/manifest.json: machine-readable versioned issue manifest.
- people/index.html and people/people.json: searchable, filterable public professional directory with verifiable article links.
- feed.xml: latest 100 public article summaries for RSS.
- sitemap.xml and robots.txt: site discovery.
- Homepage automatically links to newest indexed daily issue.

## Deployment quality and scaling

GitHub Pages workflow runs python3 scripts/build.py then python3 scripts/validate_publish.py before uploading any site artifact. A validation failure prevents publication of inconsistent issues. The site needs neither a database nor an external CMS. Check actual index size and browser load times before adding incremental pagination, lazy-load monthly shards or a dedicated search index such as Pagefind.

## Identity and access

People Directory: https://boyinjungle.github.io/miningnewsupdates/people/
Corporate website: https://www.sakariyamines.com/
Newspaper: https://boyinjungle.github.io/miningnewsupdates/newspaper/
Directory: https://boyinjungle.github.io/miningnewsupdates/

Keep Sakariya's light Heritage Broadsheet design, brand colors and original editorial content. Make source links prominent and visuals purposeful. Do not claim Proxima Nova is embedded unless licensed and actually present. **GitHub Pages is public hosting and must not serve employee-only intelligence.** An internal archive will require separately authenticated hosting.

## Linked Project and Funding Registers

Projects and processing/battery plants are listed at https://boyinjungle.github.io/miningnewsupdates/projects/; project financing events at https://boyinjungle.github.io/miningnewsupdates/funding/. The ChatGPT publishing agent must preserve stable project and transaction IDs and source every updated record. The funding register records each instrument separately with original currency and status; letters of interest, selections and conditional commitments must never be presented as disbursed or received financing. A project profile displays linked funding history but should not simply sum indicative and secured financing. The Pages build generates both directories with scripts/project_funding.py; validation prevents broken cross-references.
