import type { DemoScenario } from "../demo-scenarios";

/**
 * Silent Heart Failure Progression — Margaret Chen, 68F
 *
 * Clinical story: PCP asks CruxMD to review a patient before a routine visit.
 * The agent synthesises scattered data — trending NT-proBNP, weight gain,
 * escalating diuretics, buried visit-note symptoms — to identify early-stage
 * heart failure progression that no single data point would flag alone.
 *
 * Three interactions model a natural clinical workflow:
 *   1. "The Huddle" — quick pre-visit summary
 *   2. "Connecting the Dots" — deeper trend analysis
 *   3. "The Action Plan" — guideline-directed treatment recommendations
 */
export const heartFailureScenario: DemoScenario = {
  id: "heart-failure",
  title: "Heart Failure",
  subtitle: "Silent Progression",
  patient: "Margaret Chen, 68F",

  interactions: [
    // ── Interaction 1 — "The Huddle" ──────────────────────────────────────
    {
      userMessage:
        "I'm seeing Margaret Chen this afternoon. What should I know?",
      agentResponse: {
        reasoningText:
          "Pulling Margaret Chen's chart — active problem list, current medications, recent encounters, and trending labs. She's 68F with hypertension, type 2 diabetes, and obesity. I'm seeing four active medications: lisinopril 10 mg daily, metformin 1000 mg BID, atorvastatin 40 mg daily, and furosemide — which was added just 4 months ago and has already been uptitrated twice. That diuretic escalation pattern is notable. Let me flag the key items for the visit.",
        reasoningDurationMs: 6400,
        narrative:
          "**Margaret Chen** is a **68-year-old woman** with hypertension, type 2 diabetes, and obesity.\n\n**Active medications** — lisinopril 10 mg daily, metformin 1000 mg BID, atorvastatin 40 mg daily, and furosemide 40 mg daily.\n\nOne thing stands out: **furosemide was started 4 months ago at 20 mg and has already been increased twice** — first to 30 mg, then to 40 mg. That kind of escalating diuretic requirement in a short window warrants closer evaluation of her volume status and cardiac function.",
        insights: [
          {
            type: "warning",
            title: "Escalating diuretic requirement",
            content:
              "Furosemide dose doubled in 4 months (20 → 40 mg). Escalating loop diuretic need may indicate worsening fluid retention and should prompt evaluation for underlying cardiac dysfunction.",
            citations: [
              "Medication history — furosemide added 2025-09-14, uptitrated 2025-11-02, 2025-12-18",
            ],
          },
        ],
        followUps: [
          { question: "Show me her weight trend", intent: "trend_analysis" },
          { question: "What's her BNP history?", intent: "lab_trend" },
        ],
      },
    },

    // ── Interaction 2 — "Connecting the Dots" ─────────────────────────────
    {
      userMessage: "Show me her weight trend and BNP history",
      agentResponse: {
        reasoningText:
          "Looking at weight entries over the past 6 months and NT-proBNP results over the same period. Weight: 187 lbs in August → 191 in October → 195 in January — an 8-pound gain despite the patient reporting dietary efforts. NT-proBNP: 85 pg/mL in July, 142 in October, 219 in January. Each value falls within the lab's normal reference range (< 300 pg/mL for her age), but the upward trajectory is unmistakable. I'm also checking recent visit notes — the October encounter documents fatigue attributed to \"just getting older\" and mild exertional dyspnea charted as \"deconditioning.\" These symptoms were assessed in isolation and explained away, but together with the biomarker and weight trends they paint a different picture.",
        reasoningDurationMs: 8200,
        narrative:
          "Two trends tell the story:\n\n**Weight** — up 8 lbs over 5 months (187 → 191 → 195 lbs) despite Margaret reporting she's been dieting. Fluid retention is the most likely driver given the concurrent diuretic escalation.\n\n**NT-proBNP** — trending upward: **85 → 142 → 219 pg/mL** over the last 6 months. Each individual value falls within the normal reference range for her age (< 300 pg/mL), which is why it wasn't flagged — but the **trajectory** tells a different story.\n\nBuried in recent visit notes:\n- **October** — fatigue, attributed to \"getting older\"\n- **December** — mild exertional dyspnea on stairs, charted as \"deconditioning\"\n\nThese symptoms were assessed independently and dismissed, but when combined with rising NT-proBNP, weight gain despite diuretics, and escalating furosemide — the pattern is consistent with **progression from Stage B to Stage C heart failure**.",
        insights: [
          {
            type: "critical",
            title: "Pattern consistent with Stage B → C heart failure progression",
            content:
              "NT-proBNP rising 85 → 142 → 219 pg/mL over 6 months, 8-lb weight gain despite diuretic therapy, escalating furosemide requirement, and symptoms (fatigue, exertional dyspnea) attributed to other causes. Individual data points appear normal — the trend is not.",
            citations: [
              "NT-proBNP — 85 pg/mL (2025-07-15), 142 pg/mL (2025-10-22), 219 pg/mL (2026-01-08)",
              "Weight — 187 lbs (2025-08-10), 191 lbs (2025-10-22), 195 lbs (2026-01-08)",
              "Visit note 2025-10-22 — \"Patient reports fatigue, likely age-related\"",
              "Visit note 2025-12-18 — \"Mild dyspnea on exertion, likely deconditioning\"",
            ],
          },
          {
            type: "info",
            title: "ACC/AHA guidelines recommend GDMT at this stage",
            content:
              "The 2022 AHA/ACC/HFSA guideline for heart failure management recommends initiating guideline-directed medical therapy (GDMT) — including neurohormonal blockade — upon recognition of Stage C HF, even when symptoms are mild.",
            citations: [
              "Heidenreich PA, et al. 2022 AHA/ACC/HFSA Guideline for the Management of Heart Failure. Circulation. 2022;145(18):e895–e1032",
            ],
          },
        ],
        followUps: [
          {
            question: "What treatment should I start?",
            intent: "treatment_plan",
          },
          {
            question: "What's her cardiac risk profile?",
            intent: "risk_assessment",
          },
        ],
      },
    },

    // ── Interaction 3 — "The Action Plan" ─────────────────────────────────
    {
      userMessage: "What treatment should I start?",
      agentResponse: {
        reasoningText:
          "Reviewing Margaret's current regimen against heart failure GDMT recommendations. She's on lisinopril 10 mg — an ACE inhibitor, which is appropriate but under-dosed for HF (target 20-40 mg). She's not on a beta-blocker — needs one. She has T2DM and likely HFpEF or early HFrEF — SGLT2 inhibitors have robust evidence in both. Checking for contraindications: BP runs 130-140s systolic, HR 78 — room for beta-blocker. eGFR 62 — adequate for SGLT2i. No documented hyperkalemia. Need an echocardiogram to classify HF subtype and quantify EF before full optimization, but initial GDMT can and should start now.",
        reasoningDurationMs: 7800,
        narrative:
          "Here's a guideline-directed plan to initiate today and refine after imaging:\n\n**1. Optimize ACE inhibitor** — Uptitrate lisinopril from 10 mg to 20 mg daily (target 20–40 mg for HF). Monitor potassium and creatinine in 1–2 weeks.\n\n**2. Start beta-blocker** — Initiate carvedilol 3.125 mg BID. Low starting dose with gradual uptitration. Her resting HR of 78 and systolic BP in the 130s provide a comfortable margin.\n\n**3. Consider SGLT2 inhibitor** — Empagliflozin 10 mg daily. Strong evidence for heart failure outcomes (EMPEROR-Preserved, DELIVER trials) *and* glycemic benefit given her T2DM — dual indication.\n\n**4. Order echocardiogram** — Essential to classify HF subtype (HFrEF vs HFpEF) and guide further optimization. If EF ≤ 40%, add mineralocorticoid receptor antagonist.\n\n**5. Close follow-up** — Schedule 2-week recheck with daily home weights. Instruct Margaret to call if weight increases > 2 lbs/day or > 5 lbs/week.",
        insights: [
          {
            type: "positive",
            title: "Early GDMT initiation reduces HF hospitalization risk by 30–40%",
            content:
              "Landmark trials (PARADIGM-HF, EMPEROR-Preserved, DAPA-HF) demonstrate that early initiation of guideline-directed medical therapy significantly reduces heart failure hospitalization and cardiovascular mortality. The greatest absolute benefit is seen when therapy starts before severe decompensation.",
            citations: [
              "McMurray JJV, et al. Angiotensin–Neprilysin Inhibition versus Enalapril in Heart Failure. N Engl J Med. 2014;371:993–1004",
              "Anker SD, et al. Empagliflozin in Heart Failure with a Preserved Ejection Fraction. N Engl J Med. 2021;385:1451–1461",
            ],
          },
          {
            type: "info",
            title: "Empagliflozin — dual cardiac and renal benefit",
            content:
              "For Margaret, empagliflozin addresses two problems with one medication: SGLT2 inhibitors improve heart failure outcomes independent of diabetes status, while also providing glycemic control and renal protection (demonstrated eGFR preservation in EMPA-KIDNEY).",
            citations: [
              "The EMPA-KIDNEY Collaborative Group. Empagliflozin in Patients with Chronic Kidney Disease. N Engl J Med. 2023;388:117–127",
            ],
          },
        ],
        followUps: [
          { question: "Draft the referral", intent: "generate_referral" },
          {
            question: "What monitoring do I need?",
            intent: "monitoring_plan",
          },
        ],
      },
    },
  ],
};
