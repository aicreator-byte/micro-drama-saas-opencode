# AUTO-GENERATE Fase 2 — Frontend (kaki OpenCode)

**Peran:** kamu agen builder kaki OpenCode. **Kontrol:** Muse.
**Spek:** `~/workspace/micro-drama-saas/AUTO-GENERATE-SPEC.md` §6 (baca dulu).
**Kontrak backend (Fase 1, JANGAN diubah):** `~/workspace/micro-drama-saas/opencode/AUTO-GENERATE-F1-REPORT.md` —
`POST /api/v1/projects/{id}/auto-generate` (body: `title` wajib, `genre`, `total_episodes` 1–60
default 30, `premise`), `GET /api/v1/projects/{id}/auto-generate/{job_id}`,
`POST /api/v1/projects/{id}/auto-generate/{job_id}/retry/{step}`.
**Frontend:** `~/workspace/micro-drama-saas/opencode/app/frontend/` (Next.js;
halaman detail proyek di `src/app/projects/[id]/page.tsx`, dashboard di `src/app/dashboard/page.tsx`).

## Tugas (frontend saja)

1. **Tombol Auto-Generate** di halaman detail proyek (tempat yang masuk akal, dekat tab Story Engine).
2. **Modal/form input:** judul (wajib), genre, jumlah episode, premis.
3. **Progres job:** setelah submit, polling `GET .../auto-generate/{job_id}`; tampilkan 5 langkah
   (Series Bible → Characters → Locations → Episodes → Prompts) dengan status tiap langkah +
   pesan error bila gagal.
4. **Retry:** tombol retry pada langkah yang gagal (endpoint retry Fase 1).
5. **Selesai:** job completed → refresh/arah ke data yang terisi (bible, karakter, lokasi,
   episode, prompt). JANGAN ubah CRUD manual yang ada.
6. **§7 (keanehan, terverifikasi):** dashboard menghitung Active hanya `status == IN_PROGRESS`
   (`src/app/dashboard/page.tsx:37`), sedangkan badge "Active" di halaman proyek tampil bila
   proyek itu yang sedang dibuka (`currentProject?.id === project.id`). Samakan: pilih SATU
   definisi konsisten (mis. counter hitung DRAFT+IN_PROGRESS, atau badge diganti "Current")
   dan terapkan di dashboard + halaman proyek. Catat pilihanmu di laporan.

## Larangan

JANGAN ubah backend/API, auth/security, fallback Google, Flow. JANGAN ubah CRUD manual
(selain menambah tombol/modal ini). JANGAN push GitHub. JANGAN hapus file. JANGAN sentuh kaki lain.
Pakai komponen/UI yang sudah ada di frontend kaki ini.

## Tes + laporan

- Bila frontend punya tes/build/typecheck (cek package.json), jalankan yang relevan dan
  catat hasilnya. Minimal: build/lint lolos.
- Tulis laporan: `~/workspace/micro-drama-saas/opencode/AUTO-GENERATE-F2-REPORT.md` — file diubah,
  cara pakai (langkah klik), hasil build/tes (angka persis), apa yang NOT VERIFIED (mis. uji
  klik manual di browser — itu Fase 3).
- Bila terblokir, catat di laporan dan hentikan item itu — jangan looping.
