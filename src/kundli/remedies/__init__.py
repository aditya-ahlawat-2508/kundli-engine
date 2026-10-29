"""Remedy selection (V2 phase 22): which gems, pujas, rudraksha and Sade Sati practices are traditionally associated with a chart.
Selection rules are data (rules.yaml, `verify: true`); all wording is a content-store block."""
from .gems import gemstone_picks
from .selection import DISCLAIMER, holds, matched_rules, planet_facts, rules
from .suggest import gem_suggestion, puja_suggestion, rudraksha_suggestion, sadhesati_remedies

__all__ = ["DISCLAIMER", "gem_suggestion", "gemstone_picks", "holds", "matched_rules", "planet_facts", "puja_suggestion",
           "rudraksha_suggestion", "rules", "sadhesati_remedies"]
