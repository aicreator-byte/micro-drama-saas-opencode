import { useState } from 'react';
import {
  ActivityIndicator,
  Button,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { login } from '../api/client';

export default function LoginScreen({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async () => {
    if (!email.trim() || !password) return;
    setBusy(true);
    setError('');
    try {
      await login(email.trim(), password);
      onLoggedIn();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Login failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>MicroDrama</Text>
      <Text style={styles.subtitle}>Sign in to your account</Text>
      <TextInput
        style={styles.input}
        placeholder="Email"
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {busy ? (
        <ActivityIndicator />
      ) : (
        <Button title="Login" onPress={handleLogin} disabled={!email.trim() || !password} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 24, backgroundColor: '#fff' },
  error: { color: '#dc2626', marginBottom: 12 },
  input: {
    borderColor: '#cbd5e1',
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 12,
    padding: 12,
  },
  subtitle: { color: '#64748b', marginBottom: 24 },
  title: { fontSize: 28, fontWeight: 'bold', marginBottom: 4 },
});
