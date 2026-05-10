# Battery Share Worker

Cloudflare Worker + D1 (SQLite) backend for sharing battery data via short IDs.

## Setup (einmalig, ~10 Minuten)

```bash
# 1. Wrangler installieren
npm install -g wrangler

# 2. Einloggen
wrangler login

# 3. D1 Datenbank erstellen
wrangler d1 create battery-shares
# → gibt eine database_id aus, in wrangler.toml eintragen

# 4. Schema anlegen
wrangler d1 execute battery-shares --file=schema.sql

# 5. Deployen
wrangler deploy
# → gibt URL aus: https://battery-share.<dein-name>.workers.dev
```

## In index.html eintragen

Oben in der `<script>`-Section die Zeile suchen:

```js
const SHARE_API = '';
```

Und die Worker-URL eintragen:

```js
const SHARE_API = 'https://battery-share.<dein-name>.workers.dev';
```

## API

| Method | Path | Beschreibung |
|--------|------|--------------|
| POST | /share | Payload speichern, gibt `{"id":"AbCdEfGh"}` zurück |
| GET | /share/:id | Payload abrufen |

## Kosten

Cloudflare Workers Free Tier: 100.000 Requests/Tag, D1 Free Tier: 500 MB / 5 Mio. Reads pro Tag. Für persönlichen Gebrauch kostenlos.
