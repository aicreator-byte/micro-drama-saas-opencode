# AUTO-GENERATE Fase 1 — Backend (kaki OpenCode)

**Spek:** `~/workspace/micro-drama-saas/AUTO-GENERATE-SPEC.md` (Gate 1, disetujui Di 19 Nov 04:04)
**Brief:** `AUTO-GENERATE-F1-PROMPT.md`
**Status:** SELESAI (backend saja). Frontend TIDAK disentuh. Kaki lain TIDAK disentuh. TIDAK push GitHub.

## Yang dibangun

Satu job auto-generate, 5 langkah berurutan, tiap langkah menulis langsung ke tabel
proyek (tanpa Apply manual). Endpoint baru di `app/backend/app/api/v1/auto_generate.py`:

| Endpoint | Fungsi |
|---|---|
| `POST /api/v1/projects/{id}/auto-generate` | Buat job + 5 langkah, jalankan berurutan (sinkron, seperti `execute` Story Engine). Body: `title` (wajib), `genre`, `total_episodes` (default 30, 1–60), `premise`. Judul/genre/jumlah episode dari body juga ditulis ke header proyek. |
| `GET /api/v1/projects/{id}/auto-generate/{job_id}` | Status job + status tiap langkah + error. |
| `POST /api/v1/projects/{id}/auto-generate/{job_id}/retry/{step}` | Retry satu langkah gagal, lalu lanjut ke langkah pending berikutnya. Langkah completed ditolak (400), step tak dikenal ditolak (400). |

Langkah (urutan tetap `series_bible → characters → locations → episodes → prompts`):

1. **Series Bible** — panggilan LLM baru (`build_series_bible_prompt`): premise, main_plot,
   subplots, character_relationships, world_settings, tone, ending, episode_structure →
   upsert baris `SeriesBible`. Bible yang sudah diisi manual TIDAK ditimpa (dipakai ulang).
2. **Characters** — panggilan LLM baru (`build_characters_prompt`): 5 karakter inventaris
   (nama, role, umur, gender, background, motivasi, ketakutan, sifat) → baris `Character`.
3. **Locations** — pakai `generate_world_building_llm` yang sudah ada → baris `Location`.
4. **Episodes** — pakai `generate_story_outline_llm` + `apply_outline_episodes` (helper baru
   yang diekstrak dari endpoint apply Story Engine, perilaku identik) → baris `Episode`
   status OUTLINED, nomor yang sudah ada di-skip.
5. **Prompts** — panggilan LLM baru (`build_video_prompts_prompt`): 1 prompt
   `VIDEO_GENERATION` per episode (teks video vertikal 9:16 + negative prompt) → baris
   `Prompt` status DRAFT, terikat `episode_id`.

Aturan jalan: langkah gagal → job FAILED, langkah berikut TIDAK jalan (tetap pending).
Jalan ulang job / retry langkah → skip yang sudah ada (karakter/lokasi by nama,
episode by nomor, prompt video by episode) — tanpa duplikat. Key LLM dari env saja
(`get_ai_client` yang sudah ada), tidak disimpan di DB. Tidak ada eksekusi video.

## File yang diubah / dibuat

Dibuat:
- `app/backend/app/models/auto_generate.py` — `AutoGenerateJob`, `AutoGenerateStep`
  (+ enum status/nama langkah, `STEP_ORDER`).
- `app/backend/app/schemas/auto_generate.py` — request/response (gaya `from_attributes`
  seperti schema lain di kaki ini).
- `app/backend/app/api/v1/auto_generate.py` — router + 5 fungsi langkah + runner.
- `app/backend/tests/test_auto_generate.py` — 7 tes baru.
- `app/backend/alembic/versions/005_auto_generate_jobs.py` — migrasi (tabel
  `auto_generate_jobs` + `auto_generate_steps`).

Diubah:
- `app/backend/app/api/v1/__init__.py` — daftarkan router `auto_generate`.
- `app/backend/app/api/v1/story_engine.py` — ekstrak `apply_outline_episodes()`
  dari endpoint apply (perilaku identik, dipakai ulang langkah 4).
- `app/backend/app/models/audit_log.py` — tambah `AUTO_GENERATE_CREATE / _RUN / _RETRY`
  (nilai ≤25 karakter; kolom SQLite `action` VARCHAR(25) tanpa CHECK).
- `app/backend/app/services/ai_client.py` — 3 cabang mock untuk prompt baru
  (bible, cast 5 karakter, video prompt per episode; nomor episode di-parse dari prompt).

Tidak disentuh: semua file frontend, semua kaki lain, auth/security, fallback akun Google,
CRUD manual, Flow Bridge.

## Penyimpangan dari brief (dengan alasan, terverifikasi dari kode)

1. **Langkah 2 TIDAK memakai output `generate_character_arcs_llm`.** Fungsi itu hanya
   menulis arcs untuk karakter yang SUDAH ADA (`character_id`/`character_name` dari DB);
   pada proyek kosong ia mengembalikan arcs untuk nol karakter — tidak bisa memenuhi
   kriteria "≥4 karakter". Sebagai gantinya langkah 2 memakai panggilan LLM baru yang
   menciptakan 5 karakter lalu menulisnya ke tabel `Character`. Niat brief (karakter
   terisi otomatis) terpenuhi; jalur harfiahnya tidak mungkin.
2. **Langkah 1 tidak menimpa bible manual.** Bila bible sudah ada dan berisi premise,
   dipakai ulang (`reused_existing: true`). Menimpa akan menghapus kerja manual Di
   ("THE BILLIONAIRE CEO"). Perilaku ini ditutupi tes.
3. **§7.1 akun demo "Test": TIDAK ADA mekanisme seed di kaki ini.** Terverifikasi:
   `test@example.com` hanya ada di fixture tes (`tests/conftest.py`); tidak ada skrip
   seed / seed data di repo; DB `micro_drama.db` di repo ini kosong (0 user, 0 proyek).
   Akun "Test" yang Di lihat adalah user pertama yang registrasi di instance yang
   sedang jalan itu — `auth.py` menjadikan user pertama sebagai superuser (bootstrap).
   Jadi tidak ada kode yang bisa/harus diubah di sini; akun demo itu data di instance
   berjalan, harus dihapus/diganti di sana, bukan di repo ini.
4. **§7.2 counter "Active Projects 0" vs badge "Active": murni frontend.**
   Terverifikasi: dashboard menghitung hanya `status == IN_PROGRESS`
   (`app/frontend/src/app/dashboard/page.tsx:37`); badge "Active" di halaman proyek
   BUKAN status — tampil bila proyek itu proyek yang sedang dibuka
   (`currentProject?.id === project.id`). Tidak ada definisi status "active" di backend
   yang bisa disamakan. Dicatat untuk Fase 2 (frontend): samakan definisi/nama
   (mis. counter hitung DRAFT+IN_PROGRESS, atau badge diganti "Current").

## Hasil tes

Baseline SEBELUM perubahan (19 Nov, `venv312/bin/python -m pytest tests/`):
**162 passed, 3 failed, 1 skipped.** 3 gagal semuanya pre-existing di
`tests/test_browser_flow.py::TestExecuteBrowserEndpoint` — penyebab:
"Browser automation is unavailable: Playwright is not installed".
Bukan dari pekerjaan ini; tidak diperbaiki (instal Playwright + Chromium di luar scope).

Sesudah perubahan: **169 passed, 3 failed (yang sama persis), 1 skipped.**
7 tes baru `tests/test_auto_generate.py` — SEMUA LOLOS:
- job lengkap 5 langkah (bible + 5 karakter + 1 lokasi + 5 episode OUTLINED + 5 prompt video)
- GET job + 404 job tak ada
- bible manual dipakai ulang, tidak ditimpa
- jalan ulang job tanpa duplikat (karakter/lokasi/episode/prompt tetap 5/1/5/5)
- retry: langkah locations dibuat gagal (mock) → job FAILED, episode/prompt pending →
  retry locations → job COMPLETED, tanpa duplikat; retry langkah completed/unknown → 400
- validasi input (judul kosong, total_episodes 0 / 61 → 422)
- proyek user lain → 404

Migrasi 005 terverifikasi di DB scratch (`/tmp/mig-fresh.db`, bukan DB repo):
`alembic upgrade head` 001→005 sukses (tabel `auto_generate_jobs` +
`auto_generate_steps` ada, versi `005`); `alembic downgrade -1` sukses (005→004,
tabel terhapus). DB repo `micro_drama.db` TIDAK diubah.

## NOT VERIFIED

- **Smoke live dengan LLM nyata + server berjalan** (Fase 3): semua verifikasi di atas
  memakai mock provider. Kualitas konten LLM nyata (apakah bible/karakter/episode/
  prompt yang dihasilkan bagus dan konsisten) belum teruji.
- **Frontend** (Fase 2): belum ada tombol Auto-Generate / progres / retry di UI.
- **Paritas antar kaki:** implementasi ini khusus OpenCode; Hermes/Claude mengerjakan
  kakinya sendiri.
- **Volume besar:** mock outline selalu 5 episode; job 30 episode (1 prompt per episode
  dalam 1 panggilan LLM) belum teruji terhadap batas token — bila JSON terpotong,
  langkah 5 gagal dan bisa di-retry.
