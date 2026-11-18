Perbaiki 3 temuan verifikasi independen sesudah PHASE2-REPORT.md ditulis (pytest 109/109 dan build 14/14 BENAR; smoke live 22/25).

KONTEKS (terverifikasi dari kode + tes live, jangan diperdebatkan):
- Server start di DB segar OK (create_all). Auth JSON + login form-data, isolasi tenant, series-bible, lokasi, episode, scene 201, prompts, OAuth authorize/callback 400, Settings PATCH + tanpa bocor, 20 akun Google + ke-21 ditolak — SEMUA LULUS.
- Yang GAGAL (3 temuan):

TEMUAN 1 (wajib): karakter ke-7 DITOLAK 400.
- `app/api/v1/characters.py` baris 40-48 masih menegakkan maks 6 karakter ("Maximum of 6 characters allowed per project").
- Keputusan Di 17 Nov 06:50: maks 6 TIDAK ditegakkan ("klo udh ada gpp ga ush diubah") — karakter ke-7 dibiarkan. Prompt Phase 2 juga melarang batas ini.
- Perbaiki: hapus batas maks 6 karakter (API + validasi apa pun yang terkait). Jangan tambah batas lain.

TEMUAN 2 (wajib): story generate LLM GAGAL 502 "All AI providers failed: Invalid port: ':1]'".
- Penyebab (terverifikasi): `httpx.AsyncClient(timeout=120.0)` di `app/services/ai_client.py` memakai `trust_env=True` (default) — ia membaca proxy dari env, dan entri `no_proxy` di lingkungan ini berisi IPv6 berkurung (`[::1]`, `[fd8b:...]`) yang membuat parser proxy httpx gagal dengan `InvalidURL("Invalid port: ':1]'")`.
- BUKTI kunci + endpoint sehat: panggilan langsung dengan proxy eksplisit `httpx.AsyncClient(proxy='http://hatch-egress-proxy:3128')` ke `https://integrate.api.nvidia.com/v1/chat/completions` mengembalikan HTTP 200 ("OK"). Jadi bukan kunci/endpooint yang rusak.
- Perbaiki: bangun httpx client dengan proxy eksplisit dari env (`HTTPS_PROXY`/`https_proxy`) dan JANGAN andalkan parsing env httpx (mis. `trust_env=False` + `proxy=os.getenv(...)`, atau tangkap dan abaikan entri no_proxy yang rusak). Perbaikan harus di kode ai_client (bukan di env), supaya jalan di lingkungan ini. Uji dengan menjalankan story generate sungguhan (bukan unit test mock).

TEMUAN 3 (gap, perbaiki bila kecil): Settings GET di DB segar mengembalikan `ai_providers: []` (kosong).
- `get_ai_client` memang punya fallback default Nvidia di kode, tapi baris AppSettings yang dibuat otomatis menyimpan daftar kosong — jadi tab AI Providers di UI menampilkan daftar kosong di instalasi segar, padahal spek Phase 2: daftar provider + urutan fallback ada di setting DB.
- Perbaiki: seed provider default (Nvidia ultra-550b, key_env NVIDIA_API_KEY, enabled, priority 1) ke AppSettings saat pertama dibuat, supaya GET settings menampilkan provider itu. Jangan simpan nilai kunci di DB (hanya key_env).

TUGAS (hanya ini, kerja HANYA di /home/hatch/workspace/micro-drama-saas/opencode/):
1. Perbaiki ketiga temuan di atas. JANGAN ubah: auth/JWT, enkripsi, route/skema respons lain, tes yang sudah ada. JANGAN sentuh security. JANGAN sentuh kaki lain.
2. PERINGATAN — JANGAN pakai `pkill -f` untuk mematikan server tes: pola pkill bisa cocok dengan shell agen sendiri dan membunuh agen (sudah terjadi: builder fix sebelumnya mati karena `pkill -f "uvicorn app.main:app"`). Matikan server tes dengan PID eksplisit (tangkap `$!` saat start, lalu `kill <PID>`), atau cek port dengan curl saja tanpa mematikan.
3. SEBELUM menyatakan selesai, jalankan sendiri tes live di DB SEGAR: nyalakan server (uvicorn + kunci Nvidia asli dari env), lalu curl: karakter ke-7 → 201; story generate (outline, total_episodes 1, premise berisi kata kunci unik) → completed DAN output berisi kata kunci itu (BUKTI LLM nyata); settings GET → ai_providers berisi minimal 1 provider (Nvidia). Simpan bukti (status + cuplikan output) di laporan.
PENERIMAAN: pytest 109/109 (tidak boleh turun); smoke live: karakter ke-7 201, story generate LLM nyata completed, settings GET berisi provider; frontend `npm run build` exit 0.
Tulis PHASE2-FIX-REPORT.md (apa yang diubah + hasil tes live per cek + bukti LLM nyata).
