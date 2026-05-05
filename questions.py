DIMENSIONS = [
    "Cognitive Load & Clarity",
    "Learning & Memory Support",
    "Attention & Focus Design",
    "Fear / Reward Balance",
    "Decision-Making Under Pressure",
    "Leadership & Culture",
    "Habit Formation & Consistency",
    "Team Synchrony & Support",
    "Training & Facilitation Quality",
    "System Feedback Loops",
]

ANSWER_LABELS = [
    {"value": 1, "label": "Never"},
    {"value": 2, "label": "Rarely"},
    {"value": 3, "label": "Sometimes"},
    {"value": 4, "label": "Often"},
    {"value": 5, "label": "Consistently"},
]

QUESTIONS = [
    # Dimension 1 — Cognitive Load & Clarity
    {"id": 1,  "dimension": "Cognitive Load & Clarity", "text": "Safety procedures are written in clear, simple language that is easy to understand."},
    {"id": 2,  "dimension": "Cognitive Load & Clarity", "text": "Workers are not expected to remember complex safety rules without written support."},
    {"id": 3,  "dimension": "Cognitive Load & Clarity", "text": "Safety signage and checklists are available at the point of need."},
    {"id": 4,  "dimension": "Cognitive Load & Clarity", "text": "Roles and responsibilities for safety tasks are clearly defined."},
    {"id": 5,  "dimension": "Cognitive Load & Clarity", "text": "Workers rarely feel overwhelmed by the volume of safety information they must retain."},

    # Dimension 2 — Learning & Memory Support
    {"id": 6,  "dimension": "Learning & Memory Support", "text": "Safety training is repeated or reinforced at regular intervals, not just during induction."},
    {"id": 7,  "dimension": "Learning & Memory Support", "text": "Key safety messages are communicated in multiple formats (visual, verbal, written)."},
    {"id": 8,  "dimension": "Learning & Memory Support", "text": "Workers can easily access safety information when they need a refresher."},
    {"id": 9,  "dimension": "Learning & Memory Support", "text": "Lessons from past incidents are shared with the team in a useful way."},
    {"id": 10, "dimension": "Learning & Memory Support", "text": "New workers are given adequate time to learn safety practices before working unsupervised."},

    # Dimension 3 — Attention & Focus Design
    {"id": 11, "dimension": "Attention & Focus Design", "text": "The workplace is designed to minimise distractions in high-risk areas."},
    {"id": 12, "dimension": "Attention & Focus Design", "text": "Workers are not regularly interrupted during safety-critical tasks."},
    {"id": 13, "dimension": "Attention & Focus Design", "text": "Fatigue management practices are in place and followed."},
    {"id": 14, "dimension": "Attention & Focus Design", "text": "Safety-critical information is visually distinct and easy to notice."},
    {"id": 15, "dimension": "Attention & Focus Design", "text": "Shift handovers include a clear safety briefing to maintain situational awareness."},

    # Dimension 4 — Fear / Reward Balance
    {"id": 16, "dimension": "Fear / Reward Balance", "text": "Workers feel safe to report safety concerns without fear of blame or punishment."},
    {"id": 17, "dimension": "Fear / Reward Balance", "text": "Near-misses and errors are treated as learning opportunities, not failures."},
    {"id": 18, "dimension": "Fear / Reward Balance", "text": "Positive safety behaviours are recognised and acknowledged."},
    {"id": 19, "dimension": "Fear / Reward Balance", "text": "Workers are not pressured to cut corners to meet productivity targets."},
    {"id": 20, "dimension": "Fear / Reward Balance", "text": "The organisation responds to safety concerns promptly and without blame."},

    # Dimension 5 — Decision-Making Under Pressure
    {"id": 21, "dimension": "Decision-Making Under Pressure", "text": "Workers have clear authority to stop work if they believe it is unsafe."},
    {"id": 22, "dimension": "Decision-Making Under Pressure", "text": "Decision-making frameworks for high-risk situations are well understood by workers."},
    {"id": 23, "dimension": "Decision-Making Under Pressure", "text": "Workers feel confident making safety decisions without needing supervisor approval every time."},
    {"id": 24, "dimension": "Decision-Making Under Pressure", "text": "Time pressure rarely compromises the quality of safety decisions."},
    {"id": 25, "dimension": "Decision-Making Under Pressure", "text": "Workers know what to do when they encounter an unexpected hazard."},

    # Dimension 6 — Leadership & Culture
    {"id": 26, "dimension": "Leadership & Culture", "text": "Leaders visibly demonstrate safe behaviours in their daily actions."},
    {"id": 27, "dimension": "Leadership & Culture", "text": "Safety is consistently treated as a genuine priority, not just a compliance requirement."},
    {"id": 28, "dimension": "Leadership & Culture", "text": "Leaders listen to workers' safety concerns and follow up on them."},
    {"id": 29, "dimension": "Leadership & Culture", "text": "The organisation's safety values are clear and lived day-to-day."},
    {"id": 30, "dimension": "Leadership & Culture", "text": "Workers trust that management genuinely cares about their wellbeing."},

    # Dimension 7 — Habit Formation & Consistency
    {"id": 31, "dimension": "Habit Formation & Consistency", "text": "Safe behaviours are consistent across the team, not dependent on individual attitudes."},
    {"id": 32, "dimension": "Habit Formation & Consistency", "text": "Safety procedures are followed even when no one is watching."},
    {"id": 33, "dimension": "Habit Formation & Consistency", "text": "Workers have developed strong safety habits through repetition and practice."},
    {"id": 34, "dimension": "Habit Formation & Consistency", "text": "Safe practices are embedded into daily routines rather than treated as extra steps."},
    {"id": 35, "dimension": "Habit Formation & Consistency", "text": "Inconsistent safety behaviour is addressed promptly by peers or supervisors."},

    # Dimension 8 — Team Synchrony & Support
    {"id": 36, "dimension": "Team Synchrony & Support", "text": "Team members look out for each other's safety on the job."},
    {"id": 37, "dimension": "Team Synchrony & Support", "text": "Workers communicate effectively about safety during joint tasks."},
    {"id": 38, "dimension": "Team Synchrony & Support", "text": "Safety responsibilities are shared across the team, not left to one person."},
    {"id": 39, "dimension": "Team Synchrony & Support", "text": "Workers feel comfortable speaking up if they notice a colleague doing something unsafe."},
    {"id": 40, "dimension": "Team Synchrony & Support", "text": "The team debriefs after near-misses or safety incidents together."},

    # Dimension 9 — Training & Facilitation Quality
    {"id": 41, "dimension": "Training & Facilitation Quality", "text": "Safety training is engaging and relevant to the actual work being done."},
    {"id": 42, "dimension": "Training & Facilitation Quality", "text": "Training is practical and includes hands-on practice, not just theory."},
    {"id": 43, "dimension": "Training & Facilitation Quality", "text": "Workers feel the training they receive genuinely prepares them for real situations."},
    {"id": 44, "dimension": "Training & Facilitation Quality", "text": "Training is updated when procedures, equipment, or risks change."},
    {"id": 45, "dimension": "Training & Facilitation Quality", "text": "Trainers and facilitators are skilled at explaining safety concepts clearly."},

    # Dimension 10 — System Feedback Loops
    {"id": 46, "dimension": "System Feedback Loops", "text": "Workers receive feedback when they report a hazard or near-miss."},
    {"id": 47, "dimension": "System Feedback Loops", "text": "Safety data and incident trends are shared with the team regularly."},
    {"id": 48, "dimension": "System Feedback Loops", "text": "The organisation tracks whether safety improvements are actually working."},
    {"id": 49, "dimension": "System Feedback Loops", "text": "Workers can see that their safety input leads to real changes."},
    {"id": 50, "dimension": "System Feedback Loops", "text": "The safety system is regularly reviewed and improved based on what is happening on the ground."},
]

OPEN_TEXT_QUESTIONS = [
    "What is the biggest safety challenge your organisation faces right now?",
    "Describe a recent situation where safety was handled well. What made it work?",
    "What is one thing you would change to make your workplace safer?",
]

DEMOGRAPHICS = [
    {
        "id": "role",
        "label": "Your role",
        "options": ["Worker / Operator", "Supervisor / Team Leader", "Manager", "Executive / Director", "Safety Professional", "Other"]
    },
    {
        "id": "tenure",
        "label": "How long have you worked here?",
        "options": ["Less than 6 months", "6-12 months", "1-3 years", "3-5 years", "More than 5 years"]
    },
    {
        "id": "area",
        "label": "Which area do you work in?",
        "options": ["Operations", "Maintenance", "Administration", "Logistics", "Other"]
    },
]

 