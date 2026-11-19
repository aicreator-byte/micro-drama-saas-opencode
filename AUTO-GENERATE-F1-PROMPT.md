# AUTO-GENERATE Fase 1 — Backend (kaki OpenCode)

**Peran:** kamu agen builder kaki OpenCode. **Kontrol:** Muse (bukan kamu yang kontrol).
**Spek (Gate 1, disetujui Di 19 Nov 04:04):** `~/workspace/micro-drama-saas/AUTO-GENERATE-SPEC.md` — BACA DULU.
**Workspace kaki:** `~/workspace/micro-drama-saas/opencode/` (backend di `app/backend/app/api/v1/`).

## Tugas (Fase 1, backend saja — JANGAN sentuh frontend)

Implementasi spek §5 (API job) + §4 (5 langkah) + §7 bagian backend, di kaki OpenCode.

1. **API job:** `POST /projects/{id}/auto-generate` (body: judul/genre/jumlah episode/premis),
   `GET .../auto-generate/{job_id}` (status job + tiap langkah), `POST .../retry/{step}`.
   Job berurutan: 1 Series Bible → 2 Characters → 3 Locations → 4 Episodes → 5 Prompts.
   Langkah gagal → berikutnya TIDAK jalan; retry hanya langkah gagal.
2. **Langkah 2/3:** `apply` Story Engine HANYA bisa Episode (arcs/world = 400, terverifikasi).
   Buat jalur tulis baru dari output `generate_character_arcs` → tabel Character (default
   4–6 karakter) dan `generate_world_building` → tabel Location (default 3–5 lokasi).
3. **Langkah 5 Prompts:** TIDAK ADA endpoint generate di kaki ini (CRUD saja, terverifikasi).
   Buat endpoint generate prompt (dari Scene Engine `generate_scenes`/`generate_shots`/
   `generate_dialogue` atau LLM langsung), simpan via CRUD prompt yang ada. Minimal
   1 prompt per episode.
4. **Langkah 4 Episodes:** pakai `apply` yang sudah ada (skip nomor episode yang sudah ada,
   jangan duplikat). Status awal OUTLINED.
5. **Idempotent:** jalan ulang job → skip yang sudah ada (jangan duplikat karakter/lokasi/episode).
6. **§7 backend:** akun demo "Test" (test@example.com) jangan jadi akun aktif default —
   periksa mekanisme seed di kakimu dan perbaiki. Counter Active Projects: bila definisi
   status ada di backend, samakan (bila murni frontend, catat untuk Fase 2).
7. Pakai LLM client + Story/Scene Engine yang SUDAH ADA di kaki. Key Nvidia dari env saja,
   JANGAN simpan key di DB.

## Larangan (§8 spek)

- JANGAN eksekusi video otomatis (Flow/Veo). JANGAN ubah auth/security. JANGAN ubah fallback
  akun Google. JANGAN ubah CRUD manual yang ada. JANGAN push ke GitHub. JANGAN hapus file.
  JANGAN sentuh kaki lain.

## Tes + laporan

- Suite pytest lama harus tetap lolos (baseline 109/109). Tambah tes auto-generate: buat job,
  langkah berurutan, retry langkah gagal, jalan ulang tanpa duplikat.
- Tulis laporan: `~/workspace/micro-drama-saas/opencode/AUTO-GENERATE-F1-REPORT.md` — file yang
  diubah, endpoint baru, hasil pytest (angka persis), apa yang NOT VERIFIED.
- Bila terblokir (dependensi hilang, tes lama gagal dari sananya), catat di laporan dan
  hentikan item itu — jangan looping.
