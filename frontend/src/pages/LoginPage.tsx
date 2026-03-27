import { FormEvent, useState } from 'react';

interface LoginPageProps {
  onLogin: (password: string) => Promise<void>;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      await onLogin(password);
    } catch {
      setError('密码错误，请重试。');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <h1>监控回放工作台</h1>
        <p className="hero-copy">请输入访问密码后继续。</p>
      </section>

      <section className="panel compact-panel">
        <form onSubmit={handleSubmit}>
          <label className="field-group compact-field-group">
            <span className="field-label">访问密码</span>
            <input
              className="field-input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error != null ? <p className="error-text">{error}</p> : null}
          <button className="primary-button" disabled={submitting} type="submit">
            {submitting ? '登录中...' : '登录'}
          </button>
        </form>
      </section>
    </main>
  );
}
