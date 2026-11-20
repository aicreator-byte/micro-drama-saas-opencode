# Future Development Round 2 Report — OpenCode leg

**Tanggal:** 20 Nov 2026 (selesai ~06:30 WIB)
**Perintah:** Di, 20 Nov 06:03 — "Selesaikan semua future development masing-masing" (daftar OpenCode + Hermes + Claude di chat; laporan ini hanya kaki OpenCode).
**Cakupan:** `~/workspace/micro-drama-saas/opencode/` saja (kaki lain tidak disentuh).
**Cara kerja:** 4 subagent paralel (satu per kelompok fitur), lalu koordinator verifikasi independen + perbaiki 2 masalah integrasi (lihat §8) + smoke server live.
**Hasil ringkas:** 10/10 item selesai, fungsional + tes. Full suite **261 passed, 0 failed** (baseline round 1: 187 passed — +74 tes baru, 0 regresi). `npx tsc --noEmit` web 0 error, `npm run build` sukses, `npx tsc --noEmit` mobile 0 error. Smoke server live: register/login, from-template, upload 2 klip → assemble video 2,0 dtk (ffprobe terverifikasi), billing 503 tanpa key (benar). **Tidak push ke GitHub** (sesuai larangan tugas).

## 1. Resume async jobs on startup — SELESAI
- `resume_stale_jobs(engine)` di `app/backend/app/api/v1/auto_generate.py`: cari job RUNNING, reset step RUNNING → PENDING (runner idempotent), jadwalkan `_run_job_in_background` dari langkah pertama yang belum COMPLETED, user = `project.owner_id` (job tidak punya user_id). Job yang proyeknya hilang di-skip (log warning). No-op bila tidak ada job stale. Dipanggil dari lifespan startup `app/backend/app/main.py` (setelah `init_db`, via `asyncio.create_task`, tidak blok startup).
- Perbaikan samping: `_get_job_or_404` kini `populate_existing=True` (sesi tes panjang menyimpan status basi di identity map; di produksi no-op).
- Tes: `tests/test_job_resume.py` (3 tes) — resume job RUNNING (step 1 COMPLETED + step 2 RUNNING) → COMPLETED, step 2 jalan, hasil step 1 utuh; no-op; semua step COMPLETED tapi job RUNNING → COMPLETED tanpa re-run.

## 2. Live progress over WebSocket/SSE — SELESAI (SSE)
- `GET /api/v1/projects/{project_id}/auto-generate/{job_id}/stream` di `auto_generate.py`. `StreamingResponse` `text/event-stream`; tiap ~0,5 dtk event `progress` berisi JSON persis bentuk `AutoGenerateJobResponse` (reuse `job_to_response`); saat terminal kirim event `done` lalu tutup; timeout 120 dtk. Endpoint GET polling lama tidak diubah (tetap jalan sebagai fallback).
- **Perbaikan koordinator (§8.1):** endpoint awalnya hanya baca header `Authorization` — EventSource browser tidak bisa kirim header, jadi SSE dari web tidak akan pernah jalan (hanya fallback polling). Kini terima JWT via `?token=` juga (`_resolve_stream_user`: header dulu, lalu query token, cek sama seperti `get_current_user`).
- Frontend web: `AutoGenerateModal` di `app/frontend/src/app/projects/[id]/page.tsx` pakai `EventSource` ke stream (token via `?token=` dari localStorage) + fallback otomatis ke polling GET 2 detik bila stream error; badge "● live (SSE)" / "● live (polling)".
- Tes: `tests/test_auto_generate_stream.py` (6 tes: progress+done, 404, 401, cross-user 404, **query-token 200**, query-token salah 401 — 2 terakhir ditambah koordinator).

## 3. Video Pipeline — SELESAI (FFmpeg, dari file lokal; TIDAK generate via Flow)
- Service `app/services/video_pipeline.py`: `assemble_video()` — concat demuxer, scale+pad ke 1080x1920, burn subtitle bila ada, audio AAC bila ada, mp4 + faststart, timeout 600 dtk, durasi via ffprobe (fallback parse stderr). Validasi: input harus ada + di dalam storage root (tolak `../`/absolut di luar).
- Model `VideoJob` (`app/backend/app/models/video_job.py`): pending/processing/completed/failed, input_files JSON, output_path, duration_seconds. Endpoint: `POST /api/v1/projects/{id}/video/assemble` → 202 + job (background task), `GET .../video/jobs/{job_id}`, `GET .../video/jobs`.
- Tes: `tests/test_video_pipeline.py` (9 tes) — assemble 2 klip testsrc 1 dtk → mp4 durasi ≈2 dtk; subtitle burn; path traversal ditolak; input hilang ditolak; e2e upload → assemble → completed; 404.
- Smoke live: upload 2 klip testsrc → assemble → `completed`, durasi **2,0 dtk**, file `app/uploads/assets/video-outputs/<job>.mp4` (67.392 B, ffprobe terverifikasi; artefak smoke sudah dihapus).

## 4. Asset Management — SELESAI (storage S3-compatible + CDN, default lokal)
- `app/services/storage.py`: protokol `StorageBackend` (put/get/delete/exists/list/url) + `LocalStorageBackend` (root `settings.ASSET_STORAGE_DIR`, default `./uploads/assets`; key disanitasi) + `S3Backend` (httpx + AWS Signature V4 manual via hmac/hashlib, tanpa boto3; `S3_CDN_BASE_URL` bila diset dipakai `url()`). `get_storage_backend()` dari `settings.STORAGE_BACKEND` ("local" default; "s3" tanpa kredensial → ValueError jelas saat dipakai, bukan crash import).
- Model `Asset` (`app/backend/app/models/asset.py`). Endpoint: `POST /api/v1/projects/{id}/assets` (multipart, batas 100MB), `GET .../assets` (list), `GET .../assets/{id}/download` (lokal: StreamingResponse; s3: redirect 302 ke S3/CDN), `DELETE .../assets/{id}`.
- Settings baru di `app/core/config.py` + placeholder di `.env.example`: `ASSET_STORAGE_DIR, STORAGE_BACKEND, S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION, S3_CDN_BASE_URL`.
- Tes: `tests/test_assets.py` (9 tes) — local put/get/delete/exists/list + sanitasi; endpoint upload+list+download+delete; S3 signing TANPA network (MockTransport: header `Authorization` berisi `AWS4-HMAC-SHA256`); s3 tanpa kredensial → ValueError.
- **Perbaikan koordinator (§8.2):** router assets baru sempat men-shadow `GET /{project_id}/assets` milik FlowBridge (dipakai frontend `flowBridgeApi.listProjectAssets`). Kini list FlowBridge pindah ke `GET /projects/{id}/flow-assets` + frontend `api.ts` diperbarui; kedua list hidup (tes baru `test_list_project_flow_assets_moved_path`).

## 5. Collaboration — SELESAI (WebSocket presence + edit bible bersama)
- `app/services/collab.py`: registry in-memory per proyek `{user_id: {full_name, section, cursor, last_seen}}` + `join/leave/update_presence/heartbeat/prune` (>60 dtk), `broadcast`, `apply_bible_patch` (whitelist 6 field bible). Docstring jujur: single-worker, multi-worker butuh Redis — TIDAK dibuat.
- WS `GET /api/v1/ws/projects/{project_id}/collab?token=<JWT>` (token diverifikasi seperti `get_current_user`; tak valid → close 4401; bukan pemilik → 4404). Pesan: `presence` (update + broadcast daftar), `patch` (update SeriesBible + broadcast ke koneksi lain), `ping` → `pong`, tak dikenal → `{"type":"error"}`. REST `GET /api/v1/projects/{project_id}/collab/presence`.
- Tes: `tests/test_collab.py` (8 tes) — 2 koneksi, patch A → B terima broadcast + bible berubah di DB; presence di REST; token salah/hilang → disconnect; patch field di luar whitelist → error, bible tidak berubah; ping/pong; unit prune/join/leave.
- Batasan: room owner-only — kolaborasi 2 user berbeda butuh model sharing/anggota proyek (keputusan produk, belum ada). Frontend untuk fitur ini belum ada (backend saja).

## 6. Billing — SELESAI (Stripe, TEST MODE SAJA)
- `app/services/stripe_client.py`: `StripeClient` (httpx injectable, `trust_env=False`) — `create_customer`, `create_checkout_session`, `get_subscription`, `cancel_subscription`. Key kosong → `StripeNotConfiguredError`; **`sk_live_...` → ditolak keras** (`StripeLiveKeyForbiddenError`). Plan di `app/services/billing_plans.py`: starter $9/bln, pro $29/bln, studio $79/bln + fitur; price id dari env `STRIPE_PRICE_*`.
- Model `Subscription` (`app/backend/app/models/subscription.py`). Endpoint (`app/api/v1/billing.py`, prefix `/billing`): `GET /billing/plans` (publik), `POST /billing/checkout {plan}` → `checkout_url` + `mode: test` (Stripe tak terkonfigurasi → **503**, bukan 500; plan tak dikenal → 400; price belum dikonfigurasi → 503), `GET /billing/subscription`, `POST /billing/cancel`, `POST /billing/webhook` (verifikasi HMAC SHA256 bila `STRIPE_WEBHOOK_SECRET` diset; bila TIDAK diset hanya terima `livemode=false` + warning, tolak `livemode=true`; tangani `checkout.session.completed` + `customer.subscription.updated/deleted`).
- Frontend web: tab "Billing" baru di `app/frontend/src/app/dashboard/settings/page.tsx` (status langganan + plans + tombol Checkout → buka `checkout_url` tab baru; bila belum dikonfigurasi tampilkan "Billing belum dikonfigurasi (test mode)", tanpa URL hardcode).
- Tes: `tests/test_billing.py` (16 tes) — MockTransport (POST `https://api.stripe.com/v1/checkout/sessions` + header `Authorization: Bearer`); webhook sintetis membuat Subscription; signature salah → 400; livemode true tanpa secret ditolak; live key ditolak; tanpa key → 503.
- Smoke live: `GET /billing/plans` 200 (`configured:false`); `POST /billing/checkout` 503 "Stripe not configured: set STRIPE_SECRET_KEY (test key, sk_test_...)" — perilaku benar.

## 7. Mobile App — SELESAI (scaffold Expo, tsc 0)
- Folder `app/mobile/`: `package.json` (expo ~54.0.0, react-native 0.81.5, react 19.1.0, expo-secure-store, AsyncStorage; tanpa lib navigasi berat), `app.json` (nama "MicroDrama"), `tsconfig.json`, `babel.config.js`, `.gitignore`, `README.md`.
- `App.tsx` (navigasi berbasis state: login → projects → detail → autogen); `src/api/client.ts` (base URL `EXPO_PUBLIC_API_URL`, default `http://localhost:8001/api/v1`; token JWT via expo-secure-store, fallback AsyncStorage; login form-urlencoded sama seperti web); `src/screens/` — `LoginScreen`, `ProjectsScreen` (GET /projects + pull-to-refresh + status), `ProjectDetailScreen` (bible/characters/episodes ringkas), `AutoGenerateScreen` (form judul/genre/episode → POST auto-generate → progres via **polling GET 2 detik, bukan SSE** — alasan didokumentasi di README + komentar: EventSource di RN tak bisa kirim header auth & tidak stabil).
- Validasi koordinator: `npm install` berhasil (617 packages, ~3 mnt); `npx tsc --noEmit` **0 error**; `npx expo config` terbaca normal (SDK 54.0.0).

## 8. Analytics — SELESAI (metrik produksi + cost tracking LLM)
- (a) Rekam tiap call LLM: `_call_nvidia` isi `usage` dari `data["usage"]` (dinormalisasi ke int; mock sudah kembalikan 100/200/300). `AIClient.chat_completion` terima `usage_sink` opsional (gagal → log warning saja, call tetap sukses). Model `LlmUsageEvent` (`app/backend/app/models/llm_usage.py`): user/project/job, provider, model, prompt/completion/total tokens, `estimated_cost_usd`. Harga di `app/services/llm_pricing.py` (per 1M token, **ESTIMASI, bukan harga resmi vendor**, override env `LLM_PRICE_<MODEL>`; model tak dikenal → cost `None`, jujur). Sink disalurkan via argumen eksplisit DAN ContextVar `usage_sink_scope` (diset sekali di `_execute_steps` untuk seluruh run auto-generate; ContextVar dipilih karena passing kwarg eksplisit memecahkan mock lama di tes). `_chat_json` + ke-10 `generate_*_llm`/`refine_*` di story_engine + scene_engine membaca sink via `resolve_usage_sink()`.
- (b) Endpoint (`app/api/v1/analytics.py`, prefix `/projects`): `GET /{project_id}/analytics/summary` (total/completed/failed/running jobs, total token, estimasi biaya USD total + per model + per job) dan `GET /{project_id}/analytics/usage?limit=&offset=` (list event terbaru). Keduanya cek pemilik proyek (user lain → 404).
- Frontend web: panel "Analytics" baru di tab Overview halaman proyek — total token + estimasi biaya + per model, semua berlabel "estimasi"; bila endpoint gagal → pesan "Analytics belum tersedia", halaman tetap jalan.
- Tes: `tests/test_analytics.py` (8 tes) — 1 event tercatat dengan token mock; sink gagal tak gagalkan call; pricing model tak dikenal → None; env override jalan; job mock selesai → summary menjumlah benar (5 call → 500/1000/1500 token); paginasi; proyek kosong = nol; cross-user 404; tanpa token 401.
- Batasan (dicatat agen): usage event hilang bila step gagal — sink menulis di transaksi yang sama dengan step; rollback step gagal ikut menghapus event call tersebut.

## 9. Templates — SELESAI (template proyek per genre)
- `app/services/templates.py`: 6 genre statis (tanpa LLM) — romance, thriller, revenge, family, ceo_billionaire, fantasy. Tiap template: genre, title_suggestion, premise, main_plot, subplots, tone, world_settings, ending_direction, episode_structure, characters 4–5, locations 3–4.
- Endpoint (`app/api/v1/templates.py`): `GET /api/v1/templates` (ringkas), `GET /api/v1/templates/{genre}` (detail; tak dikenal → 404), `POST /api/v1/projects/from-template {genre, title?}` (buat Project + SeriesBible + Character + Location, TANPA LLM; kembalikan ProjectResponse).
- Frontend web: pemilih template genre di modal New Project (`app/frontend/src/app/dashboard/projects/page.tsx`) — pilih → POST from-template → redirect `/projects/{id}`; bila endpoint gagal → picker sembunyi + pesan, pembuatan manual tetap jalan.
- Tes: `tests/test_templates.py` (8 tes) — list ≥6 genre; detail romance characters ≥4 + locations ≥3; from-template membuat proyek+bible+karakter+lokasi; genre tak dikenal 404; owner = user login, user lain GET → 404; tanpa auth → 401.
- Smoke live: `POST /projects/from-template {genre: romance}` → 201, proyek "Cinta di Balik Hujan".

## 10. Export — SELESAI (Fountain + Final Draft, dst.)
- `ExportFormat` + `FOUNTAIN ("fountain")`, `FINAL_DRAFT ("fdx")` di `app/schemas/export.py`. `format_fountain(data)` di `app/api/v1/export.py`: Title Page (`Title:` + tanggal), slugline `INT. <LOKASI> - DAY/NIGHT` per scene, action, karakter UPPERCASE + parenthetical + dialog (parse JSON `dialogue` scene), `CUT TO:` antar scene; data kosong tetap hasilkan Title Page minimal. `format_final_draft(data)`: XML FDX valid (root `<FinalDraft DocumentType="Script">`, `<Paragraph Type="Scene Heading|Character|Dialogue|Action|Parenthetical">`). Endpoint export yang sudah ada menerima format baru (via `ExportRequest.format`); map ekstensi download ditambah (`fountain`, `fdx`). Format PDF tidak disentuh.
- Tes: `tests/test_export_formats.py` (6 tes) — full_project fountain mengandung `Title:` + `INT.`; episode fountain dengan dialog → `NADIA`, `Aku tidak takut.`, `(tenang)`; fdx parseable `xml.etree`, root `FinalDraft`, ada `Scene Heading`; data kosong valid; format `docx` → 422.

## 11. File yang diubah/dibuat
- Backend baru: `app/api/v1/{analytics,assets,billing,collab,templates,video}.py`, `app/models/{asset,llm_usage,subscription,video_job}.py`, `app/schemas/{analytics,asset,video}.py`, `app/services/{billing_plans,collab,llm_pricing,llm_usage,storage,stripe_client,templates,video_pipeline}.py`, `app/backend/alembic/versions/006_round2_tables.py`.
- Backend diubah: `app/api/v1/{__init__,auto_generate,export,flow_bridge,scene_engine,story_engine}.py`, `app/main.py`, `app/services/ai_client.py`, `app/core/config.py`, `app/models/__init__.py`, `app/schemas/export.py`, `.env.example` (placeholder STRIPE/S3/LLM_PRICE, tanpa nilai).
- Tes baru: `tests/test_{analytics,assets,auto_generate_stream,billing,collab,export_formats,job_resume,templates,video_pipeline}.py` (+1 tes flow-assets di `test_flow_bridge.py`).
- Frontend web diubah: `src/lib/api.ts` (`streamUrl`, `templatesApi`, `billingApi`, `analyticsApi`), `src/app/projects/[id]/page.tsx` (SSE + panel Analytics), `src/app/dashboard/projects/page.tsx` (pemilih template), `src/app/dashboard/settings/page.tsx` (tab Billing).
- Mobile baru: `app/mobile/` (lihat §7).
- **Tidak diubah:** kaki Hermes/Claude, migrasi Alembic 001–005, `.env` (tidak pernah ditulis/dicetak nilainya), data repo git.

## 12. Bukti tes (verifikasi koordinator, bukan klaim agen)
- `pytest` penuh: **261 passed, 0 failed** (83,8 dtk) — `app/backend/venv/bin/python -m pytest -q`. Termasuk 3 tes baru koordinator (SSE query-token 2, flow-assets 1).
- `npx tsc --noEmit` web: **0 error**. `npm run build`: sukses (13 route).
- `npx tsc --noEmit` mobile: **0 error**.
- Migrasi Alembic 006: `alembic upgrade head` di DB sqlite scratch → versi 006 + tabel `subscriptions, llm_usage_events, assets, video_jobs` ada; `downgrade 005` lalu `upgrade head` lagi → 006 (terverifikasi; DB scratch dihapus).
- Smoke server live (port 8137, DB sqlite `/tmp`, dimatikan + DB dihapus): `/health` 200; register 201; login ok; `GET /templates` 200; `POST /projects/from-template` 201; `GET .../analytics/summary` 200; `GET /billing/plans` 200; `POST /billing/checkout` 503 (tanpa key — benar); upload 2 klip 201; `POST .../video/assemble` 202 → `completed` durasi 2,0 dtk (ffprobe: duration 2.000000, 67.392 B); `GET .../assets` 200 (2 aset); `GET .../flow-assets` 200 ([] — benar, tidak ada aset FlowBridge di proyek smoke).
- Scan secret: tidak ada `nvapi-`/key live di kode (hanya pengecekan prefix `sk_live_` di `stripe_client.py`); `.env.example` hanya placeholder.

## 13. NOT VERIFIED (jujur, di luar jangkauan dari VM ini)
- Resume saat restart proses sungguhan (hanya `resume_stale_jobs(engine)` langsung di tes + wiring `create_task` di lifespan; restart server live + job RUNNING asli belum diuji).
- SSE dari browser/HP nyata (terverifikasi via `httpx AsyncClient.stream` di tes + kode EventSource web; perilaku EventSource browser nyata — reconnect, buffering proxy — belum diuji).
- Panggilan nyata ke `api.stripe.com` (semua tes Stripe pakai MockTransport; tidak ada key Stripe test di VM; egress ke Stripe belum diuji) + webhook Stripe asli (hanya event sintetis + HMAC buatan sendiri).
- S3 backend terhadap S3 asli (hanya MockTransport; tanpa kredensial/bucket nyata).
- Kolaborasi 2 user berbeda (room owner-only; butuh model sharing proyek) + multi-worker collab / Redis (sengaja tidak dibuat).
- Mobile di Expo Go/emulator (tidak ada device di VM); klik manual UI web di browser; job 30 episode live; login Google asli + video Flow asli.
- Harga LLM adalah ESTIMASI (placeholder di `llm_pricing.py`, bukan harga resmi NVIDIA) — wajib di-override via env sebelum dipakai mengutip biaya.
