import os
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def generate_report(
    client_name: str,
    org_name: str,
    industry: str,
    overall_score: float,
    maturity_stage: str,
    risk_band: str,
    dimension_scores: list,
    top_risks: list,
) -> str:
    """Generate a full AI report using Gemini API."""

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Build dimension breakdown text
    dimension_text = "\n".join([
        f"  - {d['dimension']}: {d['score']}/5 ({d['risk_band']})"
        for d in dimension_scores
    ])

    top_risks_text = ", ".join(top_risks)

    prompt = f"""
You are a workplace neuroscience and psychological safety expert for CereViva NeuroSafety™.

Generate a professional, detailed NeuroSafety Assessment Report for the following organisation:

CLIENT DETAILS:
- Client Name: {client_name}
- Organisation: {org_name}
- Industry: {industry or 'Not specified'}

ASSESSMENT RESULTS:
- Overall NeuroSafety Score: {overall_score}/5
- Maturity Stage: {maturity_stage}
- Risk Band: {risk_band}

DIMENSION SCORES:
{dimension_text}

TOP 3 RISK AREAS:
{top_risks_text}

Please generate a full report with the following sections:

1. EXECUTIVE SUMMARY
   - Brief overview of findings (2-3 paragraphs)
   - Overall NeuroSafety posture

2. MATURITY STAGE ANALYSIS
   - What this stage means for the organisation
   - Key characteristics observed

3. DIMENSION BREAKDOWN
   - Analysis of each dimension score
   - What each score indicates

4. TOP RISK AREAS
   - Detailed analysis of the 3 highest risk dimensions
   - Specific workplace impacts

5. STRATEGIC RECOMMENDATIONS
   - 5-7 specific, actionable recommendations
   - Prioritised by impact and urgency

6. ROADMAP TO NEXT STAGE
   - Clear steps to progress to the next maturity stage
   - 90-day action plan

7. CONCLUSION
   - Summary and encouragement

Write in a professional but approachable tone. Be specific to the industry where possible.
Format with clear headings and bullet points where appropriate.
"""

    response = model.generate_content(prompt)
    return response.text
