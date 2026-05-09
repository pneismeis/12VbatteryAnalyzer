# VW ID.3 — 12V Battery Monitor

A static web app for visualizing 12V auxiliary battery data exported from the VW ID.3 app.

**Live demo:** https://pneismeis.github.io/12VbatteryAnalyzer/

---

## What it shows

- SoC (State of Charge) and idle voltage over time
- Daily charging events and temperature
- Monthly comparison and drain-rate prediction
- SoC calendar heatmap

By default the site loads the repository's demo data (April + May 2026).

---

## Upload your own data

Click **"Bericht hinzufügen"** and drop in your `.xls` or `.csv` export from the VW ID.3 app.

**Everything stays in your browser** — the file is parsed locally using [SheetJS](https://sheetjs.com/), no data is sent anywhere. Imported months are stored in `localStorage` and appear alongside the demo data with a *lokal* badge.

---

## Add data permanently (your own instance)

1. Fork this repository
2. Place your `.xls` export in the project root
3. Run `python3 convert.py "Dateiname.xls"` — this writes a JSON file into `data/`
4. Push → GitHub Pages deploys automatically

---

## Tech stack

- Vanilla JS, no build step
- [Tailwind CSS](https://tailwindcss.com/) (CDN)
- [ApexCharts](https://apexcharts.com/) for charts
- [SheetJS](https://sheetjs.com/) for client-side XLS parsing
- GitHub Pages for hosting
