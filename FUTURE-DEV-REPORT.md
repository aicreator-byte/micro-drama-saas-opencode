# Future Development Report — OpenCode leg

**Tanggal:** 19 Nov 2026 (selesai ~21:30 WIB)
**Perintah:** Di, 19 Nov 20:44 — kerjakan SEMUA future development kaki OpenCode.
**Cakupan:** `~/workspace/micro-drama-saas/opencode/` saja (kaki lain tidak disentuh).
**Hasil ringkas:** semua item scope selesai + terverifikasi. Full suite **187 passed**
(baseline sebelum kerja: 173 passed — 14 tes baru, 0 regresi). Type-check 0 error,
build 14/14 route. Smoke live dengan LLM nyata: job async 5 episode COMPLETED
dalam ~3,6 menit, genre terinferensi "Romance".

## 1. Audit F4 — P1 + P2 OpenCode

### P1 — Ambang minimum §9.1 ditegakkan (SELESAI)
- `app/backend/app/api/v1/auto_generate.py`: konstanta `MIN_CHARACTERS = 4`,
  `MIN_LOCATIONS = 3`. Langkah 2/3 GAGAL (502) bila total yang bisa dipakai
  (sudah ada + baru dibuat) di bawah minimum — bukan hanya bila nol.
  Pesan error menyebut minimum + §9.1, mis. `Only 2 usable character(s),
  minimum is 4 (spec §9.1) — retry the step`.
- Mock world-building (`app/services/ai_client.py`) kini kembalikan 3 lokasi
  (dulu 1 — di bawah minimum, happy-path lama hanya lolos karena tak ada ambang).
- Bukti: `test_characters_step_fails_below_minimum`,
  `test_locations_step_fails_below_minimum` (pytest, keduanya hijau).

### P2a — Langkah 5 tidak lagi satu call LLM (SELESAI)
- `_run_step_prompts` dipecah per chunk `PROMPTS_CHUNK_SIZE = 5` episode per
  call (5 episode = 1 call, 7 episode = 2 call, 30 episode = 6 call).
  Episode yang sudah punya prompt dilewati (retry idempotent).
- Bukti: `test_prompts_are_chunked_per_five_episodes` — 7 episode, 2 call LLM
  terhitung, 7 prompt tertulis.

### P2b — Judul hanya-spasi ditolak (SELESAI)
- Backend: `field_validator` di `AutoGenerateCreateRequest` — judul di-strip,
  kosong setelah strip → 422. Genre hanya-spasi → `None` (jujur, bukan string kosong).
- Frontend: modal auto-generate tampilkan error inline `Title cannot be blank`
  bila judul terisi spasi saja (tombol submit sudah disabled dalam kondisi itu).
- Bukti: `test_validates_input` (judul `"   "` → 422),
  `test_request_schema_strips_title_and_blank_genre`.

### P2c — Tombol CRUD manual yang mati (SELESAI)
- Semua 8 modal kini dirender di `app/frontend/src/app/projects/[id]/page.tsx`
  (sebelumnya: 0 JSX modal, hanya state + handler): Edit Project, Series Bible,
  Character, Location, Episode, Prompt, Google OAuth, Flow Task. Semua memakai
  ulang form state + submit handler yang sudah ada.
- Dua tombol ternyata tidak punya pemicu sama sekali (`setShowEditModal(true)`
  dan edit bible tidak pernah dipanggil): tombol **Edit** ditambahkan di header
  halaman proyek, tombol **Edit Series Bible** di kartu overview bible
  (dengan pre-fill form dari bible yang ada — sebelumnya form edit kosong,
  submit bisa menimpa bible dengan string kosong).
- **Temuan saat perbaikan — tab Prompt salah model:** form + tabel tab Prompt
  memakai model template (`name/category/template/variables/is_active`) yang
  TIDAK ADA di backend; endpoint `/projects/{id}/prompts` adalah prompt
  video-generation (`prompt_type/prompt_text/title/negative_prompt/status`).
  Modal "Add Prompt" yang lama akan selalu 422. Diperbaiki: interface lokal
  `Prompt`, `promptForm`, kedua tombol reset, `openEditPrompt`, filter
  (berdasarkan `prompt_type`) dan kolom tabel (Title/Type/Status/Version/Used)
  kini mengikuti skema backend. Auto-generate step 5 kini tampil benar di tab ini.
- Bukti: `npx tsc --noEmit` 0 error, `npm run build` 14/14 route. Klik manual
  di browser NOT VERIFIED (lihat §6).

### P2d — Header proyek tidak lagi ditimpa POST auto-generate (SELESAI)
- Mutasi `project.title/genre/total_episodes` dihapus dari
  `create_auto_generate_job`. Job menyimpan inputnya sendiri; langkah-langkah
  memakai field `job.*`.
- Bukti: `test_job_does_not_overwrite_project_header` — proyek "Test Project /
  Drama / 20 episode" tidak berubah setelah job dengan judul + genre berbeda.

### P2e — Coverage penuh langkah 5 (SELESAI)
- `_run_step_prompts` kumpulkan semua chunk di memori dulu; bila ada episode
  tanpa prompt → langkah FAILED dengan daftar nomor episode yang hilang, dan
  TIDAK ADA prompt yang ditulis (tanpa insert parsial).
- Bukti: `test_prompts_step_fails_without_full_coverage` — LLM dibuat
  mengembalikan 4/5 prompt → job failed, pesan `missing video prompts for
  episode(s): [5]`, 0 prompt di DB.

### O6 — Commit parsial saat langkah gagal (SELESAI, by-design diperbaiki)
- `_execute_steps`: saat langkah gagal, `db.rollback()` dulu (buang tulisan
  parsial langkah itu), baru tandai step/job FAILED dan commit. Langkah yang
  sudah COMPLETED sebelumnya tetap tersimpan (sengaja — supaya retry bisa
  lanjut, bukan ulang dari awal).
- **Bug yang ketemu saat implementasi:** setelah `rollback()`, membaca
  `step.step.value` di pesan error me-refresh row yang expired dan MENGHAPUS
  marking FAILED yang baru diset (step tetap `running` padahal job `failed`).
  Diperbaiki dengan menangkap label step sebelum `try`.
- Bukti: tes char/loc-minimum assert 0 baris tersisa setelah langkah gagal;
  `test_retry_failed_step_then_continues` hijau.

## 2. Phase 2 gaps — EpisodeRevision + Dialogue

### EpisodeRevision CRUD (SELESAI)
- Sudah ada: list + create (snapshot). Ditambah: `GET /{id}` satu revisi dan
  `DELETE /{id}`. **Tanpa endpoint update — sengaja:** revisi adalah snapshot
  immutable. AuditAction baru: `EPISODE_REVISION_READ`, `EPISODE_REVISION_DELETE`.

### Dialogue CRUD (SELESAI)
- Sudah ada: list + create + delete. Ditambah: `GET /{id}` satu baris dan
  `PATCH /{id}` (partial update via `DialogueUpdate`). AuditAction baru:
  `DIALOGUE_READ`, `DIALOGUE_UPDATE`.
- Bukti: `tests/test_dialogue_revision.py` (4 tes: get+patch dialogue,
  get+delete revision, 404, cross-user 404) — hijau.

## 3. Umum (berlaku semua kaki)

### (a) Progres live per langkah — backend ASYNC (SELESAI)
- `POST /auto-generate` dan `POST .../retry/{step}` kini kembalikan 201/200
  segera dengan status `running`; langkah jalan di background task
  (`asyncio.create_task`) pada engine yang sama dengan request (jadi tes
  in-memory dan produksi melihat baris yang sama). `GET` mem-poll status per
  langkah. Audit RUN ditulis di background saat job selesai.
- Frontend: `useEffect` polling GET tiap 2 detik selama modal terbuka dan job
  masih running; berhenti sendiri saat completed/failed; saat completed, data
  tab di-refresh otomatis. Komentar NOTE kedaluwarsa dihapus.
- Bukti pytest: `test_post_returns_immediately_while_job_runs` (call LLM
  pertama diperlambat 1 detik → respons POST sudah kembali dengan status
  `running`, lalu poll sampai completed).
- Bukti live: smoke 19 Nov ~21:2x — POST 201 dalam **0,19 detik**,
  status `running`; poll menampilkan tiap langkah `running → completed`
  berurutan; job COMPLETED ~3,6 menit.
- Batasan yang diketahui: job yang tertinggal `running` saat server restart
  TIDAK dilanjutkan otomatis — poll job-nya dan retry langkah yang gagal
  (dicatat juga di README).

### (b) Key .env hilang bila server jalan dari CWD salah (SELESAI)
- `app/backend/app/core/config.py`: `env_file` kini daftar absolut dari lokasi
  kode — `[".env", <leg-root>/.env, <backend>/.env]` (file belakangan menang:
  backend/.env > leg-root/.env > CWD). Diverifikasi dari `/tmp`: key tetap
  termuat, `ENCRYPTION_KEY` stabil.
- Guard `DATABASE_URL`: `.env` kaki ini berisi `postgresql+asyncpg` tanpa
  driver/server — bila driver tidak terpasang, config log warning keras dan
  fallback ke sqlite lokal (bukan crash saat import engine).
- `tests/conftest.py`: pin `DATABASE_URL` sqlite in-memory sebelum import app,
  supaya koleksi tes tak pernah menyentuh URL postgres `.env`.
- `start-backend.sh` (baru, di root kaki): mereproduksi persis cara server
  live dijalankan — `cd` ke leg root, `PYTHONPATH=app/backend`,
  `DATABASE_URL` sqlite smoke DB (bisa di-override), `FLOW_AUTOMATION_ENABLED=1`,
  port 8002. Server live saat ini dijalankan lewat script ini.
- Bukti: `tests/test_config_env.py` (2 tes: path absolut + key termuat dari
  CWD `/tmp` via subprocess, hanya boolean — nilai key tidak pernah dicetak).

### (c) Genre jangan default "drama" diam-diam (SELESAI)
- Fakta yang diverifikasi: tidak ada literal default `"drama"` di kode
  backend/frontend — genre proyek nullable di semua tempat. Yang diperbaiki:
  langkah 1 kini meminta LLM mengembalikan `"genre"` dan, bila user tidak
  memberi genre, genre hasil inferensi disimpan di **job** (bukan proyek).
  Bila LLM tak mengembalikan genre, `job.genre` tetap `None` — kosong yang
  jujur, bukan tebakan.
- Mock bible kembalikan `"genre": "Romance"` supaya jalurnya teruji.
- Bukti: `test_genre_inferred_from_title_when_missing` (job tanpa genre →
  `genre: "Romance"`, `genre_inferred: true`, genre proyek tetap "Drama").
  Bukti live: smoke job tanpa genre → `genre: "Romance"`.

## 4. README diperbarui (SELESAI)
- `README.md` ditulis ulang: status Auto-Generate + Google Accounts +
  fallback + browser login + Flow automation; Quick Start pakai
  `start-backend.sh` (port 8002) + `NEXT_PUBLIC_API_URL`; endpoint
  Auto-Generate, Dialogue, EpisodeRevision, Story/Scene Engine; koreksi
  method (PATCH, bukan PUT) dan path Flow Bridge (`/projects/{id}/tasks`,
  bukan `/flow-tasks`); Known Limitations yang sudah tidak berlaku dihapus;
  Future Development kini hanya berisi yang benar-benar belum ada
  (resume job, WebSocket/SSE, video pipeline, dst.); catatan keamanan
  `.env` (jangan pernah di-commit, hanya `.env.example` di git).

## 5. File yang diubah
- Backend: `app/backend/app/api/v1/auto_generate.py`,
  `app/backend/app/schemas/auto_generate.py`,
  `app/backend/app/core/config.py`,
  `app/backend/app/services/ai_client.py` (mock saja),
  `app/backend/app/models/audit_log.py`,
  `app/backend/app/api/v1/episodes.py`,
  `app/backend/tests/conftest.py`.
- Tes: `app/backend/tests/test_auto_generate.py` (ditulis ulang: 7 → 15 tes),
  `app/backend/tests/test_dialogue_revision.py` (baru, 4 tes),
  `app/backend/tests/test_config_env.py` (baru, 2 tes).
- Frontend: `app/frontend/src/app/projects/[id]/page.tsx` (polling, 8 modal,
  realignment tab Prompt, 2 tombol Edit baru).
- Root kaki: `README.md` (ditulis ulang), `start-backend.sh` (baru),
  `FUTURE-DEV-REPORT.md` (file ini).
- **Tidak diubah:** kaki Hermes/Claude, migrasi Alembic (rantai 001–005 utuh),
  `.env` (tidak pernah ditulis/dicetak nilainya), data repo git.

## 6. Bukti tes
- `pytest` penuh: **187 passed** (baseline 173 passed; +14 tes baru, 0 gagal,
  0 skipped) — `app/backend/venv/bin/python -m pytest -q`.
- `npx tsc --noEmit`: 0 error. `npm run build`: 14/14 route.
- Smoke live (19 Nov ~21:2x, backend 8002 + frontend 3000 baru):
  register 201, login 200, project 201; POST auto-generate 201 dalam 0,19 dtk
  (`running`); poll per langkah berurutan sampai `completed` (~3,6 menit);
  genre terinferensi `Romance`; bible 1, karakter 5, lokasi 4, episode 5,
  prompt 5. Script: `/tmp/future-dev-smoke.py` (scratch, bukan workspace).
  Data smoke (user `smoke-*@future.dev`, proyek "SMOKE ASYNC TEST") tertinggal
  di `micro_drama_smoke.db` — DB smoke, bukan DB repo.
- Server live saat laporan ditulis: backend 8002 + frontend 3000 jalan dengan
  kode baru (backend via `start-backend.sh`).

## 7. NOT VERIFIED (jujur, di luar jangkauan dari VM ini)
- Klik manual tombol Auto-Generate + modal CRUD di browser (hanya tsc + build;
  butuh Di klik sendiri di http://127.0.0.1:3000 — dari Termux Di tidak
  menjangkau VM ini).
- Job 30 episode live (chunking teruji 7 episode di pytest; 30 episode belum
  dijalankan dengan LLM nyata).
- Login Google asli akun Di, submit prompt Flow nyata, video Flow asli.
- Resume job `running` pasca-restart server (sengaja tidak dibuat — lihat §3a).
