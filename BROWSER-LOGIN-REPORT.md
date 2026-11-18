# Jalur Login Browser + Auto Ganti Akun — Flow Bridge (kaki OpenCode)

Tanggal: 2026-11-17 (perintah Di 22:22 WIB — Di menolak jalur Google Cloud
Console: "Hrsnya login biasa. Dengan browser masing2")
Status: SELESAI, terverifikasi pytest + smoke live. Tidak di-push ke GitHub.

## Ringkasan

Flow task sekarang bisa dieksekusi lewat browser sungguhan tanpa Cloud
Console: Chromium (Playwright) login ke Google dengan email + password
akun — password didekripsi dari kolom `password_encrypted` yang sudah
ada, tanpa mengubah enkripsi — lalu menjalankan prompt task di Google
Flow. Sesi browser disimpan per akun (profil persisten), jadi login
cukup sekali. Bila satu akun gagal (login ditolak, kuota habis, sesi
kedaluwarsa), eksekusi OTOMATIS pindah ke akun berikutnya milik user
yang sama, dan tiap perpindahan tercatat di
`FlowBridgeTask.fallback_history` (field yang sudah ada dari kerjaan
fallback). Bila semua akun gagal, endpoint mengembalikan 503 + alasan
per akun + manual fallback (URL Flow + prompt) agar task tetap bisa
dikerjakan manual.

## Temuan lingkungan (terverifikasi, bukan asumsi)

1. **Playwright + Chromium SUDAH ada, dan `playwright install chromium`
   JALAN dari VM ini** (CDN Playwright tidak terblokir — dugaan awal di
   perintah tugas ternyata salah). Playwright 1.65.2 di venv; install
   mengunduh Chromium 1255 (headless shell + full) sehingga `launch()`
   default sekarang bekerja.
2. **Chromium TIDAK BISA bicara langsung ke egress proxy VM**:
   semua navigasi HTTPS gagal `net::ERR_TUNNEL_CONNECTION_FAILED`,
   sementara curl ke proxy + target yang sama berhasil, dan byte
   CONNECT Chromium sudah benar (dicek dengan fake proxy pencatat).
   Dicoba dan tetap gagal: proxy di launch/context, hostname/IP
   literal, pakai/tanpa kredensial, ECH off, UA spoof curl, Chromium
   full 1248 (bukan headless shell). **Solusi: relay CONNECT lokal**
   (`app/services/browser_proxy.py`, stdlib saja): Chromium -> relay
   127.0.0.1 -> egress proxy dengan CONNECT gaya curl (tanpa
   User-Agent) -> target. Lewat relay, `https://example.com` 200 dan
   `https://accounts.google.com` 200 (halaman sign-in, ada field
   email). Relay aktif default (`FLOW_BROWSER_USE_RELAY=1`); tanpa
   proxy di environment ia connect langsung, jadi aman di mesin lain.
3. **Egress proxy me-MITM TLS** (CA custom) — browser jalan dengan
   `ignore_https_errors=True` default (`FLOW_BROWSER_IGNORE_HTTPS_ERRORS=1`).
   Security DITUNDA sesuai perintah; ini dicatat sebagai batasan,
   bukan keputusan hardening.
4. **Google menolak sign-in akun yang tidak ada** dengan redirect ke
   `/v3/signin/rejected` (terverifikasi live) — bukan halaman error
   "Couldn't find your Google Account". Driver mendeteksi URL ini
   sebagai kegagalan akun (fallback ke akun berikut). Halaman sign-in
   juga me-render ulang ("Loading") beberapa detik setelah klik Next,
   jadi driver mem-poll password field/rejection/error sampai 30 dtk,
   bukan sekali cek.
5. **`ENCRYPTION_KEY` acak per proses bila tidak di-set di `.env`**
   (bawaan `config.py`, bukan buatan tugas ini): server yang
   di-restart tanpa `ENCRYPTION_KEY` yang sama TIDAK BISA mendekripsi
   password/sesi yang tersimpan. Smoke pertama gagal dengan alasan
   "stored password cannot be decrypted" karena ini; smoke diulang
   dengan `ENCRYPTION_KEY` + `SECRET_KEY` tetap dan lolos. **Untuk
   produksi: wajib set `ENCRYPTION_KEY` tetap di `.env`, kalau tidak
   semua password Google harus dimasukkan ulang tiap restart.**

## File yang diubah / ditambah

| File | Perubahan |
|---|---|
| `app/backend/app/services/browser_proxy.py` (BARU) | Relay CONNECT lokal (stdlib): Chromium -> 127.0.0.1 -> upstream proxy env (atau langsung). Tanpa log kredensial/body. |
| `app/backend/app/services/browser_flow.py` (BARU) | `PlaywrightBrowserDriver` (login, cek sesi, jalankan Flow, deteksi 2FA/captcha/kuota/rejected) + `BrowserFlowService` (login/sesi per akun, executor fallback, export manual) + `manual_flow_export` + `extract_flow_prompt`. |
| `app/backend/app/core/config.py` | Setting baru: `GOOGLE_FLOW_URL`, `FLOW_BROWSER_PROFILE_DIR`, `FLOW_BROWSER_USE_RELAY`, `FLOW_BROWSER_IGNORE_HTTPS_ERRORS`, `FLOW_BROWSER_HEADLESS`, `FLOW_GENERATION_TIMEOUT_SECONDS`. |
| `app/backend/app/services/google_account_fallback.py` | `execute_flow_task_with_fallback` dapat param `on_success` (dipakai executor browser untuk set COMPLETED/GENERATING + video URL). Loop fallback tidak berubah. |
| `app/backend/app/api/v1/flow_bridge.py` | Endpoint baru `POST .../tasks/{task_id}/execute-browser` (gate `FLOW_AUTOMATION_ENABLED=1` + Playwright, fallback browser, 503 + manual fallback bila semua gagal, FlowDomError -> 503 bukan 500). |
| `app/backend/app/api/v1/flow_bridge_automation.py` | Endpoint login lama kini mendelegasikan login sungguhan ke `BrowserFlowService` (dulu: step engine + cookie mentah disimpan tanpa enkripsi ke `encrypted_session_data`). Bentuk respons sama. |
| `app/backend/requirements.txt` | Tambah `playwright==1.65.2` (versi yang sudah terpasang). |
| `app/backend/tests/test_browser_flow.py` (BARU) | 19 tes (di bawah). |
| `BROWSER-LOGIN-REPORT.md` (file ini) | Laporan. |

Tidak disentuh: kaki Hermes/Claude, folder audit, OAuth, enkripsi,
rate limiting, security headers, SECRET_KEY, frontend, GitHub push.
Mock automation TIDAK dikembalikan (tetap dicabut).

## Cara kerja

### Login browser (tanpa Cloud Console)

1. `POST .../flow-bridge/automation/login` (atau `execute-browser`)
   memanggil `BrowserFlowService.login_account(db, account)`.
2. Password didekripsi dari `account.password_encrypted` dengan
   `encryption_service` yang sudah ada (tidak diubah), hanya di memori,
   diketik ke form Google, tidak pernah ditulis ke disk/log.
3. Playwright membuka **persistent context** per akun di
   `~/.cache/micro-drama-saas/browser-profiles/<account_id>/`
   (bisa diubah via `FLOW_BROWSER_PROFILE_DIR`). Cookie + localStorage
   tinggal di situ dan selamat dari restart proses.
4. Setelah login sukses: marker `session.json` ditulis di profil
   (`email`, `method=browser-password`, `verified_at` — tanpa secret),
   akun di DB jadi `CONNECTED` + `last_verified_at` di-update.
5. Tidak ada `client_id`/`secret` Cloud Console di jalur ini sama
   sekali. OAuth yang sudah ada tidak disentuh dan tidak dibutuhkan.

### Sesi dipakai ulang

`ensure_session`: buka profil akun -> cek `myaccount.google.com`
apakah masih login (redirect ke `accounts.google.com` = tidak) -> bila
tidak, login ulang dengan password tersimpan. Akun tanpa password
tersimpan gagal jujur (`GoogleAccountFailure: no password stored`).

### Eksekusi Flow + auto ganti akun

`POST .../tasks/{task_id}/execute-browser` (body opsional
`{google_account_id}`):

1. Gate: `FLOW_AUTOMATION_ENABLED=1` dan Playwright terpasang, kalau
   tidak 503 jujur.
2. Executor browser dipakai ke `execute_flow_task_with_fallback` yang
   sudah ada (urutan: akun task dulu, lalu LRU): tiap akun dicoba —
   sesi dipakai/login ulang -> prompt task dijalankan di
   `GOOGLE_FLOW_URL` (default `https://labs.google/fx/tools/flow`).
3. Gagal akun -> pindah otomatis: password salah, akun tidak ditemukan
   (`/signin/rejected`), 2FA/captcha/bot-detection, kuota Flow habis,
   sesi kedaluwarsa. Tiap percobaan tercatat di `fallback_history`.
4. Sukses: Flow mengembalikan video -> task `COMPLETED` +
   `output_assets=[video_url]`; bila dalam
   `FLOW_GENERATION_TIMEOUT_SECONDS` (default 600 dtk) video belum
   selesai -> task `GENERATING` (video mungkin masih dibuat di Flow).
5. Semua akun gagal -> task `FAILED` + 503 berisi `attempts` per akun
   dan `manual_fallback` (`flow_url` + `prompt` + judul task) untuk
   dikerjakan manual.
6. Error non-akun (prompt kosong, halaman Google tidak terjangkau /
   struktur DOM tidak dikenali) TIDAK memicu pindah akun: langsung
   gagal jujur (503 untuk DOM/network, tanpa membakar akun lain).

### Batasan deteksi (jujur)

- Selektor Flow (prompt box, tombol Create, `video[src]`) ditulis
  defensif (multi-selektor) tapi **DOM Flow belum pernah terverifikasi
  dengan akun nyata** — tidak ada kredensial Google asli untuk tes.
  Bila DOM berubah, driver melempar `FlowDomError` ("page structure
  not recognised") dan task tidak diklaim sukses.
- Google bisa menampilkan 2FA / captcha / "unusual traffic" kapan
  saja; semua itu dideteksi sebagai kegagalan akun (fallback ke akun
  berikut), bukan sukses diam-diam. 2FA tidak bisa dilewati otomasi —
  akun itu dilewati sampai user login manual.

## Hasil tes

### Pytest (19 tes baru, fake driver — tanpa akun Google asli)

```
cd app/backend && ./venv/bin/python -m pytest tests/test_browser_flow.py -q -p no:cacheprovider
19 passed
```

Cakupan: ekstraksi prompt (JSON / repr Python / teks polos / kosong);
login mock -> sesi tersimpan (marker ada, tanpa secret di marker);
password salah -> `GoogleAccountFailure`; tanpa password tersimpan ->
gagal jujur tanpa menyentuh browser; sesi kedaluwarsa -> login ulang;
sesi gagal -> pindah akun (history 2 percobaan, akun ke-2 sukses);
kuota Flow -> pindah akun; semua akun gagal -> `AllGoogleAccountsFailed`
+ task FAILED + kedua email di error; prompt kosong -> TIDAK fallback
(browser tidak disentuh); export manual (URL + prompt); endpoint
`execute-browser`: gate tanpa env -> 503; sukses -> `completed` +
`output_assets=[video_url]`; fallback endpoint -> akun ke-2;
semua gagal -> 503 + `manual_fallback`; relay CONNECT (unit, tanpa
network): CONNECT diteruskan + byte di-echo, tanpa header User-Agent
ke upstream; **real Chromium load halaman lokal** (`data:` URL, tanpa
network/kredensial) -> OK.

### Pytest lengkap

```
./venv/bin/python -m pytest tests/ -q -p no:cacheprovider
166 passed (147 baseline + 19 baru)
```

### Smoke live (backend port 8125, DB segar `/tmp/browser-smoke.db`,
`FLOW_AUTOMATION_ENABLED=1`, `ENCRYPTION_KEY`/`SECRET_KEY` tetap)

Seed: user `smoke@example.com`, akun A `habis@example.com`, akun B
`cadangan@example.com` (keduanya PALSU — tidak ada di Google;
password tersimpan terenkripsi).

1. `POST .../tasks/{id}/execute-browser` -> **503**
   `All Google accounts failed`: A `failed` /
   `Google rejected the sign-in for this account (account not found,
   or automation rejected)`, B `failed` / alasan sama. GET task ->
   status `failed`, `fallback_history` berisi kedua percobaan,
   `error_message` menyebut kedua email. Detail 503 berisi
   `manual_fallback` (`flow_url` + prompt task). Ini hasil yang
   BENAR untuk akun palsu: browser sungguhan mencapai halaman
   sign-in Google, Google menolak kedua akun, fallback jalan,
   tidak ada sukses palsu.
2. `POST .../flow-bridge/automation/login` (akun A) -> **201**,
   status `failed`, error sama seperti di atas (jalur login
   terdelegasi bekerja live).
3. Server tes dimatikan setelah smoke; DB + profil browser smoke
   (`~/.cache/micro-drama-saas/`, `/tmp/bl-*`) sudah dihapus.
   DB repo tidak disentuh.

### Smoke yang sempat gagal (diperbaiki selama kerja)

- Run 1: 500 `FlowDomError: could not reach Google account page:
  Page.goto: Timeout 30000ms` — `myaccount.google.com` lambat lewat
  relay. Perbaikan: cek sesi pakai `wait_until="commit"` + timeout
  60 dtk; timeout goto lain 30 -> 60 dtk.
- Run 1b: 503 `stored password cannot be decrypted` — seed dan server
  memakai `ENCRYPTION_KEY` acak yang berbeda (temuan no. 5 di atas).
  Perbaikan smoke: kunci tetap; bukan bug kode.
- Run 2: 503 `did not show a password field` — Google me-redirect
  akun palsu ke `/v3/signin/rejected` (temuan no. 4). Perbaikan:
  driver mem-poll password/rejection/error 30 dtk + deteksi URL
  `signin/rejected` sebagai kegagalan akun. Run 3 (final) lolos
  dengan alasan yang benar.

## Yang TIDAK dikerjakan + alasan

- **Login Google asli / generate video Flow asli** — tidak ada
  kredensial Google asli (Di belum berikan akun/password). Semua
  klaim di atas dibatasi pada yang terverifikasi: halaman sign-in
  termuat, akun palsu ditolak Google, fallback + manual export jalan.
  Uji dengan akun nyata butuh Di memasukkan email+password akun ke
  settings (kolom `password_encrypted` sudah ada) lalu menjalankan
  `execute-browser`.
- **Refresh token / sesi OAuth otomatis** — tidak diubah; jalur
  browser tidak memakai OAuth sama sekali.
- **Eksekusi Flow di background / antrean** — `execute-browser`
  memblokir request HTTP sampai Flow selesai (maks 600 dtk) atau
  semua akun gagal. Frontend sebaiknya memakai timeout panjang /
  polling status task. Di luar scope fungsionalitas ini.
- **Security (rate limiting, headers, SECRET_KEY, enkripsi,
  `ignore_https_errors`)** — DITUNDA sesuai perintah; tidak ada yang
  diubah kecuali mendokumentasikan `ignore_https_errors=True` sebagai
  syarat VM (MITM egress proxy).
- **UI frontend** — tidak diubah; endpoint + field sudah tersedia
  untuk dipakai frontend (`fallback_history`, `output_assets`,
  `manual_fallback` di detail 503).
- **Push GitHub** — tidak dilakukan, sesuai instruksi.

## Cara pakai (untuk Di / operator)

```bash
# .env backend — WAJIB kunci tetap, kalau tidak password Google harus
# dimasukkan ulang tiap restart (lihat temuan no. 5)
ENCRYPTION_KEY=<kunci-tetap-32-karakter>
SECRET_KEY=<kunci-tetap>
FLOW_AUTOMATION_ENABLED=1
# Opsional (default sudah benar untuk VM ini):
# GOOGLE_FLOW_URL=https://labs.google/fx/tools/flow
# FLOW_BROWSER_PROFILE_DIR=~/.cache/micro-drama-saas/browser-profiles
```

1. Tambah akun Google di Settings (maks 20/user), isi password
   Google-nya (tersimpan terenkripsi di `password_encrypted`).
2. Buat Flow task, lalu
   `POST /api/v1/projects/{id}/tasks/{task_id}/execute-browser`.
3. Bila 503: baca `detail.attempts` (akun mana gagal + kenapa) dan
   `detail.manual_fallback` (buka `flow_url`, login manual, tempel
   `prompt`). Bila akun kena 2FA/captcha, login manual sekali di
   browser biasa — sesi profil backend tidak berbagi cookie dengan
   browser Di, jadi login manual di HP/laptop tidak memperbaiki sesi
   backend; yang memperbaiki adalah login browser backend berhasil
   (atau ganti akun).
