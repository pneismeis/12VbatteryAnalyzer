#!/usr/bin/env python3
"""
Convert VW ID.3 battery XLS/CSV reports to JSON data files.

Usage:
    python3 convert.py <report.xls|report.csv> [report2.xls ...]

Output:
    data/<YYYY-MM>.json   per-month data file
    data/manifest.json    updated index
"""

import csv
import json
import os
import sys
import subprocess
import tempfile
from datetime import datetime, timedelta
from collections import defaultdict

MONTH_MAP = {
    'Jan.': 1, 'Feb.': 2, 'Mär.': 3, 'Apr.': 4,
    'Mai': 5, 'Jun.': 6, 'Jul.': 7, 'Aug.': 8,
    'Sep.': 9, 'Okt.': 10, 'Nov.': 11, 'Dez.': 12,
    # English fallbacks
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
    'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
    'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
}

def parse_ts(ts_str):
    ts_str = ts_str.strip()
    # Format: "01/Apr./2026 00:01" or "01/Mai/2026 00:01"
    parts = ts_str.split('/')
    day = int(parts[0])
    month_abbr = parts[1]
    rest = parts[2].split(' ')
    year = int(rest[0])
    h, m = rest[1].split(':')
    month_num = MONTH_MAP.get(month_abbr)
    if month_num is None:
        raise ValueError(f"Unknown month: {month_abbr}")
    return datetime(year, month_num, day, int(h), int(m))

def read_csv(filepath):
    readings = []
    with open(filepath, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) < 4:
                continue
            if not parts[0] or not parts[0][0].isdigit():
                continue
            try:
                ts = parse_ts(parts[0])
                v = float(parts[1])
                soc = int(float(parts[2]))
                temp = float(parts[3])
                readings.append((ts, v, soc, temp))
            except Exception:
                pass
    return readings

def to_csv_via_libreoffice(xls_path):
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            ['libreoffice', '--headless', '--convert-to', 'csv', xls_path, '--outdir', tmpdir],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")
        base = os.path.splitext(os.path.basename(xls_path))[0]
        csv_path = os.path.join(tmpdir, base + '.csv')
        return read_csv(csv_path)

def load_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ('.xls', '.xlsx', '.ods'):
        return to_csv_via_libreoffice(filepath)
    elif ext == '.csv':
        return read_csv(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def is_anomaly(v, soc):
    return v < 3.0 or v > 20.0 or soc < 0

def is_charging(v):
    return v >= 13.5

def build_month_json(readings, month_key):
    if not readings:
        return None

    clean = [(ts, v, soc, t) for ts, v, soc, t in readings if not is_anomaly(v, soc)]
    if not clean:
        return None

    # Group by hour
    by_hour = defaultdict(list)
    for ts, v, soc, t in clean:
        hour_key = ts.replace(minute=0, second=0)
        by_hour[hour_key].append((v, soc, t))

    hourly = []
    for hour_ts in sorted(by_hour.keys()):
        pts = by_hour[hour_ts]
        vavg = sum(p[0] for p in pts) / len(pts)
        vmin = min(p[0] for p in pts)
        vmax = max(p[0] for p in pts)
        soc_avg = sum(p[1] for p in pts) / len(pts)
        tavg = sum(p[2] for p in pts) / len(pts)
        charging = vmax >= 13.5
        hourly.append({
            'ts': hour_ts.strftime('%Y-%m-%dT%H:%M'),
            'vAvg': round(vavg, 3),
            'vMin': round(vmin, 3),
            'vMax': round(vmax, 3),
            'soc': round(soc_avg, 1),
            'temp': round(tavg, 1),
            'charging': charging,
        })

    # Group by day
    by_day = defaultdict(list)
    for h in hourly:
        day = h['ts'][:10]
        by_day[day].append(h)

    daily = []
    for day in sorted(by_day.keys()):
        hrs = by_day[day]
        idle = [h for h in hrs if not h['charging']]
        soc_vals = [h['soc'] for h in hrs]
        temp_vals = [h['temp'] for h in hrs]
        v_idle = [h['vAvg'] for h in idle] if idle else [h['vAvg'] for h in hrs]
        v_all = [h['vMax'] for h in hrs]
        charge_count = sum(1 for h in hrs if h['charging'])
        daily.append({
            'date': day,
            'socStart': hrs[0]['soc'],
            'socEnd': hrs[-1]['soc'],
            'socMin': round(min(soc_vals), 1),
            'socMax': round(max(soc_vals), 1),
            'socAvg': round(sum(soc_vals) / len(soc_vals), 1),
            'vIdleAvg': round(sum(v_idle) / len(v_idle), 3),
            'vIdleMin': round(min(v_idle), 3),
            'vMax': round(max(v_all), 3),
            'tempAvg': round(sum(temp_vals) / len(temp_vals), 1),
            'tempMin': round(min(temp_vals), 1),
            'tempMax': round(max(temp_vals), 1),
            'chargingHours': charge_count,
            'charged': charge_count > 0,
        })

    # Summary
    idle_clean = [(ts, v, soc, t) for ts, v, soc, t in clean if not is_charging(v)]
    all_soc = [x[2] for x in clean]
    all_temp = [x[3] for x in clean]
    idle_v = [x[1] for x in idle_clean] if idle_clean else [x[1] for x in clean]

    soc_start = clean[0][2]
    soc_end = clean[-1][2]
    charge_events = sum(1 for d in daily if d['charged'])

    summary = {
        'firstReading': clean[0][0].strftime('%Y-%m-%dT%H:%M'),
        'lastReading': clean[-1][0].strftime('%Y-%m-%dT%H:%M'),
        'totalReadings': len(clean),
        'socStart': soc_start,
        'socEnd': soc_end,
        'socDelta': soc_end - soc_start,
        'socMin': min(all_soc),
        'socMax': max(all_soc),
        'socAvg': round(sum(all_soc) / len(all_soc), 1),
        'voltageIdleAvg': round(sum(idle_v) / len(idle_v), 3),
        'voltageIdleMin': round(min(idle_v), 3),
        'voltageIdleMax': round(max(idle_v), 3),
        'tempMin': round(min(all_temp), 1),
        'tempMax': round(max(all_temp), 1),
        'tempAvg': round(sum(all_temp) / len(all_temp), 1),
        'chargingDays': charge_events,
        'daysRecorded': len(daily),
    }

    year, month = month_key.split('-')
    month_names = ['', 'Jänner', 'Februar', 'März', 'April', 'Mai', 'Juni',
                   'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
    label = f"{month_names[int(month)]} {year}"

    # Raw readings (per-minute resolution) for high-detail views
    readings = [
        {'ts': ts.strftime('%Y-%m-%dT%H:%M'), 'v': round(v, 3), 'soc': soc, 'temp': round(t, 1)}
        for ts, v, soc, t in clean
    ]

    return {
        'month': month_key,
        'label': label,
        'device': 'VW ID / Cupra Born 12V',
        'summary': summary,
        'daily': daily,
        'hourly': hourly,
        'readings': readings,
    }

def update_manifest(data_dir, month_key, label):
    manifest_path = os.path.join(data_dir, 'manifest.json')
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
    else:
        manifest = {'months': []}

    existing = {m['month'] for m in manifest['months']}
    if month_key not in existing:
        manifest['months'].append({'month': month_key, 'label': label})
        manifest['months'].sort(key=lambda x: x['month'])

    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"  Updated manifest: {manifest_path}")

def main():
    files = sys.argv[1:] if len(sys.argv) > 1 else []
    if not files:
        print("Usage: python3 convert.py <file.xls|file.csv> ...")
        sys.exit(1)

    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)

    for filepath in files:
        print(f"Processing: {filepath}")
        try:
            readings = load_file(filepath)
            print(f"  Loaded {len(readings)} readings")
        except Exception as e:
            print(f"  ERROR loading: {e}")
            continue

        if not readings:
            print("  No valid readings found, skipping.")
            continue

        # Group by month in case file spans multiple months
        by_month = defaultdict(list)
        for ts, v, soc, t in readings:
            key = ts.strftime('%Y-%m')
            by_month[key].append((ts, v, soc, t))

        for month_key, month_readings in sorted(by_month.items()):
            data = build_month_json(month_readings, month_key)
            if not data:
                continue
            out_path = os.path.join(data_dir, f"{month_key}.json")
            with open(out_path, 'w') as f:
                json.dump(data, f, separators=(',', ':'))
            print(f"  Written: {out_path} ({os.path.getsize(out_path)//1024}KB)")
            update_manifest(data_dir, month_key, data['label'])

if __name__ == '__main__':
    main()
