# CoBa's Daughter — Broad Static Ad System (100 ads)

Smart-funnel static ad system for the **Broad (self-care + gifting)** wedge of the Meta performance plan. **40 MOF / 60 BOF**, 1:1 master + 9:16 adapt, Plus Jakarta Sans, single-minded creative (one promo per BOF ad, RTB-led MOF).

## Files
| File | What it is |
|------|-----------|
| `STRATEGY.md` | Funnel logic, competitor teardown (Salt & Stone / Nécessaire / Flamingo Estate / OUAI), brand voice, angle architecture, testing plan |
| `100-ads.md` | Human-readable review matrix of all 100 ads |
| `bulk-create-1x1.csv` | Canva Bulk Create data for the **1:1** master |
| `bulk-create-9x16.csv` | Canva Bulk Create data for the **9:16** master |
| `CANVA-RUNBOOK.md` | Step-by-step: polish masters → Bulk Create → add photos → batch export |
| `generate_ads.py` | Single source of truth; regenerates the CSVs + matrix (`python3 generate_ads.py`) |

## Live Canva assets
- 📁 Folder: https://www.canva.com/folder/FAHLD0UsRxk
- 1:1 master (1080×1080): https://www.canva.com/d/Itb826MYvnkbrTK
- 9:16 master (1080×1920): https://www.canva.com/d/gXvxXgYWga0WIFU

## Edit the copy
Change ads in `generate_ads.py`, then `python3 generate_ads.py` to rebuild both CSVs and `100-ads.md`. Re-upload the CSVs in Canva Bulk Create.
