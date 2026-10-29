"""Muhurta rule model and loader. A ruleset = common rules + the activity's own rules. Each rule either awards `weight`
points when it passes or `veto`es the slot when it fails. Everything is data (rulesets/*.yaml); nothing here knows an
activity by name."""
from functools import cache, lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from ..data.tables import NAKSHATRAS, SIGNS, YOGA_NAMES

DIR = Path(__file__).parent
KINDS = ("weekday_in", "weekday_not_in", "tithi_in", "tithi_not_in", "nakshatra_in", "nakshatra_not_in",
         "nakshatra_class_in", "nakshatra_class_not_in", "yoga_not_in", "karana_not_in", "month_in", "month_not_in",
         "adhika_not", "sun_sign_not_in", "not_combust", "not_in_window", "in_window", "paksha_in", "tarabala_ok",
         "chandrabala_ok", "dishashoola_ok")
WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
MONTHS = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada", "Ashwin", "Kartik", "Margashirsha",
          "Pausha", "Magha", "Phalguna"]
WINDOWS = ("rahu_kaal", "yamaganda", "gulika_kaal", "abhijit_muhurta")
Kind = Literal[KINDS]  # type: ignore[valid-type]


class Rule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    kind: Kind
    values: tuple[str | int, ...] = ()
    classes: tuple[str, ...] = ()
    planets: tuple[str, ...] = ()
    windows: tuple[str, ...] = ()
    weight: float = 0.0
    veto: bool = False

    @model_validator(mode="after")
    def _check(self) -> "Rule":
        if self.veto == (self.weight > 0):
            raise ValueError(f"rule {self.id}: exactly one of veto / weight>0 is required")
        return self


class RuleSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    activity: str
    version: str
    verify: bool
    sources: tuple[str, ...]
    rules: tuple[Rule, ...]


def _tables() -> dict:
    return yaml.safe_load((DIR / "tables.yaml").read_text(encoding="utf-8"))


def _validate(rs: RuleSet, tables: dict) -> None:
    classes = set(tables["nakshatra_class"])
    for r in rs.rules:
        vals = {str(v) for v in r.values}
        bad: set[str] = set()
        if r.kind.startswith("weekday"):
            bad = vals - set(WEEKDAYS)
        elif r.kind.startswith("nakshatra_class"):
            bad = set(r.classes) - classes
        elif r.kind.startswith("nakshatra"):
            bad = vals - set(NAKSHATRAS)
        elif r.kind == "yoga_not_in":
            bad = vals - set(YOGA_NAMES)
        elif r.kind.startswith("month"):
            bad = vals - set(MONTHS)
        elif r.kind == "sun_sign_not_in":
            bad = vals - set(SIGNS)
        elif r.kind.startswith("tithi"):
            bad = {v for v in vals if not v.isdigit() or not 1 <= int(v) <= 30}
        elif r.kind == "paksha_in":
            bad = vals - {"shukla", "krishna"}
        elif r.kind in ("not_in_window", "in_window"):
            bad = set(r.windows) - set(WINDOWS)
        elif r.kind == "not_combust":
            bad = set(r.planets) - {"Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
        if bad:
            raise ValueError(f"{rs.activity}/{r.id}: unknown names {sorted(bad)}")


@cache
def load(activity: str) -> RuleSet:
    path = DIR / "rulesets" / f"{activity}.yaml"
    if activity.startswith("_") or not path.exists():
        raise ValueError(f"unknown muhurta activity {activity!r}")
    own = yaml.safe_load(path.read_text(encoding="utf-8"))
    common = yaml.safe_load((DIR / "rulesets" / "_common.yaml").read_text(encoding="utf-8"))
    skip = set(own.get("skip_common", []))
    rules = [Rule(**r) for r in common["rules"] if r["id"] not in skip] + [Rule(**r) for r in own["rules"]]
    ids = [r.id for r in rules]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{activity}: duplicate rule ids")
    rs = RuleSet(activity=activity, version=own["version"], verify=bool(own["verify"] or common["verify"]),
                 sources=tuple(common["sources"]) + tuple(own["sources"]), rules=tuple(rules))
    _validate(rs, _tables())
    return rs


def activities() -> list[str]:
    return sorted(p.stem for p in (DIR / "rulesets").glob("*.yaml") if not p.stem.startswith("_"))


@lru_cache(maxsize=1)
def tables() -> dict:
    return _tables()


__all__ = ["KINDS", "MONTHS", "WEEKDAYS", "WINDOWS", "Rule", "RuleSet", "activities", "load", "tables"]
