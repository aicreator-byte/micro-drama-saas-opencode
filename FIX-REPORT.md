# FIX-REPORT — Kaki OpenCode Micro Drama SaaS (pasca-audit 3-arah ronde 2)

Tanggal: 17 Nov 2026. Lingkup: hanya `~/workspace/micro-drama-saas/opencode/`.
Kaki hermes/claude dan folder `audit-3way-round2*` tidak disentuh. Tidak ada push ke GitHub.
Tidak ada data dikirim ke layanan luar.

Dasar audit: `audit-3way-round2/SUMMARY.md` (§5.5, 5.6, 5.7, 5.8, 5.18, §6, §7)
+ Action Plan P0/P1 OpenCode di PART-9-10-11 ketiga laporan + temuan F-01 s.d. F-31
laporan OpenCode (`audit-3way-round2-opencode/AUDIT-REPORT.md`).

## 1. Ringkasan hasil

| Verifikasi | Hasil |
|---|---|
| pytest backend (`./venv312/bin/python -m pytest tests/ -q -p no:cacheprovider`) | **137 passed, 435 warnings** (baseline 109 passed, 1876 warnings) |
| `npm run build` frontend (setelah `rm -rf .next`) | **14/14 halaman, exit 0** |
| Migrasi DB segar (`alembic upgrade head`) | **001 → 002 → 003**, kolom baru ada, `alembic_version = 003` |
| Smoke live, backend port 8102, DB segar `/tmp/smoke8102.db` | **29/29 cek lolos** (skrip `/tmp/smoke_opencode.py`) |
| Smoke frontend `next start -p 3102` | `/dashboard` **200** (bukan 307 ke `/login`), `/projects/abc` 200, `/login` 200 |

Catatan: `git status` sudah kotor sebelum pekerjaan ini dimulai (modifikasi pre-existing
di hermes + opencode, termasuk `D app/backend/alembic/versions/001_initial_schema.py`);
daftar file di bawah hanya yang diubah dalam pekerjaan ini.

## 2. Yang diperbaiki

### 2.1 Automation mock dicabut dari DB (F-02, O-P0-02)
- `app/api/v1/flow_bridge_automation.py`: helper `_require_real_automation` — 4 endpoint
  mutasi (login, generate-images, check-account, refresh-session) mengembalikan **503**
  selama `mock_mode=True`; blok penulisan hasil ke `GoogleAccount`/`FlowBridgeTask`
  juga dijaga `and not automation.mock_mode`. Literal `"password": "***"` dihapus —
  mode nyata mengambil password dari kolom terenkripsi `password_encrypted`.
- `app/services/flow_bridge_automation.py`: instance global kini baca env
  `FLOW_AUTOMATION_ENABLED=1` untuk mode nyata (default mock).
- Mock provider AI (`ai_client._call_mock`) **dipertahankan** untuk tes; yang dicabut
  adalah mock *automation browser* yang menulis ke DB. Login nyata tetap NOT VERIFIED
  (tidak ada akun Flow nyata untuk diuji).
- Bukti smoke: `POST /flow-bridge/automation/login` → **503**; ciphertext
  `encrypted_session_data` identik sebelum/sesudah login; dekripsi = marker asli;
  status akun tetap `connected`.

### 2.2 Kolom karakter hilang (F-03, O-P0-03)
- `app/models/character.py`: tambah `voice_pattern`, `physical_traits`, `skills`
  (Text, nullable).
- `app/schemas/character.py`: ketiganya masuk `CharacterBase` + `CharacterUpdate`;
  `skills` masuk validator `parse_json_if_string`.
- `app/api/v1/characters.py`: create/update menyimpan + mengembalikan ketiga field.
- Migrasi baru `alembic/versions/003_add_character_fields.py` (revision `003`, down `002`).
- Pendukung migrasi: `alembic.ini` ditambah `script_location = alembic` (sebelumnya
  tidak ada → `alembic upgrade head` selalu gagal); `002_settings_and_google_oauth.py`
  — hapus 2 `create_index` eksplisit yang duplikat index auto
  (`ix_dialogues_scene_id`, `ix_episode_revisions_episode_id`) sehingga migrasi
  gagal di DB segar.
- Bukti smoke: karakter dibuat dengan ketiga field → **201**, nilai kembali utuh;
  task dialogue scene dengan karakter → **200** (sebelumnya AttributeError).

### 2.3 Middleware frontend login loop (F-04)
- `src/middleware.ts`: guard cookie `auth-storage` dihapus — middleware kini
  pass-through. Auth bersifat client-side (JWT di localStorage via zustand persist
  `auth-storage`; `DashboardLayout` + interceptor 401 di `lib/api.ts` yang redirect
  ke `/login`). Jangan tambah lagi cek cookie tanpa juga men-set cookie saat login.
- Bukti smoke: `curl` ke `/dashboard` dan `/projects/abc` pada `next start` → **200**,
  tanpa redirect ke `/login`.

### 2.4 Task PROCESSING → FAILED + retry (F-08, O-P0-05)
- `app/api/v1/story_engine.py` + `app/api/v1/scene_engine.py`: pada kegagalan LLM,
  task di-set `status=FAILED` + `error_message` + `completed_at`, commit + audit,
  lalu re-raise (caller tetap dapat 502). Execute hanya menolak status PROCESSING,
  jadi task FAILED bisa di-retry.
- Bukti smoke (tanpa `NVIDIA_API_KEY`): execute story → **502**; GET task →
  `failed` + `error_message` + `completed_at`; execute ulang → **502** (bukan 400).

### 2.5 Bootstrap superuser + change-password + dedupe (F-07/O-P0-06, F-24, F-31)
- `app/api/v1/auth.py`: register — bila belum ada superuser di DB, user pertama jadi
  `is_superuser=True` (agar `/settings` terjangkau di instalasi segar tanpa edit DB);
  audit REGISTER kini mencatat `is_superuser`. Endpoint baru
  `POST /auth/change-password` (verifikasi password lama, 400 bila salah,
  audit `PASSWORD_CHANGE`). `get_current_user` lokal yang duplikat dihapus — kini
  import dari `app.api.deps` (satu implementasi).
- `app/schemas/user.py`: tambah skema `PasswordChange` (`current_password`,
  `new_password` min 8).
- Bukti smoke: user pertama `is_superuser=true`, user kedua `false`;
  non-superuser GET `/settings` → **403**; change-password → **200**; login
  password baru → **200**, password lama → **401**.

### 2.6 PATCH /settings 500 (Hermes P0-11, F-20, F-23)
- `app/api/v1/settings.py`: `update_data.model_dump(...)` sudah mengubah nested model
  jadi dict, jadi `[p.model_dump() for p in providers]` selalu 500 — diperbaiki jadi
  toleran dict/model. Allowlist provider: hanya `nvidia` (plus `mock` hanya bila
  env `TESTING=true`); PATCH provider lain → 400. GET tidak lagi menulis audit log
  (dulu `PROJECT_READ` yang menyesatkan); PATCH kini memakai action `SETTINGS_UPDATE`.
- `app/models/audit_log.py` (enum `AuditAction`): tambah `EXPORT_SERIES_BIBLE`,
  `EXPORT_CHARACTERS`, `EXPORT_LOCATIONS`, `EXPORT_SCENES`, `EXPORT_FULL_PROJECT`,
  `SETTINGS_UPDATE`, `STORY_ENGINE_TASK_DELETE`, `SCENE_ENGINE_TASK_DELETE`,
  `DIALOGUE_CREATE`, `DIALOGUE_DELETE`, `EPISODE_REVISION_CREATE`.
- **Caveat:** enum SQLAlchemy di SQLite memakai CHECK constraint saat CREATE TABLE —
  DB lama yang dibuat sebelum perubahan ini akan menolak nilai action baru; berlaku
  bersih di DB segar (smoke pakai DB segar).
- Bukti smoke: PATCH `ai_providers` nvidia → **200** (dulu 500); GET `/settings`
  superuser → **200**, provider nvidia ter-seed.

### 2.7 Story/Scene Engine — context, semua karakter, tipe tak tereksekusi, apply (F-17/P1-07, F-18, F-19)
- `build_story_outline_prompt`: hapus `characters[:5]` + `generate_story_outline_llm`
  hapus `.limit(5)`; tambah parameter `user_context` — `StoryEngineRequest.context`
  kini disisipkan sebagai `USER INSTRUCTIONS (follow these first)` di prompt outline.
  Scene: hapus pemotongan `[:6]` (breakdown), `[:4]` (shots), `[:5]` (action) —
  semua karakter masuk prompt.
- `GENERATE_EPISODE` diimplementasi (`build_single_episode_prompt` +
  `generate_single_episode_llm`, `episode_number` dari parameters, context diteruskan).
  `GENERATE_SCENES` (scene engine) dialihkan ke breakdown (sebelumnya tanpa cabang →
  ValueError → FAILED).
- Endpoint baru `POST /{project_id}/story-engine/tasks/{task_id}/apply`: outline/episode
  → baris `Episode` (nomor yang sudah ada di-skip, tidak pernah ditimpa; status
  `OUTLINED`). Endpoint baru `POST.../scene-engine/tasks/{task_id}/apply`: breakdown
  → `Scene`; shots → `Shot`; dialogue → `Dialogue` (mengganti dialog lama scene itu);
  action → teks `Scene.action`. Keduanya 400 bila task belum COMPLETED/tanpa output.
- Delete story/scene task kini audit `STORY_ENGINE_TASK_DELETE` /
  `SCENE_ENGINE_TASK_DELETE` (dulu salah mencatat `*_CREATE`).
- `app/services/ai_client.py` (`_call_mock`): tambah cabang mock untuk prompt
  single-episode agar `GENERATE_EPISODE` bisa dites.
- Bukti smoke (provider mock di-seed langsung ke DB, lihat §4): dialogue execute →
  **200**, apply → **200**, 2 baris Dialogue terbaca; `generate_episode` (episode 3,
  context flashback Nadia) execute → **200**, apply → **200**,
  `created_episodes: [{episode_number: 3}]`.
- Catatan: hanya outline story yang diberi `user_context`; arcs/world memakai prompt
  lama (tanpa context) — cukup untuk temuan.

### 2.8 Google Accounts — URL-encode + disconnect bersih (F-09, Claude P1 #11, F-23)
- `app/api/v1/google_accounts.py`: `build_authorize_url` kini pakai
  `urllib.parse.urlencode` (dulu gabung `f"{k}={v}"` mentah — scope berspasi mentah,
  redirect_uri mentah). List akun tidak lagi audit `GOOGLE_ACCOUNT_VERIFY`.
  Disconnect kini mengosongkan `password_encrypted` + `session_expires_at` juga
  (dulu hanya `encrypted_session_data`). State OAuth `created_at` dari `fromisoformat`
  diberi `tzinfo=timezone.utc` bila naive.
- Bukti smoke: `GET /google-accounts/oauth/authorize` → **200**,
  URL tanpa spasi mentah, mengandung `redirect_uri=http%3A`.

### 2.9 Export — download nyata + CSV benar + riwayat 8 tipe (F-15, F-16, P1-08)
- `app/api/v1/export.py`: `download_export` dulu stub 307 — kini regenerasi deterministik
  dari DB via `create_export` internal, decode data-URL, kembalikan bytes dengan
  `Content-Disposition: attachment` + mime benar. `format_export` CSV kini CSV
  sungguhan (list record → baris; jika tidak ada list → baris key,value), mime
  `text/csv` (dulu JSON bermime JSON). Riwayat kini memfilter kedelapan action
  `EXPORT_*` (dulu hanya 3). `new_values` audit kini menyimpan `episode_id`
  (dibutuhkan regenerasi export episode).
- Bukti smoke: export characters create → **201**; download → **200** +
  `Content-Disposition: attachment`.

### 2.10 Dialogue + EpisodeRevision API (F-25, P2-03 — implementasi minimal)
- Skema baru `app/schemas/dialogue.py`, `app/schemas/episode_revision.py`.
- `app/api/v1/episodes.py` (append): `GET/POST.../scenes/{scene_id}/dialogues`,
  `DELETE.../dialogues/{dialogue_id}`, `GET/POST.../episodes/{episode_id}/revisions`
  (snapshot title/summary/scenes, nomor revisi auto-increment).

### 2.11 Dead code + hygiene (F-26, F-31, F-27)
- Hapus `app/api/v1/audit_log.py` (router mati, tidak di-mount, tidak diimpor siapa pun).
- Sapu `datetime.utcnow()` → `datetime.now(timezone.utc)` di 25 file backend:
  `default=`/`onupdate=`/`default_factory=` jadi lambda; import `timezone` ditambahkan.
  Sisa 0 kemunculan `utcnow` di source (hanya bytecode lama di `__pycache__`).
- Bonus bug yang ketemu saat menguji apply (bukan di daftar audit, tapi memblokir F-19):
  `Scene.characters_present`/`Shot.characters_in_shot` disimpan sebagai `str(list)`
  (repr Python) tapi skema respons menuntut `List[str]` → semua read scene/shot dengan
  karakter terisi gagal validasi 500. Perbaiki di `app/schemas/episode.py`: validator
  `_parse_list_field` (JSON → `ast.literal_eval` → fallback) di `SceneBase` +
  `ShotBase`; penyimpanan di `app/api/v1/episodes.py` diubah dari `str(...)` ke
  `json.dumps(...)`.

## 3. Frontend — yang diubah

- `src/middleware.ts` — pass-through (lihat §2.3).
- `src/lib/api.ts` — tambah `authApi.changePassword`, `storyEngineApi` dan
  `sceneEngineApi` (list/create/get/execute/apply/delete), `dialoguesApi.list`,
  `episodeRevisionsApi` (list/create); `exportApi.download` kini pakai
  `responseType: 'blob'`.
- `src/types/index.ts` — `Character` tambah `voice_pattern`, `physical_traits`, `skills`.
- `src/app/dashboard/settings/page.tsx` (F-24) — `handlePasswordSubmit` kini memanggil
  `authApi.changePassword` (dulu hanya `showMessage('success', 'Password change feature coming soon')`).
- `src/app/projects/[id]/page.tsx`:
  - Import: `useAuthStore` dari `@/store` (bukan `@/lib/auth-store`); tambah
    `exportApi, flowBridgeApi, storyEngineApi, sceneEngineApi`. `isAuthenticated()`
    (fungsi) → `isAuthenticated` (boolean) di 2 tempat.
  - Semua `api.put(` → `api.patch(` (backend hanya mendefinisikan PATCH untuk update;
    semua form edit sebelumnya 405).
  - Path Flow Bridge salah `/flow-bridge/${projectId}/...` → `flowBridgeApi.*`
    (router ter-mount di `/projects`: `/{project_id}/tasks`, `/{project_id}/assets`).
  - Path export salah `/export/${projectId}/export/...` → `exportApi.*` (F-16).
  - `handleExecuteFlowTask` (hanya `alert('Flow task execution not yet implemented in API')`)
    + tombol Execute dihapus (F-14); tambah catatan jujur di tab Flow Bridge: tugas
    hanya pelacakan manual, eksekusi di Google Flow, tidak ada otomasi browser
    (mock dimatikan).
  - Form karakter: `voice_pattern`, `physical_traits`, `skills` ditambah ke state
    awal + reset create + 2 reset tombol Add Character.
  - **UI Story/Scene Engine (F-13, O-P1-03)** — tab `series-bible`: tabel statis
    "Story Engine Tasks" (placeholder "No story engine tasks yet", tombol "New Task"
    yang keliru membuka modal Series Bible) diganti UI nyata: form create story
    (tipe `generate_outline/generate_episode/generate_character_arcs/generate_world_building`
    + total episode / nomor episode + textarea context) dan scene
    (tipe `breakdown_episode/generate_scenes/generate_shots/generate_dialogue/generate_action`
    + pilih episode/scene + context), tabel task dengan badge status (termasuk FAILED
    merah + `error_message`), tombol Execute/Retry, Apply (bila COMPLETED dan tipe
    mendukung), Delete, dan penampil output JSON. Tab `series-bible` kini juga
    memuat episode + task engine saat dibuka.
  - Perbaikan terkait yang ketemu saat build: interface lokal `Episode` memakai
    field `number` padahal backend mengirim `episode_number` — diubah ke
    `episode_number` (sort + tampilan + `episodeForm` ikut diperbaiki); tambah
    interface lokal `Scene`; tambah 3 field baru ke interface lokal `Character`
    (sebelumnya hanya `types/index.ts` yang diperbarui, build gagal).
- `src/lib/auth-store.ts` — **dihapus** (duplikat store P2-06: dua `useAuthStore`
  dengan persist key `auth-storage` yang sama; tidak ada lagi importir setelah
  unifikasi ke `@/store`).
- Direktori build basi `app/frontend/.next` dihapus (P1-13) lalu build bersih.

## 4. Hasil tes ulang (aktual, bukan kutipan)

### 4.1 pytest — 137/137
`./venv312/bin/python -m pytest tests/ -q -p no:cacheprovider` di
`opencode/app/backend`: **137 passed, 435 warnings in 15.15s**
(baseline sebelum perbaikan: 109 passed, 1876 warnings).
28 tes baru: `tests/test_settings.py` (baru: bootstrap superuser, GET/PATCH 403
non-superuser, PATCH `ai_providers` round-trip, PATCH mock → 400, PATCH OAuth,
change-password), `test_scene_engine.py` (dialogue/action dengan karakter,
`generate_scenes`, FAILED+retry deterministik via `key_env=DEFINITELY_MISSING_KEY_XYZ`,
apply breakdown/dialogue), `test_story_engine.py` (`generate_episode` + context,
FAILED+retry, apply outline), `test_characters.py` (round-trip field baru),
`test_export.py` (download 200 + attachment, CSV sungguhan, download unknown → 404),
`test_google_accounts.py` (automation login → 503 + session utuh, check-account → 503,
disconnect bersih, authorize URL ter-encode), `test_episodes.py`
(dialogue CRUD, revision snapshot nomor 1 lalu 2).

### 4.2 Build frontend — 14/14
`npm run build` (setelah `rm -rf .next`): `✓ Compiled successfully`,
`✓ Generating static pages (14/14)`, exit 0. Hanya warning lint pre-existing
(`useEffect` deps, `<img>` vs `<Image>`, alt-text).

### 4.3 Smoke live — 29/29 + middleware
Backend: `uvicorn app.main:app --host 127.0.0.1 --port 8102`,
`DATABASE_URL=sqlite+aiosqlite:////tmp/smoke8102.db` (DB segar; DB repo
`app/backend/micro_drama.db` tidak tersentuh — mtime tetap 2026-11-17 02:29:26 UTC,
368640 byte). Frontend: `next start -p 3102` dari build produksi.

| # | Cek | Hasil |
|---|---|---|
| 1 | register user pertama | 201, `is_superuser=true` |
| 2 | register user kedua | `is_superuser=false`; GET `/settings` → 403 |
| 3 | GET `/settings` (superuser) | 200, provider nvidia ter-seed |
| 4 | PATCH `/settings` `ai_providers` nvidia | 200 (dulu 500) |
| 5 | Buat project | 201 |
| 6 | Buat karakter + `voice_pattern`/`physical_traits`/`skills` | 201, nilai kembali utuh |
| 7 | Buat akun Google (session marker) | 201 |
| 8 | Automation login | **503** |
| 9 | `encrypted_session_data` sesudah login | ciphertext identik; dekripsi = marker |
| 10 | Status akun Google | tetap `connected` |
| 11 | Story `generate_outline` execute tanpa key | **502** |
| 12 | Task sesudah gagal | `failed` + `error_message` + `completed_at` |
| 13 | Retry task gagal | **502** (bukan 400) |
| 14 | Scene `generate_dialogue` (mock) execute | 200 |
| 15 | Apply dialogue | 200, 2 baris Dialogue terbaca via GET |
| 16 | `generate_episode` ep. 3 + context (mock) execute | 200 |
| 17 | Apply episode | 200, `created_episodes: [{episode_number: 3}]` |
| 18 | Change password | 200 |
| 19 | Login password baru / lama | 200 / **401** |
| 20 | Export characters create / download | 201 / 200 + `Content-Disposition: attachment` |
| 21 | Authorize URL OAuth | 200, tanpa spasi mentah, `redirect_uri` ter-encode |
| 22 | Middleware: `GET /dashboard`, `/projects/abc`, `/login` | **200** semua, tanpa redirect |

Cek 14–17 memakai provider **mock yang di-seed langsung ke DB** (UPDATE kolom
`ai_providers` di `app_settings`) karena allowlist PATCH menolak mock di luar
`TESTING=true` — scaffolding tes, bukan perubahan produk.

**NOT VERIFIED — LLM nyata:** `NVIDIA_API_KEY` tidak ada di environment maupun
di `.env` kaki ini (grep: 0 baris), jadi generasi LLM nyata tidak bisa diuji.
Jalur engine yang butuh LLM diuji lewat mock; kegagalan tanpa key diuji lewat
transisi FAILED (cek 11–13). Login automation nyata juga NOT VERIFIED (tidak ada
akun Flow nyata). Server smoke dimatikan setelah tes (port 8102 dan 3102
terkonfirmasi 000 sesudah kill).

## 5. Yang TIDAK diperbaiki + alasan

### 5.1 Security — DITUNDA per perintah Di (catat sebagai dilewati)
- **F-01 rotasi secret — BLOKIR, lihat §6.** Dilarang eksplisit: butuh perintah Di.
- F-05 SHA-256 tanpa salt (selalu bcrypt); F-06 kunci acak per proses; F-11 token
  localStorage + logout tanpa revokasi; F-12 rate limiting + security headers;
  F-10 state OAuth tak ditandatangani (butuh SECRET_KEY yang justru bocor);
  F-21 `verify=False` di `ai_client.py:139` (menghapus buta bisa memutus LLM via
  proxy VM — butuh perbaikan CA/proxy, tidak bisa diuji tanpa key); F-22 derivasi
  kunci enkripsi (pad/truncate `'0'`); F-28 CORS permisif; F-29 registrasi terbuka
  tanpa gate (butuh keputusan Di — bootstrap superuser di §2.5 justru mengandalkan
  registrasi pertama); F-30 rename `password_encrypted` → `refresh_token_encrypted`
  (migrasi, P2); S-P1-01/02/04/05/06 terkait kunci/env/token.

### 5.2 Bukan security, tetap tidak dikerjakan
- **P1 #10 Claude (Story/Scene Engine ke background task + polling):** tidak dikerjakan
  — eksekusi sinkron dipertahankan; perbaikan F-08 (FAILED + retry) adalah
  penangkal operasionalnya.
- **P1-09 UUID invalid → 400/404 tidak berlaku untuk OpenCode:** tidak ada `UUID(`
  parsing di kode app (hanya `uuid.uuid4()`); ID path bertipe str, ID tak valid →
  404 via query.
- **Impor sesi Google manual dipertahankan sesuai desain Phase 2** (bukan bug):
  auditor OpenCode menyatakan by-design sesuai perintah Phase 2; item Claude P1 #13
  yang meminta menghapusnya DITOLAK dengan alasan ini.
- P2 lain di luar P0/P1: O-P2-01 sudah tercakup via allowlist F-20; O-P2-04 sebagian
  (hapus `audit_log.py` mati + dedupe `get_current_user`; REDIS_URL/Celery tak
  terpakai dibiarkan); O-P2-05 sudah (sapu utcnow); O-P2-06 sebagian (unifikasi
  auth store; CORS dibiarkan = security); O-P2-07 gate registrasi (butuh keputusan
  Di); O-P2-08 rename kolom (lihat F-30).

## 6. BLOKIR — secret live ter-commit, wajib rotate (JANGAN rotate tanpa perintah Di)

`.env` kaki OpenCode **identik byte-demi-byte dengan `.env.example`**
(md5 `3fb82f90fb55915d88297b5ca848de5a`, commit `3b35f09`).
Secret live ter-commit di repo; wajib rotate sebelum kaki ini dipakai produksi.
Tidak ada kredensial yang diubah dalam pekerjaan ini.

## 7. Temuan tambahan (di luar daftar audit, tidak diperbaiki)

- **Tidak ada JSX modal sama sekali di `app/projects/[id]/page.tsx`** (2325 baris):
  tombol Add Character/Location/Episode/dll memanggil `setShow*Modal(true)` tapi
  tidak ada render modal — state + handler ada, markup tidak ada. Gap pre-existing
  di luar cakupan audit; field karakter baru sudah masuk state agar API tetap bisa
  dipakai. (Form create Story/Scene Engine baru dibuat inline, bukan modal.)
- `fetchAuditLogs` mengirim param `project_id` yang tidak dikenal endpoint
  `/audit-logs` (FastAPI mengabaikannya; tab audit menampilkan semua log user).
  Dibiarkan apa adanya.
- `.env` kaki ini mengandung `NEXT_PUBLIC_API_URL` (variabel frontend) sehingga
  menjalankan backend dari direktori `opencode/` gagal validasi Settings
  (`extra="forbid"`). Smoke dijalankan dari `app/backend/` dengan nilai `.env`
  dimuat terfilter (tanpa `NEXT_PUBLIC_API_URL`, `DATABASE_URL` di-override ke DB
  segar). Perlu diputuskan: pisah `.env` backend/frontend, atau longgarkan
  `extra="forbid"`.

## 8. File yang diubah (pekerjaan ini saja)

Backend (`opencode/app/backend/`):
`app/models/{character,audit_log}.py`, `app/schemas/{character,user,episode}.py`,
`app/schemas/{dialogue,episode_revision}.py` (baru),
`app/api/v1/{auth,settings,story_engine,scene_engine,flow_bridge_automation,google_accounts,export,episodes,characters}.py`,
`app/api/v1/audit_log.py` (hapus), `app/services/{ai_client,flow_bridge_automation}.py`,
`alembic.ini`, `alembic/versions/003_add_character_fields.py` (baru),
`alembic/versions/002_settings_and_google_oauth.py`,
sapu `utcnow` di 25 file backend,
`tests/{test_settings.py (baru),test_scene_engine.py,test_story_engine.py,test_characters.py,test_export.py,test_google_accounts.py,test_episodes.py}`.

Frontend (`opencode/app/frontend/src/`):
`middleware.ts`, `lib/api.ts`, `lib/auth-store.ts` (hapus),
`types/index.ts`, `app/dashboard/settings/page.tsx`,
`app/projects/[id]/page.tsx`.
