import type { DemoScenario } from "../demo-scenarios";

export const hypoglycemiaScenario: DemoScenario = {
  id: "hypoglycemia",
  title: "Dangerous Improvement",
  subtitle: "Hypoglycemia Cascade",
  patient: "Robert Garcia, 79M",
  interactions: [
    // Interaction 1 — The Deceptive Win
    {
      userMessage:
        "Pull up Robert Garcia's labs — he's on my schedule for diabetes follow-up this afternoon.",
      agentResponse: {
        reasoningText: `Pulling Robert Garcia, 79M, diabetes management data and recent labs...

**HbA1c trend**: 8.2% → 7.4% → 6.8% over past 12 months. That's a significant drop — looks like good news, but let me check his medication profile and risk factors before concluding.

**Active medications**:
- Metformin 1000mg BID
- Glipizide 10mg BID (sulfonylurea — high hypoglycemia risk)
- Propranolol 80mg BID (non-selective beta-blocker for CAD)
- Aspirin 81mg daily
- Atorvastatin 40mg daily

**Wait — this combination is concerning.** Propranolol is a non-selective beta-blocker. It blocks both β1 and β2 receptors. β2-adrenergic blockade masks the catecholamine-mediated warning signs of hypoglycemia — tachycardia, tremor, anxiety, diaphoresis. Patients on non-selective beta-blockers can drop to dangerously low glucose levels without feeling it.

**ADA Standards of Care 2026**: For older adults (≥65) with multiple comorbidities or established cardiovascular disease, a less stringent HbA1c target of <8.0% is recommended. An HbA1c of 6.8% in a 79-year-old on a sulfonylurea isn't a win — it's a red flag for over-treatment and possible occult hypoglycemia.

Cross-referencing recent encounters...`,
        reasoningDurationMs: 7200,
        narrative: `Robert's A1c dropped from 8.2% to **6.8%** over the past year. That might look like progress, but I'm flagging it as a concern.

At 79 with coronary artery disease, **an HbA1c of 6.8% is too aggressive**. The ADA recommends a target of <8.0% for older adults with established cardiovascular disease — tight control in this population increases hypoglycemia risk without improving outcomes.

More concerning: he's on **glipizide** (a sulfonylurea with high hypoglycemia risk) combined with **propranolol** (a non-selective beta-blocker). Propranolol blocks the body's early warning system for low blood sugar — the racing heart, tremor, and anxiety that normally alert a patient to eat something. Robert could be dropping dangerously low **without feeling it**.

This A1c "improvement" may actually represent recurrent hypoglycemia that's being masked.`,
        insights: [
          {
            type: "warning",
            title: "HbA1c 6.8% May Indicate Over-Treatment",
            content:
              "ADA Standards of Care recommend a less stringent HbA1c target of <8.0% for adults ≥65 with established cardiovascular disease and multiple comorbidities. Tight glycemic control in this population increases hypoglycemia risk without improving cardiovascular outcomes.",
            citations: [
              "ADA Standards of Care 2026 — Chapter 13: Older Adults",
              "ACCORD Trial — Intensive glucose lowering increased mortality in high-risk T2DM patients (NEJM 2008;358:2545–59)",
            ],
          },
          {
            type: "warning",
            title: "Propranolol Masks Hypoglycemia Symptoms",
            content:
              "Non-selective beta-blockers (propranolol) block β2-mediated catecholamine responses to hypoglycemia — tachycardia, tremor, anxiety, and diaphoresis. Patients lose their physiologic early warning system, leading to hypoglycemia unawareness.",
            citations: [
              "Shorr RI, et al. Antihypertensives and the risk of serious hypoglycemia in older persons using insulin or sulfonylureas. JAMA. 1997;278(1):40–43",
            ],
          },
        ],
        followUps: [
          {
            question: "Show me his glucose readings and recent visits",
            intent: "glucose_pattern_review",
          },
          {
            question: "Why is that A1c too low?",
            intent: "geriatric_glycemic_targets",
          },
        ],
      },
    },

    // Interaction 2 — The Hidden Pattern
    {
      userMessage: "Show me his glucose logs and any recent encounters — let's see if he's actually been having hypo episodes.",
      agentResponse: {
        reasoningText: `Pulling glucose logs, encounter records, and renal function for Robert Garcia...

**Home glucose logs (past 30 days):**
- 12 of 28 recorded readings are between 60–70 mg/dL
- 3 readings below 60 mg/dL: 58, 54, 52
- Pattern: lowest readings occur pre-lunch and overnight (2–4 AM)
- Notably few readings above 140 mg/dL — the distribution is left-shifted

**ED encounter — 2 weeks ago:**
- Chief complaint: "Fall at home"
- Triage glucose: 52 mg/dL
- Given orange juice, glucose rose to 98
- Discharged with diagnosis: "Mechanical fall, resolved hypoglycemia"
- **No medication changes recommended at discharge**
- No notification sent to PCP

**Spouse report from last office visit (nurse note):**
- Wife reports patient had "confusion episode" lasting ~20 minutes last month
- Patient was "staring blankly and not making sense"
- Happened while watching TV after skipping afternoon snack
- Wife also reports he "almost ran a red light" two weeks prior — seemed confused
- PCP note: "Consider TIA workup, carotid ultrasound ordered"

**Renal function trend:**
- eGFR 12 months ago: 58 mL/min/1.73m²
- eGFR 6 months ago: 52 mL/min/1.73m²
- eGFR current: 48 mL/min/1.73m²
- Stage 3b CKD, progressive decline

**Connecting the picture:** The ED fall, the confusion episode, the near-miss driving event — these were almost certainly hypoglycemic events, not TIAs. The propranolol masked the typical warning signs, so nobody connected the dots. Meanwhile, declining renal function is reducing clearance of both glipizide and metformin, effectively increasing their potency over time without any dose change.`,
        reasoningDurationMs: 9800,
        narrative: `The pattern here is alarming. Looking across Robert's glucose logs, ED visit, and his wife's observations, a clear picture emerges:

**Glucose logs** show 12 out of 28 readings in the 60–70 mg/dL range, with 3 readings below 60. The lowest readings cluster before lunch and overnight — classic sulfonylurea-driven hypoglycemia.

**Two weeks ago**, Robert went to the ED after a **fall at home**. His triage glucose was **52 mg/dL**. He was given juice, improved, and sent home. No one changed his medications. No one notified you.

His wife has reported a **confusion episode** where he stared blankly and couldn't speak for 20 minutes, and a **near-miss while driving** where he appeared disoriented and nearly ran a red light. Both were attributed to possible TIA — but the timing and presentation fit hypoglycemia far better than cerebrovascular disease.

Making everything worse, his **kidney function is declining** — eGFR has dropped from 58 to 48 over the past year. Both glipizide and metformin are renally cleared. As his kidneys deteriorate, these drugs accumulate to higher effective levels. He's functionally on an escalating dose without anyone prescribing one.`,
        insights: [
          {
            type: "critical",
            title:
              "Recurrent Hypoglycemia with Unawareness",
            content:
              "The ED fall (glucose 52), confusion episode, and near-miss driving event were almost certainly hypoglycemic events — not TIAs. Propranolol-induced hypoglycemia unawareness prevented recognition of the true cause. This pattern represents an immediate safety risk.",
            citations: [
              "Cryer PE. Hypoglycemia, functional brain failure, and brain death. J Clin Invest. 2007;117(4):868–870",
              "Seaquist ER, et al. Hypoglycemia and diabetes: a report of a workgroup of the ADA and the Endocrine Society. Diabetes Care. 2013;36(5):1384–95",
            ],
          },
          {
            type: "warning",
            title: "Declining Renal Function Increases Drug Accumulation",
            content:
              "eGFR trending 58 → 52 → 48 mL/min (Stage 3b CKD). Glipizide's active metabolites and metformin both depend on renal clearance. Declining kidney function effectively increases drug exposure, amplifying hypoglycemia risk without any dose change.",
            citations: [
              "Kidney Disease: Improving Global Outcomes (KDIGO) Diabetes Management in CKD Guideline 2022",
              "FDA Drug Safety Communication: Metformin and eGFR-based dosing recommendations (2016)",
            ],
          },
        ],
        followUps: [
          {
            question: "What changes do I need to make?",
            intent: "medication_adjustment_plan",
          },
          {
            question: "Is he safe to drive?",
            intent: "driving_safety_assessment",
          },
        ],
      },
    },

    // Interaction 3 — Unwinding the Cascade
    {
      userMessage: "I'm stopping the glipizide today. Walk me through the full de-escalation — beta-blocker switch, metformin dose adjustment, and the new A1c target.",
      agentResponse: {
        reasoningText: `Developing a medication adjustment plan to address the three compounding factors: sulfonylurea hypoglycemia, beta-blocker masking, and renal accumulation...

**1. Glipizide (stop):**
- Sulfonylureas are the highest-risk oral hypoglycemic class in elderly patients
- Glipizide's active metabolites accumulate with declining eGFR
- ADA/AGS explicitly recommend avoiding sulfonylureas in adults ≥65 due to hypoglycemia risk
- Alternative: If additional glycemic control needed after stopping, consider a DPP-4 inhibitor (sitagliptin, dose-adjusted for renal function) — minimal hypoglycemia risk

**2. Propranolol → Metoprolol succinate (switch):**
- Metoprolol succinate is β1-selective — does not block β2-mediated hypoglycemia warning signs
- Equivalent cardioprotection for his CAD
- Start metoprolol succinate 50mg daily, titrate as needed
- Taper propranolol over 1–2 weeks (do not abruptly discontinue — rebound hypertension/tachycardia risk)

**3. Metformin (dose reduce):**
- Current: 1000mg BID (2000mg/day)
- FDA guidance: eGFR 30–45 = max 1000mg/day; eGFR 45–60 = consider dose reduction
- At eGFR 48, reduce to 500mg BID (1000mg/day)
- Recheck eGFR in 3 months — if <30, discontinue

**4. HbA1c target (relax):**
- New target: 7.5–8.0%
- Aligns with ADA geriatric guidelines for patients with established CVD, CKD, and history of hypoglycemia
- Prioritize avoidance of hypoglycemia over tight control

**5. Safety measures:**
- Patient and wife education on hypoglycemia recognition (especially neuroglycopenic symptoms — confusion, behavioral changes — since adrenergic symptoms are masked)
- Assess driving safety — recurrent hypoglycemia unawareness is a contraindication to driving in most states
- Consider 2-week CGM to quantify hypoglycemia burden before and after medication changes

**6. Follow-up:**
- Recheck BMP + eGFR in 2 weeks
- Phone check at 1 week for glucose readings
- Office visit in 4 weeks for A1c and med reconciliation`,
        reasoningDurationMs: 10200,
        narrative: `Here's the plan to unwind this cascade — we need to address all three compounding factors simultaneously:

**1. Stop glipizide.** This is the single highest-impact change. Sulfonylureas are the most dangerous oral hypoglycemic in elderly patients, and the ADA/AGS Beers Criteria explicitly recommend avoidance in adults ≥65. With his declining kidney function, the drug is accumulating beyond its intended dose. If he still needs additional glycemic control after stopping, a **DPP-4 inhibitor** (like dose-adjusted sitagliptin) provides glucose lowering with minimal hypoglycemia risk.

**2. Switch propranolol to metoprolol succinate.** Metoprolol is β1-selective — it provides the same cardioprotection for his coronary artery disease but **does not mask hypoglycemia symptoms**. Start metoprolol succinate 50mg daily and taper propranolol over 1–2 weeks to avoid rebound effects.

**3. Reduce metformin to 500mg BID.** At an eGFR of 48, the FDA recommends dose reduction. This halves his metformin exposure while maintaining some glycemic benefit. Recheck eGFR in 3 months — if it drops below 30, metformin must be discontinued entirely.

**4. Relax the HbA1c target to 7.5–8.0%.** At 79 with CAD, CKD, and documented hypoglycemia unawareness, tight control causes more harm than benefit. The goal is **avoiding dangerous lows**, not chasing a lower number.

**5. Educate Robert and his wife** on recognizing neuroglycopenic symptoms — confusion, behavioral changes, difficulty concentrating — since the typical adrenergic warnings (racing heart, shakiness) have been masked. His wife is a critical safety net.

**6. Reassess driving safety.** Recurrent hypoglycemia with unawareness is a contraindication to driving. This is a difficult conversation, but the near-miss red light event makes it urgent.`,
        insights: [
          {
            type: "positive",
            title: "Eliminating Three Compounding Factors",
            content:
              "Stopping glipizide removes the sulfonylurea-driven hypoglycemia. Switching to metoprolol restores the body's hypoglycemia warning system. Reducing metformin accounts for declining renal clearance. Together, these changes address the root cause — not just the symptom.",
            citations: [
              "American Geriatrics Society 2023 Updated AGS Beers Criteria — sulfonylureas listed as potentially inappropriate in older adults",
              "ADA Standards of Care 2026 — Chapter 13: Older Adults, Table 13.1",
            ],
          },
          {
            type: "info",
            title: "Consider CGM to Quantify Hypoglycemia Burden",
            content:
              "A 2-week continuous glucose monitor (CGM) trial before and after medication changes will objectively quantify time below range (<70 mg/dL) and nocturnal hypoglycemia episodes — data that finger-stick logs miss.",
            citations: [
              "Battelino T, et al. Clinical targets for continuous glucose monitoring data interpretation. Diabetes Care. 2019;42(8):1593–1603",
            ],
          },
        ],
        actions: [
          { label: "Discontinue glipizide", type: "order" },
          { label: "Prescribe metoprolol succinate 50mg daily", type: "order" },
          { label: "Reduce metformin to 500mg BID", type: "order" },
          { label: "Order 2-week CGM trial", type: "order" },
          { label: "Flag driving safety review", type: "alert" },
          { label: "Schedule 2-week follow-up", type: "document" },
        ],
        followUps: [
          {
            question: "How do I approach the driving conversation?",
            intent: "patient_communication",
          },
          {
            question: "What monitoring does he need over the next month?",
            intent: "follow_up_plan",
          },
        ],
      },
    },
  ],
};
