import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Button,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import {
  createAutoGenerate,
  getAutoGenerateJob,
  type AutoGenerateJob,
  type Project,
} from '../api/client';

const STEP_LABELS: Record<string, string> = {
  series_bible: 'Series Bible',
  characters: 'Characters',
  locations: 'Locations',
  episodes: 'Episodes',
  prompts: 'Prompts',
};

// NOTE: progress uses 2s GET polling, not SSE. EventSource is unreliable in
// React Native (no header auth, spotty polyfills, background throttling),
// so the app polls GET /projects/{id}/auto-generate/{job_id} until the job
// is terminal — the same fallback the web frontend uses when SSE fails.
export default function AutoGenerateScreen({
  project,
  onBack,
}: {
  project: Project;
  onBack: () => void;
}) {
  const [title, setTitle] = useState(project.title);
  const [genre, setGenre] = useState(project.genre || '');
  const [totalEpisodes, setTotalEpisodes] = useState(String(project.total_episodes || 30));
  const [job, setJob] = useState<AutoGenerateJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  useEffect(() => stopPolling, []);

  const start = async () => {
    if (!title.trim()) return;
    setBusy(true);
    setError('');
    setJob(null);
    try {
      const created = await createAutoGenerate(project.id, {
        title: title.trim(),
        genre: genre.trim() || undefined,
        total_episodes: Math.min(60, Math.max(1, parseInt(totalEpisodes, 10) || 30)),
      });
      setJob(created);
      if (created.status === 'completed' || created.status === 'failed') return;
      timerRef.current = setInterval(async () => {
        try {
          const updated = await getAutoGenerateJob(project.id, created.id);
          setJob(updated);
          if (updated.status === 'completed' || updated.status === 'failed') stopPolling();
        } catch (e) {
          console.error('Failed to poll auto-generate job:', e);
        }
      }, 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start auto-generate.');
    } finally {
      setBusy(false);
    }
  };

  const stepIcon = (status: string) =>
    status === 'completed' ? '✓' : status === 'failed' ? '✗' : status === 'running' ? '…' : '○';

  return (
    <ScrollView style={styles.container}>
      <Button title="← Back to project" onPress={onBack} />
      <Text style={styles.title}>Auto-Generate</Text>
      <Text style={styles.subtitle}>
        AI fills the whole project: bible, characters, locations, episodes and prompts.
      </Text>

      {!job && (
        <View>
          <TextInput
            style={styles.input}
            placeholder="Title *"
            value={title}
            onChangeText={setTitle}
          />
          <TextInput
            style={styles.input}
            placeholder="Genre (optional)"
            value={genre}
            onChangeText={setGenre}
          />
          <TextInput
            style={styles.input}
            placeholder="Total episodes"
            keyboardType="number-pad"
            value={totalEpisodes}
            onChangeText={setTotalEpisodes}
          />
          {error ? <Text style={styles.error}>{error}</Text> : null}
          {busy ? (
            <ActivityIndicator />
          ) : (
            <Button title="Start Auto-Generate" onPress={start} disabled={!title.trim()} />
          )}
        </View>
      )}

      {job && (
        <View>
          <Text style={styles.jobTitle}>
            {job.title} · {job.total_episodes} episodes
          </Text>
          <Text style={styles.status}>Status: {job.status}</Text>
          {job.error_message ? <Text style={styles.error}>{job.error_message}</Text> : null}
          {[...job.steps]
            .sort((a, b) => a.step_order - b.step_order)
            .map((step) => (
              <View key={step.id} style={styles.step}>
                <Text style={styles.stepText}>
                  {stepIcon(step.status)} {STEP_LABELS[step.step] || step.step} — {step.status}
                </Text>
                {step.status === 'failed' && step.error_message ? (
                  <Text style={styles.error}>{step.error_message}</Text>
                ) : null}
              </View>
            ))}
          {job.status === 'completed' && (
            <Text style={styles.done}>Done — open the project to see the results.</Text>
          )}
          <View style={{ marginTop: 16 }}>
            <Button
              title="Start a new job"
              onPress={() => {
                stopPolling();
                setJob(null);
              }}
            />
          </View>
        </View>
      )}
      <View style={{ height: 32 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: '#fff', flex: 1, padding: 16 },
  done: { color: '#16a34a', fontWeight: '600', marginTop: 16 },
  error: { color: '#dc2626', marginVertical: 8 },
  input: {
    borderColor: '#cbd5e1',
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 12,
    padding: 12,
  },
  jobTitle: { fontSize: 16, fontWeight: '600', marginTop: 12 },
  status: { color: '#64748b', marginVertical: 8, textTransform: 'capitalize' },
  step: { borderBottomColor: '#e2e8f0', borderBottomWidth: 1, paddingVertical: 10 },
  stepText: { fontSize: 15 },
  subtitle: { color: '#64748b', marginBottom: 16 },
  title: { fontSize: 22, fontWeight: 'bold', marginTop: 12 },
});
