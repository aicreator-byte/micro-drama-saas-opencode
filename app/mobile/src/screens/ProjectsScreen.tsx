import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { listProjects, type Project } from '../api/client';

export default function ProjectsScreen({
  onSelect,
  onLogout,
}: {
  onSelect: (project: Project) => void;
  onLogout: () => void;
}) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      const res = await listProjects();
      setProjects(res.projects ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load projects');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
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
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Projects</Text>
        <TouchableOpacity onPress={onLogout}>
          <Text style={styles.logout}>Logout</Text>
        </TouchableOpacity>
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <FlatList
        data={projects}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <Text style={styles.empty}>No projects yet. Create one from the web app.</Text>
        }
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.card} onPress={() => onSelect(item)}>
            <Text style={styles.cardTitle}>{item.title}</Text>
            <Text style={styles.cardMeta}>
              {(item.genre || 'No genre')} · {item.total_episodes} episodes
            </Text>
            <Text style={styles.status}>{item.status.replace('_', ' ')}</Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#f8fafc',
    borderColor: '#e2e8f0',
    borderRadius: 10,
    borderWidth: 1,
    marginBottom: 12,
    padding: 14,
  },
  cardMeta: { color: '#64748b', marginTop: 4 },
  cardTitle: { fontSize: 16, fontWeight: '600' },
  center: { alignItems: 'center', flex: 1, justifyContent: 'center' },
  container: { backgroundColor: '#fff', flex: 1, padding: 16 },
  empty: { color: '#64748b', marginTop: 32, textAlign: 'center' },
  error: { color: '#dc2626', marginBottom: 12 },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  logout: { color: '#2563eb' },
  status: { color: '#2563eb', fontSize: 12, marginTop: 6, textTransform: 'capitalize' },
  title: { fontSize: 22, fontWeight: 'bold' },
});
