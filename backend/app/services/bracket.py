import math
import random
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.tournament import Tournament
from app.models.user import User


def get_round_name(round_number: int, total_rounds: int) -> str:
    """Return a human-readable French round name according to distance from the final."""
    rounds_from_final = total_rounds - round_number
    if rounds_from_final == 0:
        return "Finale"
    if rounds_from_final == 1:
        return "Demi-finales"
    if rounds_from_final == 2:
        return "Quarts de finale"
    if rounds_from_final == 3:
        return "8es de finale"
    if rounds_from_final == 4:
        return "16es de finale"
    return f"Tour {round_number}"


def generate_single_elimination_bracket(
    db: Session,
    tournament: Tournament,
    participant_users: Sequence[User],
) -> list[Match]:
    """Generate a single elimination bracket for the given tournament and participants.

    - The participants are shuffled randomly.
    - If the number of participants N is not a power of 2, the bracket is padded to the
      next power of 2 with BYEs (exempts).
    - In round 1, if a real player faces a BYE (player2 is None), the real player
      is automatically declared winner and advances to round 2.
    - All future rounds' match nodes are created and connected via ``next_match_id``.
    """
    n = len(participant_users)
    if n < 2:
        raise ValueError("At least 2 participants are required to generate a bracket")

    # Determine bracket size (next power of 2 >= n)
    bracket_size = 1 << (n - 1).bit_length()
    total_rounds = int(math.log2(bracket_size))

    # Shuffle participants randomly for a fair random draw
    shuffled_participants = list(participant_users)
    random.shuffle(shuffled_participants)

    # Pad with None for BYEs
    seeds: list[User | None] = list(shuffled_participants) + [None] * (bracket_size - n)

    # Create match placeholders for all rounds
    matches_by_round: list[list[Match]] = []
    matches_in_current_round_count = bracket_size // 2

    for r in range(1, total_rounds + 1):
        round_matches: list[Match] = []
        r_name = get_round_name(r, total_rounds)
        for order in range(matches_in_current_round_count):
            m = Match(
                tournament_id=tournament.id,
                round_number=r,
                round_name=r_name,
                match_order=order,
                status="pending",
            )
            db.add(m)
            round_matches.append(m)
        matches_by_round.append(round_matches)
        matches_in_current_round_count //= 2

    db.flush()

    # Link each match to its next_match_id in the subsequent round
    for r_idx in range(len(matches_by_round) - 1):
        current_matches = matches_by_round[r_idx]
        next_matches = matches_by_round[r_idx + 1]
        for m_idx, current_m in enumerate(current_matches):
            parent_match = next_matches[m_idx // 2]
            current_m.next_match_id = parent_match.id

    # Populate Round 1 pairings
    round1_matches = matches_by_round[0]
    for idx, match in enumerate(round1_matches):
        p1 = seeds[idx * 2]
        p2 = seeds[idx * 2 + 1]

        match.player1_id = p1.id if p1 else None
        match.player2_id = p2.id if p2 else None

        # Handle BYE: if player2 is a BYE (None), player1 auto-qualifies
        if p1 is not None and p2 is None:
            match.winner_id = p1.id
            match.status = "completed"
            if match.next_match_id is not None:
                # Advance p1 to the next round match
                next_m = db.get(Match, match.next_match_id)
                if next_m is not None:
                    if idx % 2 == 0:
                        next_m.player1_id = p1.id
                    else:
                        next_m.player2_id = p1.id

        elif p1 is None and p2 is not None:
            # Symmetrical case if p1 was BYE
            match.winner_id = p2.id
            match.status = "completed"
            if match.next_match_id is not None:
                next_m = db.get(Match, match.next_match_id)
                if next_m is not None:
                    if idx % 2 == 0:
                        next_m.player1_id = p2.id
                    else:
                        next_m.player2_id = p2.id

    db.flush()

    # Return all generated matches ordered by round and order
    all_matches: list[Match] = []
    for r_matches in matches_by_round:
        all_matches.extend(r_matches)

    return all_matches
