"""Traditional gemstone indications from the lords of the 1st (life stone), 5th (benefic stone) and 9th (lucky stone)
houses. Output is data only; wording and cautions live in the content library."""
from ..data.tables import GEMS, SIGN_LORDS


def gemstone_picks(lagna_sign: int) -> list[dict[str, object]]:
    out = []
    for role, house in (("life_stone", 1), ("benefic_stone", 5), ("lucky_stone", 9)):
        planet = SIGN_LORDS[(lagna_sign + house - 1) % 12]
        gem, subs, day, finger, metal, deity, mantra = GEMS[planet]
        out.append({"role": role, "house": house, "planet": planet, "gem": gem, "substitutes": subs, "day": day,
                    "finger": finger, "metal": metal, "deity": deity, "mantra": mantra})
    return out
