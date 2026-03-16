from typing import Tuple

DIFFICULTY_LEVELS = ["easy", "medium", "hard"]
STREAK_THRESHOLD  = 3   # consecutive answers needed to shift level


def update_difficulty(
    level: int,
    streak: int,
    is_correct: bool,
    threshold: int = STREAK_THRESHOLD,
) -> Tuple[int, int, bool]:
    """
    Core adaptive algorithm.

    Args:
        level:      current difficulty index (0=easy, 1=medium, 2=hard)
        streak:     current streak counter (+N = correct run, -N = wrong run)
        is_correct: whether the student just answered correctly
        threshold:  consecutive answers needed before shifting difficulty

    Returns:
        (new_level, new_streak, shifted) — shifted=True if level changed
    """
    shifted = False

    if is_correct:
        # Reset streak direction if it was negative
        new_streak = 1 if streak < 0 else streak + 1
        if new_streak >= threshold and level < len(DIFFICULTY_LEVELS) - 1:
            level += 1
            new_streak = 0
            shifted = True
    else:
        # Reset streak direction if it was positive
        new_streak = -1 if streak > 0 else streak - 1
        if abs(new_streak) >= threshold and level > 0:
            level -= 1
            new_streak = 0
            shifted = True

    return level, new_streak, shifted


def difficulty_name(level: int) -> str:
    return DIFFICULTY_LEVELS[max(0, min(level, len(DIFFICULTY_LEVELS) - 1))]


def build_event_message(
    is_correct: bool,
    shifted: bool,
    level: int,
    streak: int,
    threshold: int = STREAK_THRESHOLD,
) -> str:
    lname = difficulty_name(level)
    if shifted:
        direction = "increased" if is_correct else "decreased"
        return f"Difficulty {direction} to {lname}"
    if is_correct:
        remaining = threshold - streak
        if remaining <= 0:
            return f"Already at maximum difficulty ({lname})"
        return f"Correct — {remaining} more in a row to advance"
    else:
        remaining = threshold - abs(streak)
        if remaining <= 0:
            return f"Already at minimum difficulty ({lname})"
        return f"Wrong — {remaining} more in a row to drop difficulty"
