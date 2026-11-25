# v0.2.4 - Security Hardening & Diagnostics Privacy

## What's Changed
- **Frontend Card Security**: Added strict URL protocol validation (`safeUrl`) in `caripasarmalam-card.js` for external maps and market links to prevent arbitrary URL scheme injection.
- **Diagnostics Privacy**: Anonymized person entity keys in `diagnostics.py` (e.g. `home`, `person_0`, `person_1`) to ensure household member identities are never exposed in diagnostic logs.
- **Automated CI Packaging**: Added `.github/workflows/release.yml` to automatically build and attach clean integration release archives via GitHub Actions.
- **Version Bump**: Synchronized version `0.2.4` across `manifest.json` and `caripasarmalam-card.js`.
