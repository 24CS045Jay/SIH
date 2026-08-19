# KMRL Document Intelligence & Action Portal — Deployment Guide

This guide details the deployment steps for hosting the KMRL Portal on **Vercel** (Frontend) and **Render** (Backend & Database).

---

## 1. Backend & Database Deployment (Render)

### Using `render.yaml` Blueprint (Recommended)
1. Push this repository to GitHub/GitLab.
2. Log in to [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** → **Blueprint**.
4. Connect this repository. Render will automatically discover `render.yaml` and provision:
   - `kmrl-postgres` (PostgreSQL instance)
   - `kmrl-redis` (Redis instance)
   - `kmrl-backend` (Dockerized FastAPI web service)
5. After deployment, seed the demo corpus:
   - Open the **Shell** tab in the `kmrl-backend` service.
   - Run:
     ```bash
     python scripts/seed.py
     python scripts/seed_demo_corpus.py
     ```
6. Copy your backend service URL (e.g. `https://kmrl-backend.onrender.com`).

---

## 2. Frontend Deployment (Vercel)

1. Log in to [Vercel Dashboard](https://vercel.com/).
2. Click **Add New...** → **Project**.
3. Import this repository.
4. Configure Project Settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Add Environment Variable:
   - `VITE_API_BASE_URL` = `https://kmrl-backend.onrender.com/api/v1` (replace with your Render backend URL)
6. Click **Deploy**.

---

## 3. Post-Deployment Verification & CORS Setup

1. Copy your Vercel frontend URL (e.g. `https://kmrl-portal.vercel.app`).
2. Go to Render → `kmrl-backend` → **Environment** tab.
3. Update `CORS_ORIGINS` to include your Vercel URL:
   ```env
   CORS_ORIGINS=https://kmrl-portal.vercel.app,http://localhost:5173
   ```
4. Verify endpoints:
   - Health Check: `GET https://kmrl-backend.onrender.com/api/v1/health`
   - Detailed Health Check: `GET https://kmrl-backend.onrender.com/api/v1/health/detailed`
   - OpenAPI Docs: `GET https://kmrl-backend.onrender.com/api/v1/docs`
   - Frontend SPA: Open `https://kmrl-portal.vercel.app` and sign in with any demo role.
