import type { DemoScenario } from "../demo-scenarios";

export const qtProlongationScenario: DemoScenario = {
  id: "qt-prolongation",
  title: "QT Prolongation",
  subtitle: "Time Bomb",
  patient: "Dorothy Williams, 74F",
  interactions: [
    // Interaction 1 — Chart Review
    {
      userMessage:
        "Pull up Dorothy Williams — urgent care sent her records from yesterday",
      agentResponse: {
        reasoningText: `Scanning medication list for Dorothy Williams, 74F...

**Active medications**: diltiazem 240mg daily (AFib rate control), citalopram 20mg daily (depression), omeprazole 20mg daily (GERD).

**New prescription**: azithromycin 500mg day 1, then 250mg days 2–5 (Z-pak) — prescribed yesterday at urgent care for acute bronchitis.

Checking drug interaction databases... azithromycin is a known QT-prolonging agent. Cross-referencing with current medication list:
- **Citalopram**: FDA black box warning for dose-dependent QT prolongation
- **Diltiazem**: CYP3A4 inhibitor — will increase azithromycin serum levels by reducing hepatic clearance
- **Azithromycin**: Independent QT prolongation risk, now with elevated levels due to CYP3A4 interaction

Pulling recent labs... K+ 3.3 mEq/L (low normal 3.5), Mg 1.7 mg/dL (low normal 1.8). Both below threshold — hypokalemia and hypomagnesemia independently prolong QT interval.

This is a multi-hit QT prolongation scenario. Flagging immediately.`,
        reasoningDurationMs: 7800,
        narrative: `Dorothy Williams is a **74-year-old woman** with atrial fibrillation, GERD, and depression. She visited urgent care yesterday for acute bronchitis and was prescribed **azithromycin (Z-pak)**.

I've identified a **dangerous drug interaction** that needs immediate attention. Her current medications include **citalopram** (which carries an FDA black box warning for QT prolongation) and **diltiazem** (a CYP3A4 inhibitor that will raise azithromycin blood levels). Adding azithromycin — itself a QT-prolonging drug — creates a triple-threat scenario.

Making matters worse, her most recent labs show **potassium at 3.3 mEq/L** and **magnesium at 1.7 mg/dL**, both below normal. Low electrolytes independently destabilize cardiac repolarization and amplify drug-induced QT prolongation.`,
        insights: [
          {
            type: "critical",
            title: "Multi-Drug QT Prolongation Risk",
            content:
              "Dangerous combination: azithromycin + citalopram + diltiazem (CYP3A4 inhibitor boosting azithromycin levels). Three concurrent QT-prolonging factors identified.",
            citations: [
              "CredibleMeds QT Drug List — azithromycin: Known Risk",
              "FDA Safety Communication: Citalopram dose-dependent QT prolongation (2012)",
              "Flockhart Drug Interactions — diltiazem moderate CYP3A4 inhibitor",
            ],
          },
          {
            type: "warning",
            title: "Electrolyte Abnormalities Amplify QT Risk",
            content:
              "K+ 3.3 mEq/L (ref: 3.5–5.0) and Mg 1.7 mg/dL (ref: 1.8–2.4). Hypokalemia and hypomagnesemia reduce the repolarization reserve, lowering the threshold for drug-induced arrhythmia.",
            citations: [
              "Roden DM. Drug-Induced Prolongation of the QT Interval. N Engl J Med. 2004;350(10):1013–22",
            ],
          },
        ],
        followUps: [
          { question: "How serious is this?", intent: "risk_quantification" },
          {
            question: "What should I do right now?",
            intent: "intervention_plan",
          },
        ],
      },
    },

    // Interaction 2 — Risk Quantification
    {
      userMessage: "How serious is this?",
      agentResponse: {
        reasoningText: `Quantifying torsades de pointes (TdP) risk using the Tisdale Risk Score framework and known risk factor analysis...

**Patient-level risk factors:**
1. **Female sex** — Women have longer baseline QTc (~20ms longer than men) and 2–3× higher TdP incidence
2. **Age >65** — Reduced repolarization reserve with aging
3. **Heart disease (AFib)** — Structural cardiac disease is an independent risk factor
4. **Hypokalemia (K+ 3.3)** — Reduces IKr channel function, directly prolongs QT
5. **Hypomagnesemia (Mg 1.7)** — Impairs K+ channel recovery

**Drug-level risk factors:**
6. **Citalopram** — Known Risk category (CredibleMeds), dose-dependent IKr blockade
7. **Azithromycin** — Known Risk category, linked to cardiovascular death in observational studies (Ray et al., NEJM 2012)
8. **Diltiazem as CYP3A4 inhibitor** — Increases azithromycin exposure, magnifying its QT effect

**Prior ECG data:** Last ECG 6 months ago showed QTc 438ms. With a female upper limit of 460ms, she was already at the 95th percentile before adding azithromycin. Adding the current drug combination and electrolyte derangement could push QTc well above 500ms — the danger zone for TdP.

**Tisdale Score estimate:** ≥11 points (high risk). This score predicts >20% incidence of QT prolongation requiring intervention in hospitalized patients.

This combination of 5+ concurrent risk factors places her in the highest risk tier for torsades de pointes.`,
        reasoningDurationMs: 9200,
        narrative: `This is a **medical emergency that needs to be addressed today**.

Dorothy has **5+ concurrent risk factors** for torsades de pointes (TdP), a potentially fatal ventricular arrhythmia:

**Patient factors**: Female sex (2–3× higher TdP risk than males), age >65, underlying atrial fibrillation, hypokalemia (K+ 3.3), and hypomagnesemia (Mg 1.7).

**Drug factors**: Three QT-prolonging agents acting simultaneously, with diltiazem inhibiting CYP3A4 and **boosting azithromycin blood levels** beyond what the prescriber intended.

Her last ECG showed a **QTc of 438ms** — already at the 95th percentile for women. The current drug-electrolyte combination could push her QTc above 500ms, where TdP risk rises exponentially. Each additional 10ms of QTc prolongation increases arrhythmia risk by **5–7%** — and she's facing contributions from multiple sources simultaneously.

The urgent care physician likely checked for azithromycin allergies but would not have had access to her complete medication list, recent labs, or prior ECG. This is exactly the kind of fragmented-care scenario where dangerous interactions slip through.`,
        insights: [
          {
            type: "critical",
            title: "High Risk for Torsades de Pointes — Act Today",
            content:
              "5+ concurrent risk factors for TdP: female sex, age >65, cardiac disease, 3 QT-prolonging drugs, CYP3A4 interaction, hypokalemia, hypomagnesemia. Baseline QTc already 438ms (95th percentile for women). Estimated Tisdale Score ≥11 (high risk).",
            citations: [
              "Tisdale JE, et al. Development and validation of a risk score to predict QT interval prolongation in hospitalized patients. Circ Cardiovasc Qual Outcomes. 2013;6(4):479–87",
              "Drew BJ, et al. Prevention of torsade de pointes in hospital settings. Circulation. 2010;121(8):1047–60",
            ],
          },
          {
            type: "info",
            title: "QTc Prolongation Risk Is Exponential",
            content:
              "Each 10ms increase in QTc above 460ms confers a 5–7% exponential increase in TdP risk. A QTc >500ms is considered the danger threshold requiring immediate intervention.",
            citations: [
              "Roden DM. Drug-Induced Prolongation of the QT Interval. N Engl J Med. 2004;350(10):1013–22",
            ],
          },
        ],
        followUps: [
          {
            question: "What's the safe alternative?",
            intent: "antibiotic_substitution",
          },
          {
            question: "Should I get a stat ECG?",
            intent: "diagnostic_workup",
          },
        ],
      },
    },

    // Interaction 3 — Intervention
    {
      userMessage: "What's the safe alternative?",
      agentResponse: {
        reasoningText: `Reviewing antibiotic alternatives for acute bronchitis without QT prolongation risk...

**Why azithromycin was chosen (and why it's wrong here):**
- Azithromycin is first-line for community-acquired respiratory infections due to convenience (5-day course, once daily)
- However, it's contraindicated in patients with multiple QT risk factors

**Safe alternatives:**
- **Amoxicillin-clavulanate (Augmentin)** — No QT prolongation risk, excellent coverage for typical bronchitis pathogens (H. influenzae, M. catarrhalis, S. pneumoniae). 875/125mg BID × 7 days.
- Doxycycline — Also QT-safe, but may interact with omeprazole absorption
- Amoxicillin alone — Narrower spectrum, reasonable if no beta-lactamase concerns

**Recommended: Amoxicillin-clavulanate** — broadest coverage with zero QT risk.

**Immediate actions needed:**
1. Discontinue azithromycin — call patient directly
2. Switch to amoxicillin-clavulanate 875/125mg BID × 7 days
3. Order stat ECG — need current QTc to assess whether damage has already occurred (she may have taken 1–2 doses already)
4. Order stat BMP — recheck K+ and obtain current electrolytes
5. Replete K+ to >4.0 mEq/L and Mg to >2.0 mg/dL (oral supplementation if ECG is reassuring, IV if QTc >500ms)
6. Flag chart for QT-prolonging drug avoidance — permanent medication alert

**Timing is critical:** Azithromycin's QT-prolongation risk is highest in the first 5 days of therapy, with peak risk in days 1–3. She may have already taken her loading dose.`,
        reasoningDurationMs: 8500,
        narrative: `Here's the action plan — **contact Dorothy today**, ideally within the next few hours:

**1. Stop azithromycin immediately.** Call her directly and instruct her to stop the Z-pak. Azithromycin's QT risk peaks in the first 1–3 days, and she may have already taken the loading dose.

**2. Switch to amoxicillin-clavulanate** (875/125mg twice daily for 7 days). This covers all typical bronchitis pathogens — *H. influenzae*, *M. catarrhalis*, *S. pneumoniae* — with **zero QT prolongation risk**. It's equally effective for her indication.

**3. Order a stat ECG** to assess her current QTc interval. If she's already taken azithromycin doses, we need to know where her QTc stands right now. A QTc >500ms would warrant urgent electrolyte correction and monitoring.

**4. Order a stat basic metabolic panel** and replete electrolytes aggressively:
- **Potassium target: >4.0 mEq/L** (oral KCl 40 mEq if ECG reassuring)
- **Magnesium target: >2.0 mg/dL** (oral Mg oxide 400mg BID)

**5. Flag her chart** for QT-prolonging drug avoidance. Add a permanent medication alert so future prescribers — including urgent care and ER physicians — are warned before adding any QT-risk medications.`,
        insights: [
          {
            type: "positive",
            title: "Safe Antibiotic Alternative Available",
            content:
              "Amoxicillin-clavulanate 875/125mg BID × 7 days provides equivalent bronchitis coverage with no QT prolongation risk. No dose adjustment needed for her age or current medications.",
            citations: [
              "Mandell LA, et al. IDSA/ATS Consensus Guidelines on Management of Community-Acquired Pneumonia. Clin Infect Dis. 2007;44(Suppl 2):S27–72",
            ],
          },
          {
            type: "warning",
            title: "Contact Patient Today — Peak Risk Window",
            content:
              "Azithromycin QT-prolongation risk is highest in the first 5 days of use, with peak cardiovascular event risk in days 1–3. If she has already taken the 500mg loading dose, she is currently in the highest-risk period.",
            citations: [
              "Ray WA, et al. Azithromycin and the Risk of Cardiovascular Death. N Engl J Med. 2012;366(20):1881–90",
            ],
          },
        ],
        followUps: [
          {
            question: "Draft the patient callback script",
            intent: "patient_communication",
          },
          {
            question: "What monitoring does she need this week?",
            intent: "follow_up_plan",
          },
        ],
      },
    },
  ],
};
