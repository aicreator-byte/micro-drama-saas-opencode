'use client';

// Halaman kolaborasi real-time (perbaikan P2-6 ronde 2).
//
// Sebelumnya fitur kolaborasi hanya ada di backend (WebSocket + REST)
// tanpa halaman web — tidak bisa dipakai end-to-end. Halaman ini:
//   - menampilkan siapa saja yang sedang di room (presence via WS,
//     fallback polling REST tiap 5 dtk),
//   - mengedit 6 field bible yang masuk whitelist (patch via WS,
//     fallback REST POST .../collab/patch).
//
// BATAS YANG DIKETAHUI (ditampilkan di halaman, bukan disembunyikan):
//   - Room HANYA pemilik proyek (owner-only): user lain belum bisa masuk
//     karena belum ada model sharing/anggota proyek.
//   - Registry in-memory single-worker: presence + broadcast tidak lintas
//     proses/worker; deployment multi-worker butuh Redis (belum dibuat).
//   - Satu proses melayani banyak tab/perangkat dari user yang sama.
import { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Loader2, Save, Users, AlertCircle } from 'lucide-react';
import { API_BASE_URL, api, collabApi, projectsApi } from '@/lib/api';

const PATCHABLE_FIELDS: { field: string; label: string }[] = [
  { field: 'premise', label: 'Premise' },
  { field: 'main_plot', label: 'Main Plot' },
  { field: 'tone_and_visual_style', label: 'Tone & Visual Style' },
  { field: 'world_settings', label: 'World Settings' },
  { field: 'ending_direction', label: 'Ending Direction' },
  { field: 'episode_structure', label: 'Episode Structure' },
];

interface PresenceUser {
  user_id: string;
  full_name: string | null;
  section: string | null;
  cursor: string | null;
  last_seen: number;
}

export default function CollabPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const [projectTitle, setProjectTitle] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [users, setUsers] = useState<PresenceUser[]>([]);
  const [mode, setMode] = useState<'ws' | 'rest'>('rest');
  const [bible, setBible] = useState<Record<string, string>>({});
  const [field, setField] = useState(PATCHABLE_FIELDS[0].field);
  const [value, setValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState('');
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let stopped = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;

    const loadPresence = async () => {
      try {
        const res = await collabApi.presence(projectId);
        if (!stopped) setUsers((res.data.users || []) as PresenceUser[]);
      } catch {
        // presence gagal (mis. proyek bukan milik user) — biarkan error
        // halaman yang bicara; polling berhenti di cleanup.
      }
    };

    const loadProject = async () => {
      try {
        const res = await projectsApi.get(projectId);
        if (stopped) return;
        setProjectTitle((res.data.title as string) || projectId);
        const bibleRes = await api.get(`/projects/${projectId}/series-bible`);
        const b = (bibleRes.data || {}) as Record<string, unknown>;
        const next: Record<string, string> = {};
        for (const { field: f } of PATCHABLE_FIELDS) {
          next[f] = typeof b[f] === 'string' ? (b[f] as string) : '';
        }
        setBible(next);
        setValue(next[field] || '');
        setIsLoading(false);
      } catch (err) {
        if (!stopped) {
          setError('Project not found or not accessible.');
          setIsLoading(false);
        }
      }
    };

    void loadProject();
    void loadPresence();
    pollTimer = setInterval(() => { void loadPresence(); }, 5000);

    // WebSocket room (JWT via ?token= — handshake WS tidak bisa kirim
    // header; sama seperti SSE lama, dicatat di batas halaman ini).
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    if (token) {
      try {
        const wsBase = API_BASE_URL.replace(/^http/, 'ws');
        const ws = new WebSocket(
          `${wsBase}/ws/projects/${projectId}/collab?token=${encodeURIComponent(token)}`,
        );
        wsRef.current = ws;
        ws.onopen = () => setMode('ws');
        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data as string) as {
              type?: string;
              users?: PresenceUser[];
              field?: string;
              value?: string;
            };
            if (msg.type === 'presence' && Array.isArray(msg.users)) setUsers(msg.users);
            if (msg.type === 'patch' && msg.field && typeof msg.value === 'string') {
              setBible((prev) => ({ ...prev, [msg.field as string]: msg.value as string }));
            }
          } catch {
            // abaikan pesan yang tidak bisa diparse
          }
        };
        ws.onerror = () => setMode('rest');
        ws.onclose = () => setMode('rest');
      } catch {
        setMode('rest');
      }
    }

    return () => {
      stopped = true;
      if (pollTimer) clearInterval(pollTimer);
      wsRef.current?.close();
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const handleFieldChange = (nextField: string) => {
    setField(nextField);
    setValue(bible[nextField] || '');
  };

  const handleSave = async () => {
    setSaving(true);
    setSavedAt('');
    try {
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'patch', field, value }));
        setBible((prev) => ({ ...prev, [field]: value }));
      } else {
        await collabApi.patch(projectId, field, value);
        setBible((prev) => ({ ...prev, [field]: value }));
      }
      setSavedAt(new Date().toLocaleTimeString());
    } catch {
      setError('Failed to save patch.');
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
      <div className="max-w-3xl mx-auto">
        <Link href={`/projects/${projectId}`} className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
          <ArrowLeft className="w-4 h-4" /> Back to project
        </Link>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white mt-4">
          Collaboration — {projectTitle}
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Mode: {mode === 'ws' ? 'live (WebSocket)' : 'REST fallback (polling 5 dtk)'} ·{' '}
          {users.length} user di room
        </p>

        <div className="card mt-4 flex gap-2 items-start bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800">
          <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <p className="text-sm text-amber-800 dark:text-amber-200">
            Batas saat ini: room hanya untuk pemilik proyek (user lain belum bisa
            masuk — belum ada model sharing/anggota proyek), dan presence +
            broadcast hanya jalan dalam satu proses server (deployment
            multi-worker butuh Redis). Banyak tab/perangkat dari akun yang sama
            bisa bergabung.
          </p>
        </div>

        {error && (
          <div className="card mt-4 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
            <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
          </div>
        )}

        <div className="card mt-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Users className="w-5 h-5" /> Users in room
          </h2>
          {users.length === 0 ? (
            <p className="text-sm text-slate-500 mt-2">No one else here yet.</p>
          ) : (
            <ul className="mt-2 space-y-1">
              {users.map((u) => (
                <li key={u.user_id} className="text-sm text-slate-700 dark:text-slate-300">
                  {u.full_name || u.user_id}
                  {u.section ? ` — ${u.section}` : ''}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card mt-4">
          <h2 className="text-lg font-semibold">Edit Series Bible</h2>
          <label className="block text-sm font-medium mt-3 mb-1">Field</label>
          <select
            value={field}
            onChange={(e) => handleFieldChange(e.target.value)}
            className="w-full border rounded px-3 py-2 bg-white dark:bg-slate-800"
          >
            {PATCHABLE_FIELDS.map((f) => (
              <option key={f.field} value={f.field}>{f.label}</option>
            ))}
          </select>
          <label className="block text-sm font-medium mt-3 mb-1">Value</label>
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            rows={6}
            className="w-full border rounded px-3 py-2 bg-white dark:bg-slate-800"
          />
          <div className="flex items-center gap-3 mt-3">
            <button
              onClick={() => { void handleSave(); }}
              disabled={saving}
              className="inline-flex items-center gap-2 px-4 py-2 rounded bg-primary-600 text-white disabled:opacity-50"
            >
              <Save className="w-4 h-4" /> {saving ? 'Saving…' : 'Save patch'}
            </button>
            {savedAt && <span className="text-sm text-green-600">Saved at {savedAt}</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
