# ════════════════════════════════════════════════════════════
# AEGIS AML — MASTER FRONTEND BUILD PROMPT
# ════════════════════════════════════════════════════════════
#
# SETUP:
# 1. Open VS Code → Ctrl+` (integrated terminal)
# 2. cd into this folder (the one with all .md spec files)
# 3. Run: claude
# 4. Switch model: /model → select claude-fable
# 5. Paste this entire file as your first message
# ════════════════════════════════════════════════════════════

---

## STEP 0 — READ EVERYTHING FIRST

Before writing a single line of code, read ALL of these files in this folder:
- `PRD.md` — Full product requirements, every page, every component
- `MVP.md` — Scope decisions and feature boundaries
- `DatabaseSchema.md` — Data models (for context only)
- `APISpec.md` — Every API endpoint with exact request/response shapes
- `BuildOrder.md` — Full build instructions by phase

They are your source of truth. This prompt adds frontend detail on top of them.

---

## ⛔ CRITICAL INSTRUCTION — READ THIS BEFORE ANYTHING ELSE ⛔

**YOUR ONLY JOB IS THE FRONTEND. NOTHING ELSE.**

Do NOT create any backend files.
Do NOT create any Python files.
Do NOT create any database migrations.
Do NOT create any Docker files.
Do NOT touch anything outside the `frontend/` directory.

When the frontend is 100% complete — every page, every component, every animation, every mock data state working — you will say:

> "✅ FRONTEND COMPLETE. All pages built, all components working, mock data connected, animations implemented. Ready for backend integration in the next session."

Then STOP. Do not continue into backend work under any circumstances.

---

## WHAT YOU ARE BUILDING

**Aegis AML** — a B2B SaaS compliance platform for Indian fintechs and brokers.
Compliance officers use it to review AI-generated Suspicious Activity Reports (SARs)
and approve them for submission to FIU-India.

The frontend has two portals:
1. **Client Portal** — for fintech/broker compliance teams
2. **Admin Dashboard** — for Aegis operators (us)

---

## TECH STACK (LOCKED — ZERO DEVIATION)

```
React 18 + TypeScript + Vite
Tailwind CSS v3 (utility classes + custom CSS variables)
React Router v6 (nested routes)
Zustand — global auth state only
@tanstack/react-query v5 — all server state, with mock data fallbacks
Recharts — data visualizations
Lucide React — icons (no other icon library)
Axios — HTTP client
```

**Install command:**
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install react-router-dom @tanstack/react-query zustand axios recharts lucide-react
npm install -D @types/node
```

No Framer Motion. No shadcn. No MUI. No Radix. Build every component from scratch.

---

## THE VISION

The three design benchmarks are **Stripe Dashboard**, **Apple product pages**, and the
**Financial Times**. Not all three at once — one quality stolen from each:

- **Stripe**: Data density done right. You can scan a table and understand everything.
  Numbers are formatted. Status is always visible. Nothing is hidden.
- **Apple**: Every pixel is intentional. Motion communicates. Transitions earn their place.
  The product feels inevitable — like it couldn't have been designed any other way.
- **Financial Times**: Trust. Authoritative. The design says "we know what we're doing."
  Data has context. Important things carry visual weight.

The result: a dark, precision-built compliance tool that looks like a ₹200Cr company made it.

**Hard rules — what this is NOT:**
- Not a gradient-blob background app
- Not a glassmorphism playground
- Not an over-padded "modern SaaS" with too much whitespace
- Not an AI-generated UI with random margins and font sizes
- Not a dashboard with decorative charts that tell you nothing
- Nothing blinks, spins, or bounces without a reason

**Hard rules — what this IS:**
- Every spacing value is from the 8px grid
- Every animation has a purpose and a duration
- Every hover state exists
- Every empty state is designed
- Every loading state uses skeletons
- Indian number formatting everywhere (₹9,90,000 not ₹990,000)

---

## DESIGN SYSTEM

### index.css — paste this exactly

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  /* ── Backgrounds ── */
  --bg-base:         #09090b;
  --bg-surface:      #111113;
  --bg-elevated:     #1c1c1f;
  --bg-overlay:      #28282c;

  /* ── Borders ── */
  --border:          #2e2e33;
  --border-subtle:   #1e1e22;
  --border-strong:   #52525b;

  /* ── Accent — use sparingly ── */
  --accent:          #6366f1;
  --accent-hover:    #5558e8;
  --accent-subtle:   rgba(99,102,241,0.12);
  --accent-glow:     rgba(99,102,241,0.25);
  --accent-text:     #a5b4fc;

  /* ── Semantic ── */
  --success:         #22c55e;
  --success-subtle:  rgba(34,197,94,0.10);
  --success-glow:    rgba(34,197,94,0.25);
  --warning:         #f59e0b;
  --warning-subtle:  rgba(245,158,11,0.10);
  --danger:          #ef4444;
  --danger-subtle:   rgba(239,68,68,0.10);
  --info:            #38bdf8;
  --info-subtle:     rgba(56,189,248,0.10);

  /* ── Text ── */
  --text-1:          #f4f4f5;
  --text-2:          #a1a1aa;
  --text-3:          #71717a;
  --text-4:          #52525b;

  /* ── Type ── */
  --font-sans:       'Inter', -apple-system, system-ui, sans-serif;
  --font-mono:       'JetBrains Mono', 'Fira Code', monospace;

  /* ── Radius ── */
  --r-sm:   4px;
  --r-md:   8px;
  --r-lg:   12px;
  --r-xl:   16px;
  --r-full: 9999px;

  /* ── Shadows ── */
  --shadow-sm:    0 1px 2px rgba(0,0,0,0.6);
  --shadow-md:    0 4px 6px -1px rgba(0,0,0,0.6);
  --shadow-lg:    0 10px 24px -4px rgba(0,0,0,0.7);
  --shadow-focus: 0 0 0 3px rgba(99,102,241,0.35);

  /* ── Transitions ── */
  --t-fast:  100ms ease-out;
  --t-base:  150ms ease-out;
  --t-slow:  250ms cubic-bezier(0.4, 0, 0.2, 1);
  --t-spring:300ms cubic-bezier(0.34, 1.56, 0.64, 1);
}

html { height: 100%; }
body {
  height: 100%;
  background: var(--bg-base);
  color: var(--text-1);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ── Keyframes — copy all of these, they are used throughout ── */

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

@keyframes slideInFromTop {
  from { opacity: 0; transform: translateY(-8px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes slideInFromRight {
  from { opacity: 0; transform: translateX(20px); }
  to   { opacity: 1; transform: translateX(0); }
}

@keyframes slideOutToLeft {
  from { opacity: 1; transform: translateX(0); }
  to   { opacity: 0; transform: translateX(-20px); }
}

@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.95); }
  to   { opacity: 1; transform: scale(1); }
}

@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position:  200% 0; }
}

@keyframes processingPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.4; transform: scale(0.75); }
}

@keyframes borderFlash {
  0%    { border-left-color: var(--accent); background: var(--accent-subtle); }
  100%  { border-left-color: var(--border-subtle); background: transparent; }
}

@keyframes drawCheckmark {
  from { stroke-dashoffset: 120; }
  to   { stroke-dashoffset: 0; }
}

@keyframes particleFly {
  0%   { transform: translate(0,0) scale(1);   opacity: 1; }
  100% { transform: translate(var(--dx), var(--dy)) scale(0); opacity: 0; }
}

@keyframes successGlow {
  0%, 100% { box-shadow: 0 0 30px rgba(34,197,94,0.15); }
  50%       { box-shadow: 0 0 60px rgba(34,197,94,0.35); }
}

@keyframes riskArc {
  from { stroke-dashoffset: 251; }
  to   { stroke-dashoffset: var(--arc-target); }
}

@keyframes countUp {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes toastSlideIn {
  from { transform: translateX(110%); opacity: 0; }
  to   { transform: translateX(0);    opacity: 1; }
}

@keyframes toastSlideOut {
  from { transform: translateX(0);    opacity: 1; max-height: 80px; }
  to   { transform: translateX(110%); opacity: 0; max-height: 0; }
}

@keyframes progressShrink {
  from { width: 100%; }
  to   { width: 0%; }
}

@keyframes dotGrid {
  0%, 100% { opacity: 0.4; }
  50%       { opacity: 0.7; }
}

@keyframes subtleFloat {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-3px); }
}

/* ── Scroll bar ── */
::-webkit-scrollbar       { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--border-strong); }

/* ── Selection ── */
::selection { background: var(--accent-subtle); color: var(--text-1); }
```

---

### Spacing System (8px grid — use ONLY these values)

| Token | px | Use |
|-------|----|-----|
| space-1 | 4 | icon inner padding, tiny gaps |
| space-2 | 8 | between label and field |
| space-3 | 12 | compact card padding |
| space-4 | 16 | standard inner padding |
| space-5 | 20 | section gaps |
| space-6 | 24 | card padding |
| space-8 | 32 | between sections |
| space-10 | 40 | page top padding |
| space-12 | 48 | large layout gaps |
| space-16 | 64 | major block separation |

### Typography Scale

```
Display: 32px / weight 700 / tracking -0.025em / --text-1
H1:      24px / weight 600 / tracking -0.02em  / --text-1
H2:      20px / weight 600 / tracking -0.015em / --text-1
H3:      16px / weight 600 / tracking -0.01em  / --text-1
H4:      14px / weight 600 / tracking -0.005em / --text-1
Body:    14px / weight 400 / tracking normal   / --text-2
Small:   13px / weight 400 / tracking normal   / --text-3
Label:   11px / weight 500 / tracking 0.06em   / --text-3 (UPPERCASE)
Mono:    13px / JetBrains Mono                 / --text-1
```

### Component Primitives

**Button:**
```
Primary:   bg var(--accent), color white, hover bg var(--accent-hover)
           height 36px, padding 0 16px, font 14px/500, radius var(--r-md)
           transition: background var(--t-fast), transform var(--t-fast)
           active: transform scale(0.98)
           loading: show 16px spinner (border-2 border-white/30 border-t-white animate-spin), cursor-not-allowed

Secondary: bg var(--bg-elevated), border 1px var(--border), color var(--text-1)
           hover: bg var(--bg-overlay), border-color var(--border-strong)

Ghost:     transparent, border transparent, color var(--text-2)
           hover: bg var(--bg-elevated), color var(--text-1)

Danger:    bg var(--danger-subtle), border 1px rgba(239,68,68,0.3), color var(--danger)
           hover: bg rgba(239,68,68,0.18), border-color var(--danger)

Size SM:   height 28px, padding 0 10px, font 13px
Size LG:   height 42px, padding 0 20px, font 15px
```

**Input:**
```
height 36px, bg var(--bg-elevated), border 1px var(--border)
radius var(--r-md), padding 0 12px, font 14px var(--font-sans), color var(--text-1)
placeholder color var(--text-4)
transition: border-color var(--t-fast), box-shadow var(--t-fast)
focus: border-color var(--accent), box-shadow var(--shadow-focus), outline none
error: border-color var(--danger), box-shadow 0 0 0 3px rgba(239,68,68,0.2)
```

**Card:**
```
bg var(--bg-surface), border 1px var(--border-subtle)
radius var(--r-lg), padding 24px
interactive card hover: border-color var(--border), transition var(--t-base)
active/selected card: border-color var(--accent), box-shadow 0 0 0 1px var(--accent)
```

**Table row:**
```
height 48px, border-bottom 1px var(--border-subtle)
hover: bg var(--bg-elevated), transition background var(--t-fast)
header: height 40px, font 11px/500 uppercase tracking-wider, color var(--text-3)
numbers/amounts: font-mono, text-align right
```

---

## COMPLETE PAGE SPECIFICATIONS

---

### `/login` — Login

**Layout:** 100vw × 100vh. Background `var(--bg-base)`.

**Background:** CSS dot grid with a very slow breathing animation:
```css
.login-bg {
  background-image: radial-gradient(circle, #2a2a2e 1px, transparent 1px);
  background-size: 28px 28px;
  animation: dotGrid 4s ease-in-out infinite;
}
/* Also add a slow-moving radial glow at centre-top */
.login-bg::before {
  content: '';
  position: fixed;
  top: -200px; left: 50%;
  transform: translateX(-50%);
  width: 600px; height: 600px;
  background: radial-gradient(ellipse, rgba(99,102,241,0.08) 0%, transparent 70%);
  animation: subtleFloat 8s ease-in-out infinite;
  pointer-events: none;
}
```

**Card:** 400px wide. `var(--bg-surface)`, border `var(--border)`, `var(--r-xl)`, `var(--shadow-lg)`.
Padding 40px. Centered in viewport (flexbox).
Entrance animation: `scaleIn 250ms ease-out` on mount.

**Inside card:**
- Aegis shield SVG (40×40px). Design: a hexagonal shield outline, stroke `var(--accent)`, strokeWidth 2.
  The shield has a small "A" letterform in the centre in the accent color.
  Subtle `subtleFloat 6s ease-in-out infinite` animation on the icon.
- "AEGIS AML" — 26px/700. Use gradient text:
  ```css
  background: linear-gradient(135deg, #6366f1 0%, #818cf8 50%, #38bdf8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  ```
- "Compliance Intelligence Platform" — 13px `var(--text-3)`. marginTop 4px.
- Divider: 1px `var(--border-subtle)`, margin 24px 0.
- Email input (full width) + password input (full width, with EyeIcon toggle for visibility).
- "Sign in →" button (primary, full width, height 40px). Loading state replaces text with spinner.
- Error message (if wrong credentials): 12px `var(--danger)`, slides down from input with `fadeInUp 150ms`. Has AlertCircleIcon inline.
- Divider + "New entity? Request access →" link (13px `var(--text-3)`, hover color `var(--accent-text)`).

---

### `/signup` — Registration Wizard

Same background as login. Card: 480px wide, padding 40px.

**Step progress bar** (top of card):
```
[①]━━━━━━━[②]━━━━━━━[③]
```
Each circle: 28px. Active: filled `var(--accent)`. Completed: filled `var(--accent)` with checkmark. Pending: outlined `var(--border)`.
Line between: fills with `var(--accent)` as you progress (width transition, 400ms).

**Step 1 — Company Details:**
Fields: Company Name, Company Type (custom styled select), CIN (optional, with "?" tooltip: "Corporate Identity Number — issued by MCA"), Website.
Button: "Continue →" (right-aligned, primary).

**Step 2 — Administrator:**
Full Name, Work Email, Phone, Designation.
"← Back" (ghost, left) + "Continue →" (primary, right).

**Step 3 — Review & Submit:**
Summary in a 2-col grid: each entry is `label` + `value`. Light border separates each row.
Checkbox (styled) + legal text.
"Submit Application" (primary, full width).

**Step transitions:** entering step slides from right (`slideInFromRight 250ms`). Leaving step slides to left (`slideOutToLeft 200ms`). Both happen simultaneously — CSS class swap.

**Success state** (replaces step 3 content, no new page):
Large checkmark circle (48px, green bg), "Application Submitted!", description, "You'll hear back within 1–2 business days."
The transition: step 3 fades out (`fadeIn` reverse), success fades in. 300ms.

---

### `/dashboard` — Main Dashboard

Page entrance: each section fades in with `fadeInUp`, staggered 80ms per block.

**Greeting:** "Good [morning/afternoon/evening], [firstName]" — computed from `new Date().getHours()`.
Subtitle: "AML Pipeline Status" in `var(--text-3)`.
Right side: "Submit Test Alert" button (indigo, ZapIcon, sm size).

**4 Stat Cards** (CSS grid, `repeat(4, 1fr)`, gap 16px. Collapses to 2×2 on tablet, 1×4 on wide):

Each card: `var(--bg-surface)`, border `var(--border-subtle)`, `var(--r-lg)`, 24px padding.
Hover: `border-color var(--border)`, transition `var(--t-base)`. Very subtle, not dramatic.
On hover, a very faint indigo glow from the bottom of the card:
```css
.stat-card:hover {
  box-shadow: 0 4px 20px -4px rgba(99,102,241,0.15);
}
```

Inside each card:
- Row 1: Icon (in a 32px circle with subtle bg) + Delta badge (right-aligned: "+12% vs last month" in green, or red if negative).
- Row 2: Value — large number (28px/700). On page mount: animate from 0 to value using a count-up (1200ms ease-out). Apply `countUp` animation to trigger repaint.
- Row 3: Label in 11px uppercase `var(--text-3)`.

Cards:
1. Alerts This Month — `InboxIcon` — bg `rgba(99,102,241,0.12)` icon circle
2. Pending Review — `ClockIcon` — bg `rgba(245,158,11,0.12)`. If value > 0: value text is `var(--warning)` + badge pulses (subtle `processingPulse 2s infinite`).
3. Approved SARs — `CheckCircle2Icon` — bg `rgba(34,197,94,0.12)`
4. Avg. Review Time — `TimerIcon` — bg `rgba(56,189,248,0.12)` — value shows "8.3 min"

**Activity Chart** (Recharts `LineChart`):
Card wrapper: full width, 240px height.
Title row: "Alerts Ingested — Last 14 Days" (H3) + date range in `var(--text-3)`.
Chart:
- Single `Line`, stroke `var(--accent)`, strokeWidth 2, dot `false`.
- On hover: custom dot appears (6px circle, `var(--accent)`, white border).
- Custom tooltip: `var(--bg-overlay)` bg, `var(--border)` border, `var(--r-md)`, 12px font.
- `XAxis` + `YAxis`: tick color `var(--text-4)`, 12px, no outer border.
- `CartesianGrid`: stroke `var(--border-subtle)`, strokeDasharray "3 3".
- `isAnimationActive={true}` — the line draws itself on mount. Duration 1000ms.

**Recent Activity Table** (last 5 alerts):
Columns: Transaction ID | Amount | Risk Score | Rules Triggered | Status | Time
"View all in Queue →" footer link.

"Submit Test Alert" modal: appears centered, 380px. Dropdown for scenario + "Inject Alert" button.
On success: close modal + toast "Test alert injected. Check the queue in ~8 seconds." + queue badge count increments.

---

### `/status` — Verification Status Page (shown for PENDING / REJECTED tenants)

**This replaces the entire app for unverified tenants.**

Centered, vertically centered on screen.

**PENDING_VERIFICATION:**
- Animated amber ring (40px circle, border 3px amber, one arc rotates: `@keyframes spin 1.5s linear infinite`). This is NOT a spinner — it's a partial ring showing "in progress."
- "Application Under Review" — H1.
- Description in `var(--text-3)`.
- Timeline component (horizontal, 3 nodes):
  - "Submitted" — filled green circle + checkmark
  - "Under Review" — amber pulsing circle
  - "Activated" — empty grey circle
  Connecting lines: filled/unfilled accordingly.
- "Typically 1–2 business days." — small note.
- "support@aegis-aml.com" — email link.

**REJECTED:**
- Red X circle (40px, animated: scale 0→1 on mount, `--t-spring`).
- "Application Not Approved" — H1.
- Rejection reason in a `var(--danger-subtle)` card.
- "Contact us to appeal" button.

---

### `/queue` — Review Queue

**Page header:** "Review Queue" — H1. Pending count badge (amber pill, e.g. "3 pending") right of title.

**Filter bar** (sticky, 56px height, `var(--bg-base)` bg with `border-bottom var(--border-subtle)`):

Left group: Status chip filters — "All" / "Pending Review" / "Approved" / "Rejected"
Each chip: 28px height, 12px font. Active: `var(--accent)` bg, white text. Inactive: ghost.
Switching chips has a 150ms bg transition.

Right group: Search input (200px) + from-date + to-date inputs.
Search: has SearchIcon inside left side. Typing filters table instantly (client-side, React Query + filter). Escape key clears.

**Table:**
Full width. `border-collapse: separate`, `border-spacing: 0`.
Header: 11px uppercase, `var(--text-3)`, `letter-spacing: 0.06em`.

Columns:
| Column | Style |
|--------|-------|
| Alert ID | 13px mono `var(--text-3)`, first 8 chars + "..." |
| Amount | 14px/500 `var(--text-1)`, right-aligned, Indian format: ₹X,XX,XXX |
| Type | 13px `var(--text-2)` |
| Risk Score | Colored dot (6px) + score number. <50 green, 50–74 amber, 75+ red |
| Rules Triggered | Max 2 pills (11px, `var(--accent-subtle)` bg, `var(--accent-text)` text) + "+N" if more |
| Received | Relative time ("4 min ago") in `var(--text-3)` |
| Status | `<AlertStatusBadge>` |
| → | "Review" button (ghost-sm) — only visible on row hover |

Row hover: `bg var(--bg-elevated)`, `cursor: pointer`. Clicking anywhere on row = navigate to workspace.

**New alert animation:**
When a new alert arrives (polling, React Query `refetchInterval: 5000`):
The new row enters at the top with: `slideInFromTop 300ms ease-out`.
For 2 seconds, the row has `animation: borderFlash 2s ease-out forwards`.
After 2 seconds: transitions to normal styling.

**Empty state:**
```
[SVG: shield outline with checkmark inside, 64px, var(--text-4)]
"All Clear"  ← H2
"No pending alerts. Submit a test alert to try the pipeline."  ← var(--text-3)
[Submit Test Alert button]
```

---

### `/queue/:alertId` — SAR WORKSPACE

**This is the heart of the product. Every design decision here matters.**

Full viewport height (100vh). No outer scroll. No topbar. Only a minimal 48px header bar.

**Header bar** (48px, `var(--bg-surface)`, border-bottom `var(--border-subtle)`):
Left: `←` back button (ghost, ChevronLeftIcon) + breadcrumb "Queue / TXN-2026-061099182" (13px mono).
Right: `<AlertStatusBadge>` + time elapsed since alert ("Received 4 min ago").

**3-Panel Grid:**
```css
.workspace {
  display: grid;
  grid-template-columns: var(--p1, 1fr) 6px var(--p2, 1fr) 6px var(--p3, 1.4fr);
  height: calc(100vh - 48px);
  overflow: hidden;
}
```
JS: drag handles update CSS custom properties `--p1`, `--p2`, `--p3`.
Min panel width: 280px (enforced in JS).

**Drag handles:** 6px wide dividers.
Default: `var(--border-subtle)` bg.
Hover: `var(--accent)` bg, transition `var(--t-fast)`. `cursor: col-resize`.
Active (dragging): `var(--accent)` bg, stays colored during drag.

**Panel entrance:** on page mount, panels stagger in: P1 at 0ms, P2 at 80ms, P3 at 160ms.
Each uses `fadeInUp 300ms ease-out`.

---

#### PANEL 1 — Transaction Intelligence

`var(--bg-surface)`, `overflow-y: auto`, padding 24px.

**Transaction block:**
Amount: 28px/700 `var(--text-1)`. Below: direction chip (DEBIT = `var(--danger-subtle)` + red text, CREDIT = `var(--success-subtle)` + green text) + type text in `var(--text-3)`.
Transaction ID: 12px mono `var(--text-3)` + `<CopyButton>` inline.

**Risk Gauge** (centered, 96px diameter):
```
SVG circle (r=40, cx=48, cy=48):
  - Background ring: stroke var(--border), strokeWidth 7, fill none
  - Score arc: stroke [color by score], strokeWidth 7, fill none
    strokeLinecap="round"
    strokeDasharray="251"  (circumference = 2π×40)
    strokeDashoffset: calculated = 251 - (score/100 × 251)
    transform="rotate(-90 48 48)"
    animation: riskArc 800ms cubic-bezier(0.4,0,0.2,1) forwards
    (use CSS var --arc-target set inline)
  - Centre text: score (20px/700, colored by score level)
  - "Risk Score" label below circle (10px uppercase var(--text-3))
```
Score color: <50 `var(--success)`, 50–74 `var(--warning)`, 75+ `var(--danger)`.

**Divider + "Subject" label** (11px uppercase `var(--text-3)`):

Each field row: label (11px uppercase `var(--text-3)`, 80px min-width) + value (14px `var(--text-1)`).
For PII/masked fields: value in `var(--font-mono)` 13px + `LockIcon` (10px, `var(--text-4)`) before the value.
Tooltip on LockIcon: "PII masked for analysis security. Restored on approval."
```
Customer Ref:  USR_a1b2c3d4  🔒
Account Ref:   ACC_e5f6a7b8  🔒
IP Address:    IP_a3b4c5d6   🔒
Device:        DEV_e7f8a9b0  🔒
```

**Divider + "Counterparty":**
```
Account:       ACC_c9d0e1f2  🔒
Institution:   ICICI Bank    (no mask — institution name is not PII)
```

**Raw Payload accordion:**
Header: "View Raw JSON" + ChevronDownIcon. On click: rotates chevron 180°, expands smoothly (`max-height` CSS transition, 300ms).
Inside: `<CodeBlock>` component. JSON syntax highlighted:
- Keys: `var(--accent-text)` 
- String values: `var(--success)`
- Number values: `var(--warning)` 
- Booleans/null: `var(--info)`
- Background: `var(--bg-base)`, border-radius `var(--r-md)`, padding 16px, font-mono 12px, overflow-x auto.

---

#### PANEL 2 — Compliance Analysis

`var(--bg-base)` (slightly different from Panel 1, creates visual separation).
`overflow-y: auto`, padding 24px.

**Header row:** "AML Analysis" (H3) + Overall Risk badge (right-aligned, large: 26px height, 12px/600).
HIGH = `var(--danger-subtle)` bg + `var(--danger)` text + AlertTriangleIcon 12px.
MEDIUM = `var(--warning-subtle)` bg + `var(--warning)` text.
LOW = `var(--success-subtle)` bg + `var(--success)` text.

**Triggered rules** (stagger entrance: each card at 60ms interval, `fadeInUp 250ms`):
Each triggered rule is a card:
```css
.rule-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-left: 3px solid [color];  /* HIGH=danger, MED=warning, LOW=success */
  border-radius: var(--r-md);
  padding: 16px;
  margin-bottom: 8px;
}
```
Inside the card:
- Row 1: rule name (14px/600 `var(--text-1)`) + confidence pill (right-aligned, 22px height):
  HIGH = red pill, MEDIUM = amber pill, LOW = green pill.
- Row 2: evidence explanation (13px italic `var(--text-3)`, marginTop 6px).
- Row 3: field badge (shows which field triggered it): `var(--bg-elevated)`, 11px mono, `var(--r-sm)`, padding 2px 6px.

**Clean Checks accordion:**
Header: "Clean Checks (6)" (13px `var(--text-3)`, ChevronDownIcon). Collapsed by default.
Expanded: each non-triggered rule as a simple row: CheckIcon (10px green) + rule name (13px `var(--text-3)`).

---

#### PANEL 3 — SAR Draft

`var(--bg-surface)`. `display: flex; flex-direction: column;` — editor fills remaining space.

**Header** (flex, space-between, padding 16px 24px, border-bottom `var(--border-subtle)`):
"SAR Draft" (H3) + model badge ("Groq · llama-3.3-70b", `var(--bg-elevated)`, border, `var(--r-full)`, 11px mono, 22px height).

**Draft editor area** (`flex: 1`, `overflow-y: auto`):
A `contenteditable="true"` div:
```css
.sar-editor {
  min-height: 100%;
  padding: 24px;
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.85;
  color: var(--text-1);
  outline: none;
  border: 1px solid transparent;
  border-radius: var(--r-md);
  transition: border-color var(--t-base), box-shadow var(--t-base);
  white-space: pre-wrap;
}
.sar-editor:focus {
  border-color: var(--accent);
  box-shadow: var(--shadow-focus);
}
```

On first load: apply a very subtle typewriter-ish entrance. Use CSS:
```css
.sar-editor { animation: fadeIn 400ms ease-out; }
```

SAR section headers (lines matching `^[0-9]+\. [A-Z]`):
Parse on paste/load and wrap in `<span class="sar-section-header">`:
```css
.sar-section-header {
  display: block;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-3);
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 4px;
  margin: 20px 0 8px 0;
}
```

Below editor: 2-col row (12px `var(--text-4)`): "1,847 characters" | "Last edited by you, 2 min ago" (right-aligned).

**Bottom action bar** (sticky, height 64px, `border-top var(--border-subtle)`, `padding 0 24px`, `display flex`, `align-items center`, `justify-content space-between`):

Left: generation meta — "Generated in 2.3s · Groq llama-3.3-70b" (12px `var(--text-4)`, SparklesIcon 12px inline).

Right: 3 buttons, 8px gap:
- "Preview" — secondary-sm, `EyeIcon`
- "Reject" — danger-ghost-sm, `XCircleIcon`
- "Approve & Send ↗" — primary, `SendIcon`, 14px/500

---

#### Approve & Send — Full Animation Sequence

**Step 1: Confirmation Modal**
Opens with `scaleIn 200ms`. Standard modal: 400px.
"Confirm SAR Approval" title.
Summary card: amount, triggered rules badges, officer name.
Amber callout: "⚠ This will re-hydrate real PII and deliver the SAR via webhook."
"Cancel" (secondary) + "Confirm Approval" (primary green).

**Step 2: Processing State** (after clicking Confirm)
Modal content cross-fades to loading state.
Aegis shield icon (32px, animated `subtleFloat`).
Below: sequential steps appear one by one, each after 700ms:
```
● Re-hydrating PII tokens...          (appears at 0ms)
  ✓ Re-hydrating PII tokens           (check appears at 700ms)
● Generating SAR PDF...               (appears at 700ms)
  ✓ Generating SAR PDF                (check appears at 1400ms)
● Delivering via webhook...           (appears at 1400ms)
  ✓ Delivered — HMAC Verified ✓       (appears at 2100ms)
```
Each step uses `fadeInUp 200ms`. The check icon fades in, the bullet fades out simultaneously.

**Step 3: Success State** (appears at ~2500ms)
Modal content cross-fades to success.

The exact sequence:
- `t=0ms`:  White/dark bg, center empty.
- `t=100ms`: Green ambient radial glow radiates from centre. `successGlow 2s ease-in-out infinite`.
- `t=200ms`: SVG checkmark circle draws itself.
  ```svg
  <circle cx="32" cy="32" r="28" stroke="var(--success)" stroke-width="2.5" fill="var(--success-subtle)"/>
  <polyline points="20,33 28,41 44,23" stroke="var(--success)" stroke-width="3"
    stroke-dasharray="120" stroke-dashoffset="120"
    style="animation: drawCheckmark 500ms 200ms ease-out forwards"/>
  ```
- `t=400ms`: 8 particles burst outward simultaneously.
  Each particle: 5×5px circle, `var(--success)`, positioned at circle centre.
  Each has a different `--dx` and `--dy` (distribute evenly: 0°, 45°, 90°, 135°, 180°, 225°, 270°, 315°).
  `transform: translate(0,0)` → `translate(var(--dx), var(--dy))` + `scale(0)`.
  `animation: particleFly 600ms cubic-bezier(0.4,0,0.2,1) forwards`.
  Radii: 40px for the 4 cardinal, 35px for the diagonals.
- `t=700ms`: "SAR Approved & Delivered" (20px/600) fades in from below (`fadeInUp 250ms`).
- `t=900ms`: Delivery timestamp + "HMAC Verified ✓" badge (green) fades in.
- `t=1200ms`: "Back to Queue" button fades in.
- `t=1200ms onward`: slim countdown progress bar at bottom of modal (4000ms duration `progressShrink`).
  At 0: auto-navigate to `/queue`.

**After modal closes:** The queue row for this alert updates to APPROVED status in real time (React Query invalidation).

---

#### Reject Alert Flow

Small modal (380px): textarea (minHeight 80px) for reason.
"Reject Alert" (danger) + "Cancel".
On success: toast "Alert rejected and cleared." + navigate to `/queue` after 1.5s.

---

#### Preview Rehydrated SAR Modal

Full-screen modal (max-width 720px). `backdrop-filter: blur(6px)`.

Red banner (48px): `var(--danger-subtle)` bg, border-bottom `var(--danger)/30`.
"⚠ Confidential — Contains Real PII. For officer review only. Not stored by Aegis."

Document area: `background #f9f9f9`, color `#1a1a1a`, border-radius `var(--r-lg)`.
Padding: 48px horizontally, 40px vertically.
Font: 14px Georgia serif (makes it feel like an actual legal document).
Section headers: 11px uppercase, letter-spacing 0.08em, `#555`, border-bottom 1px `#ddd`.

Subtle watermark text behind document: "PREVIEW — NOT FOR DISTRIBUTION" rotated 30°, 10% opacity, red.

"Close Preview" — X button top right of modal.

---

### `/usage` — Usage & Analytics

**4 stat cards** (same design as dashboard).

**Two charts**, side by side (50/50 grid, gap 16px):
Left — "Monthly SAR Approvals" — Recharts `BarChart`.
Bar fill: `var(--accent)`. Radius on top of bar: [4,4,0,0].
On hover: bar brightens. Custom tooltip.

Right — "Daily Alert Volume" — Recharts `AreaChart`.
Fill: gradient from `var(--accent)` (opacity 0.2) to transparent.
Line: `var(--accent)`. No dots.

**Recent SARs table** (last 20):
Columns: SAR ID (mono) | Transaction | Amount | Approved By | Approved At | Download.
"Download" column: small secondary button "PDF" with `DownloadIcon`.

---

### `/settings/credentials` — API Credentials

Two card sections, 24px gap between.

**Card 1: API Credentials**

Tenant ID row: label + monospace value in `var(--bg-base)` pill (border, padding 4px 10px, `var(--r-sm)`) + `<CopyButton>`.

`<CopyButton>`: shows `CopyIcon`. On click: `copy to clipboard` API → icon swaps to `CheckIcon` (green) for 1500ms → reverts. Tooltip: "Copied!" during that window.

API Key row: `<APIKeyReveal>` component.
Default display: `sk-ae-a1b2••••••••••••••••••••••••••••••••` in mono.
Right side: `EyeOffIcon` button ("Reveal").

On "Reveal":
- Mini confirmation modal: password input + "Reveal Key" button.
- On success: key appears in full. An amber border appears on the key display box.
- 10-second countdown: SVG circular timer (thin ring around the "Reveal" button area depletes clockwise).
- At 3s remaining: text below the key: "Hiding key in 3..." (amber).
- At 0: key re-masks with a brief flash animation.
- `CopyIcon` is available only during the reveal window.

"Rotate API Key" button: `RotateCcwIcon`, danger-ghost, at bottom of card.
Opens modal: "Rotate API Key?"
Warning: "Your current key will stop working immediately. Update your integration before rotating."
Red callout box with the warning text.
"Rotate" (danger) + "Cancel".
On success: new key appears in a prominent one-time-reveal panel with:
`AlertTriangleIcon` + "New key — copy immediately." + key in large mono + `CopyButton`.
Red strip at top of panel: "This key will not be shown again."

**Card 2: Integration Guide** (collapsed by default, ChevronDownIcon expands)
Tab bar: cURL / Python / Node.js.
Switching tabs: `fadeIn 150ms`.
`<CodeBlock>` for each with syntax highlighting + CopyIcon top-right of block.

---

### `/settings/webhook` — Webhook Config

**Section 1: Delivery Configuration**

"Use Aegis Test Receiver" — `<Toggle>` component.
`<Toggle>`: 44px×24px pill. Off: `var(--bg-elevated)`. On: `var(--accent)`. Circle slides (200ms `var(--t-slow)`).
Label left: "Use Built-in Test Receiver". Description right of toggle in `var(--text-3)`.

When ON:
- Green badge "Active" appears with `fadeInUp 150ms`.
- Read-only input showing `https://api.aegis-aml.com/api/v1/webhooks/sink/TEN-0001` + `CopyButton`.
- Info text: "Webhook payloads are delivered internally. No server needed for testing."

When OFF:
- Input field: "https://your-server.com/callback".
- "Save & Generate Secret" button below.
- After save: secret appears in the `<APIKeyReveal>` pattern.

**Section 2: Test**
"Send Test Payload" button (secondary, `ZapIcon`).
After click: inline result appears below the button (200ms `fadeInUp`):
- Success: `CheckCircleIcon` (green) + "Delivered in 42ms"
- Fail: `XCircleIcon` (red) + "Failed: 404 Not Found"

**Section 3: Delivery Log**
Title: "Delivery Log" + "auto-updating" chip (green pulsing dot + "Live", 12px).
Polling: every 3000ms when `document.visibilityState === 'visible'`.

`<WebhookEventCard>` list (max 10).
Collapsed state (48px): `[time ago]  [url/Internal Sink]  [HTTP badge]  [HMAC badge]  [ChevronDown]`
HTTP badge: 200=green, 4xx=amber, 5xx=red.
HMAC badge: "Verified ✓" green / "Failed ✗" red.
Expand: `max-height` CSS transition (300ms). Reveals full JSON in `<CodeBlock>`.

---

### `/settings/schema` — Schema Mapping

**3 cards**, CSS grid `repeat(3, 1fr)`, gap 16px.

Each card: `var(--bg-surface)`, border `var(--border-subtle)`, `var(--r-lg)`, 24px padding.
Active: border-color `var(--accent)`, box-shadow `0 0 0 1px var(--accent)`.
Top-right of active card: "Active" badge (`var(--accent-subtle)` bg, `var(--accent-text)` text, 10px).

Content:
- Icon (32px, colored) matching the schema type.
- Schema name (H3).
- Description (13px `var(--text-3)`, 3 lines).
- Key fields (3–4 pills: `var(--bg-elevated)`, `var(--r-sm)`, 11px mono `var(--text-3)`).
- "Select" button (ghost-sm, bottom). Disabled on active card.

Selecting: optimistic update → border transitions to accent (150ms) → toast "Schema updated."

Below cards: "Extracted Fields" section.
Two-column table showing all 16 standard Aegis fields with realistic example values.
Header: 11px uppercase. Mono font for field names.

---

### `/settings/llm` — LLM Configuration

**Provider cards** (2 cards side by side):
Card 1 "SaaS Managed — Groq": active/selectable.
  - Groq identifier (styled text "groq" with their monospace aesthetic).
  - Model: `llama-3.3-70b-versatile` in mono badge.
  - "Managed by Aegis. No configuration required."
Card 2 "Private LLM": locked.
  - Diagonal "Coming Soon" ribbon across top-right corner.
  - `var(--text-4)` everything.
  - Hover: tooltip "Connect your private LLM endpoint — available in a future release."

**SAR Template Style** — 3 stacked radio cards:
Each: full-width, 16px padding, border `var(--border-subtle)`, `var(--r-md)`.
Active: border-left 3px `var(--accent)` + `var(--accent-subtle)` bg.
Smooth border/bg transition on selection (150ms).

Options: Narrative / Structured Fields / Both (Recommended) [default].

**Token Usage** mini-row below: CpuIcon + "X tokens used · Y requests".

---

### `/admin/verifications`

Header: "Verification Queue" + amber count badge.

Table:
Columns: Company | Type | CIN | Contact | Website | Submitted | Actions

Actions: "✓ Approve" (success-ghost-sm) + "✗ Reject" (danger-ghost-sm). Side by side.

**Approve modal** → success screen:

Success screen inside modal:
- Green header section (24px bg `var(--success-subtle)`): "✓ [Company Name] Approved"
- Body: Credentials block.
  Tenant ID row: label + mono value + `CopyButton`.
  API Key row: full key visible (one-time) in mono, amber bg, border.
  "Copy All Credentials" button.
- Warning strip (amber): `AlertTriangleIcon` + "Copy these now — the API key will not be shown again."
- "Done" button.

Row slide-out: `animation: slideOutToLeft 300ms forwards` when row is dismissed.

---

### `/admin/customers`

Filters: Status chips + search input.
Table: Tenant | Public ID (mono) | Type | Status | Alerts | SARs | Joined | ⋮

Kebab menu (⋮ — `MoreHorizontalIcon`): appears on row hover.
Dropdown menu: `var(--bg-overlay)`, `var(--border)`, `var(--shadow-lg)`, `var(--r-md)`.
Menu items: "Suspend" (amber, `BanIcon`) / "Reinstate" (green) / "View Details" (grey, `ChevronRightIcon`).

"View Details" → expands row inline with `slideInFromTop 200ms`:
Shows 2-col grid of company details.

Suspend: confirmation modal. On success: status badge flips to "Suspended" (red) immediately.

---

### `/admin/logs`

Filter bar: tenant selector + endpoint input + status chips (All/2xx/4xx/5xx) + date range + "Reset" link.

Table: Timestamp | Tenant | Method | Endpoint | Status | Latency

Method badge: POST (blue pill) / GET (grey) / DELETE (red).
Status badge: 2xx (green) / 4xx (amber) / 5xx (red).
Latency: <200ms → `var(--success)`, 200–500ms → `var(--warning)`, >500ms → `var(--danger)`.

Auto-refresh toggle (top right): `RefreshCwIcon` + "Auto-refresh" text. When on: green pulsing dot + "Updates every 10s".

---

### `/admin/groq` — Groq Usage

3 large stat cards: Total Tokens (all time) | Tokens This Month | Est. Cost (USD).
Cost: "$X.XX" (computed at $0.0015/1K input tokens, $0.002/1K output tokens).

Horizontal bar chart (Recharts): top 5 tenants by token usage.
`BarChart` with `layout="vertical"`. Bar: `var(--accent)`.
Each bar labelled with tenant name left of axis.

Per-tenant table: Tenant | Tokens This Month | Requests | Est. Cost | Last Active.
"Last Active": relative time.

Note at bottom: "Pricing estimated based on Groq published rates. Actual billing may vary."

---

## GLOBAL COMPONENTS — FULL SPEC

### `<Sidebar>` (Client Portal)

240px width, fixed left. `var(--bg-surface)`, `border-right var(--border-subtle)`. `height: 100vh`.

**Logo area** (64px): Aegis shield SVG (24px) + "AEGIS" (16px/700 `var(--text-1)`) + "AML" (16px/700 `var(--accent)`).
Below: tenant name truncated, 12px `var(--text-3)`.

**Nav group items** (height 40px each, padding 0 12px):
```css
.nav-item {
  display: flex; align-items: center; gap: 10px;
  height: 40px; padding: 0 12px;
  border-radius: var(--r-md);
  font-size: 14px; color: var(--text-2);
  cursor: pointer;
  transition: background var(--t-fast), color var(--t-fast);
  position: relative;
}
.nav-item:hover  { background: var(--bg-elevated); color: var(--text-1); }
.nav-item.active { background: var(--accent-subtle); color: var(--text-1); }
.nav-item.active::before {
  content: '';
  position: absolute; left: 0; top: 6px; bottom: 6px;
  width: 3px; background: var(--accent);
  border-radius: 0 2px 2px 0;
}
```
Icon: 16px, same color as text. Active: `var(--accent-text)`.
Pending count badge: right-aligned, 20px circle, 11px/500, `var(--danger)` bg (or `var(--warning)` if ≤2).
Pulses: `processingPulse 2s infinite` when count > 0.

**Settings label divider:** 11px uppercase `var(--text-4)`, padding 8px 12px, marginTop 8px.

**Collapse button** (bottom of sidebar, above user section):
A small 24px button with `ChevronLeftIcon`. On click: sidebar animates to 64px width (transition 250ms).
Collapsed: only 16px icons visible, with tooltips on hover.
Labels and text hidden via `overflow: hidden` + `opacity: 0` transition.

**User section** (bottom, 64px, border-top `var(--border-subtle)`):
Avatar: 32px circle, `var(--accent)` bg, white initial letter (14px/600).
Name: 13px/500 `var(--text-1)`. Role: 11px `var(--text-3)` below name.
`LogOutIcon` button (right side, ghost, 16px, `var(--text-4)`, hover `var(--danger)`).

### `<AdminSidebar>` — same structure

Difference: "Aegis AML" + "Admin Console" subtitle in `var(--warning)` (amber — visual distinction).
Nav items: Verifications (UserCheckIcon) + count badge, Customers (Building2Icon), API Logs (ActivityIcon), Groq Usage (ZapIcon).

### `<TopBar>`

64px height, `var(--bg-base)`, `border-bottom var(--border-subtle)`, padding 0 24px.
Left: current page title (H2, `var(--text-1)`).
Right: "⌘K" button (secondary-sm, Kbd-style: `var(--bg-elevated)`, mono font) + user avatar (28px).

### `<CommandPalette>`

Global: `useEffect` → `window.addEventListener('keydown', handler)`.
Triggered by `Cmd+K` (Mac) / `Ctrl+K` (Win/Linux). Registered at app root.

Backdrop: `rgba(0,0,0,0.65)` with `backdrop-filter: blur(4px)`. `fadeIn 150ms`.
Modal: 560px, centred, top 18% of viewport. `var(--bg-surface)`, `var(--border)`, `var(--shadow-lg)`, `var(--r-xl)`. `scaleIn 200ms`.

Search input: 48px height, `border-bottom var(--border)`, no other border. `SearchIcon` 16px left. 16px/400 font. Placeholder: "Search pages, alerts..."

Results section (max-height 320px, overflow-y auto):
Navigation results: `LayoutDashboardIcon`, `InboxIcon`, `SettingsIcon` etc. + page name + shortcut hint right.
Alert results (from React Query cache): `FileTextIcon` + "TXN-XXXXXXXX" + amount right.
Group headers: 11px uppercase `var(--text-4)`, padding 8px 16px.

Each result item: 40px, padding 0 16px. Hover/selected: `var(--bg-elevated)`.
Arrow keys navigate. Enter: navigate + close. Escape: close.
Fuzzy match highlighting: matching chars in `var(--accent-text)` bold.
Empty: "No results for '[query]'" centred in results area.

### `<Toast>` System

`<ToastProvider>` wraps the entire app. Exposes `useToast()` hook.
Stack: fixed bottom-right, `right: 24px, bottom: 24px`, flex column-reverse, gap 8px. `z-index: 9999`.

Each toast: 320px wide. `var(--bg-surface)`, `border: 1px var(--border)`, `var(--shadow-lg)`, `var(--r-lg)`.
Left border 3px: success=`var(--success)`, error=`var(--danger)`, warning=`var(--warning)`, info=`var(--accent)`.
Content: icon (16px) + title (14px/500) + optional description (13px `var(--text-3)`). `X` close button (right, `var(--text-4)`, hover `var(--text-1)`).
Progress bar: 4px at bottom, same color as left border, `progressShrink 4000ms linear forwards`.
Enters: `toastSlideIn 300ms cubic-bezier(0.4,0,0.2,1)`. Exits: `toastSlideOut 200ms ease-in`.
Max 4 toasts. Oldest exits before new enters if at limit.

### `<AlertStatusBadge>`

Height 22px, padding 0 8px, `var(--r-full)`, 11px/500.

| Status | BG | Text | Extra |
|--------|----|------|-------|
| PENDING_INGESTION | `var(--bg-elevated)` | `var(--text-3)` | — |
| PROCESSING | `var(--info-subtle)` | `var(--info)` | 6px blue dot, `processingPulse 1.5s infinite` |
| PENDING_REVIEW | `var(--warning-subtle)` | `var(--warning)` | — |
| APPROVED | `var(--success-subtle)` | `var(--success)` | — |
| REJECTED | `var(--danger-subtle)` | `var(--danger)` | — |
| DELIVERED | `var(--accent-subtle)` | `var(--accent-text)` | — |

### `<Skeleton>`

```css
.skeleton {
  background: linear-gradient(90deg,
    var(--bg-elevated) 25%,
    var(--bg-overlay) 50%,
    var(--bg-elevated) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.8s ease-in-out infinite;
  border-radius: var(--r-sm);
}
```
Variants via props: `<Skeleton width="120px" height="16px" />`.
Pre-built: `<Skeleton.TextLine />`, `<Skeleton.Card />`, `<Skeleton.TableRow />`, `<Skeleton.StatCard />`.

### `<Modal>`

Backdrop: `rgba(0,0,0,0.65)` `backdrop-filter: blur(4px)`. `fadeIn 200ms`.
Panel: `var(--bg-surface)`, `var(--border)`, `var(--shadow-lg)`, `var(--r-xl)`. Default width 480px.
`scaleIn 200ms ease-out` on open. Reverse on close.
Header: title (H3) + X button (top right, `XIcon`, ghost, 32px).
Footer: button row, right-aligned.
Close on backdrop click (if `dismissible` prop = true, default true).
Close on Escape key.

### `<RiskGauge>` (SVG)

Props: `score: number` (0–100), `size?: number` (default 88px).

Draws a circular arc. On mount, animates arc from 0 to score value (800ms).
Color thresholds: score < 50 → `var(--success)`, 50–74 → `var(--warning)`, 75+ → `var(--danger)`.
Centre: score number + "Risk Score" label below.
Stroke width: 7px.

### `<CopyButton>`

Shows `CopyIcon` (16px, `var(--text-3)`).
On click: copies `value` prop to clipboard. Icon swaps to `CheckIcon` (green). Tooltip "Copied!". After 1500ms: reverts.
Hover: icon color `var(--text-1)`.

### `<Toggle>`

44×24px pill. Transition 200ms `var(--t-slow)` for the sliding circle.
Off: `var(--bg-elevated)`. On: `var(--accent)`.
Circle: 18px, white, shadow `var(--shadow-sm)`.
Off position: `left: 3px`. On position: `left: 23px`.

### `<CodeBlock>`

Props: `code: string`, `language?: 'json' | 'bash' | 'python' | 'javascript'`.
`var(--bg-base)` bg, `var(--border)` border, `var(--r-md)`, padding 16px, `font-mono 13px`, `overflow-x: auto`.
`<CopyButton>` positioned top-right.
JSON syntax highlighting via regex (no library):
- Keys: `var(--accent-text)`
- Strings: `var(--success)`
- Numbers: `var(--warning)`
- Booleans/null: `var(--info)`
- Punctuation: `var(--text-3)`

### `<EmptyState>`

Props: `icon: ReactNode`, `title: string`, `description: string`, `action?: ReactNode`.
Centred, padding 48px. Icon 48px `var(--text-4)`. Title H3 `var(--text-2)`. Description 14px `var(--text-3)`. Action button below.

---

## API CLIENT (api/client.ts)

```typescript
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' }
})

// Request: attach access token
client.interceptors.request.use(config => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response: on 401, attempt token refresh
client.interceptors.response.use(
  r => r,
  async error => {
    if (error.response?.status === 401) {
      // try refresh, if fails → clearAuth + redirect /login
    }
    return Promise.reject(error)
  }
)
```

All API functions return typed data or throw. React Query handles loading/error state.
For MVP, all React Query hooks have `placeholderData` using mock data below (so UI renders immediately).

---

## MOCK DATA

```typescript
// src/mocks/data.ts

export const MOCK_USER = {
  id: 'usr-001', email: 'demo@demofintech.com',
  fullName: 'Nikhil Karur', role: 'TENANT_ADMIN',
  tenant: {
    id: 'ten-001', name: 'DemoFintech Pvt Ltd',
    status: 'ACTIVE', tenantIdPublic: 'TEN-0001', companyType: 'FINTECH'
  }
}

export const MOCK_STATS = {
  alertsThisMonth: 47, deltaAlerts: 12,
  pendingReview: 3,
  approvedSars: 31, deltaSars: 8,
  avgReviewMinutes: 8.3
}

export const MOCK_ALERTS = [
  {
    id: '550e8400-e29b-41d4-a716-446655440000',
    transaction_id: 'TXN-2026-061099182',
    transaction_amount: 990000,
    transaction_currency: 'INR',
    transaction_type: 'NEFT_TRANSFER',
    transaction_direction: 'DEBIT',
    transaction_timestamp: '2026-06-10T09:30:00+05:30',
    risk_score: 87,
    status: 'PENDING_REVIEW',
    triggered_rules: ['STRUCTURING', 'RISK_SCORE_THRESHOLD'],
    source: 'API',
    created_at: '2026-06-10T09:30:05Z'
  },
  {
    id: 'alert-002',
    transaction_id: 'TXN-2026-061088741',
    transaction_amount: 2500000,
    transaction_currency: 'INR',
    transaction_type: 'INTERNATIONAL_WIRE',
    transaction_direction: 'DEBIT',
    risk_score: 91,
    status: 'PENDING_REVIEW',
    triggered_rules: ['HIGH_RISK_TYPE', 'RISK_SCORE_THRESHOLD', 'ROUND_NUMBER'],
    source: 'API',
    created_at: '2026-06-10T08:15:00Z'
  },
  {
    id: 'alert-003',
    transaction_id: 'TXN-2026-060977321',
    transaction_amount: 150000,
    transaction_currency: 'INR',
    transaction_type: 'UPI_TRANSFER',
    transaction_direction: 'CREDIT',
    risk_score: 62,
    status: 'APPROVED',
    triggered_rules: ['VELOCITY'],
    source: 'SIMULATOR',
    created_at: '2026-06-09T14:22:00Z'
  }
]

export const MOCK_FULL_ALERT = {
  ...MOCK_ALERTS[0],
  masked_payload: {
    customer_name: 'USR_a1b2c3d4',
    account_id: 'ACC_e5f6a7b8',
    counterparty_account: 'ACC_c9d0e1f2',
    counterparty_institution: 'ICICI Bank',
    ip_address: 'IP_a3b4c5d6',
    device_id: 'DEV_e7f8a9b0'
  },
  compliance: {
    overall_risk: 'HIGH',
    triggered_rules: [
      {
        rule_id: 'STRUCTURING', rule_name: 'Structuring / Smurfing Detected',
        triggered: true, confidence: 'HIGH',
        evidence: { field: 'transaction_amount', value: '990000',
          explanation: 'Transaction of ₹9,90,000 is just below the ₹10,00,000 reporting threshold — a classic structuring indicator under PMLA.' }
      },
      {
        rule_id: 'RISK_SCORE_THRESHOLD', rule_name: 'Risk Score Threshold Exceeded',
        triggered: true, confidence: 'HIGH',
        evidence: { field: 'risk_score', value: '87',
          explanation: 'Incoming risk score of 87 exceeds the configured threshold of 75.' }
      }
    ],
    clean_checks: [
      { rule_id: 'RAPID_MOVEMENT', rule_name: 'Rapid Fund Movement', triggered: false },
      { rule_id: 'ROUND_NUMBER', rule_name: 'Round-Number Transaction', triggered: false },
      { rule_id: 'DORMANT_ACTIVATION', rule_name: 'Dormant Account Activation', triggered: false },
      { rule_id: 'HIGH_RISK_TYPE', rule_name: 'High-Risk Transaction Type', triggered: false },
      { rule_id: 'VELOCITY', rule_name: 'Unusual Transaction Velocity', triggered: false },
      { rule_id: 'COUNTERPARTY_RISK', rule_name: 'Counterparty Institution Risk', triggered: false }
    ]
  },
  sar_draft: {
    id: 'draft-001',
    draft_text: `SUSPICIOUS ACTIVITY REPORT (DRAFT)\n\nReporting Entity: DemoFintech Pvt Ltd\nDate of Draft: 10 June 2026\nFIU-India Report Type: STR (Suspicious Transaction Report)\n\n1. REPORT REFERENCE\nTransaction Reference: TXN-2026-061099182\nDate of Suspicious Activity: 10 June 2026\n\n2. SUBJECT OF REPORT\nCustomer Reference: USR_a1b2c3d4\nAccount Reference: ACC_e5f6a7b8\nTransaction Amount: INR 9,90,000\nTransaction Type: NEFT Transfer (Outward)\nTransaction Direction: Debit\n\n3. COUNTERPARTY DETAILS\nCounterparty Account: ACC_c9d0e1f2\nCounterparty Institution: ICICI Bank\n\n4. SUSPICIOUS ACTIVITY INDICATORS\na) Structuring Detected (HIGH Confidence): The debit transaction amount of ₹9,90,000 is positioned ₹10,000 below the mandatory STR threshold of ₹10,00,000. This deliberate positioning is a well-documented structuring technique used to evade PMLA reporting obligations under Section 12.\n\nb) Elevated Risk Score (HIGH Confidence): The transaction monitoring system computed a risk score of 87 out of 100, significantly exceeding the configured alert threshold of 75.\n\n5. NARRATIVE DESCRIPTION\nOn 10 June 2026 at 09:30 IST, customer reference USR_a1b2c3d4 (account reference ACC_e5f6a7b8) initiated an outward NEFT transfer of INR 9,90,000 to counterparty account ACC_c9d0e1f2 at ICICI Bank. The transaction amount, being precisely INR 10,000 below the statutory reporting threshold, raises reasonable suspicion of deliberate structuring to avoid mandatory disclosure requirements.\n\nThe TMS independently flagged this with a composite risk score of 87/100, corroborating the structural anomaly. The convergence of near-threshold amount and elevated risk score constitutes reasonable grounds for suspicion under PMLA 2002.\n\n6. OFFICER DECLARATION\n[OFFICER NAME]:\n[DESIGNATION]:\n[DATE OF APPROVAL]:`,
    llm_model: 'llama-3.3-70b-versatile',
    generation_latency_ms: 2341,
    officer_edit_count: 0,
    created_at: '2026-06-10T09:30:12Z'
  }
}

export const MOCK_WEBHOOK_EVENTS = [
  {
    id: 'evt-001',
    received_at: '2026-06-10T10:20:03Z',
    hmac_valid: true,
    status: 'DELIVERED',
    payload: { sar_id: 'sar-001', approved_at: '2026-06-10T10:20:00Z',
               compliance_rules_triggered: ['STRUCTURING', 'RISK_SCORE_THRESHOLD'],
               narrative_text: 'SUSPICIOUS ACTIVITY REPORT...' }
  }
]

// Format utility (utils/format.ts)
export function formatINR(amount: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR',
    minimumFractionDigits: 0, maximumFractionDigits: 0
  }).format(amount)
  // Returns "₹9,90,000" — Indian number format
}
```

---

## FINAL CHECKLIST (Fable must verify every item before declaring done)

- [ ] `/login` — animated dot-grid bg, gradient logo, form with error state, loading state
- [ ] `/signup` — 3-step wizard, animated step indicator, slide transitions between steps
- [ ] `/dashboard` — stat cards with count-up, line chart with animation, recent activity table
- [ ] `/status` — pending state with animated ring, rejected state
- [ ] `/queue` — filter bar, table with all columns, new item animation, empty state
- [ ] `/queue/:alertId` — full 3-panel workspace, draggable handles, all 3 panels render
- [ ] Panel 1 — risk gauge SVG with animation, masked field display, raw JSON accordion
- [ ] Panel 2 — triggered rule cards with stagger animation, clean checks accordion
- [ ] Panel 3 — contenteditable editor, section header formatting, sticky action bar
- [ ] Approve flow — confirmation modal → processing steps → full success animation with particles
- [ ] Reject flow — modal with reason, toast, redirect
- [ ] Preview rehydrated modal — document styling, watermark, red banner
- [ ] `/usage` — stat cards, two charts, recent SARs table
- [ ] `/settings/credentials` — API key blur-reveal with 10s timer, rotate flow
- [ ] `/settings/webhook` — toggle, test result, live delivery log with polling
- [ ] `/settings/schema` — 3 selectable cards with transition
- [ ] `/settings/llm` — provider cards, radio template style, token stats
- [ ] `/admin/verifications` — table, approve modal with credential reveal, row slide-out
- [ ] `/admin/customers` — table, kebab menu, expand row
- [ ] `/admin/logs` — filtered table, auto-refresh
- [ ] `/admin/groq` — stat cards, horizontal bar chart, table
- [ ] Sidebar — active state, count badge, collapse to icon rail
- [ ] CommandPalette — Cmd+K trigger, fuzzy search, keyboard nav
- [ ] Toast system — all 4 types, progress bar, auto-dismiss
- [ ] AlertStatusBadge — all 6 states with correct colors and PROCESSING pulse
- [ ] Skeleton loaders — on all data-loading states (no bare spinners)
- [ ] All numbers formatted in Indian number system (₹X,XX,XXX)
- [ ] Mobile: sidebar collapses, tables scroll horizontally

---

## ⛔ STOP INSTRUCTION (REMINDER) ⛔

When every item in the checklist above is complete:

Write exactly this:
> "✅ FRONTEND COMPLETE. All pages, components, animations, and mock data states are implemented.
> Deliverable: a fully working React + Vite frontend at localhost:5173.
> Ready for backend integration in the next Claude Code session."

Then STOP. Do not write any backend, Python, database, or infrastructure code.
