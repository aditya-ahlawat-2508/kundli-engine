"""Planetary dignity and relationships (natural, temporal, compound)."""
from .data.tables import ENEMIES, EXALTATION, FRIENDS, MOOLATRIKONA, OWN_SIGNS, SIGN_LORDS


def natural_relation(a: str, b: str) -> str:
    """Natural relation of a toward b: friend | enemy | neutral."""
    if b in FRIENDS[a]:
        return "friend"
    if b in ENEMIES[a]:
        return "enemy"
    return "neutral"


def temporal_relation(sign_a: int, sign_b: int) -> str:
    """b is a temporal friend of a if its sign is 2,3,4,10,11 or 12 from a's sign, else enemy."""
    return "friend" if ((sign_b - sign_a) % 12) + 1 in (2, 3, 4, 10, 11, 12) else "enemy"


def compound_relation(a: str, b: str, sign_a: int, sign_b: int) -> str:
    """Panchadha maitri: great_friend | friend | neutral | enemy | great_enemy."""
    n, t = natural_relation(a, b), temporal_relation(sign_a, sign_b)
    table = {("friend", "friend"): "great_friend", ("neutral", "friend"): "friend",
             ("enemy", "friend"): "neutral", ("friend", "enemy"): "neutral",
             ("neutral", "enemy"): "enemy", ("enemy", "enemy"): "great_enemy"}
    return table[(n, t)]


def dignity(planet: str, sign: int, deg: float, sign_positions: dict[str, int]) -> str:
    """exalted | debilitated | moolatrikona | own | <compound relation with sign lord>.

    `sign_positions` maps planet -> sign index in the chart being judged (used for temporal friendship).
    """
    ex_sign, _ = EXALTATION[planet]
    if sign == ex_sign:
        return "exalted"
    if sign == (ex_sign + 6) % 12:
        return "debilitated"
    mt = MOOLATRIKONA.get(planet)
    if mt and sign == mt[0] and mt[1] <= deg < mt[2]:
        return "moolatrikona"
    if sign in OWN_SIGNS[planet]:
        return "own"
    lord = SIGN_LORDS[sign]
    return compound_relation(planet, lord, sign_positions[planet], sign_positions[lord])
