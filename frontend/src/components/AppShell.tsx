import { type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, PackageSearch, Truck, MessagesSquare, FlaskConical, Sun, Moon } from 'lucide-react'
import { useTheme } from '@/lib/theme'
import { cn } from '@/lib/utils'

/** The signature element: a small animated waveform that resolves into a
 * steady signal — literal mark for "sensing demand out of noise." */
function SignalMark() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <motion.path
        d="M1 20 L6 20 L9 8 L12 24 L15 4 L18 20 L21 14 L27 14"
        stroke="var(--color-signal)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 1.1, ease: 'easeInOut' }}
      />
    </svg>
  )
}

const NAV_ITEMS = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/', active: true },
  { label: 'Inventory', icon: PackageSearch, path: '/inventory', active: true },
  { label: 'Procurement', icon: Truck, path: '/procurement', active: false },
  { label: 'Copilot', icon: MessagesSquare, path: '/copilot', active: false },
  { label: 'Simulations', icon: FlaskConical, path: '/simulations', active: false },
]

export function AppShell({ children }: { children: ReactNode }) {
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()

  return (
    <div className="min-h-screen flex" style={{ backgroundColor: 'var(--color-canvas)' }}>
      <aside
        className="w-60 shrink-0 hidden md:flex flex-col justify-between py-6 px-4"
        style={{ borderRight: '1px solid var(--color-border)' }}
      >
        <div>
          <div className="flex items-center gap-2.5 px-2 mb-8">
            <SignalMark />
            <div>
              <p className="font-display font-semibold text-[15px] leading-none" style={{ color: 'var(--color-ink)' }}>
                DemandSense
              </p>
              <p className="text-[11px] tracking-wide uppercase mt-1" style={{ color: 'var(--color-ink-faint)' }}>
                AI
              </p>
            </div>
          </div>

          <nav className="flex flex-col gap-1">
            {NAV_ITEMS.map(({ label, icon: Icon, path, active }) => {
              const isCurrent = location.pathname === path
              const content = (
                <>
                  <Icon size={16} style={isCurrent ? { color: 'var(--color-signal)' } : undefined} />
                  {label}
                  {!active && (
                    <span
                      className="ml-auto text-[10px] px-1.5 py-0.5 rounded-full font-mono-data"
                      style={{ backgroundColor: 'var(--color-border)', color: 'var(--color-ink-faint)' }}
                    >
                      soon
                    </span>
                  )}
                </>
              )
              const className = cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left',
                isCurrent ? 'bg-[var(--color-surface-raised)]' : active ? 'hover:bg-[var(--color-surface-raised)]' : 'opacity-40 cursor-not-allowed'
              )
              const style = { color: isCurrent ? 'var(--color-ink)' : active ? 'var(--color-ink-muted)' : 'var(--color-ink-faint)' }

              if (!active) {
                return (
                  <button key={label} disabled className={className} style={style} title="Coming in a later phase">
                    {content}
                  </button>
                )
              }
              return (
                <Link key={label} to={path} className={className} style={style}>
                  {content}
                </Link>
              )
            })}
          </nav>
        </div>

        <div className="px-2">
          <p className="text-[11px] leading-relaxed" style={{ color: 'var(--color-ink-faint)' }}>
            Phase 1 of 11
            <br />
            Ingestion &amp; Forecasting
          </p>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header
          className="h-16 shrink-0 flex items-center justify-between px-6"
          style={{ borderBottom: '1px solid var(--color-border)' }}
        >
          <div>
            <h1 className="font-display font-semibold text-[15px]" style={{ color: 'var(--color-ink)' }}>
              {location.pathname === '/inventory' ? 'Inventory Intelligence' : 'Demand Intelligence'}
            </h1>
            <p className="text-xs" style={{ color: 'var(--color-ink-muted)' }}>
              {location.pathname === '/inventory'
                ? 'ABC analysis, movement, dead stock, and stockout risk across your catalog'
                : 'Upload demand history, compare models, view forecasts'}
            </p>
          </div>

          <button
            onClick={toggleTheme}
            className="w-9 h-9 rounded-lg flex items-center justify-center transition-colors"
            style={{ border: '1px solid var(--color-border)', color: 'var(--color-ink-muted)' }}
            aria-label="Toggle color theme"
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </header>

        <main className="flex-1 overflow-y-auto px-6 py-8">
          <div className="max-w-6xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  )
}
