# ECB Tone Monitor

Small static dashboard for ECB speech tone, published with GitHub Pages.

The public repo only keeps the files needed for the site in `docs/`.
All working code, data, and logs stay locally in `local/` and are not published.

To update the dashboard locally:

```powershell
python local/src/prepare_subset.py
python local/src/score_speeches.py --mode heuristic --output local/data/ecb_subset_scored.csv
Copy-Item local\data\ecb_subset_scored.csv docs\data\ecb_subset_scored.csv -Force
```

Then publish the update:

```powershell
git add docs README.md .gitignore
git commit -m "Update dashboard"
git push origin HEAD:main
```
