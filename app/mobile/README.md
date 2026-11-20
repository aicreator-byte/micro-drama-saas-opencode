# MicroDrama — Mobile App (Expo / React Native)

Scaffold React Native (Expo) untuk Micro Drama SaaS: login, daftar proyek,
detail proyek (bible/karakter/episode ringkas), dan Auto-Generate dengan
progres per langkah.

## Prasyarat

- Node.js 18+ dan npm
- Backend Micro Drama SaaS jalan (default `http://localhost:8002/api/v1`)
- Expo Go di HP (atau emulator Android / simulator iOS) untuk menjalankan app

## Cara jalan

```bash
cd app/mobile
npm install
npx expo start
```

Lalu scan QR dengan Expo Go, atau tekan `a` (Android) / `i` (iOS).

## Konfigurasi API

Base URL API diambil dari `EXPO_PUBLIC_API_URL`. Default:
`http://localhost:8002/api/v1`.

Cara set (contoh — backend di laptop, HP di Wi-Fi yang sama):

```bash
EXPO_PUBLIC_API_URL=http://192.168.1.10:8002/api/v1 npx expo start
```

atau buat file `.env` di `app/mobile/`:

```
EXPO_PUBLIC_API_URL=http://192.168.1.10:8002/api/v1
```

Catatan: `localhost` dari HP menunjuk ke HP itu sendiri, bukan laptop —
pakai IP LAN laptop saat testing dari HP fisik.

## Struktur

```
App.tsx                    Navigasi sederhana berbasis state (tanpa lib navigasi)
src/api/client.ts          fetch client: base URL, token, endpoint auth/proyek/auto-generate
src/screens/LoginScreen.tsx        POST /auth/login, token disimpan
src/screens/ProjectsScreen.tsx     GET /projects, list + pull-to-refresh + status
src/screens/ProjectDetailScreen.tsx GET /projects/{id} + bible/characters/episodes
src/screens/AutoGenerateScreen.tsx form → POST /projects/{id}/auto-generate → progres
```

## Token

Token JWT disimpan via `expo-secure-store` bila tersedia; bila tidak
(mis. web), fallback ke `@react-native-async-storage/async-storage`.

## Auto-Generate: polling, bukan SSE

Progres auto-generate memakai polling `GET /projects/{id}/auto-generate/{job_id}`
tiap 2 detik sampai job terminal — sama seperti fallback yang dipakai
frontend web saat SSE gagal. SSE (`EventSource`) sengaja tidak dipakai di
React Native: tidak bisa kirim header auth, polyfill tidak stabil, dan
background throttling membuat stream putus.

## Typecheck

```bash
npm run typecheck   # tsc --noEmit
```
