from questions import DIMENSIONS

def get_risk_band(score: float) -> str:
    if score < 1.80:
        return "Reactive"
    elif score < 2.60:
        return "Exposed"
    elif score < 3.40:
        return "Vulnerable"
    elif score < 4.20:
        return "Strengthening"
    else:
        return "Optimised"

def get_maturity_stage(score: float) -> str:
    if score < 1.80:
        return "Stage 1: Reactive"
    elif score < 2.60:
        return "Stage 2: Dependent"
    elif score < 3.40:
        return "Stage 3: Independent"
    elif score < 4.20:
        return "Stage 4: Interdependent"
    else:
        return "Stage 5: NeuroAdaptive"

def calculate_scores(responses: list) -> dict:
    # Group answers by dimension
    by_dimension = {dim: [] for dim in DIMENSIONS}
    for r in responses:
        if r["dimension"] in by_dimension:
            by_dimension[r["dimension"]].append(r["answer"])

    # Score each dimension
    dimension_scores = []
    for dim in DIMENSIONS:
        answers = by_dimension[dim]
        score = round(sum(answers) / len(answers), 2) if answers else 0
        dimension_scores.append({
            "dimension": dim,
            "score": score,
            "risk_band": get_risk_band(score),
            "maturity_stage": get_maturity_stage(score),
        })

    # Overall score
    overall_score = round(
        sum(d["score"] for d in dimension_scores) / len(dimension_scores), 2
    )

    # Top 3 weakest dimensions
    top_risks = [
        d["dimension"]
        for d in sorted(dimension_scores, key=lambda x: x["score"])[:3]
    ]

    return {
        "dimension_scores": dimension_scores,
        "overall_score": overall_score,
        "risk_band": get_risk_band(overall_score),
        "maturity_stage": get_maturity_stage(overall_score),
        "top_risks": top_risks,
    }