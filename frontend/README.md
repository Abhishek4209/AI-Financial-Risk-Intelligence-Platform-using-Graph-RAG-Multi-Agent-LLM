# Ledgerline Risk Intelligence Frontend

## Run locally

1. Install Node.js 20+ (Node.js 22 is also supported).
2. Open a terminal in this `frontend` directory.
3. Install dependencies:
   ```bash
   npm install
   ```
4. Start Vite:
   ```bash
   npm run dev
   ```
5. Open the URL printed by Vite, usually `http://localhost:5173`.

## Backend / demo mode

The UI is designed to render without the API server. Overview, cases, and customers use local sample data if the backend at `http://localhost:8000` is unavailable. Credit-risk, fraud-risk, compliance, and document-upload flows show clearly marked demo responses when their backend endpoints are unavailable; those demo responses are not real model predictions or regulatory advice.

To use a backend on another address, create `.env` in this folder with:

```env
VITE_API_URL=http://localhost:8000
```

Then restart the Vite server.
