"""
Regulatory Moat Scorer

Assesses moat strength based on regulatory/ESG compliance factors.

CSRD (Corporate Sustainability Reporting Directive) and ESG regulations
create de facto moats: companies that comply early gain competitive advantage
through brand trust, lower cost of capital, and institutional investment access.

Moat factors:
    - ESG compliance tier (best-in-class, compliant, lagging, non-compliant)
    - Carbon intensity (lower = stronger moat in decarbonization theme)
    - Patent portfolio (stronger = better moat)
    - Regulatory burden (high burden = fewer competitors = better moat)
    - Institutional ownership % (higher = more validated moat)
"""

from dataclasses import dataclass
from social_arb.core.protocols import (
    DomainVulnerability, VulnerabilityScanResult
)


@dataclass
class RegulatoryMoatScorer:
    """Assess moat strength via regulatory/ESG lens."""

    @property
    def domain_name(self) -> str:
        return "regulatory_moat"

    def scan(self, target: str, data: dict) -> VulnerabilityScanResult:
        """
        Score regulatory moat for a company/investment.

        Args:
            target: Company name or ticker
            data: {
                "esg_score": int,  # 1-100 (ESG provider score)
                "carbon_intensity": float,  # kg CO2 per $ revenue
                "patent_count": int,  # Number of patents in relevant domain
                "regulatory_burden_score": int,  # 1-10 (how much compliance required)
                "institutional_ownership_pct": float,  # 0-100
                "csrd_compliant": bool,  # CSRD compliance status
                "carbon_reporting": bool,  # Carbon disclosure compliance
            }

        Returns:
            VulnerabilityScanResult with moat score and exploitability.
        """
        esg_score = min(100, data.get("esg_score", 50))
        carbon = data.get("carbon_intensity", 10.0)
        patents = data.get("patent_count", 0)
        regulatory_burden = data.get("regulatory_burden_score", 5)
        institutional_own = min(100, data.get("institutional_ownership_pct", 30))
        csrd_compliant = data.get("csrd_compliant", False)
        carbon_reporting = data.get("carbon_reporting", False)

        # Components of moat score (each 0-10)
        esg_component = (esg_score / 100) * 10  # Higher ESG = stronger moat
        carbon_component = max(0, 10 - (carbon / 10))  # Lower carbon = stronger moat
        patent_component = min(10, (patents / 50) * 10)  # More patents = stronger moat
        regulatory_component = min(10, (regulatory_burden / 10) * 10)  # More regulation = harder for competitors
        institutional_component = (institutional_own / 100) * 10  # Institutional validation

        # Bonus for CSRD/carbon reporting compliance (demonstrates credibility)
        compliance_bonus = 1.0
        if csrd_compliant:
            compliance_bonus += 1.0
        if carbon_reporting:
            compliance_bonus += 0.5

        # Overall moat score: average of components + compliance bonus
        moat_score = (
            (esg_component * 0.25 +
             carbon_component * 0.20 +
             patent_component * 0.20 +
             regulatory_component * 0.15 +
             institutional_component * 0.20) +
            compliance_bonus
        )
        moat_score = min(10, max(1, moat_score))  # Clamp 1-10

        # Exploitability: inversely correlated with moat
        is_exploitable = moat_score < 5.0

        # Vulnerability type
        if moat_score >= 8:
            vuln_type = "strong_moat"
            reasoning = (
                f"Strong regulatory moat. ESG score {esg_score}, "
                f"carbon intensity {carbon:.1f}, patents {patents}. "
                f"Compliant with CSRD: {csrd_compliant}."
            )
            specific_weakness = None
            fix_exploit = (
                "Difficult to compete with. Look for execution risk or market saturation."
            )
        elif moat_score >= 6:
            vuln_type = "medium_moat"
            reasoning = (
                f"Moderate regulatory moat. ESG {esg_score}, carbon {carbon:.1f}, patents {patents}. "
                f"CSRD compliance: {csrd_compliant}."
            )
            specific_weakness = (
                "Some regulatory gaps. Monitor for non-compliance or regulatory changes."
            )
            fix_exploit = "Exploit if regulatory environment tightens; non-compliant competitors will struggle."
        elif moat_score >= 4:
            vuln_type = "weak_moat"
            reasoning = (
                f"Weak moat. ESG {esg_score}, carbon {carbon:.1f}, patents {patents}. "
                f"Non-compliant: CSRD={not csrd_compliant}, Carbon={not carbon_reporting}."
            )
            specific_weakness = (
                "Significant regulatory/ESG gaps. Vulnerable to compliance enforcement."
            )
            fix_exploit = (
                "Upcoming regulations will pressure non-compliant competitors. "
                "Compliant players gain market share + lower cost of capital."
            )
        else:
            vuln_type = "regulatory_risk"
            reasoning = (
                f"High regulatory risk. Poorly positioned for ESG/CSRD transition. "
                f"ESG {esg_score}, carbon {carbon:.1f}, patents {patents}."
            )
            specific_weakness = "Massive ESG/regulatory gap. High non-compliance risk."
            fix_exploit = (
                "At risk of enforcement, capital restrictions, or investor divestment. "
                "Look for short opportunities or acquisition targets."
            )

        return VulnerabilityScanResult(
            vulnerability_type=vuln_type,
            moat_score=int(moat_score),
            is_exploitable=is_exploitable,
            reasoning=reasoning,
            specific_weakness=specific_weakness,
            fix_or_exploit=fix_exploit,
        )
