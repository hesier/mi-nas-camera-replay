import { LoginPage } from './pages/LoginPage';
import { useAuth } from './hooks/useAuth';
import { ReplayPage } from './pages/ReplayPage';

export default function App() {
  const auth = useAuth();

  if (!auth.ready) {
    return (
      <main className="app-shell">
        <p className="panel-note">登录状态检查中...</p>
      </main>
    );
  }

  if (!auth.authenticated) {
    return <LoginPage onLogin={auth.loginWithPassword} />;
  }

  return <ReplayPage onLogout={auth.logoutCurrent} />;
}
