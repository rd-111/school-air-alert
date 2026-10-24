# School Air Alert Design System

This document is the design source of truth for future frontend work. The palette and component guidance below define the target visual system. The current application still uses the earlier green-led palette in `frontend/src/styles.css`; this audit does not apply the redesign to application code.

## Product principles

- Calm and clear: make the current forecast and its limits easy to understand at a glance.
- Trustworthy: label forecast, demo, unavailable, and modeled data accurately. Never style a forecast as a measured reading.
- School-first: use plain language, readable type, and comfortable touch targets for administrators on phones and desktops.
- Accessible: color supplements words, icons, and structure; it never carries a status by itself.
- Restrained: use a small number of accent colors, surfaces, and motion effects. Avoid decorative gradients and glass effects that compete with the data.

## Current frontend architecture

- React 18 and JavaScript, built with Vite. Styling is plain CSS in `frontend/src/styles.css`; there is no UI framework or icon package.
- `frontend/src/App.jsx` owns the language selector, navigation, theme control, and routes:
  - `/` — dashboard (`DashboardPage`)
  - `/report` — monthly report (`ReportPage`)
  - `/poster` — printable notice (`PosterPage`)
  - Unknown paths currently render the dashboard.
- The dashboard is composed from small components for school selection and registration, location, status, hourly chart and readings, activity windows and advice, forecast provenance, and optional smoke context.
- `frontend/src/api/client.js` is the frontend API boundary. `VITE_DATA_MODE` selects demo or live mode, and `VITE_API_URL` configures the backend origin. NASA FIRMS credentials remain backend-only.
- Visible interface text is supplied by `frontend/src/i18n/en.json`, `hi.json`, and `mr.json`; `locales.test.js` checks key shape consistency.
- The theme is applied to the document root with `data-theme="light|dark"`. The existing persistence key is `school-air-alert-theme`; absent a saved choice, the application reads `prefers-color-scheme`. The early bootstrap in `frontend/index.html` sets the theme before the app mounts.
- The hourly chart uses Recharts. Its grid, line, highlight, axes, and tooltip should use the same semantic theme tokens as the surrounding interface.

## Audit: current design strengths and weaknesses

### Strengths

- Existing CSS variables already support two themes, surfaces, text, status colors, chart colors, and shadows.
- Forecast status is presented with text and an icon as well as color.
- Dashboard, report, and poster share the same global theme. Print styles deliberately produce a white, high-contrast poster.
- Mobile layout rules, keyboard focus styling, and reduced-motion handling already exist.
- Demo/live, forecast provenance, and smoke-context disclaimers are represented in the interface.

### Opportunities for the next visual pass

- The current palette is predominantly green, with layered background gradients. It does not yet use the requested restrained teal and blue palette.
- Surface, border, and radius values are spread through a long stylesheet. Some declarations are compacted onto single lines, making visual changes harder to review.
- Cards currently use several radii (roughly 10–22 px) and varying border treatments. A smaller, shared radius scale would make the interface feel more deliberate.
- The header combines navigation, language selection, and theme selection; its mobile order and available width should be reviewed at narrow viewport sizes.
- Typography uses an Inter-first system stack but does not load or bundle a font. A future pass should retain a reliable system fallback and avoid a new remote font dependency unless approved.
- Chart colors are now tokenized, but chart legibility and tooltip contrast should be checked in both themes at actual phone and desktop widths.
- Automated tests cover behavior and translations, but there is no automated visual-regression or contrast test. The ratios below are calculated for the documented color pairs; actual component combinations still need visual review.

## Design tokens

These values are the target values for implementation. Keep them in the existing CSS custom-property system in `frontend/src/styles.css`, using semantic names rather than adding a second theme mechanism. `:root[data-theme="dark"]` remains the dark-theme selector. Do not change the localStorage key or theme preference behavior.

### Color

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--page-bg` | `#F6F9FB` | `#0A1118` | Main page background |
| `--surface` | `#FFFFFF` | `#111B26` | Cards, panels, poster on screen |
| `--surface-secondary` | `#EDF3F7` | `#172433` | Nested surfaces, hover and quiet controls |
| `--border` | `#DCE5EC` | `#243649` | Dividers and control boundaries |
| `--text` | `#0B1B2B` | `#E7EEF5` | Primary text |
| `--text-muted` | `#4A5D70` | `#9AAABB` | Supporting text and labels |
| `--primary` | `#0F766E` | `#2DD4BF` | Brand, primary actions, non-status emphasis |
| `--accent` | `#2563EB` | `#60A5FA` | Links and secondary emphasis |
| `--focus` | `#0F766E` | `#2DD4BF` | Keyboard focus ring |

`--primary` and `--accent` are not air-quality categories. Keep their uses separate from status tokens.

### Air-quality status colors

Keep the current classification behavior unchanged. Use category-specific text/accent and soft surfaces so the meanings remain clear in both themes. Always show the status word and the existing status icon.

| Status | Light text/accent | Light surface | Dark text/accent | Dark surface |
| --- | --- | --- | --- | --- |
| GREEN | `#176B52` | `#E9F6ED` | `#69D19D` | `#193A2D` |
| YELLOW | `#8A5B00` | `#FFF5D9` | `#F0BF4E` | `#3B321D` |
| RED | `#9B302E` | `#FFF0EB` | `#FF8174` | `#3C2524` |
| UNKNOWN | `#63717C` | `#F0F4F6` | `#A9BDC8` | `#263139` |

These are presentation colors, not threshold definitions or official air-quality guidance.

### Contrast check

Ratios use the WCAG relative-luminance contrast calculation. The documented core pairs meet the WCAG AA 4.5:1 target for normal text:

| Pair | Contrast |
| --- | ---: |
| Light primary text `#0B1B2B` on white | 17.41:1 |
| Light muted text `#4A5D70` on white | 6.79:1 |
| White on light primary `#0F766E` | 5.47:1 |
| White on light accent `#2563EB` | 5.17:1 |
| Dark primary text `#E7EEF5` on `#0A1118` | 16.22:1 |
| Dark primary text on `#111B26` | 14.85:1 |
| Dark muted text `#9AAABB` on `#0A1118` | 7.99:1 |
| Dark muted text on `#111B26` | 7.32:1 |
| Dark primary `#2DD4BF` on `#0A1118` | 10.20:1 |
| Dark accent `#60A5FA` on `#0A1118` | 7.47:1 |
| GREEN text/accent on its light surface | 6.14:1 |
| YELLOW text/accent on its light surface | 5.64:1 |
| RED text/accent on its light surface | 6.91:1 |
| GREEN text/accent on its dark surface | 6.65:1 |
| YELLOW text/accent on its dark surface | 7.39:1 |
| RED text/accent on its dark surface | 5.83:1 |

Check any new foreground/background combinations before adding them. Large text can use the WCAG AA 3:1 threshold, but body copy and controls should use at least 4.5:1. Non-text controls and chart marks should remain distinguishable from adjacent surfaces.

## Typography

- Font stack: `Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`. Do not make the design depend on a font download.
- Use clear editorial hierarchy: one page title, section titles, then labels and supporting copy. Keep eyebrow text sparse and avoid using all-caps for long messages.
- Body text: 16 px minimum. Supporting text should remain comfortably readable; do not reduce essential labels to tiny caption text.
- Suggested scale: 14 px small metadata, 16 px body, 18–20 px section heading, 32–50 px page heading. Use `clamp()` for responsive headings.
- Use numeric tabular alignment for PM2.5 readings and report counts where practical.

## Spacing, shape, and layout

### Spacing scale

Use a 4 px base scale: `4, 8, 12, 16, 24, 32, 48, 64 px`. Prefer 16–24 px card padding, 24–32 px between major sections, and 8–12 px within control groups. Dense hourly details may use the smaller steps.

### Radius scale

- Small controls and chips: 8 px.
- Inputs and buttons: 10–12 px.
- Standard cards and panels: 16 px.
- Hero status card or special printable surface: at most 20 px.
- Pills: fully rounded only when the shape communicates a compact badge or control.

### Shadows

Use borders to define surfaces first. Suggested light shadow: `0 8px 24px rgb(11 27 43 / 6%)`; dark shadow: `0 10px 28px rgb(0 0 0 / 24%)`. Reserve hover shadows for interactive elements. Do not give every card a strong shadow.

### Breakpoints and containers

- Mobile: below 700 px. One-column forms and activity cards; controls may wrap without clipping.
- Tablet: 700–1023 px. Use two-column layouts only where each column remains readable.
- Desktop: 1024 px and above. Center dashboard content at a maximum width of 1120 px.
- Monthly report: follow the dashboard container. Printable poster: maximum width 800 px on screen and full printable width in print.
- The current stylesheet uses a 700 px mobile breakpoint and these container widths; keep changes aligned unless a tested layout issue requires adjustment.

## Component guidance

### Navigation and theme control

- Preserve the current React Router paths and language selector.
- Keep the theme toggle visible in the shared header with a 42–44 px minimum touch target, an icon, translated visible mode name, and an action-oriented accessible name.
- Keep focus visible; do not communicate the selected theme only through the icon.
- Ensure header controls wrap or scroll cleanly on narrow screens without hiding navigation.

### Buttons

- Primary action: `--primary` background with a verified contrasting foreground.
- Secondary action: surface background, border, and primary text.
- Quiet action: transparent until hover/focus, with a visible focus ring.
- Minimum interactive target: 44 by 44 CSS px where practical. Provide disabled and hover states without relying on color alone.

### Cards and panels

- Use `--surface`, `--surface-secondary`, and `--border` consistently.
- Maintain one clear title and readable content order per card. Reserve the strongest elevation for the current status summary.
- Avoid wrapping every small datum in a separate card. Group related metadata with definition lists or compact rows.

### Status badges and forecast summary

- Display GREEN, YELLOW, RED, or UNKNOWN as text, with a recognizable icon and a status-specific accent.
- Keep status accents semantically separate from the brand teal and blue.
- Do not describe a forecast as an observation, a health guarantee, or official government advice unless the source and policy establish that claim.

### Form controls

- Use the theme surface, text, and border tokens for inputs, selects, and checkboxes.
- Retain explicit labels, readable validation/error messages, keyboard focus, and an adequate touch area.
- Errors must include text and not rely on red alone. Keep native validation and request errors understandable.

### Charts

- Chart gridlines: subtle `--border`; axes and labels: `--text-muted`; PM2.5 line: a high-contrast chart token; tooltip: `--surface` with `--text` and a visible border.
- Highlight the best window with a low-opacity supporting color, not a status-color replacement.
- Preserve numeric units and descriptive accessible text. Provide the existing hourly readings list alongside the visualization so information is not chart-only.
- Verify chart axes, focus/tooltip behavior, and contrast in both themes at mobile width.

### Loading, error, and empty states

- Keep the shared page structure and theme surfaces. Use one concise heading, a helpful explanation, and a retry action when retry is available.
- Loading should be perceivable with text or an accessible status role. Avoid indefinite decorative motion.
- Empty and unavailable states must not be styled as GREEN or as a successful live result.
- Preserve clear demo/live labeling and provider provenance.

### Report and printable poster

- Use shared theme tokens on screen. Keep the poster legible and structured in both screen themes.
- In print, continue to hide navigation and controls and force a high-contrast paper-friendly palette regardless of the selected screen theme.
- Keep status words and advice visible in monochrome printing; do not rely on background color alone.

## Accessibility and motion

- Meet WCAG 2.2 AA contrast for text and controls. Verify actual combinations, not color values in isolation.
- Use semantic headings, landmarks, labels, buttons, and links. Keep keyboard operation and `:focus-visible` styles.
- Give icon-only graphics an accessible name through their control; mark decorative SVGs `aria-hidden="true"`.
- Preserve the visible GREEN/YELLOW/RED text plus icons and accessible chart description.
- Respect `prefers-reduced-motion: reduce`. Remove non-essential transforms and animations in that mode; never make data comprehension depend on animation.
- Avoid flashing, pulsing, and rapidly changing status effects.

## Implementation boundaries

- Keep the existing `data-theme` root attribute and `school-air-alert-theme` localStorage key. On first visit, use the system preference; persist an explicit user selection. Keep the early bootstrap to minimize theme flash.
- Keep theme values as CSS custom properties. Components should consume semantic tokens rather than add one-off neutral colors.
- Keep all user-facing text in the English, Hindi, and Marathi locale dictionaries, with matching key structures.
- Do not introduce a UI framework, Tailwind, icon package, remote font dependency, new business rules, or backend changes as part of visual refinement.
- Maintain existing routes, API contracts, data-source labels, safety disclaimers, and report/poster behavior.
