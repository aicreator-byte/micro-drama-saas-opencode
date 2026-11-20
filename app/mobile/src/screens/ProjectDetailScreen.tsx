import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Button,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import {
  getProject,
  getSeriesBible,
  listCharacters,
  listEpisodes,
  type Character,
  type Episode,
  type Project,
  type SeriesBible,
} from '../api/client';

export default function ProjectDetailScreen({
  project: initial,
  onBack,
  onAutoGenerate,
}: {
  project: Project;
  onBack: () => void;
  onAutoGenerate: (project: Project) => void;
}) {
  const [project, setProject] = useState<Project>(initial);
  const [bible, setBible] = useState<SeriesBible | null>(null);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      const [p, chars, eps] = await Promise.all([
        getProject(initial.id),
        listCharacters(initial.id),
        listEpisodes(initial.id),
      ]);
      setProject(p);
      setCharacters(Array.isArray(chars) ? chars : []);
      setEpisodes(Array.isArray(eps) ? eps : []);
      try {
        setBible(await getSeriesBible(initial.id));
      } catch {
        setBible(null); // no bible yet — not an error
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load project');
    } finally {
      setLoading(false);
    }
  }, [initial.id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Button title="← Back to projects" onPress={onBack} />
      <Text style={styles.title}>{project.title}</Text>
      <Text style={styles.meta}>
        {(project.genre || 'No genre')} · {project.status.replace('_', ' ')} ·{' '}
        {project.total_episodes} episodes
      </Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Button title="Auto-Generate with AI" onPress={() => onAutoGenerate(project)} />

      <Text style={styles.section}>Series Bible</Text>
      {bible ? (
        <Text style={styles.body}>{bible.premise || bible.main_plot || 'Bible exists.'}</Text>
      ) : (
        <Text style={styles.muted}>No Series Bible yet.</Text>
      )}

      <Text style={styles.section}>Characters ({characters.length})</Text>
      {characters.length === 0 ? (
        <Text style={styles.muted}>No characters yet.</Text>
      ) : (
        characters.slice(0, 10).map((c) => (
          <Text key={c.id} style={styles.body}>
            • {c.name}
            {c.role ? ` — ${c.role}` : ''}
          </Text>
        ))
      )}

      <Text style={styles.section}>Episodes ({episodes.length})</Text>
      {episodes.length === 0 ? (
        <Text style={styles.muted}>No episodes yet.</Text>
      ) : (
        episodes.slice(0, 10).map((e) => (
          <Text key={e.id} style={styles.body}>
            • Ep {e.episode_number}: {e.title || '(untitled)'}
            {e.status ? ` (${e.status})` : ''}
          </Text>
        ))
      )}
      <View style={{ height: 32 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  body: { color: '#334155', marginBottom: 4 },
  center: { alignItems: 'center', flex: 1, justifyContent: 'center' },
  container: { backgroundColor: '#fff', flex: 1, padding: 16 },
  error: { color: '#dc2626', marginVertical: 12 },
  meta: { color: '#64748b', marginBottom: 16 },
  muted: { color: '#94a3b8' },
  section: { fontSize: 17, fontWeight: '600', marginBottom: 8, marginTop: 20 },
  title: { fontSize: 22, fontWeight: 'bold', marginTop: 12 },
});
