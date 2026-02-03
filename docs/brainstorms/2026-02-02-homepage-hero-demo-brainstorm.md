# Brainstorm: Homepage Live Demo — Conversational Canvas Showcase

**Date**: 2026-02-02
**Status**: Ready for planning

## Problem Statement

The homepage describes what CruxMD does but doesn't **show** it. Visitors see feature bullet points and marketing copy, but never experience the product's core value proposition: an LLM synthesizing scattered clinical data into life-changing insights in real-time. A live, scroll-triggered demo of the conversational canvas would sell the product far better than static text.

## Proposed Solution

A scripted replay demo that renders real CruxMD chat components (typewriter text, reasoning collapsible, InsightCards, follow-up suggestions) driven by scroll position. The demo replaces the current features grid section and uses a sticky canvas layout (Apple-style) where the chat stays pinned while scroll progress drives the conversation forward. Four clinical scenarios are available via tabs, with "Silent Heart Failure" as the default.

## Key Decisions

- **Scripted replay, not live API**: Pre-baked conversation scripts feed the existing chat components. No backend calls. Components render exactly as they do in production — typewriter, staggered insights, reasoning toggle — maintaining full visual authenticity.
- **Scroll-triggered progression**: Scroll position within the demo section drives which messages/phases appear. User controls pacing naturally.
- **Sticky canvas layout**: Chat canvas pins to viewport while descriptive content or scroll-progress region scrolls beside it. Cinematic, similar to Apple product pages.
- **Replaces features grid**: The demo IS the feature showcase. Scenarios demonstrate capabilities better than bullet points.
- **Tab-based scenario switcher**: Horizontal tabs above the demo canvas for switching between 4 clinical scenarios. Resetting scroll progress on switch.
- **Purely passive (no input)**: Users watch the conversation unfold. No text input, no clickable follow-ups. Play/pause toggle optional.

## Clinical Scenarios

### 1. Silent Heart Failure Progression (Default)
**Patient**: 68F with HTN, T2DM, obesity. On lisinopril, metformin, atorvastatin, recently started furosemide.

**The story**: PCP asks CruxMD to review this patient before a routine visit. The agent synthesizes:
- NT-proBNP trending upward over 6 months (85 → 142 → 219 pg/mL) — each value "normal" in isolation
- 8 lb weight gain over 3 months despite reported dieting
- Furosemide dose increased twice in 4 months
- Visit notes mentioning fatigue ("getting older") and mild exertional dyspnea ("deconditioning")

**Insight**: Pre-heart failure progressing to Stage C. Recommend initiating GDMT (optimize ACE-I, add beta-blocker, consider SGLT2i), close monitoring. Prevents hospitalization for acute decompensated HF.

### 2. QT Prolongation Time Bomb
**Patient**: 74F with AFib, GERD, depression. On diltiazem, citalopram, omeprazole.

**The story**: Urgent care added azithromycin for bronchitis. Agent flags compounding QT-prolongation risk: azithromycin + citalopram + diltiazem (CYP3A4 interaction), plus low K (3.3) and low Mg (1.7). Female sex + age >65 further elevate risk.

**Insight**: High risk of torsades de pointes. Recommend alternative antibiotic, correct electrolytes, obtain ECG. Prevents potential sudden cardiac death.

### 3. Young Athlete — Hidden HCM
**Patient**: 17M basketball player at sports physical.

**The story**: Agent connects father's death at 42 ("massive heart attack"), grandfather's sudden death in 50s, brother screened for "heart problem," positional systolic murmur, and exertional lightheadedness dismissed as dehydration.

**Insight**: Family history pattern strongly suggests hypertrophic cardiomyopathy. Recommend ECG + echocardiography before sports clearance. HCM causes ~40% of sudden cardiac deaths in young athletes.

### 4. Dangerous "Improvement" — Hypoglycemia Cascade
**Patient**: 79M with longstanding T2DM, CAD. On metformin, glipizide, propranolol (non-selective), aspirin, atorvastatin.

**The story**: HbA1c "improved" from 8.2% to 6.8% — looks great on paper. Agent flags: propranolol masking hypoglycemia symptoms, glucose logs showing readings in 60-70s, recent ED visit for "fall" with glucose of 52, declining eGFR (58→48), and wife reporting confusion episodes.

**Insight**: Over-treatment with hypoglycemia unawareness. Recommend switching to cardioselective beta-blocker, reducing/stopping glipizide, adjusting metformin for renal function, relaxing HbA1c target to 7.5-8%.

## Staged Interactions (Per Scenario)

Each scenario plays out as 3 user→agent interactions, showing a natural clinical workflow: initial question → deeper investigation → actionable plan.

### Scenario 1: Silent Heart Failure (Default)

**Interaction 1 — "The Huddle"**
- **User**: "I'm seeing Margaret Chen this afternoon. What should I know?"
- **Agent reasoning**: Reviews medication list, recent visits, trending labs
- **Agent narrative**: Concise patient summary — 68F, HTN/T2DM/obesity, 4 active meds. Flags that furosemide was added 4 months ago and already dose-increased twice.
- **Insight (warning)**: "Escalating diuretic requirement — consider volume status evaluation"
- **Follow-ups**: "Show me her weight trend" / "What's her BNP history?"

**Interaction 2 — "Connecting the Dots"**
- **User**: "Show me her weight trend and BNP history"
- **Agent reasoning**: Connects the temporal pattern across data sources
- **Agent narrative**: Weight up 8 lbs over 3 months, NT-proBNP trending 85 → 142 → 219 over 6 months — each individually "normal" but trajectory concerning. Surfaces buried visit notes: fatigue attributed to aging, mild dyspnea attributed to deconditioning.
- **Insight (critical)**: "Pattern consistent with Stage B → C heart failure progression. Individual values normal, trend is not."
- **Insight (info)**: "ACC/AHA guidelines recommend GDMT initiation at this stage"
- **Follow-ups**: "What treatment should I start?" / "What's her cardiac risk profile?"

**Interaction 3 — "The Action Plan"**
- **User**: "What treatment should I start?"
- **Agent reasoning**: Reviews current meds, contraindications, guidelines
- **Agent narrative**: Optimize lisinopril dosing, initiate low-dose carvedilol, consider empagliflozin (SGLT2i with dual cardiac/renal benefit given her diabetes), order echocardiogram, schedule 2-week follow-up with daily weights.
- **Insight (positive)**: "Early GDMT initiation reduces HF hospitalization risk by 30-40%"
- **Insight (info)**: "Empagliflozin indicated for both T2DM and HFpEF — dual benefit"
- **Follow-ups**: "Draft the referral" / "What monitoring do I need?"

---

### Scenario 2: QT Prolongation Time Bomb

**Interaction 1 — "Chart Review"**
- **User**: "Pull up Dorothy Williams — urgent care sent her records from yesterday"
- **Agent reasoning**: Scans medication list against new azithromycin prescription
- **Agent narrative**: 74F, AFib/GERD/depression, now with azithromycin Z-pak from urgent care for bronchitis.
- **Insight (critical)**: "Dangerous multi-drug QT prolongation risk: azithromycin + citalopram + diltiazem"
- **Insight (warning)**: "Recent labs show K 3.3, Mg 1.7 — electrolyte abnormalities amplify QT risk"
- **Follow-ups**: "How serious is this?" / "What should I do right now?"

**Interaction 2 — "Risk Quantification"**
- **User**: "How serious is this?"
- **Agent reasoning**: Tallies compounding risk factors
- **Agent narrative**: Female sex, age >65, heart disease, 3 QT-prolonging factors, CYP3A4 interaction boosting azithromycin levels, uncorrected low K and Mg. Last ECG 6 months ago showed QTc 438ms — already borderline.
- **Insight (critical)**: "5+ concurrent risk factors for torsades de pointes. This is a medical emergency to address today."
- **Insight (info)**: "Each 10ms QTc increase = 5-7% exponential rise in TdP risk"
- **Follow-ups**: "What's the safe alternative?" / "Should I get a stat ECG?"

**Interaction 3 — "Intervention"**
- **User**: "What's the safe alternative?"
- **Agent reasoning**: Reviews antibiotic options without QT risk
- **Agent narrative**: Discontinue azithromycin immediately, switch to amoxicillin-clavulanate, order stat ECG and BMP, replete K to >4.0 and Mg to >2.0, flag chart for QT-prolonging drug avoidance.
- **Insight (positive)**: "Amoxicillin-clavulanate has no QT prolongation risk and covers typical bronchitis pathogens"
- **Insight (warning)**: "Contact patient today — azithromycin risk highest in first 5 days of use"

---

### Scenario 3: Young Athlete — Hidden HCM

**Interaction 1 — "Sports Physical"**
- **User**: "I've got a sports physical for Tyler Reeves, 17, basketball. Anything in the chart?"
- **Agent reasoning**: Pulls demographics, family history, prior visit notes
- **Agent narrative**: Healthy 17M, no chronic conditions, varsity basketball clearance. Flags family history: father died at 42 of "massive heart attack," paternal grandfather died suddenly in 50s. Brother referred for "cardiac screening" 2 years ago — outcome not in chart.
- **Insight (warning)**: "Two first/second-degree relatives with premature cardiac death — screen for inherited cardiomyopathy before sports clearance"
- **Follow-ups**: "What should I look for on exam?" / "What screening does he need?"

**Interaction 2 — "Exam Findings"**
- **User**: "I heard a soft systolic murmur that changes with position. He also says he gets lightheaded during intense practice."
- **Agent reasoning**: Correlates dynamic murmur + exertional symptoms + family history
- **Agent narrative**: Positional variation in the murmur is a hallmark of HCM (louder with Valsalva/standing, softer with squatting). Exertional lightheadedness with this family history is a red flag for LVOT obstruction or arrhythmia risk.
- **Insight (critical)**: "High pre-test probability for hypertrophic cardiomyopathy. Do NOT clear for sports until workup complete."
- **Insight (info)**: "HCM is the leading cause of sudden cardiac death in athletes under 35 (~40% of cases)"
- **Follow-ups**: "What workup do I order?" / "Should I pull him from practice now?"

**Interaction 3 — "Protecting the Patient"**
- **User**: "What workup do I order?"
- **Agent reasoning**: Reviews screening guidelines
- **Agent narrative**: 12-lead ECG (abnormal in 97% of HCM), transthoracic echocardiogram, urgent cardiology referral, withhold sports clearance pending results. Also: obtain brother's screening results, offer family genetic counseling.
- **Insight (positive)**: "If confirmed, early diagnosis enables ICD evaluation, activity modification, and family screening — dramatically reducing sudden death risk"
- **Insight (info)**: "First-degree relatives of HCM patients should all undergo screening with ECG + echo"

---

### Scenario 4: Dangerous "Improvement" — Hypoglycemia Cascade

**Interaction 1 — "The Deceptive Win"**
- **User**: "Robert Garcia is here for diabetes follow-up. His A1c came down nicely."
- **Agent reasoning**: Reviews A1c trend, medication list, recent encounters
- **Agent narrative**: 79M, HbA1c improved 8.2% → 6.8% over 6 months. On metformin 1000mg BID + glipizide 10mg BID + propranolol 80mg BID.
- **Insight (warning)**: "HbA1c 6.8% may indicate over-treatment in a 79-year-old — ADA recommends <8.0% for elderly patients with comorbidities"
- **Insight (warning)**: "Propranolol (non-selective beta-blocker) masks hypoglycemia warning symptoms — tachycardia, tremor, anxiety"
- **Follow-ups**: "Why is that A1c too low?" / "Show me his glucose readings"

**Interaction 2 — "The Hidden Pattern"**
- **User**: "Show me his glucose readings and recent visits"
- **Agent reasoning**: Cross-references glucose logs, ED visit, wife's symptoms, renal function
- **Agent narrative**: Glucose logs show multiple readings 60-70 mg/dL. ED visit 2 weeks ago — fall, glucose 52, given juice, discharged without medication change. Wife reported confusion and a "strange episode" while driving — attributed to possible TIA. eGFR declining 58 → 48 over the past year.
- **Insight (critical)**: "Recurrent hypoglycemia with unawareness — the fall, confusion, and driving episode were likely hypoglycemic events, not TIA"
- **Insight (warning)**: "Declining renal function increases accumulation risk for both metformin and glipizide"
- **Follow-ups**: "What changes do I need to make?" / "Is he safe to drive?"

**Interaction 3 — "Unwinding the Cascade"**
- **User**: "What changes do I need to make?"
- **Agent reasoning**: Reviews each medication's contribution and alternatives
- **Agent narrative**: Stop glipizide (highest hypoglycemia risk, renally cleared), switch propranolol to metoprolol succinate (cardioselective, doesn't mask hypoglycemia), reduce metformin to 500mg BID given eGFR 48, relax HbA1c target to 7.5-8.0%, educate patient and wife on hypoglycemia recognition, reassess driving safety.
- **Insight (positive)**: "These changes eliminate the three compounding factors: sulfonylurea + non-selective beta-blocker + renal accumulation"
- **Insight (info)**: "Consider CGM for 2 weeks to quantify hypoglycemia burden before and after changes"

---

## Scope

### In Scope
- Scroll-triggered demo component replacing features grid
- Sticky canvas layout with scroll-progress driver
- Tab switcher for 4 scenarios
- Scripted conversation data for all 4 scenarios
- Reuse of existing chat components (AgentMessage, UserMessage, InsightCard, ThinkingIndicator, FollowUpSuggestions)
- Responsive behavior (mobile may need different layout — perhaps inline instead of sticky)
- Silent Heart Failure as fully scripted first; other 3 follow

### Out of Scope
- Any backend/API integration — purely frontend
- User input or interactive elements within the chat
- Chart/visualization components (future enhancement — could add BNP trend chart, potassium chart)
- Audio/video narration
- Analytics tracking of demo engagement (can add later)

## Open Questions
- How many scroll "steps" per scenario? (e.g., 1 user message + 1 agent response = ~4 phases: user message, reasoning spinner, narrative typewriter, insights reveal)
- Should the demo auto-play if user stops scrolling mid-conversation, or freeze until they scroll more?
- Mobile layout: inline scroll or simplified version?
- Should scenario tabs show a brief one-line description or just the title?
- Do we want a subtle "Try it yourself →" CTA at the end that links to `/chat`?

## Constraints
- Must reuse existing canvas components to maintain visual authenticity — no separate "demo mode" styling
- Scroll-triggered animation needs to feel smooth, not janky — likely need Intersection Observer or a scroll library (framer-motion scroll progress, GSAP ScrollTrigger, or similar)
- Four scenario scripts need clinically accurate content — will need review
- Performance: pre-rendered content, no API calls, should be lightweight

## Risks
- **Scroll jank**: Sticky + scroll-driven animations can be tricky across browsers. Mitigation: use well-tested scroll libraries, test on Safari/Firefox/Chrome.
- **Mobile complexity**: Sticky canvas doesn't translate well to mobile. Mitigation: fall back to inline scroll-triggered reveal on small screens.
- **Content accuracy**: Clinical scenarios must be medically sound. Mitigation: research-backed content (already sourced), final review by clinician if possible.
- **Component coupling**: Reusing chat components means demo breaks if components change. Mitigation: components are stable and well-typed; demo uses same data shapes.
