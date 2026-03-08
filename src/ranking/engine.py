from src.ranking.feedback import adjust_score_for_feedback
from src.ranking.rules import compute_rule_score
from src.schemas.event import NormalizedEvent
from src.schemas.user import UserProfileSchema


class RankingEngine:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def rank_events(
        self,
        events: list[NormalizedEvent],
        profile: UserProfileSchema,
        feedback_history: list[dict] | None = None,
    ) -> list[tuple[NormalizedEvent, float]]:
        feedback_history = feedback_history or []
        scored: list[tuple[NormalizedEvent, float]] = []

        for event in events:
            rule_score = compute_rule_score(event, profile)
            fb_adjusted = adjust_score_for_feedback(rule_score, event, feedback_history)

            # LLM family_score from synthesis layer (set during enrichment)
            llm_score = event.family_score if event.family_score is not None else 0.5

            final = 0.5 * rule_score + 0.2 * fb_adjusted + 0.3 * llm_score
            scored.append((event, round(final, 4)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
