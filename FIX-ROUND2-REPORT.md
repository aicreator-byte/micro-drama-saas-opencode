# FIX-ROUND2-REPORT — Kaki OpenCode

**Tanggal:** 20 November 2026
**Sumber temuan:** `../audit-3way-round2-opencode/AUDIT-REPORT.md` (skor 8,0/10, P0 0, P1 2, P2 7, verdict LAYAK DENGAN CATATAN; pytest 261 passed + tsc 0 terkonfirmasi auditor)
**Ruang lingkup:** `~/workspace/micro-drama-saas/opencode/` saja. Tidak ada push GitHub. Tidak ada nilai key/password yang dicetak atau ditulis di mana pun.

---

## Ringkasan hasil

| Item | Status |
|---|---|
| P1-1 Webhook Stripe tanpa secret | FIXED + tes regresi |
| P1-2 Alur bayar nyata putus | FIXED + tes regresi |
| P2-1 Batas upload sebelum baca penuh | FIXED |
| P2-2 JWT SSE via `?token=` | FIXED (token stream terikat job, 5 menit) |
| P2-3 Mobile default port 8002 | FIXED |
| P2-4 VideoJob processing ikut resume | FIXED |
| P2-5 Usage event tahan rollback | FIXED (+ drain sebelum commit terminal) |
| P2-6 Kolaborasi | FIXED sebagian (REST patch + halaman web); batas didokumentasikan |
| P2-7 SSE timeout + reconnect | FIXED di level protokol; browser nyata NOT VERIFIED |

**Verifikasi akhir (20 Nov, setelah semua perbaikan):**
- Full pytest: **283 passed, 0 failed, 0 error** — dijalankan **2× berturut-turut**, hasil identik. Baseline ronde 2 = 261; +19 tes baru + 3 tes stream baru = 283.
- `npx tsc --noEmit` frontend web: **0**. `npx tsc --noEmit` mobile: **0**.
- `npm run build` frontend: **OK** (14 route, termasuk `/projects/[id]/collab` baru).
- Migrasi Alembic `007`: `upgrade 006 → head` → `downgrade 006` → `upgrade head` di DB scratch SQLite — **OK**; tabel `checkout_sessions` ada, kolom `subtitle_key`/`audio_key`/`resolution` ada di `video_jobs`.
- Scan secret (`nvapi-`, `sk_live_`, `sk_test_`, `ghp_`, `AKIA`, `xoxb-`) di kode backend/frontend/mobile: **BERSIH**.
- File diubah: 19 file kode + 3 file tes + 1 migrasi + 1 laporan ini. Lihat `git status` di `opencode/` untuk daftar lengkap.

---

## P1-1 — Webhook Stripe tanpa secret menerima event palsu

**Temuan audit:** endpoint webhook menerima event `livemode=false` apa adanya bila `STRIPE_WEBHOOK_SECRET` tidak dikonfigurasi — penyerang bisa mengklaim Studio gratis.

**Perbaikan** (`app/backend/app/api/v1/billing.py`):
- Tanpa `STRIPE_WEBHOOK_SECRET` → **SEMUA** event ditolak 400 (sebelumnya hanya event livemode=true yang ditolak).
- Bila secret diset, event tetap diverifikasi HMAC SHA256 (`stripe.Webhook.construct_event`); tanda tangan hilang/salah → 400.
- Pertahanan lapis dua: `_upsert_subscription` hanya membuat baris baru bila `user_id` dari metadata benar-benar ada di DB lokal.

**Tes regresi** (`tests/test_fix_round2.py`): webhook palsu tanpa secret → 400 + 0 subscription; tanda tangan salah/hilang dengan secret diset → 400. Tes lama `test_billing.py` diperbarui: event kini ditandatangani (`_sign_event` helper), `test_webhook_without_secret_always_refused` (livemode False DAN True → 400).

## P1-2 — Alur bayar nyata putus

**Temuan audit:** `create_checkout_session` tidak mengirim metadata; webhook tidak bisa mengaitkan event ke user; handler mengandalkan metadata suntikan.

**Perbaikan** (`billing.py`, `app/backend/app/services/stripe_client.py`, `app/backend/app/services/billing_plans.py`):
- `create_checkout_session` kini kirim `metadata[user_id]`, `metadata[plan]` **+** `subscription_data[metadata][user_id/plan]` (diwarisi objek subscription Stripe); `create_customer` kirim `metadata[user_id]`.
- Model baru `app/models/checkout_session.py` (tabel `checkout_sessions`: id = session id Stripe `cs_...`, user_id, plan, stripe_customer_id; diekspor di `app/models/__init__.py`). Endpoint checkout mencatat baris pemetaan (best-effort; gagal catat hanya log warning).
- Webhook `checkout.session.completed` — atribusi user urutan: metadata → baris CheckoutSession (by session id) → Subscription lama via customer id. Bila tidak bisa dikaitkan → **400 "Cannot attribute checkout event to a user"** (gagal keras, bukan diam-diam `received:true`).
- Webhook `customer.subscription.updated/deleted` — plan diturunkan dari **price id objek subscription asli dulu** (`billing_plans.get_plan_by_price_id`, baru), lalu metadata event, terakhir plan baris lama. (Bug sempat muncul: plan baris lama menutupi plan metadata — urutan prioritas diperbaiki jadi price > metadata > lama.)
- Helper baru `_resolve_webhook_user(db, event_obj, session_id)` dan `_plan_from_subscription_object(obj)` di `billing.py`.

**Tes regresi** (`tests/test_fix_round2.py`): checkout kirim metadata sesi + subscription_data + baris CheckoutSession tercatat; webhook asli tanpa metadata → Subscription dibuat via pemetaan; event tak bisa dikaitkan → 400 + 0 subscription; plan dari price id mengalahkan metadata menyesatkan.

---

## P2-1 — Batas upload dicek sebelum file dibaca penuh

**Perbaikan** (`app/backend/app/api/v1/assets.py`): baca chunk 1 MB, batalkan 413 begitu kumulatif > `MAX_FILE_SIZE` — file tidak pernah dibaca penuh ke memori.

**Pelajaran:** pre-check `Content-Length` sempat ditambah lalu **dihapus** — pada multipart nilainya mencakup framing MIME (file 5 byte ber-Content-Length ~250 byte → salah 413). Chunked read adalah enforcement yang benar.

**Tes:** limit 10 byte — file 20 byte → 413, file 5 byte → 201.

## P2-2 — JWT SSE jangan lewat `?token=`

**Perbaikan** (`app/backend/app/core/security.py`, `app/backend/app/api/v1/auto_generate.py`, `app/frontend/src/lib/api.ts`, `app/frontend/src/app/projects/[id]/page.tsx`):
- `create_stream_token(user_id, job_id, expires_minutes=5)` + `decode_stream_token(token, job_id)` (purpose=`"sse"`, terikat satu job); `STREAM_TOKEN_EXPIRE_MINUTES = 5`.
- Endpoint baru `POST /{project_id}/auto-generate/{job_id}/stream-token` (auth via header; kembalikan `stream_token` + `expires_in_seconds: 300`).
- `_resolve_stream_user` kini terima `job_id`; `?token=` **HANYA** terima token stream — JWT penuh via query → 401. Header Authorization tetap terima JWT penuh.
- Frontend: `autoGenerateApi.streamToken()` baru; `streamUrl` tetap pakai `?token=${encodeURIComponent(token)}` (file aslinya memang sudah begitu).

**Tes:** token stream diterima; JWT penuh via query → 401; token stream job lain → 401; endpoint token: 401 tanpa auth, 404 job tak ada. (`tests/test_auto_generate_stream.py` diperbarui.)

**Risiko sisa (didokumentasikan):** WS kolaborasi masih pakai JWT penuh via `?token=` — handshake WebSocket tidak bisa kirim header, jadi token stream untuk WS butuh desain terpisah (di luar scope P2-2).

## P2-3 — Mobile default base URL port 8002

**Perbaikan** (`app/mobile/src/api/client.ts`, `app/mobile/README.md`): default `http://localhost:8001/api/v1` → `8002`; semua kemunculan 8001 di README mobile → 8002 (4 tempat).

## P2-4 — VideoJob processing ikut resume saat restart

**Perbaikan** (`app/backend/app/models/video_job.py`, `app/backend/app/api/v1/video.py`, `app/backend/app/main.py`, migrasi `007`):
- Kolom baru VideoJob: `subtitle_key`, `audio_key`, `resolution` (nullable); endpoint assemble kini menyimpan ketiganya saat membuat job.
- `resume_stale_video_jobs(engine)` baru: job `pending`/`processing` di-reset ke `pending` lalu `_run_assemble` dijadwalkan ulang (idempotent, output ditimpa); job tanpa `input_files` → `failed` "interrupted by restart (missing input list)". Di-wire ke `lifespan` di `main.py` bersama `resume_stale_jobs`.
- **Bug laten ketemu + diperbaiki:** `_VIDEO_DB_LOCK = asyncio.Lock()` module-level terikat ke loop pertama yang memakainya → tes kedua yang memakai endpoint video di loop berbeda melempar "Lock is bound to a different event loop". Perbaikan: `_get_video_db_lock()` malas per-loop (dict `_lock_holder`, buat ulang bila loop berganti); semua 4 pemakaian diganti. Satu-satunya `asyncio.Lock()` module-level di backend (grep terverifikasi).

**Tes:** job processing + klip nyata → completed; job tanpa input → failed "interrupted by restart"; resume tanpa job → noop.

## P2-5 — Usage event LLM tetap tercatat bila step gagal

**Perbaikan** (`app/backend/app/services/llm_usage.py`, `app/backend/app/api/v1/auto_generate.py`):
- `BufferedUsageSink` baru (+ `make_buffered_usage_sink`): event dikumpulkan di memori selama run, `drain(engine)` menulis semuanya dalam SATU transaksi terpisah. `_execute_steps` kini pakai buffered sink.
- **Drain SEBELUM commit terminal** (helper `_drain_usage_before_terminal_commit`, dipanggil di jalur sukses + kedua jalur gagal di `_execute_steps_inner`): penonton yang melihat status COMPLETED/FAILED tidak bisa kembali saat drain masih jalan. `finally` di `_execute_steps` dipertahankan sebagai jaring pengaman (biasanya 0 event).
- `make_usage_sink` lama tetap dipakai endpoint story/scene (satu call per request; commit di akhir request) — tidak diubah.

**Tes:** unit buffered sink tahan rollback; integrasi step 2 gagal setelah 1 call LLM → 2 event tercatat.

## P2-6 — Kolaborasi

**Perbaikan** (`app/backend/app/api/v1/collab.py`, `app/frontend/src/app/projects/[id]/collab/page.tsx` baru, `app/frontend/src/lib/api.ts`, tombol di project page):
- Endpoint REST baru `POST /projects/{project_id}/collab/patch` (owner-only 404, whitelist field, 400 bila field tak valid; tanpa broadcast — klien REST muat ulang sendiri).
- Halaman web baru `projects/[id]/collab/page.tsx`: presence via WS (+ fallback polling REST 5 dtk), edit 6 field bible whitelist via WS (fallback REST), banner batas yang diketahui. Tombol "Collaboration" (ikon Users) ditambahkan di header project page di samping Auto-Generate.
- `collabApi` baru di `api.ts` (presence + patch). Docstring `collab.py` diperbarui dengan batas yang diketahui.

**Tes:** REST patch OK + bible berubah; field buruk → 400; proyek user lain → 404.

**NOT FIXED (didokumentasikan):** model keanggotaan/sharing proyek (butuh tabel anggota — belum dibuat), Redis multi-worker (kolaborasi tetap in-memory single-worker), token stream untuk WS (lihat P2-2).

## P2-7 — SSE timeout 120 dtk + reconnect browser

**Perbaikan** (`auto_generate.py` docstring, `page.tsx`):
- Backend: stream tetap tutup setelah 120 dtk (`SSE_TIMEOUT_SECONDS = 120.0`) dengan event `done {"status":"timeout"}`; re-open stream dengan job id sama tetap jalan.
- Frontend `page.tsx`: `openStream(attempt)` baru — minta stream token dulu via `streamToken()`, buka EventSource; handler `done`: terminal (completed/failed) → apply + tutup; `timeout` → buka ulang maks 5× jeda 1 dtk lalu polling; payload lain/hilang → polling. **Bug lama diperbaiki:** handler `done` lama meng-apply payload `{"status":"timeout"}` mentah ke state job (bisa merusak modal). Cleanup effect kini juga clear `reconnectTimer`.

**Tes:** stream timeout 0,6 dtk (di-monkeypatch) → done timeout; re-open → progress lagi; token stream kedaluwarsa → 401.

**NOT VERIFIED (jujur):** EventSource di browser nyata — reconnect diuji di level protokol via httpx stream, bukan browser.

---

## Temuan tambahan saat kerja (di luar audit, diperbaiki karena menghalangi suite hijau)

1. **Background task bocor antar-tes (race teardown).** Full suite sempat 282 passed + 1 ERROR yang berpindah-pindah (`test_reuses_existing_bible`, lalu `test_update_episode`, lalu tes stream): endpoint auto-generate menjalankan job di `asyncio.create_task`; tes yang hanya menunggu status job bisa kembali saat task masih commit audit/usage — loop ditutup di tengah transaksi, greenlet bocor ke fixture tes berikutnya (MissingGreenlet / IllegalStateChangeError di setup tes berikut). Perbaikan dua lapis:
   - Produk: drain usage **sebelum** commit terminal (P2-5 di atas) — menutup window race utama.
   - Tes: teardown fixture `client` di `tests/conftest.py` kini menunggu semua background task selesai (`asyncio.wait`, timeout 30 dtk) sebelum fixture DB di-teardown. Setelah ini: **283 passed, 0 error, 2× run berturut-turut identik.**
2. **MissingGreenlet di tes baru** — 4 tempat menangkap id ke variabel lokal SEBELUM `expire_all()` (checkout, webhook tanpa metadata, video tanpa input, collab patch), pola yang sama seperti `test_billing.py`.
3. **Prioritas plan webhook** (lihat P1-2) dan **pre-check Content-Length multipart** (lihat P2-1) — keduanya ketemu lewat tes baru, diperbaiki.

## NOT FIXED — ringkasan

| Item | Alasan |
|---|---|
| Model keanggotaan/sharing proyek (P2-6) | Butuh tabel anggota + endpoint invite; perubahan skema di luar perbaikan audit |
| Redis multi-worker kolaborasi (P2-6) | Butuh infrastruktur Redis; batas didokumentasikan di `collab.py` + banner UI |
| Token stream untuk WS kolaborasi (P2-2) | Handshake WS tak bisa kirim header; butuh desain terpisah |
| Reconnect EventSource di browser nyata (P2-7) | Butuh klik manual UI; diuji di level protokol |
| Login Google asli + submit Flow | Tetap NOT VERIFIED (di luar scope audit ronde 2; butuh browser yang mencapai Google) |

## Perintah verifikasi (untuk diulang)

```bash
cd ~/workspace/micro-drama-saas/opencode/app/backend
./venv/bin/python -m pytest -q -p no:cacheprovider   # 283 passed (~40 dtk)
cd ../frontend && npx tsc --noEmit && npm run build   # tsc 0, build OK
cd ../mobile && npx tsc --noEmit                       # tsc 0
```
