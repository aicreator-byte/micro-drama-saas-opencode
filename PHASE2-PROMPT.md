MARKER: PHASE2-OPENCODE
# Phase 2 — Kaki OpenCode: LLM nyata + OAuth Google nyata + UI modul unik

Baca dulu `../PHASE2-PROMPT.md` (spec bersama + desain settings/env + larangan) —
itu mengikat. Prompt ini hanya tugas spesifik kaki OpenCode.

KONTEKS (terverifikasi dari kode + audit, jangan diperdebatkan):
- Kerja HANYA di `/home/hatch/workspace/micro-drama-saas/opencode/`. Jangan sentuh
  kaki lain atau file di luar direktori ini.
- Backend: `app/backend/app/` — router di `app/backend/app/api/v1/` (prefix
  `/api/v1` via `app/backend/app/main.py`); config
  `app/backend/app/core/config.py`; enkripsi
  `app/backend/app/core/encryption.py`; model/skema per modul di
  `app/backend/app/models/` + `app/backend/app/schemas/`; service Flow Bridge
  di `app/backend/app/services/flow_bridge_automation.py`.
- Frontend: Next.js di `app/frontend/src/app/` (login, register, dashboard:
  projects, characters, locations, episodes, prompts, settings, series-bible;
  detail proyek `app/projects/[id]/page.tsx`). Halaman Settings SUDAH ADA
  (`dashboard/settings/page.tsx`) — kembangkan itu, jangan buat baru.
- Baseline: pytest 109/109, smoke 19/19, build 14/14 halaman. Jangan turunkan.

TUGAS (hanya ini):
1. **LLM nyata ganti mock Story Engine + Scene Engine**
   (`app/backend/app/api/v1/story_engine.py` — mock di 4 endpoint: story,
   character arc, world building, refinement; `scene_engine.py` — mock di
   4 endpoint: episode breakdown, shot list, dialogue, action/choreography):
   buat satu modul klien AI kecil (mis.
   `app/backend/app/services/ai_client.py`, pakai `httpx` yang sudah
   terpasang): baca daftar provider + urutan fallback dari setting (lihat
   spec bersama), kunci dari env var, panggil chat completions, fallback ke
   provider berikut bila gagal/kuota/kosong. Ganti KEDELAPAN mock dengan
   panggilan LLM nyata. Provider terverifikasi jalan: Nvidia NIM ultra-550b —
   jadikan entri pertama/aktif. Jangan klaim provider lain jalan.
2. **Settings API + model** (baru, ikuti pola router/model yang ada):
   tabel/model `AppSettings` (satu baris): `ai_providers` (JSON, lihat spec),
   `google_oauth_client_id` + `google_oauth_client_secret` (enkripsi pakai
   `app/backend/app/core/encryption.py`). Endpoint `GET /api/v1/settings`
   (tanpa nilai rahasia — hanya flag `configured`) dan `PATCH /api/v1/settings`
   (ubah urutan/enabled provider, isi kredensial OAuth). Kunci AI tetap env var,
   tidak disimpan di DB. Kembangkan halaman Settings yang sudah ada untuk
   mengedit ini (daftar provider + urutan fallback + kredensial OAuth sebagai
   field password yang tidak pernah tampil nilainya).
3. **OAuth Google nyata + verify nyata**
   (`app/backend/app/api/v1/google_accounts.py`): endpoint `verify` yang ada
   HANYA menstempel `last_verified_at` (baris ~223–244) — GANTI dengan
   pengecekan nyata (`tokeninfo`/`userinfo`); bila tidak bisa dicek, kembalikan
   status jujur "unverified". Implementasikan authorize URL Google asli
   (state acak per request, simpan + validasi di callback), callback tukar
   `code` → token (httpx POST ke token endpoint Google), simpan token
   terenkripsi, refresh saat kedaluwarsa. Tambah field `password_encrypted`
   pada record akun Google (enkripsi yang sama) untuk Flow Bridge.
   BATAS: kredensial OAuth client asli dari Di belum ada — verifikasi alur
   + URL + callback + refresh; login end-to-end = NOT VERIFIED di laporan.
4. **UI modul unik** (frontend, di halaman detail proyek `app/projects/[id]/`):
   7 dari 9 tab masih placeholder — bangun UI nyata untuk Story Engine,
   Scene Engine, Flow Bridge, Google Accounts, Export, Audit Logs (pakai
   endpoint yang sudah ada + yang baru dari tugas 1–3; ikuti pola tab
   Characters/Episodes yang sudah jalan). Tab Prompts sudah ada — jangan
   bangun ulang, hanya wire bila perlu.
5. **Paritas model (sekunder)**: tambah model `Dialogue` + `EpisodeRevision`
   (ikuti pola model/skema yang ada, pakai migrasi Alembic) — Hermes punya
   keduanya, OpenCode belum. JANGAN ubah model lain.
6. **Kerapian kecil** (sekunder, jangan bila mengorbankan tugas 1–4):
   serialisasi JSON konsisten (`json.dumps` di semua tempat, tambah helper
   parsing); hapus file migrasi Alembic duplikat (`001_initial_schema.py`);
   hapus `micro_drama.db` (±340MB) dari repo + tambahkan ke `.gitignore`.

JANGAN UBAH: route/prefix `/api/v1`/skema respons yang ada; `SECRET_KEY`,
auth/JWT, enkripsi yang ada; batas karakter (maks 6 TIDAK ditegakkan);
Flow Bridge Playwright yang sudah jalan (tugas ini TIDAK mengganti
automasi browser — hanya tambah fallback akun + password terenkripsi).

SEBELUM menyatakan selesai, jalankan sendiri tes live (uvicorn + SQLite segar):
register + login (form-data) + proyek + 6 karakter + episode + story generate
LLM nyata + scene generate LLM nyata (konten BUKAN template mock — buktikan
dengan potongan respons) + shot list LLM nyata + auth URL Google terbentuk
(awal `https://accounts.google.com/o/oauth2/v2/auth`, berisi `state`) + callback
menolak `state` salah + verify akun melakukan cek nyata + Settings PATCH
tersimpan + `GET /settings` tidak membocorkan rahasia + tab Story/Scene/
Flow/Google/Export/Audit me-render + pytest tidak turun dari 109 +
`npm run build` exit 0. Tulis `PHASE2-REPORT.md` (apa yang diubah + hasil
tes live per endpoint + NOT VERIFIED: login Google end-to-end).
