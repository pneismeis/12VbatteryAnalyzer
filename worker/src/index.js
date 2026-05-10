const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS, 'Content-Type': 'application/json' },
  });
}

function text(body, status = 200) {
  return new Response(body, {
    status,
    headers: { ...CORS, 'Content-Type': 'text/plain; charset=utf-8' },
  });
}

function randomId(len = 8) {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';
  const bytes = crypto.getRandomValues(new Uint8Array(len));
  return Array.from(bytes, b => chars[b % chars.length]).join('');
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS });
    }

    // POST /share  — store compressed payload, return short ID
    if (request.method === 'POST' && url.pathname === '/share') {
      const data = await request.text();
      if (!data || data.length > 200_000) {
        return json({ error: 'Invalid payload' }, 400);
      }
      const id = randomId(8);
      await env.DB.prepare(
        'INSERT INTO shares (id, data, created_at) VALUES (?, ?, ?)'
      ).bind(id, data, Date.now()).run();
      return json({ id });
    }

    // GET /share/:id  — retrieve by ID
    if (request.method === 'GET' && url.pathname.startsWith('/share/')) {
      const id = url.pathname.slice(7).replace(/[^A-Za-z0-9]/g, '');
      if (!id) return json({ error: 'Missing id' }, 400);
      const row = await env.DB.prepare('SELECT data FROM shares WHERE id = ?')
        .bind(id).first();
      if (!row) return text('Not found', 404);
      return text(row.data);
    }

    return text('Battery Share API', 200);
  },
};
