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
    client = genai.Client(api_key=GEMINI_API_KEY)

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
2. MATURITY STAGE ANALYSIS
3. DIMENSION BREAKDOWN
4. TOP RISK AREAS
5. STRATEGIC RECOMMENDATIONS (5-7 actionable items)
6. ROADMAP TO NEXT STAGE (90-day action plan)
7. CONCLUSION

Write in a professional but approachable tone. Be specific to the industry where possible.
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text
