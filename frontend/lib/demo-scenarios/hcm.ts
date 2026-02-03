import type { DemoScenario } from "../demo-scenarios";

export const hcmScenario: DemoScenario = {
  id: "hcm",
  title: "Hidden HCM",
  subtitle: "Hypertrophic Cardiomyopathy",
  patient: "Tyler Reeves, 17M",
  interactions: [
    // Interaction 1 — Sports Physical
    {
      userMessage:
        "Sports physical for Tyler Reeves, 17, varsity basketball. Pull the family history and any prior cardiac workup before I go in.",
      agentResponse: {
        reasoningText: `Pulling demographics and chart history for Tyler Reeves, 17M...

**Demographics**: 17-year-old male, varsity basketball player, presenting for pre-participation sports physical.

**Past medical history**: No chronic conditions, no prior hospitalizations. Up to date on immunizations. Last visit 14 months ago for ankle sprain (basketball-related).

**Family history** — this is where it gets concerning:
- **Father**: Died at age 42 of "massive heart attack" (per maternal report at intake)
- **Paternal grandfather**: Sudden death in his 50s, circumstances unclear
- **Brother (age 20)**: Referred for "cardiac screening" 2 years ago — **outcome not documented in this chart**

Two first-degree and one second-degree relative with premature cardiac death or cardiac concern. This pattern is highly suggestive of a heritable cardiomyopathy, most commonly hypertrophic cardiomyopathy (HCM).

Checking for prior cardiac workup on Tyler... none found. No ECG, no echocardiogram, no cardiology referral on file.

This patient should NOT receive sports clearance without further evaluation.`,
        reasoningDurationMs: 7200,
        narrative: `Tyler Reeves is a **17-year-old male varsity basketball player** here for a pre-participation sports physical. He has no chronic medical conditions and no prior hospitalizations.

However, his **family history is a major red flag**. His father died at age 42 of a "massive heart attack," and his paternal grandfather died suddenly in his 50s. His older brother was referred for cardiac screening 2 years ago, but the **results are not in Tyler's chart**.

Two first- or second-degree relatives with premature cardiac death, plus a sibling with a known cardiac concern — this pattern strongly suggests an **inherited cardiomyopathy**, most likely hypertrophic cardiomyopathy (HCM). Tyler has never had an ECG or echocardiogram.`,
        insights: [
          {
            type: "warning",
            title: "Premature Cardiac Death in Two Relatives",
            content:
              "Father died at 42 (\"massive heart attack\"), paternal grandfather sudden death in 50s. Brother referred for cardiac screening — results unknown. Pattern consistent with inherited cardiomyopathy. Screen before sports clearance.",
            citations: [
              "Maron BJ, et al. Eligibility and Disqualification Recommendations for Competitive Athletes With Cardiovascular Abnormalities. Circulation. 2015;132(22):e273–80",
              "Gersh BJ, et al. 2011 ACCF/AHA Guideline for the Diagnosis and Treatment of Hypertrophic Cardiomyopathy. Circulation. 2011;124(24):e783–831",
            ],
          },
        ],
        followUps: [
          {
            question: "What should I look for on exam?",
            intent: "physical_exam_guidance",
          },
          {
            question: "What screening does he need?",
            intent: "diagnostic_workup",
          },
        ],
      },
    },

    // Interaction 2 — Exam Findings
    {
      userMessage:
        "I'm hearing a soft systolic murmur with dynamic variation on Valsalva. He also reports exertional lightheadedness during intense drills. Correlate that with the family history.",
      agentResponse: {
        reasoningText: `Correlating exam findings with family history and reported symptoms...

**Physical exam finding**: Soft systolic murmur with positional variation.
- In HCM, the murmur is caused by dynamic left ventricular outflow tract (LVOT) obstruction and/or mitral regurgitation from systolic anterior motion (SAM) of the mitral valve.
- **Louder with Valsalva or standing** (decreased preload → smaller LV cavity → more obstruction)
- **Softer with squatting** (increased preload → larger LV cavity → less obstruction)
- This dynamic behavior is nearly pathognomonic for HCM. Fixed valvular lesions (e.g., aortic stenosis) do NOT change with position.

**Symptom**: Exertional lightheadedness during intense basketball practice.
- In the context of HCM, this could represent:
  1. Dynamic LVOT obstruction causing reduced cardiac output during exertion
  2. Exercise-induced arrhythmia (ventricular tachycardia) — HCM is the #1 substrate for sudden cardiac death in young athletes
  3. Inadequate blood pressure response to exercise

**Risk stratification**: Family history of sudden death + dynamic murmur + exertional symptoms = **high pre-test probability for HCM**. This combination demands urgent evaluation before any further athletic activity.

The previous provider notes from the ankle sprain visit mention he was "healthy, active in basketball" — no cardiac exam documented. The family history was recorded but not flagged for follow-up.`,
        reasoningDurationMs: 8900,
        narrative: `These findings significantly raise concern. The **positional variation in the murmur** is a hallmark of hypertrophic cardiomyopathy — the murmur gets louder with Valsalva or standing (decreased preload worsens the obstruction) and softer with squatting. This dynamic behavior distinguishes HCM from fixed valvular lesions like aortic stenosis.

**Exertional lightheadedness** in this context is alarming. It could indicate dynamic left ventricular outflow tract (LVOT) obstruction reducing cardiac output during high-intensity exercise, or it could be a warning sign of exercise-induced ventricular arrhythmia — the mechanism behind sudden cardiac death in HCM.

Taken together — a family history of two premature cardiac deaths, a sibling with a cardiac concern, a dynamic systolic murmur, and exertional presyncope — Tyler has a **high pre-test probability for HCM**. He should not return to basketball until a full workup is complete.`,
        insights: [
          {
            type: "critical",
            title: "Do NOT Clear for Sports — High Suspicion for HCM",
            content:
              "Dynamic systolic murmur (louder with Valsalva/standing, softer with squatting) + exertional lightheadedness + family history of premature cardiac death = high pre-test probability for hypertrophic cardiomyopathy. Withhold sports clearance until workup complete.",
            citations: [
              "Maron BJ, et al. Hypertrophic Cardiomyopathy. Lancet. 2013;381(9862):242–55",
              "Maron BJ. Sudden Death in Young Athletes. N Engl J Med. 2003;349(11):1064–75",
            ],
          },
          {
            type: "info",
            title: "HCM — Leading Cause of Sudden Death in Young Athletes",
            content:
              "Hypertrophic cardiomyopathy accounts for approximately 40% of sudden cardiac deaths in athletes under 35. It is an autosomal dominant genetic condition, explaining the family pattern seen here.",
            citations: [
              "Maron BJ, et al. Sudden Deaths in Young Competitive Athletes: Analysis of 1866 Deaths in the US, 1980–2006. Circulation. 2009;119(8):1085–92",
            ],
          },
        ],
        followUps: [
          {
            question: "What workup do I order?",
            intent: "diagnostic_workup",
          },
          {
            question: "Should I pull him from practice now?",
            intent: "activity_restriction",
          },
        ],
      },
    },

    // Interaction 3 — Protecting the Patient
    {
      userMessage: "I'm withholding clearance. Walk me through the full workup and the referral pathway — I want cardiology looped in this week.",
      agentResponse: {
        reasoningText: `Reviewing screening and diagnostic guidelines for suspected HCM in a young athlete...

**Immediate diagnostic workup:**

1. **12-lead ECG** — Abnormal in ~97% of HCM patients. Common findings: LVH voltage criteria, deep T-wave inversions (especially in lateral leads), pathological Q waves, ST-segment abnormalities. A normal ECG substantially lowers the probability but does not exclude HCM.

2. **Transthoracic echocardiogram (TTE)** — Gold standard for diagnosis. Looking for:
   - Asymmetric septal hypertrophy (≥15mm in adults, ≥z-score 2 in adolescents)
   - Systolic anterior motion (SAM) of the mitral valve
   - LVOT gradient at rest and with provocation (Valsalva)
   - Diastolic dysfunction

3. **Urgent cardiology referral** — Pediatric or sports cardiology preferred given his age. They can determine if cardiac MRI or genetic testing is warranted.

**Additional critical steps:**

4. **Withhold sports clearance** — Per AHA/ACC guidelines, athletes with suspected HCM must be restricted from competitive sports until evaluation is complete and risk stratification performed.

5. **Obtain brother's screening results** — Contact the brother's cardiologist (with consent) or ask the family directly. If the brother was diagnosed with HCM, Tyler's pre-test probability approaches 50% (autosomal dominant, first-degree relative).

6. **Offer family genetic counseling** — If HCM is confirmed in Tyler or his brother, all first-degree relatives should be screened. Genetic testing can identify the specific sarcomere mutation and guide cascade screening.`,
        reasoningDurationMs: 8100,
        narrative: `Here's the workup plan:

**1. 12-lead ECG** — This is abnormal in approximately 97% of HCM patients. Look for left ventricular hypertrophy, deep T-wave inversions in lateral leads, pathological Q waves, and ST-segment changes. A normal ECG makes HCM less likely but does not rule it out.

**2. Transthoracic echocardiogram** — The gold standard for diagnosis. This will assess for asymmetric septal hypertrophy, systolic anterior motion of the mitral valve, and LVOT obstruction at rest and with Valsalva provocation.

**3. Urgent cardiology referral** — Ideally pediatric or sports cardiology given Tyler's age. They will determine whether cardiac MRI or genetic testing is needed based on initial findings.

**4. Withhold sports clearance** pending results. Per AHA/ACC guidelines, athletes with suspected cardiomyopathy must be restricted from competitive sports until evaluation and risk stratification are complete.

**5. Obtain the brother's screening results.** If his brother was diagnosed with HCM, Tyler's probability of carrying the same mutation is roughly 50% — it's autosomal dominant. Contact the family or the brother's cardiologist with appropriate consent.

**6. Offer family genetic counseling.** If HCM is confirmed, all first-degree relatives should undergo screening with ECG and echocardiogram. Genetic testing can identify the specific sarcomere gene mutation and enable targeted cascade screening.`,
        insights: [
          {
            type: "positive",
            title: "Early Diagnosis Saves Lives",
            content:
              "If HCM is confirmed, early diagnosis enables ICD evaluation for sudden death prevention, evidence-based activity modification, and family cascade screening — dramatically reducing the risk of sudden cardiac death in Tyler and his relatives.",
            citations: [
              "Maron BJ, et al. Assessment of the 12-Lead ECG as a Screening Test for Detection of Cardiovascular Disease in Healthy General Populations of Young People. Circulation. 2014;130(16):1303–14",
            ],
          },
          {
            type: "info",
            title: "Screen All First-Degree Relatives",
            content:
              "HCM is autosomal dominant with variable expressivity. All first-degree relatives of confirmed HCM patients should undergo screening with ECG + echocardiogram. Genetic testing identifies the specific sarcomere mutation and enables targeted cascade screening of the extended family.",
            citations: [
              "Ommen SR, et al. 2020 AHA/ACC Guideline for the Diagnosis and Treatment of Patients With Hypertrophic Cardiomyopathy. Circulation. 2020;142(25):e558–631",
            ],
          },
        ],
        actions: [
          { label: "Order 12-lead ECG", type: "order" },
          { label: "Order transthoracic echocardiogram", type: "order" },
          { label: "Refer to pediatric cardiology", type: "refer" },
          { label: "Withhold sports clearance", type: "alert" },
          { label: "Request brother's cardiac records", type: "document" },
        ],
        followUps: [
          {
            question: "Draft the cardiology referral",
            intent: "referral_creation",
          },
          {
            question: "How do I explain this to his family?",
            intent: "patient_communication",
          },
        ],
      },
    },
  ],
};
