import { useTheme } from '@/hooks/useTheme';
import { useAuth } from '@/hooks/useAuth';
import type { ThemeMode, ThemeAccent } from '@/providers/ThemeProvider';

const THEMES: { value: ThemeAccent; label: string; className: string }[] = [
  { value: 'amber', label: 'Amber', className: 'theme-swatch-amber' },
  { value: 'wine', label: 'Wine', className: 'theme-swatch-wine' },
  { value: 'ocean', label: 'Ocean', className: 'theme-swatch-ocean' },
  { value: 'forest', label: 'Forest', className: 'theme-swatch-forest' },
];

export function SettingsPage() {
  const { mode, accent, setMode, setAccent } = useTheme();
  const { user } = useAuth();

  return (
    <div className="content-wrapper">
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Customize your Taskyn experience</p>
        </div>
      </div>

      <div className="settings-layout">
        {/* Settings Navigation */}
        <nav className="settings-nav">
          <a href="#appearance" className="settings-nav-item active">
            <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3" /><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" /></svg>
            Appearance
          </a>
          <a href="#account" className="settings-nav-item">
            <svg viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
            Account
          </a>
          <span className="settings-nav-item disabled">
            <svg viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /></svg>
            Data & Storage
          </span>
          <span className="settings-nav-item disabled">
            <svg viewBox="0 0 24 24"><rect x="2" y="2" width="8" height="8" rx="2" /><rect x="14" y="2" width="8" height="8" rx="2" /><rect x="2" y="14" width="8" height="8" rx="2" /><rect x="14" y="14" width="8" height="8" rx="2" /></svg>
            Integrations
          </span>
        </nav>

        {/* Settings Content */}
        <div>
          {/* Appearance */}
          <section id="appearance" className="settings-section">
            <h2 className="settings-section-title">Appearance</h2>
            <p className="settings-section-desc">Customize how Taskyn looks on your device</p>

            <div className="settings-group">
              <div className="settings-item">
                <div className="settings-item-info">
                  <div className="settings-item-label">Mode</div>
                  <div className="settings-item-desc">Switch between dark and light mode</div>
                </div>
                <div className="settings-item-control">
                  <div className="mode-toggle">
                    <button
                      className={mode === 'dark' ? 'active' : ''}
                      onClick={() => setMode('dark' as ThemeMode)}
                    >
                      <svg viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" /></svg>
                      Dark
                    </button>
                    <button
                      className={mode === 'light' ? 'active' : ''}
                      onClick={() => setMode('light' as ThemeMode)}
                    >
                      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" /><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" /><line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" /><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" /></svg>
                      Light
                    </button>
                  </div>
                </div>
              </div>

              <div className="settings-item">
                <div className="settings-item-info">
                  <div className="settings-item-label">Accent Color</div>
                  <div className="settings-item-desc">Choose your preferred accent color</div>
                </div>
                <div className="settings-item-control">
                  <div className="theme-picker">
                    {THEMES.map((t) => (
                      <div
                        key={t.value}
                        className="theme-option"
                        onClick={() => setAccent(t.value)}
                      >
                        <div className={`theme-swatch ${t.className}${accent === t.value ? ' selected' : ''}`} />
                        <span className={`theme-label${accent === t.value ? ' selected' : ''}`}>{t.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Account */}
          <section id="account" className="settings-section">
            <h2 className="settings-section-title">Account</h2>
            <p className="settings-section-desc">Your account information</p>

            <div className="settings-group">
              <div className="settings-item">
                <div className="settings-item-info" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div className="account-avatar">
                    {user?.name?.charAt(0).toUpperCase() ?? '?'}
                  </div>
                  <div>
                    <div className="settings-item-label">{user?.name ?? 'Unknown'}</div>
                    <div className="settings-item-desc">{user?.email ?? ''}</div>
                  </div>
                </div>
              </div>
              <div className="settings-item">
                <div className="settings-item-info">
                  <div className="settings-item-label">Full Name</div>
                  <div className="settings-item-desc">{user?.name ?? 'Not set'}</div>
                </div>
              </div>
              <div className="settings-item">
                <div className="settings-item-info">
                  <div className="settings-item-label">Email Address</div>
                  <div className="settings-item-desc">{user?.email ?? 'Not set'}</div>
                </div>
              </div>
              <div className="settings-item">
                <div className="settings-item-info">
                  <div className="settings-item-label">Instance</div>
                  <div className="settings-item-desc">Local</div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
