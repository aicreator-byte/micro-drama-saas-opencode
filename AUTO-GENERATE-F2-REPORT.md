# AUTO-GENERATE Fase 2 — Frontend (kaki OpenCode)

**Spek:** `~/workspace/micro-drama-saas/AUTO-GENERATE-SPEC.md` §6 (Gate 1, disetujui Di 19 Nov 04:04)
**Brief:** `AUTO-GENERATE-F2-PROMPT.md`
**Kontrak backend (Fase 1, TIDAK diubah):** `AUTO-GENERATE-F1-REPORT.md`
**Status:** SELESAI (frontend saja). Backend TIDAK disentuh, kaki lain TIDAK disentuh, TIDAK push GitHub.

## Yang dibangun

### 1. Tombol Auto-Generate — halaman detail proyek
`app/frontend/src/app/projects/[id]/page.tsx` (header, di samping judul proyek):
tombol **Auto-Generate** (ikon Sparkles) → buka modal. Form terisi awal dari proyek
(judul, genre, jumlah episode).

### 2. Modal input
Judul (wajib), Genre, Jumlah episode (1–60, default 30), Premis (opsional).
Submit → `POST /api/v1/projects/{id}/auto-generate`.

### 3. Progres 5 langkah + Retry
Setelah submit, modal menampilkan 5 langkah (Series Bible → Characters → Locations →
Episodes → Prompts) dengan status tiap langkah + pesan error bila gagal. Langkah gagal
mendapat tombol **Retry** (`POST .../auto-generate/{job_id}/retry/{step}`).
Job selesai → semua data tab di-refresh otomatis (project, bible, karakter, lokasi,
episode, prompt) + muncul tombol **View results** yang melompat ke tab
Series Bible / Characters / Locations / Episodes / Prompts. Tombol **Refresh status**
memakai `GET .../auto-generate/{job_id}` untuk job yang lalu; **Start a new job**
mengulang dari form.

### 4. API client baru
`app/frontend/src/lib/api.ts` — `autoGenerateApi` (`create` / `get` / `retry`),
gaya sama seperti `storyEngineApi` yang sudah ada.

### 5. §7 — counter vs badge (diperbaiki)
- **Counter dashboard** (`app/frontend/src/app/dashboard/page.tsx`): "Active Projects"
  tadinya hanya `status == IN_PROGRESS` → sekarang **DRAFT + IN_PROGRESS**.
  Definisi tunggal: aktif = pekerjaan yang masih berjalan (draft atau in progress);
  COMPLETED / ARCHIVED bukan aktif. Proyek draft seperti "THE BILLIONAIRE CEO"
  sekarang terhitung aktif (sebelumnya 0).
- **Badge di daftar proyek** (`app/frontend/src/app/dashboard/projects/page.tsx`):
  badge "Active" yang sebenarnya menandai proyek yang sedang dipilih
  (`currentProject?.id === project.id`) diganti jadi **"Current"** — sesuai artinya,
  dan konsisten dengan menu "Set as Current" yang sudah ada. Tidak lagi bentrok
  dengan counter.

## Penyimpangan dari brief (dengan alasan, terverifikasi dari kode backend)

**Progres live saat job berjalan TIDAK BISA ditampilkan — bukan karena frontend,
melainkan kontrak backend Fase 1.** Terverifikasi di
`app/backend/app/api/v1/auto_generate.py` (`create_auto_generate_job`, baris 513–575):
`POST /auto-generate` membuat job, lalu menjalankan ke-5 langkah **sinkron di dalam
request** (`await _execute_steps(...)`) dan baru mengembalikan respons setelah semua
langkah selesai. `POST .../retry/{step}` juga sinkron. Akibatnya:
- Tidak ada job id yang bisa di-poll selama job berjalan (tidak ada endpoint list jobs).
- `GET .../auto-generate/{job_id}` hanya bermakna SETELAH job selesai / untuk job lalu.

Yang dilakukan frontend sebagai gantinya (jujur, tanpa pura-pura live):
- Saat submit berjalan: status "Generating all 5 steps — this can take a few minutes"
  + daftar 5 langkah berstatus menunggu + pesan "keep this tab open".
- Setelah respons kembali: status final tiap langkah + error + Retry per langkah gagal.
- Tombol "Refresh status" (GET) untuk memeriksa ulang job yang sudah ada.

Bila progres live per langkah diinginkan, backend harus mengembalikan job id dulu lalu
jalan di background — itu perubahan backend, di luar scope Fase 2 (brief melarang ubah
backend). Dicatat untuk Fase 3 / tindak lanjut, bukan dikerjakan di sini.

## File diubah (4 file, frontend saja)

| File | Perubahan |
|---|---|
| `app/frontend/src/lib/api.ts` | + `autoGenerateApi` (create/get/retry). |
| `app/frontend/src/app/projects/[id]/page.tsx` | + tombol header, + modal Auto-Generate (form/progres/retry/hasil), + tipe `AutoGenerateJob`/`AutoGenerateStep`, + handler submit/retry/refresh. CRUD manual tidak diubah. |
| `app/frontend/src/app/dashboard/page.tsx` | Counter Active: IN_PROGRESS saja → DRAFT + IN_PROGRESS. |
| `app/frontend/src/app/dashboard/projects/page.tsx` | Badge "Active" → "Current". |

**Tidak disentuh:** semua file backend (`app/backend/...` — timestamp terakhir 21:10/21:11
UTC = pekerjaan Fase 1, bukan Fase 2), kaki lain, auth/security, fallback akun Google,
Flow Bridge, CRUD manual.

## Hasil verifikasi (angka persis)

- `npm run type-check` (`tsc --noEmit`): **bersih, 0 error.**
- `npm run lint` (`next lint`): **0 error, 3 warning — ketiganya pre-existing, bukan
  dari pekerjaan ini** (useEffect deps baris 480; `<img>` tanpa optimasi baris 1978;
  `<img>` tanpa alt baris 2141). Peringatan exhaustive-deps yang sempat muncul dari
  `refreshAutoGenData` sudah diperbaiki (fungsi biasa, bukan useCallback — hanya
  dipanggil dari event handler).
- `npm run build` (`next build`): **sukses — 14/14 halaman ter-generate**,
  `/projects/[id]` 14,9 kB, First Load JS 141 kB.
- Tidak ada test frontend di repo ini (package.json: hanya dev/build/start/lint/
  type-check) — tidak ada tes yang bisa dijalankan/ditambah.

## Temuan pre-existing (DITEMUKAN, TIDAK diperbaiki — di luar scope)

Halaman detail proyek (`projects/[id]/page.tsx`) punya state `showSeriesBibleModal`,
`showCharacterModal`, `showLocationModal`, `showEpisodeModal`, `showPromptModal`,
`showFlowTaskModal`, `showOauthModal` + tombol yang mengesetnya `true`, **tetapi tidak
ada satu pun JSX modal yang dirender** (grep `show*Modal &&` / `fixed inset-0` kosong).
Artinya tombol "Create Series Bible", "Add Character", dst. di halaman ini saat ini
tidak membuka apa-apa. Ini cacat lama (bukan dari Fase 2) — modal Auto-Generate yang
saya buat dirender dengan benar (pola `fixed inset-0` dari halaman dashboard/projects)
dan tidak mengikuti pola rusak itu. Perbaikan modal-modal CRUD lama diserahkan ke
keputusan kontrol (Fase 3 akan menemukannya saat smoke test manual).

## Cara pakai (untuk Fase 3)

1. Buka proyek → klik **Auto-Generate** di header.
2. Isi judul (wajib) / genre / jumlah episode / premis → **Start Auto-Generate**.
3. Tunggu sampai selesai (beberapa menit, 5 panggilan LLM) → lihat status tiap langkah.
4. Langkah gagal → **Retry** pada langkah itu saja.
5. Job completed → klik **Series Bible / Characters / Locations / Episodes / Prompts**
   untuk melihat hasil (data sudah di-refresh otomatis).

## NOT VERIFIED

- **Klik manual di browser + smoke live dengan LLM nyata** (itu Fase 3): semua
  verifikasi di atas adalah type-check/lint/build, bukan interaksi browser.
- **Kualitas konten LLM nyata** (bible/karakter/episode/prompt hasil generate).
- **Job 30 episode end-to-end** (1 prompt per episode dalam 1 panggilan LLM) —
  bila JSON terpotong, langkah 5 gagal dan bisa di-retry (sudah ada tombolnya).
- **Paritas antar kaki:** implementasi ini khusus OpenCode; Hermes/Claude mengerjakan
  kakinya sendiri.
