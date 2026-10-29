import { DarkTheme, DefaultTheme, ThemeProvider } from 'expo-router';
import { Stack } from 'expo-router';
import { useColorScheme } from 'react-native';
import { LanguageProvider } from '../i18n/LanguageContext';

export default function RootLayout() {
  const colorScheme = useColorScheme();
  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <LanguageProvider>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="index" />
          <Stack.Screen name="language-selection" />
          <Stack.Screen name="login" />
          <Stack.Screen name="register" />
          <Stack.Screen name="forgot-password" />
          <Stack.Screen name="scan" />
          <Stack.Screen name="problem-description" />
          <Stack.Screen name="voice-record" />
          <Stack.Screen name="prescription" />
          <Stack.Screen name="analysis" />
          <Stack.Screen name="result" />
          <Stack.Screen name="spray-guidance" />
        </Stack>
      </LanguageProvider>
    </ThemeProvider>
  );
}
