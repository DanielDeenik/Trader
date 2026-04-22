"""Investment-specific engines for Social Arb topology."""

from .sentiment_divergence import SentimentDivergenceCalculator
from .kelly_sizer import KellyCriterionSizer
from .irr_simulator import IRRMOICSim
from .regulatory_moat import RegulatoryMoatScorer
from .cross_domain_amplifier import CrossDomainAmplifier

__all__ = [
    "SentimentDivergenceCalculator",
    "KellyCriterionSizer",
    "IRRMOICSim",
    "RegulatoryMoatScorer",
    "CrossDomainAmplifier",
]
