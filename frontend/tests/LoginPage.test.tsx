import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { LoginPage } from '../src/pages/LoginPage';

describe('LoginPage', () => {
  it('shows login error when password is invalid', async () => {
    const failingLogin = vi.fn(async () => {
      throw new Error('invalid password');
    });

    render(<LoginPage onLogin={failingLogin} />);

    fireEvent.change(screen.getByLabelText('访问密码'), {
      target: { value: 'wrong-pass' },
    });
    fireEvent.click(screen.getByText('登录'));

    expect(await screen.findByText('密码错误，请重试。')).toBeInTheDocument();
  });
});
