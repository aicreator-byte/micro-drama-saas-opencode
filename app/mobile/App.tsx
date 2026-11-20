// MicroDrama mobile — state-based navigation (no navigation library).
// Screens: login -> projects -> project detail -> auto-generate.
import { useEffect, useState } from 'react';
import { ActivityIndicator, SafeAreaView, StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { clearToken, getToken, type Project } from './src/api/client';
import LoginScreen from './src/screens/LoginScreen';
import ProjectsScreen from './src/screens/ProjectsScreen';
import ProjectDetailScreen from './src/screens/ProjectDetailScreen';
import AutoGenerateScreen from './src/screens/AutoGenerateScreen';

type Route =
  | { name: 'login' }
  | { name: 'projects' }
  | { name: 'detail'; project: Project }
  | { name: 'autogen'; project: Project };

export default function App() {
  const [route, setRoute] = useState<Route | null>(null);

  useEffect(() => {
    (async () => {
      const token = await getToken();
      setRoute(token ? { name: 'projects' } : { name: 'login' });
    })();
  }, []);

  const logout = async () => {
    await clearToken();
    setRoute({ name: 'login' });
  };

  if (!route) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="auto" />
      {route.name === 'login' && (
        <LoginScreen onLoggedIn={() => setRoute({ name: 'projects' })} />
      )}
      {route.name === 'projects' && (
        <ProjectsScreen
          onSelect={(project) => setRoute({ name: 'detail', project })}
          onLogout={logout}
        />
      )}
      {route.name === 'detail' && (
        <ProjectDetailScreen
          project={route.project}
          onBack={() => setRoute({ name: 'projects' })}
          onAutoGenerate={(project) => setRoute({ name: 'autogen', project })}
        />
      )}
      {route.name === 'autogen' && (
        <AutoGenerateScreen
          project={route.project}
          onBack={() => setRoute({ name: 'detail', project: route.project })}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: 'center', flex: 1, justifyContent: 'center' },
  container: { backgroundColor: '#fff', flex: 1 },
});
