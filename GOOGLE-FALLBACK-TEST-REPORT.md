# Uji Fallback Akun Google — Flow Bridge (kaki OpenCode)

Tanggal: 19 Nov 2026, ~08:40–08:50 WIB
Scope: HANYA mekanisme fallback akun Google di kaki OpenCode (endpoint
`execute-browser`). Bukan auto-generate, bukan fitur lain, bukan kaki lain.

## Ringkas

Mekanisme fallback **TERVERIFIKASI jalan**: eksekusi mencoba akun pertama,
gagal, otomatis pindah ke akun kedua, gagal lagi, lalu 503 jujur dengan
alasan per akun + manual fallback. `fallback_history` tercatat lengkap
di task. Relay CONNECT dipakai (Chromium mencapai Google sungguhan —
penolakan datang dari halaman sign-in Google, bukan dari network).

## Pivot (perintah parent 08:39 WIB)

Browser cloud TIDAK bisa membuka frontend localhost (127.0.0.1:3000
ditolak, invalid_request), jadi akun Google asli Di TIDAK bisa
ditambahkan lewat browser dan TIDAK ditunggu. Uji dialihkan ke 2 akun
tes palsu yang dibuat via API. **Login Google asli (akun Di) NOT
VERIFIED** — akun Di tidak pernah masuk ke DB kaki ini.

## Setup (semua via API, DB micro_drama_smoke.db yang sudah ada)

- User tes: `fallback-test@example.com` (register + login form OAuth2 OK)
- Akun A: `gagal-a@example.com`, id `8eedc19e-8c5b-43cf-bc7e-afb06c47946b`,
  status `connected`, password salah (nilai tidak dicatat di laporan ini)
- Akun B: `gagal-b@example.com`, id `a758d313-50eb-450a-8a94-01f7326becd6`,
  status `connected`, password salah yang berbeda
- Proyek: `FALLBACK-TEST`, id `3dff190e-77f7-4197-a238-7e6542a4e7d4`
- Task: `Fallback Test Task`, id `96b9905f-e5f1-42e0-9ee1-16de9a423bfd`,
  terikat akun A, prompt teks singkat (night market, neon)
- Akun dibuat via `POST /api/v1/google-accounts` (email + session_data
  dummy `{}`) lalu `PATCH /{id}` (password → tersimpan terenkripsi).
  Catatan: form Settings di frontend hanya terima email + session_data,
  bukan email + password — password masuk lewat endpoint PATCH.

## Temuan 1 — gate automation mati di server yang sedang jalan

Probe pertama `POST .../execute-browser` → **503 dalam 0,0 dtk**:
`Browser automation is unavailable: set FLOW_AUTOMATION_ENABLED=1`.
Penyebab: `automation_enabled()` baca `os.getenv(...)` (bukan Settings),
dan backend yang dijalankan parent 08:30 tidak membawa variabel itu
(`.env` juga tidak memuatnya).

Perbaikan (setup tes, bukan ubah kode): backend di-restart dengan
`FLOW_AUTOMATION_ENABLED=1`, CWD + `DATABASE_URL` + `PYTHONPATH` sama
persis. Insiden saat restart: `pkill` pola pertama mematikan PID yang
salah (bukan listener 8002), server baru gagal bind (address in use)
dan mati diam-diam sementara server lama tetap jalan — ketahuan karena
`/proc/<pid>/environ` listener tidak memuat flag tersebut. Diperbaiki
dengan kill PID listener asli (19695, terkonfirmasi via `ss`) lalu
start ulang; listener baru PID 21932, flag terverifikasi ada di environ
(`grep -c '^FLOW_AUTOMATION_ENABLED=1$'` = 1), `/api/v1/projects` 401
(server hidup). `ENCRYPTION_KEY` tetap dari `opencode/.env` (CWD sama),
jadi password tersimpan tetap bisa didekripsi.

## Hasil eksekusi

`POST /api/v1/projects/{id}/tasks/{task_id}/execute-browser` → **503
dalam 51,2 dtk**:

```json
{
  "message": "All Google accounts failed for this Flow task (browser login / Flow run)",
  "attempts": [
    {"email": "gagal-a@example.com", "outcome": "failed",
     "reason": "Google rejected the sign-in for this account (account not found, or automation rejected)"},
    {"email": "gagal-b@example.com", "outcome": "failed",
     "reason": "Google rejected the sign-in for this account (account not found, or automation rejected)"}
  ],
  "manual_fallback": {"flow_url": "https://labs.google/fx/tools/flow",
    "prompt": "A short cinematic test shot: a man walks through a night market, neon lights.",
    "task_title": "Fallback Test Task"}
}
```

Urutan terverifikasi: akun A dulu (akun terikat task), lalu akun B
(LRU). Kedua alasan gagal identik dan jujur untuk akun palsu.

## Status tersimpan (GET task + GET google-accounts, setelah eksekusi)

- Task: status `failed`, `google_account_id` tetap akun A,
  `fallback_history` berisi kedua percobaan (id + email + outcome +
  reason, urutan A lalu B), `error_message` menyebut kedua email +
  alasan.
- Kedua akun: status tetap `connected`, `error_message` null —
  kegagalan dicatat di task, bukan di akun.
- Log backend: 2 baris WARNING `google_account_fallback` ("failed,
  trying next") untuk A lalu B; **0 baris ERROR**; tidak ada
  `ERR_TUNNEL_CONNECTION_FAILED` atau traceback.

## Relay (FLOW_BROWSER_USE_RELAY)

Dipakai. Setting default `True` (config.py:38, tanpa override di `.env`
maupun environment proses). Bukti di log backend:
`INFO:app.services.browser_proxy:CONNECT relay listening on 127.0.0.1:43681`.
Profil browser persisten dibuat per akun di
`~/.cache/micro-drama-saas/browser-profiles/<account_id>/` (dua
direktori, masing-masing berisi `Default/`). Penolakan sign-in datang
dari Google (redirect penolakan akun), bukan dari kegagalan network —
Chromium mencapai `accounts.google.com` lewat relay. Konsisten dengan
smoke browser-login 17 Nov (alasan penolakan yang sama untuk akun palsu).

## Yang dibuktikan / TIDAK dibuktikan

Dibuktikan:
- Loop fallback browser: urutan percobaan, pindah akun saat gagal,
  pencatatan `fallback_history`, 503 + `manual_fallback` saat semua gagal.
- Relay CONNECT berfungsi untuk Chromium → Google dari VM ini.
- Gate `FLOW_AUTOMATION_ENABLED` bekerja (503 jujur saat mati).

TIDAK dibuktikan (NOT VERIFIED):
- Login Google asli (akun Di) — tidak pernah masuk DB; butuh akun
  dimasukkan lewat UI/API dari mesin yang menjangkau localhost.
- Jalur sukses: akun valid → login berhasil → prompt dijalankan di
  Flow → video/COMPLETED. DOM Flow belum pernah diuji dengan akun nyata.
- Penanganan live 2FA/captcha/kuota habis (hanya klasifikasi kodenya
  yang teruji lewat tes unit 17 Nov, bukan live).
- Generate video — tidak dicoba (di luar scope perintah).

## Perubahan di luar kode produk

- Restart backend 8002 dengan `FLOW_AUTOMATION_ENABLED=1` (proses
  PID 21932; kode tidak diubah; DB dan `.env` tidak diubah).
- Data tes di `micro_drama_smoke.db`: user `fallback-test@example.com`,
  2 akun Google palsu, proyek `FALLBACK-TEST`, 1 task failed.
  (DB yang sama dipakai F3 smoke; data F3 tidak disentuh.)
