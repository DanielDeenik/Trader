# Signal Monitoring Dashboard Template
## Cloud Infrastructure & Payments Companies (Weekly Tracker)

### Instructions
Copy this template into a spreadsheet (Google Sheets, Excel, Airtable) and update weekly. Each metric tracks a specific mosaic component.

---

## DEVELOPER ADOPTION SIGNALS

### GitHub Activity Tracking
| Company | SDK Repo | Stars (Week) | Stars (Trend) | Forks | Open Issues | Commits (30d) | Signal Assessment |
|---------|----------|--------------|---------------|-------|-------------|----------------|-------------------|
| Stripe | stripe/stripe-dotnet | 1250 | ↑ slightly | 450 | 23 | 45 | **Normal growth** |
| Stripe | stripe/stripe-js | 2100 | → flat | 620 | 31 | 38 | **⚠️ Plateau?** |
| Adyen | adyen/adyen-dotnet | 340 | ↑ steady | 180 | 15 | 28 | **Slow but steady** |
| Lithic | lithic/lithic-node | 210 | ↑↑ | 95 | 8 | 35 | **Accelerating 📈** |
| Databricks | databricks/databricks-sdk | 1850 | ↑↑↑ | 520 | 42 | 72 | **Strong momentum** |

**Interpretation**:
- Stars trending up = Developer mindshare increasing
- Commits declining = Less active maintenance (watch for maturity vs. abandonment)
- Open issues rising = Product quality concerns or growing feature requests
- Compare **relative trends** (Stripe vs. Adyen) to detect market share shifts

---

### Stack Overflow Question Volume (Monthly)
| Tag | Q&A Count (Month) | Trend | Avg Answer Time | Solution Rate | Signal |
|-----|------------------|-------|-----------------|---------------|---------
| stripe | 245 | ↑ 5% | 3.2 hours | 92% | Healthy ecosystem |
| adyen | 89 | → flat | 5.1 hours | 85% | Niche, slower support |
| payments | 512 | ↑ 12% | 4.8 hours | 88% | Growing complexity |
| databricks | 340 | ↑↑ 18% | 2.9 hours | 90% | Growing adoption + good support |

**Interpretation**:
- Rising Q&A count = Product gaining adoption
- Fast answer times = Strong community/support
- Low solution rates = Harder to use product (competitive threat?)

---

### NPM Download Trends (Monthly)
| Package | Downloads (Month) | Trend | Market Share | Signal |
|---------|------------------|-------|--------------|--------|
| stripe | 1.2M | ↑ 8% | 45% | Dominant, steady growth |
| adyen-web | 180K | ↑ 6% | 7% | Small but growing |
| @lithic/sdk | 45K | ↑ 18% | 1.7% | **Accelerating adoption** |
| next.js | 4.2M | ↑ 3% | - | Baseline growth (context) |

**Interpretation**:
- Market share = Download share of total payment SDK downloads
- Lithic accelerating at 18% signals vertical SaaS momentum
- Use context package (next.js) to normalize for overall ecosystem growth

---

## HIRING & ORG EXPANSION SIGNALS

### Job Posting Velocity
| Company | Total Open Roles | Growth Roles (Payments, Gov, etc.) | Geographic Expansion | Signal Assessment |
|---------|-----------------|-------------------------------------|---------------------|-------------------|
| Stripe | 142 | 18 (payments), 8 (gov) | Expanding APAC | **Moderate growth** |
| Adyen | 89 | 12 (enterprise), 5 (gov) | Europe-focused | **Conservative** |
| Lithic | 31 | 8 (vertical SaaS), 3 (dev relations) | NYC-focused | **Focused hiring** |
| Databricks | 217 | 35 (enterprise), 22 (AI/ML) | Expanding globally | **Aggressive expansion** |

**Interpretation**:
- Government role hiring = Signal of govtech push
- Vertical SaaS hiring = Signal of vertical platform focus
- Geographic expansion = Market entry/growth
- Ratio of growth to total roles = Growth speed

---

### Key Executive Movements (Track via LinkedIn)
| Company | Executive | Role | Movement | Signal | Date |
|---------|-----------|------|----------|--------|------|
| Stripe | [New Hire] | VP Government Sales | Hired from [Competitor] | **Govtech pivot signal** | Mar 2026 |
| Adyen | [Departure] | Chief Product Officer | To [Startup] | ⚠️ Talent drain? | Feb 2026 |
| Databricks | [Hire] | VP Enterprise | From Microsoft | **Enterprise push** | Jan 2026 |
| Lithic | [Hire] | Head of Vertical SaaS | From Stripe | **Product focus** | Mar 2026 |

**Interpretation**:
- Government role = Regulatory/govtech strategy shift
- Departures = Product struggle or better opportunity elsewhere
- Hires from specific competitors = Strategic product direction

---

## REGULATORY & COMPLIANCE SIGNALS

### Government/Regulatory Progress
| Company | Initiative | Status | Timeline | Significance | Data Source |
|---------|-----------|--------|----------|--------------|-------------|
| Stripe | FedRAMP Certification | Not Started | - | **Critical Gap** | GSA.gov |
| Adyen | Banking License (US) | In Progress | Q3 2026 | Moat Builder | OCC Filing |
| Lithic | FedRAMP Authorization | In Progress | Q4 2026 | **Game Changer** | GSA.gov |
| Databricks | Government Procurement | No Signal | - | Opportunity | SAM.gov |

**Interpretation**:
- FedRAMP = Gate to government market (18-24 month lead time)
- Banking license = Vertical integration play; increased moat
- Government contract wins = Lock-in signal (10-year contracts)

---

### Patent Filings (Quarterly Review)
| Company | Patent Topic | Filing Date | Status | Competitive Signal |
|---------|-------------|-----------|--------|-------------------|
| Stripe | AI Fraud Detection | Q4 2025 | Issued | Building proprietary AI |
| Adyen | Multi-currency Settlement | Q3 2025 | Pending | Competitive differentiation |
| Lithic | Card Issuance Logic | Q2 2026 | Pending | Vertical-specific innovation |

**Interpretation**:
- AI/fraud detection patents = Moat expansion
- Vertical-specific patents = Competitive protection in niche

---

## CUSTOMER & REVENUE SIGNALS

### Enterprise Customer Wins (Announced)
| Company | Customer Category | Type | Significance | Announcement Date | Revenue Impact |
|---------|-----------------|------|--------------|------------------|-----------------|
| Stripe | Government | $5.6B Salesforce Army Contract (indirect) | **Massive moat builder** | Jan 2026 | $500M+ over 5 years |
| Adyen | Enterprise | [Monitor for announcements] | - | - | - |
| Lithic | Vertical SaaS | [Track integrations] | Market validation | Ongoing | $10M+ by 2027 |
| Databricks | Enterprise | Accenture partnership | **Enterprise lock-in signal** | Feb 2026 | $200M+ over 3 years |

**Interpretation**:
- Government contracts = Permanent moat (vendor lock-in)
- Enterprise partnerships = Accelerated adoption signal
- Accenture partnership for Databricks = 500+ large enterprise exposure

---

### Market Share & Competitive Positioning (Quarterly)
| Metric | Stripe | Adyen | Lithic | Benchmark |
|--------|--------|-------|--------|-----------|
| Payment Volume Processed (2025) | $1.9T | ~$800B est. | ~$2B est. | Total market $50T+ |
| Volume Growth YoY | +34% | +18% | +80% est. | SMB growth +40% |
| Market Share (Web payments) | ~25% | ~12% | <0.5% | Rest fragmented |
| Target Customer | SMB/Scale-up | Enterprise | Vertical SaaS | - |

**Interpretation**:
- Stripe maintaining volume leadership but growth moderating
- Lithic's high growth confirms vertical SaaS momentum
- Adyen's slower growth signals competitive pressure

---

## ALTERNATIVE DATA: SOCIAL SENTIMENT & COMMUNITY

### Developer Community Sentiment (Monthly Snapshot)
| Source | Company | Sentiment | Key Quotes | Signal |
|--------|---------|-----------|-----------|--------|
| Hacker News | Stripe | Positive (with caveats) | "Best DX but fees are rising" | **Satisfaction declining** |
| Hacker News | Adyen | Mixed | "Enterprise-grade but complex" | **Niche positioning** |
| Reddit r/programming | Lithic | Positive (emerging) | "Finally a payment provider that gets vertical SaaS" | **Emerging mindshare** |
| Twitter (@AdyenDevs, @StripeDev) | Both | Active but declining engagement | Fewer retweets/replies over time | Monitor engagement metrics |

**Interpretation**:
- Sentiment shifts = Early warning of churn/competitive loss
- Emerging positive sentiment = Market opportunity (Lithic)
- Declining developer satisfaction = Moat erosion (watch for Stripe)

---

## REGULATORY FILINGS & IPO SIGNALS

### IPO Readiness Tracking
| Company | IPO Indicator | Status | Timeline Implication | Signal Strength |
|---------|--------------|--------|---------------------|-----------------|
| Databricks | Confidential IPO Filing | ✅ Filed | Q2 2026 likely | **Very High** |
| Stripe | IPO rumors | Ongoing (delayed) | H2 2026 or later | Medium |
| Lithic | IPO signals | None yet | 2027+ | Low |
| Revolut | Profitability rumored | To be verified | 2027+ | Medium |

**Interpretation**:
- Confidential filing = 60-90 days to public filing
- CFO hires = 6-12 month pre-IPO signal
- Secondary market valuations (Carta) = Real-time IPO readiness gauge

---

### Regulatory Status Monitoring
| Company | Regulatory Area | Status | Deadline | Risk Level |
|---------|-----------------|--------|----------|-----------|
| Stripe | FedRAMP Certification | Not Started | TBD | 🔴 High (missing govtech market) |
| Adyen | US Banking License | In Process | Q3 2026 | 🟡 Medium (standard process) |
| Lithic | FedRAMP Certification | In Process | Q4 2026 | 🟢 Low (on track) |
| Databricks | Government Compliance | No Signal | TBD | 🟡 Medium (opportunity) |

---

## SYNTHESIS & ACTION ITEMS

### Weekly Mosaic Update (After collecting data)

**Question**: What is the most important signal change this week?

**Answer**: [Synthesize top 3 data points]
- Signal 1: _____
- Signal 2: _____
- Signal 3: _____

**Implication for Investment Thesis**: [How does this change your view?]

**Action**: [Buy/Hold/Sell or Monitor Closer?]

---

### Quarterly Thesis Reassessment

**Company**: [Stripe, Databricks, etc.]

**Previous Thesis**: [Summary from 3 months ago]

**Signal Summary** (updated via tracking above):
- **Developer adoption**: [trending up/flat/down?]
- **Government/Regulatory**: [any progress?]
- **Customer wins**: [acceleration/deceleration?]
- **Competitive threat**: [rising/stable/declining?]

**Thesis Update**: [Is your original thesis still valid?]

**Valuation Adjustment**: [Should fair value estimate change?]

**Next Quarter Focus**: [What signals matter most going forward?]

---

## TEMPLATES FOR SPECIFIC COMPANIES

### Stripe Monitoring Checklist
- [ ] GitHub SDK stars trend (weekly)
- [ ] Job postings for government sales (weekly)
- [ ] Stack Overflow "stripe" Q&A volume (monthly)
- [ ] IPO rumor tracking (weekly)
- [ ] Adyen earnings call notes (quarterly)
- [ ] SEC Edgar for confidential filings (weekly)
- [ ] Vertical SaaS alternative tracking (monthly)

### Databricks Monitoring Checklist
- [ ] SEC Edgar for IPO filing (weekly)
- [ ] GitHub SDK adoption (weekly)
- [ ] Accenture partnership depth (monthly)
- [ ] Enterprise customer wins (as announced)
- [ ] Snowflake competitive positioning (quarterly)
- [ ] AI infrastructure market sizing (quarterly)

### Lithic Monitoring Checklist
- [ ] GitHub SDK downloads (monthly)
- [ ] Job postings for vertical SaaS (monthly)
- [ ] Vertical SaaS platform integrations (monthly)
- [ ] FedRAMP certification progress (quarterly)
- [ ] Acquisition rumors (ongoing)
- [ ] Vertical market penetration (quarterly)

---

## SCORING SYSTEM (Optional)

Assign 1-5 points to each metric (5 = strongest signal):

| Company | Dev Adoption | Government | Hiring | Sentiment | Competitive | Overall Score |
|---------|-------------|-----------|--------|-----------|------------|-----------------|
| Stripe | 4.5 | 1.5 | 3.5 | 3.0 | 2.5 | **3.0/5.0** |
| Databricks | 4.8 | 2.0 | 4.5 | 4.5 | 3.5 | **3.9/5.0** |
| Lithic | 3.5 | 3.0 | 3.5 | 4.2 | 4.0 | **3.6/5.0** |
| Adyen | 3.2 | 3.5 | 2.5 | 3.0 | 3.2 | **3.1/5.0** |

**Interpretation**:
- 4.0+/5.0 = Strong mosaic signals; increasing conviction
- 3.0-4.0 = Mixed signals; watch closely for inflection
- <3.0 = Weak mosaic; thesis at risk unless new catalysts emerge

---

**Template Version**: March 2026
**Update Frequency**: Weekly (signals) + Monthly (aggregates) + Quarterly (synthesis)
**Tool Recommendation**: Google Sheets (easy sharing, built-in charting)
