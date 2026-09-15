# Frontend Changes — Dark / Light Theme Toggle

Adds a theme toggle button that switches the UI between the existing dark theme and a
new light theme. Frontend only — no backend files were touched.

## Summary

- Icon-based toggle button pinned to the **top-right** of the viewport.
- Sun icon in dark mode, moon icon in light mode, cross-fading with a rotate + scale animation.
- Full light-theme palette driven entirely by CSS variables.
- Choice persists in `localStorage`; falls back to the OS `prefers-color-scheme` setting.
- Accessible: native `<button>` with `role="switch"`, live `aria-checked`/`aria-label`, visible focus ring, keyboard-operable.

## Files changed

### `frontend/index.html`

- **Inline head script** — reads `localStorage.theme` (or the OS preference) and sets
  `data-theme` on `<html>` *before first paint*, so the page never flashes the wrong theme.
  Wrapped in `try/catch` so a blocked `localStorage` (private mode) falls back to dark.
- **Toggle button** — new `#themeToggle` as the first child of `.container`, containing two
  inline SVGs (`.theme-icon-sun`, `.theme-icon-moon`) inside a `.theme-toggle-icons` wrapper.
  Markup carries `type="button"`, `role="switch"`, `aria-checked`, `aria-label` and `title`;
  the icon wrapper is `aria-hidden="true"` so screen readers only announce the label.
- Bumped the cache-busting query strings on `style.css` and `script.js` from `v=9` to `v=10`.

### `frontend/style.css`

- **Theme variables** — the old `:root` block is now `:root, [data-theme="dark"]` (dark stays
  the default), and a parallel `[data-theme="light"]` block defines the light palette:
  white background, `#f1f5f9` surfaces, dark slate text, lighter borders, and a softer shadow.
- **New variables** so previously hardcoded colors can follow the theme:
  - `--code-bg` — inline `code` / `pre` background (was a hardcoded `rgba(0,0,0,0.2)`, which
    was invisible on a white background).
  - `--error-text` / `--success-text` — light theme uses darker red/green so status text stays
    readable on white; dark theme keeps its original colors via the `var(..., fallback)` default.
- **Transition block** — a shared `transition: background-color / color / border-color 0.3s ease`
  on the themed surfaces (body, sidebar, chat areas, message bubbles, input container, stat items,
  code blocks) so switching themes animates instead of snapping. `#chatInput` and `.suggested-item`
  are deliberately excluded because their existing `transition: all` rules already cover it.
- **`.theme-toggle` styles** — 44px circular button, `position: fixed` at `top/right: 1.25rem`,
  `z-index: 100`, using `--surface` / `--border-color` / `--shadow` so it matches the existing
  aesthetic (same variables as the sidebar cards). Hover lifts it 1px and tints it with the accent
  color, `:active` scales it to 0.94, and `:focus-visible` shows the same 3px `--focus-ring` used
  by the send button and input.
- **Icon animation** — both SVGs are absolutely stacked in a 20×20 wrapper. The inactive icon is
  `opacity: 0` and rotated ±90° at `scale(0.5)`; the active one is `opacity: 1`, `rotate(0) scale(1)`.
  Transitioned over 0.3s/0.4s `cubic-bezier(0.4, 0, 0.2, 1)`, which reads as the sun spinning out
  while the moon spins in.
- **Responsive** — inside the existing `max-width: 768px` query the button shrinks to 38px with
  tighter offsets and 18px icons.
- **Reduced motion** — a new `@media (prefers-reduced-motion: reduce)` block disables the toggle's
  transitions and hover/active transforms.
- **Drive-by fix** — `.message-content blockquote` referenced the undefined variable `--primary`;
  corrected to `--primary-color` so the blockquote border actually renders.

### `frontend/script.js`

- Added `themeToggle` to the cached DOM element list and `initTheme()` to `DOMContentLoaded`.
- `setupEventListeners()` binds `click` on the toggle. Because it is a real `<button>`, Enter and
  Space activate it and it sits in the natural tab order — no extra key handling needed.
- New functions:
  - `initTheme()` — syncs the button's ARIA state with the theme the inline script already applied,
    then subscribes to `prefers-color-scheme` changes so the UI follows the OS *until* the user
    makes an explicit choice.
  - `toggleTheme()` — flips between `light` and `dark` and persists the result.
  - `applyTheme(theme, persist)` — sets `data-theme` on `<html>`, optionally writes to
    `localStorage`, and updates `aria-checked`, `aria-label` and `title`
    ("Switch to light theme" ↔ "Switch to dark theme").
  - `getStoredTheme()` — `localStorage` read guarded by `try/catch`.

## Behavior

| Situation | Result |
| --- | --- |
| First visit, OS set to light | Light theme |
| First visit, OS set to dark / unknown | Dark theme (unchanged from before) |
| User clicks the toggle | Theme flips, animates, and is saved |
| Reload after clicking | Saved theme applied before first paint, no flash |
| OS theme changes later | Followed only if the user never clicked the toggle |
| `localStorage` unavailable | Toggle still works for the session; defaults to dark |

## Manual test checklist

1. Load `http://localhost:8000` — toggle sits in the top-right, showing a sun on the dark theme.
2. Click it — colors cross-fade to light, icon animates to a moon.
3. Reload — light theme is restored with no dark flash.
4. Tab to the button — focus ring is visible; Enter and Space both toggle.
5. Send a query — user bubble, assistant bubble, sources list, and any code blocks are all
   readable in both themes.
6. Narrow the window below 768px — the button shrinks and stays clear of the chat content.
