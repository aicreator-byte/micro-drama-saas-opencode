# Google Account Fallback — Flow Bridge (kaki OpenCode)

Tanggal: 2026-11-17 (perintah Di 21:03 WIB)
Status: SELESAI, terverifikasi pytest + smoke live. Tidak di-push ke GitHub.

## Ringkasan

Flow task sebelumnya terikat ke satu `google_account_id`: kalau akun itu
habis/kuota/token invalid, task gagal tanpa alternatif. Sekarang task
otomatis mencoba akun Google berikutnya milik user yang sama (yang
connected + sesi valid), sampai ada yang berhasil atau semua habis —
lalu gagal jujur (task FAILED + 503 + alasan per akun).

Pola meniru fallback LLM di `app/services/ai_client.py` (coba berurutan,
pindah hanya saat gagal, error jujur bila semua gagal), tapi di level
akun Google, mengikuti arsitektur OpenCode sendiri.

## Batasan yang ditemukan (jujur)

- **Belum ada eksekusi Flow otomatis di kaki ini.** API Flow Bridge
  sebelumnya hanya CRUD task; eksekusi nyata lewat browser automation
  masih digate `FLOW_AUTOMATION_ENABLED=1` + Playwright, dan mock
  automation sudah dicabut (tidak dikembalikan). Karena itu fallback
  diterapkan di **level pemilihan akun + retry task** (sesuai instruksi
  tugas bila eksekusi otomatis belum ada):
  - `POST .../tasks/{task_id}/execute` memilih akun yang usable dan
    menandai task `ready_for_generation` dengan akun tersebut.
  - Sukses di sini = **akun usable & terpilih**, BUKAN video berhasil
    digenerate. Generasi video nyata tetap manual / via automation
    (yang masih digate), dan service menyediakan hook `executor`
    agar executor Flow nyata nanti tinggal di-inject tanpa mengubah
    loop fallback.
- Pemeriksaan akun bersifat lokal (status + sesi terdekripsi + belum
  kedaluwarsa + ada access token). Tidak ada panggilan ke Google, tidak
  ada refresh token otomatis di jalur ini, tidak ada sesi palsu.

## File yang diubah / ditambah

| File | Perubahan |
|---|---|
| `app/backend/app/services/google_account_fallback.py` (BARU) | Loop fallback generik + klasifikasi kegagalan akun + validasi akun + wiring ke task |
| `app/backend/app/models/flow_bridge.py` | `FlowBridgeTask.fallback_history` (Text, JSON list attempt) |
| `app/backend/alembic/versions/004_add_flow_fallback_history.py` (BARU) | Migrasi 004 (revisi 003) |
| `app/backend/app/schemas/flow_bridge.py` | `fallback_history` di `FlowBridgeTaskResponse`; `FlowBridgeTaskExecuteRequest` (opsional `google_account_id` preferensi) |
| `app/backend/app/api/v1/flow_bridge.py` | Endpoint `execute` + `retry`; auto-select akun usable saat create task tanpa `google_account_id` |
| `app/backend/tests/test_google_fallback.py` (BARU) | 10 tes fallback |
| `GOOGLE-FALLBACK-REPORT.md` (file ini) | Laporan |

Tidak disentuh: kaki Hermes/Claude, folder audit, OAuth login, enkripsi,
rate limiting, security headers, SECRET_KEY, kredensial apa pun.

## Cara kerja fallback

1. **Urutan kandidat** — akun task saat ini (atau `google_account_id`
   di body execute/retry) dulu, lalu akun connected lain milik user
   yang sama, urut least-recently-used (akun yang paling lama tidak
   dipakai dulu, agar beban tersebar).
2. **Kapan pindah akun** — hanya kegagalan akun: HTTP 401/403/429, atau
   pesan berisi `quota`, `rate limit`, `token expired/invalid`,
   `refresh failed`, `session expired`, `unauthorized`, dsb.
   (`GoogleAccountFailure`, `classify_account_failure`).
   Error non-akun (mis. prompt invalid) **tidak** memicu pindah —
   langsung dilempar, akun lain tidak disentuh.
3. **Validasi akun (default executor)** — status harus `connected`,
   ada `encrypted_session_data`, sesi terdekripsi berisi access token,
   belum kedaluwarsa, dan `error_message` tidak menandai kuota habis.
   Gagal validasi = `GoogleAccountFailure` → lanjut ke akun berikut.
4. **Pencatatan** — tiap percobaan dicatat di
   `task.fallback_history` (JSON list `{google_account_id, email,
   outcome, reason}`), `google_account_id` task pindah ke akun yang
   berhasil, `last_used_at` akun berhasil di-update.
5. **Semua akun habis** — task `FAILED`, `error_message` berisi
   ringkasan per akun (email + alasan), endpoint kembalikan **503**
   dengan `detail.attempts` (bukan sukses diam-diam).
6. **Create task** — bila `google_account_id` tidak diisi, task
   otomatis diikat ke akun usable pertama; bila tidak ada yang usable,
   task tetap dibuat tanpa akun (fallback jalan saat execute/retry).

### Endpoint baru

- `POST /api/v1/projects/{project_id}/tasks/{task_id}/execute`
  (body opsional `{google_account_id}`) → 200 task
  `ready_for_generation` + `fallback_history`; 503 bila semua akun gagal.
- `POST /api/v1/projects/{project_id}/tasks/{task_id}/retry`
  (body opsional sama) → retry manual task failed/pending; task
  completed ditolak 400.

## Hasil tes

### Baseline (sebelum perubahan)

```
cd app/backend && ./venv/bin/python -m pytest tests/ -q -p no:cacheprovider
137 passed
```

### Pytest sesudah perubahan (10 tes baru)

```
./venv/bin/python -m pytest tests/test_google_fallback.py -q -p no:cacheprovider
10 passed
```

Tes mencakup: akun pertama 429 quota → akun kedua berhasil; semua akun
gagal → `AllGoogleAccountsFailed` + task FAILED + error berisi kedua
email; error non-akun tidak memicu fallback (akun kedua tidak disentuh);
endpoint execute pindah dari akun expired ke akun valid; semua expired
→ 503 + task failed; retry setelah akun diperbaiki → berhasil; retry
task completed → 400; create task auto-select akun usable.

### Pytest lengkap sesudah perubahan

```
./venv/bin/python -m pytest tests/ -q -p no:cacheprovider
147 passed (137 baseline + 10 baru)
```

### Migrasi 004 (DB segar)

```
DATABASE_URL="sqlite+aiosqlite:////tmp/mig-test.db" ./venv/bin/python -m alembic upgrade head
... 003 -> 004, Add fallback_history to flow_bridge_tasks
pragma_table_info('flow_bridge_tasks') -> [('fallback_history',)]
```

### Smoke live (backend port 8123, DB segar `/tmp/fallback-smoke.db`)

Perintah: `uvicorn app.main:app --host 127.0.0.1 --port 8123` dengan
`DATABASE_URL=sqlite+aiosqlite:////tmp/fallback-smoke.db`;
seed: user `smoke@example.com`, akun A `habis@example.com` (sesi
kedaluwarsa), akun B `cadangan@example.com` (sesi valid).

1. Buat task terikat akun A → `POST .../tasks` 201, status `pending`.
2. `POST .../tasks/{id}/execute` → **200**, status
   `ready_for_generation`, `google_account_id` = B,
   `fallback_history`: A `failed` / `session expired`, B `success`.
3. Akun B dibuat kedaluwarsa, task ke-2 dieksekusi → **503**
   `All Google accounts failed`, GET task → status `failed`,
   `error_message` menyebut kedua email + alasan.
4. Akun B diperbaiki (sesi valid lagi), `POST .../retry` → **200**,
   status `ready_for_generation`, akun B terpilih.

Server tes dimatikan setelah smoke (`curl /health` → tidak merespons);
DB + file seed sementara di `/tmp` sudah dihapus. DB repo tidak disentuh.

## Yang TIDAK dikerjakan + alasan

- **Eksekusi Flow otomatis (generate video nyata) dengan fallback
  di dalam automation** — belum ada executor otomatis di kaki ini;
  automation nyata masih digate dan mock sudah dicabut. Fallback
  diimplementasikan di level pemilihan akun + retry, dengan hook
  `executor` siap dipakai executor nyata nanti.
- **Refresh token otomatis saat fallback** — di luar scope; refresh
  tetap lewat endpoint `POST /google-accounts/{id}/refresh` yang sudah
  ada. Akun dengan sesi kedaluwarsa dilewati, bukan di-refresh diam-diam.
- **Security (rate limiting, headers, SECRET_KEY, enkripsi)** —
  DITUNDA sesuai perintah; tidak ada yang diubah.
- **Rotasi secret live yang ter-commit** (`.env` = `.env.example`) —
  masih blocker terbuka; tidak disentuh.
- **UI frontend** — tidak diubah; endpoint + field sudah tersedia
  untuk dipakai frontend nanti (`fallback_history` di response task).
- **Push GitHub** — tidak dilakukan, sesuai instruksi.
