# ContentPilot Frontend

Minimal React + Vite frontend for prototype validation.

## Run

```bash
npm install
npm run dev
```

## Backend URL

By default the app calls:
- `http://localhost:8000`

To change it, add an env var:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

The homepage checks `GET /health` and shows backend connection status.
