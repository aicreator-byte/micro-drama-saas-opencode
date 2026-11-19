# FASE 4 — AUDIT SILANG AUTO-GENERATE (auditor: OPENCODE)

Perintah Di — Gate 2 DISETUJUI 19 Nov 06:47: audit silang fitur auto-generate.
Kamu auditor independen untuk kaki OPENCODE. Kamu MENG-AUDIT dua kaki lain:
- Hermes: `~/workspace/micro-drama-saas/hermes/`
- Claude: `~/workspace/micro-drama-saas/claude/`

JANGAN audit kaki OpenCode (itu tugas auditor lain). JANGAN ubah file kaki
yang diaudit (read-only). JANGAN push GitHub. JANGAN pakai key Nvidia live —
tidak ada panggilan LLM nyata; verifikasi via kode + tes + data yang sudah ada.

## Bahan acuan
- Spek: `~/workspace/micro-drama-saas/AUTO-GENERATE-SPEC.md` (§4 langkah,
  §5 API, §6 frontend, §7, §9 kriteria selesai)
- Laporan Fase 1/2 tiap kaki: `{leg}/AUTO-GENERATE-F1-REPORT.md`,
  `{leg}/AUTO-GENERATE-F2-REPORT.md`
- Laporan Fase 3 (smoke live):
  `~/workspace/micro-drama-saas/AUTO-GENERATE-F3-REPORT.md` — klaim smoke +
  2 bug yang diperbaiki kontroler saat smoke (field `NVIDIA_API_KEY` di
  Settings; fallback `ai_client` ke Settings). Verifikasi perbaikan itu di
  kode: apakah benar, lengkap, dan apakah pola bug yang sama masih ada di
  jalur auto-generate. Verifikasi klaim F3 bila memungkinkan tanpa LLM live
  (cek proyek smoke via API/DB read-only).

## Yang diaudit (fungsional saja — security DITUNDA, jangan audit security)
1. Backend: endpoint POST auto-generate + GET job + POST retry; 5 langkah
   (Bible → Characters → Locations → Episodes → Prompts); simpan langsung
   tanpa Apply; retry per langkah; idempotensi; validasi input; penanganan
   gagal LLM / job gagal; status job.
2. Frontend: tombol Auto-Generate + modal (judul/genre/jumlah episode/
   premis); progres 5 langkah + retry; perbaikan counter/badge §7 (bila
   berlaku di kaki itu).
3. Tes: jalankan suite tes auto-generate kaki yang diaudit (pytest), catat
   hasil (lolos/gagal, tes baru vs lama). Tes gagal: bedakan pre-existing
   vs terkait auto-generate.
4. Kesesuaian spek §9: apakah kriteria selesai terpenuhi di tiap kaki.

## Batasan
- JANGAN nyalakan server backend (port 8001–8003 sedang dipakai server
  smoke); verifikasi via kode + pytest saja.
- JANGAN sentuh kaki OpenCode, JANGAN sentuh kaki lain di luar yang diaudit.

## Keluaran
Tulis `~/workspace/micro-drama-saas/audit-3way-autogen-opencode/AUDIT-REPORT.md`:
- Per kaki yang diaudit: temuan terverifikasi (pisahkan FAKTA dari
  inferensi), tingkat keparahan (P0/P1/P2), yang sudah benar, skor per
  dimensi (kebenaran, kelengkapan vs spek, error handling, UX, cakupan
  tes), verdict.
- Tanpa perbaikan kode — audit saja. Bila menemukan bug, tulis lokasi
  file + baris + bukti, jangan perbaiki.
