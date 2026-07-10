# Deploying DataPilot AI to Vercel

## Prerequisites

- Vercel account at [vercel.com](https://vercel.com)
- GitHub repo connected to Vercel
- Your API keys ready (Groq, Google, Upstash)

---

## Step-by-Step Deployment

### 1. Connect GitHub Repo to Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repository: `Hayat-array/DataPilot-AI`
3. Select **Framework Preset → Other**
4. Set **Root Directory** to `.` (project root)

### 2. Set Environment Variables

In your Vercel dashboard → Project → Settings → Environment Variables, add:

| Variable | Value |
|---|---|
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | *(generate a long random string)* |
| `GROQ_API_KEY` | *(your Groq API key)* |
| `GOOGLE_API_KEY` | *(your Google API key)* |
| `UPSTASH_VECTOR_REST_URL` | *(your Upstash vector URL)* |
| `UPSTASH_VECTOR_REST_TOKEN` | *(your Upstash vector token)* |
| `VALIDATE_ENV_ON_START` | `false` |

> **⚠️ NEVER** commit real keys to `.env` or `.env.example` — always use Vercel dashboard for secrets.

### 3. Deploy

Vercel will automatically deploy on every push to `main`.

Or trigger manually:

```bash
npm i -g vercel
vercel --prod
```

---

## File Structure for Vercel

```
backend/
├── api/
│   └── index.py       ← Vercel WSGI entry point (auto-detected)
├── app/               ← Flask application package
├── vercel.json        ← Vercel build + routing config
├── requirements.txt   ← Python dependencies
└── .env.example       ← Environment variable template (safe placeholders only)
```

---

## Important Notes

- **File uploads / sandbox execution** use the local filesystem which is **ephemeral** on Vercel. For production, configure cloud storage (e.g., AWS S3 or Cloudflare R2) for the `uploads/` and `generated_code/` directories.
- **Cold starts** may be slow on the free tier — consider upgrading to Vercel Pro for better performance.
- **Max Lambda size** is set to `50mb` in `vercel.json` — if ML libraries like `sentence-transformers` exceed this, consider moving heavy inference to a separate microservice.
