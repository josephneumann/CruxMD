# CruxMD Design Reference

Generated from code analysis for Figma synchronization.

---

## Design Tokens (from `globals.css`)

### Color Palette - Anthropic Brand

| Name | Hex | Usage |
|------|-----|-------|
| **Slate Dark** | `#191919` | Primary text, dark mode background |
| **Slate Medium** | `#262625` | Dark mode surfaces, cards |
| **Slate Light** | `#40403E` | Dark mode borders, secondary |
| **Cloud Dark** | `#666663` | Muted foreground text |
| **Cloud Medium** | `#91918D` | — |
| **Cloud Light** | `#BFBFBA` | Dark mode muted text |
| **Ivory Dark** | `#E5E4DF` | Borders, secondary background |
| **Ivory Medium** | `#F0F0EB` | Muted background, sidebar |
| **Ivory Light** | `#FAFAF7` | Page background (light mode) |
| **Book Cloth** | `#CC785C` | Primary brand, CTAs, focus ring |
| **Kraft** | `#D4A27F` | Warning insights, warm highlights |
| **Manilla** | `#EBDBBC` | Accent, subtle warm backgrounds |
| **Sage** | `#7D8B6F` | Positive insights, chart color |
| **Periwinkle** | `#8B8FC7` | Chart tertiary |
| **Focus Blue** | `#61AAF2` | Info insights, focus states |
| **Error Red** | `#BF4D43` | Destructive, critical insights |
| **White** | `#FFFFFF` | Cards, surfaces |
| **Black** | `#000000` | Pure black (rare use) |

### Semantic Tokens - Light Mode

| Token | Value | Description |
|-------|-------|-------------|
| `--background` | `#FAFAF7` | Page background |
| `--foreground` | `#191919` | Primary text |
| `--card` | `#FFFFFF` | Card background |
| `--card-foreground` | `#191919` | Card text |
| `--primary` | `#CC785C` | Primary actions (Book Cloth) |
| `--primary-foreground` | `#FFFFFF` | Text on primary |
| `--secondary` | `#E5E4DF` | Secondary background |
| `--muted` | `#F0F0EB` | Muted background |
| `--muted-foreground` | `#666663` | Muted text |
| `--accent` | `#EBDBBC` | Accent background (Manilla) |
| `--border` | `#E5E4DF` | Border color |
| `--destructive` | `#BF4D43` | Error states |
| `--ring` | `#CC785C` | Focus ring |

### Clinical Insight Colors

| Type | Background | Border | Icon |
|------|------------|--------|------|
| **Info** | `#61AAF2/10` | `#61AAF2` | `#61AAF2` |
| **Warning** | `#D4A27F/10` | `#D4A27F` | `#D4A27F` |
| **Critical** | `#BF4D43/10` | `#BF4D43` | `#BF4D43` |
| **Positive** | `#7D8B6F/10` | `#7D8B6F` | `#7D8B6F` |

### Border Radius

| Token | Value |
|-------|-------|
| `--radius` | `0.5rem` (8px) |
| `--radius-sm` | `4px` |
| `--radius-md` | `6px` |
| `--radius-lg` | `8px` |
| `--radius-xl` | `12px` |
| `--radius-2xl` | `16px` |

---

## Typography

**Font Family:** Geist Sans (variable) / Geist Mono (code)

| Element | Size | Weight | Line Height |
|---------|------|--------|-------------|
| H1 (Hero) | `text-3xl md:text-5xl` (30-48px) | `font-medium` (500) | `leading-tight` |
| H2 (Section) | `text-2xl md:text-3xl` (24-30px) | `font-medium` (500) | — |
| Body | `text-base` (16px) | `font-normal` (400) | `leading-relaxed` |
| Body Large | `text-lg md:text-xl` (18-20px) | `font-normal` (400) | — |
| Small / Caption | `text-sm` (14px) | — | — |
| Extra Small | `text-xs` (12px) | — | — |

---

## Components Inventory

### In Code (need Figma counterparts)

| Component | File | Variants | Notes |
|-----------|------|----------|-------|
| **Button** | `ui/button.tsx` | default, destructive, outline, secondary, ghost, link | Sizes: default, xs, sm, lg, icon, icon-xs, icon-sm, icon-lg |
| **Card** | `ui/card.tsx` | — | Sub-components: CardHeader, CardTitle, CardDescription, CardContent, CardFooter, CardAction |
| **Alert** | `ui/alert.tsx` | default, destructive | Used as base for InsightCard |
| **InsightCard** | `clinical/InsightCard.tsx` | info, warning, critical, positive | Clinical-specific with icons and citations |
| **Header** | `Header.tsx` | — | Logo + GitHub button, `px-6 py-3` |
| **Avatar** | `ui/avatar.tsx` | — | Radix-based |
| **Select** | `ui/select.tsx` | — | Radix-based dropdown |

### In Figma (existing)

- Header, Hero, Tabs, Footer (layout components)
- Color swatches (documented)
- Logo variations (wordmarks, marks)

### Missing from Figma

- [ ] Button component with all variants
- [ ] Card component
- [ ] InsightCard (4 severity types)
- [ ] Input/Textarea
- [ ] Quick Action Chips (chat page)
- [ ] Model selector dropdown

---

## Page Layouts

### Home Page (`/`)

**Sections (top to bottom):**

1. **Header** — Logo left, GitHub icon right, `border-b`, `px-6 py-3`
2. **Hero** — Centered, `bg-muted/30`, contains:
   - Mark (X logo) — 80x80px
   - H1: "Clinical Intelligence Platform"
   - Subhead: paragraph text
   - CTAs: Primary "Start Chat" + Ghost "See how it works"
3. **Trust Bar** — 3 items with icons, `border-b`
4. **Problem/Solution** — 2-column grid with left borders (primary/accent)
5. **Features Grid** — 4 Cards, `bg-muted/30`
6. **How It Works** — 3 steps with numbered circles
7. **Product Preview** — InsightCard example (warning type), `bg-muted/30`
8. **Social Proof** — Card with blockquote
9. **Final CTA** — `bg-primary` full-width, "Start Chat" secondary button
10. **Footer** — Logo, nav links, disclaimer

**Layout specs:**
- Max content width: `max-w-6xl` (1152px)
- Section padding: `px-8 py-16 md:py-24`
- Card gap: `gap-6`

### Chat Page (`/chat`)

**Layout:** Full-screen centered, no header

1. **Greeting** — Centered, contains:
   - Mark (40x40px) — animates when thinking
   - H1: "Good [time], Dr. Neumann" — `text-3xl md:text-4xl font-light`
2. **Input Card** — `max-w-2xl`, `rounded-2xl`, contains:
   - Textarea placeholder: "How can I help you today?"
   - Bottom toolbar: Plus icon, Clock icon | Model selector, Send button
3. **Quick Action Chips** — 4 pills with icons
4. **Disclaimer** — `text-xs text-muted-foreground`

**Specs:**
- Input card: `bg-card rounded-2xl border shadow-sm`
- Quick chips: `rounded-full border bg-card hover:bg-muted/50`
- Send button: `h-8 w-8 rounded-lg bg-primary`

---

## Icon Usage

All icons from **Lucide React** (`lucide-react` package)

| Icon | Usage |
|------|-------|
| `Github` | Header nav |
| `Lock` | Trust bar - "no PHI" |
| `Clock` | Trust bar - "seconds not minutes", Chat toolbar |
| `Code` | Trust bar - "FHIR R4" |
| `Layers` | Feature - "Complete patient context" |
| `AlertCircle` | Feature - "Meaningful insights", Critical insight |
| `MessageSquare` | Feature - "Ask questions" |
| `Database` | Feature - "Works with your data" |
| `Plus` | Chat toolbar - new |
| `ArrowUp` | Chat send button |
| `ChevronDown` | Model selector |
| `Phone` | Quick action - "Patients to call" |
| `BookOpen` | Quick action - "Latest research" |
| `BarChart3` | Quick action - "My performance" |
| `Users` | Quick action - "Panel overview" |
| `Info` | Info insight |
| `AlertTriangle` | Warning insight |
| `CheckCircle` | Positive insight |

---

## Screenshots Reference

Screenshots captured from live localhost:3000:
- Home page: Hero, Features, How It Works, InsightCard example, CTA, Footer
- Chat page: Full centered layout with input card and quick actions

Use these as underlays when recreating in Figma.
