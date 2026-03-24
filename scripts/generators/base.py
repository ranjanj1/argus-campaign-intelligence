from __future__ import annotations

import math
import random
from datetime import date, timedelta

from faker import Faker

from scripts.models.client_context import VerticalConfig

# ---------------------------------------------------------------------------
# Shared Faker instance — seeded in seed_data.py via set_seed()
# ---------------------------------------------------------------------------
fake = Faker()
_rng = random.Random()


def set_seed(seed: int) -> None:
    Faker.seed(seed)
    _rng.seed(seed)
    random.seed(seed)


# ---------------------------------------------------------------------------
# Industry vertical configurations
# ---------------------------------------------------------------------------
VERTICAL_CONFIGS: dict[str, VerticalConfig] = {
    "retail": VerticalConfig(
        industry="retail",
        roas_range=(2.5, 8.0),
        ctr_range=(0.012, 0.045),
        cpa_range=(8.0, 35.0),
        conversion_rate_range=(0.015, 0.06),
        cpm_range=(4.0, 18.0),
        monthly_budget_range=(15_000, 80_000),
        primary_channels=["meta", "google_search", "google_shopping", "tiktok", "email"],
        tone_keywords=["sale", "discount", "free shipping", "limited offer", "best value", "shop now"],
        competitors=["ShopMax", "RetailGiant", "BargainWorld", "TrendMart"],
        business_objectives=[
            "Increase online sales by 30% YoY",
            "Reduce customer acquisition cost to under $25",
            "Grow email subscriber list by 50K",
            "Achieve 4.0x blended ROAS across all channels",
        ],
    ),
    "saas": VerticalConfig(
        industry="saas",
        roas_range=(1.8, 5.5),
        ctr_range=(0.008, 0.028),
        cpa_range=(45.0, 250.0),
        conversion_rate_range=(0.005, 0.025),
        cpm_range=(12.0, 55.0),
        monthly_budget_range=(8_000, 40_000),
        primary_channels=["linkedin", "google_search", "meta", "display", "email"],
        tone_keywords=["free trial", "demo", "ROI", "productivity", "integration", "enterprise"],
        competitors=["SaaSLeader", "CloudSuite", "ProStack", "WorkflowPro"],
        business_objectives=[
            "Generate 500 qualified MQLs per month",
            "Reduce cost-per-trial to under $80",
            "Increase trial-to-paid conversion rate to 15%",
            "Expand into enterprise segment with ABM campaigns",
        ],
    ),
    "ecommerce": VerticalConfig(
        industry="ecommerce",
        roas_range=(2.0, 7.0),
        ctr_range=(0.010, 0.040),
        cpa_range=(12.0, 60.0),
        conversion_rate_range=(0.012, 0.055),
        cpm_range=(5.0, 22.0),
        monthly_budget_range=(12_000, 65_000),
        primary_channels=["meta", "google_shopping", "tiktok", "pinterest", "email"],
        tone_keywords=["fast delivery", "eco-friendly", "new arrivals", "exclusive", "members only"],
        competitors=["EcoShop", "GreenCart", "NatureStore", "OrganicBuy"],
        business_objectives=[
            "Scale revenue to $2M monthly with positive ROAS",
            "Grow repeat purchase rate to 35%",
            "Reduce cart abandonment rate to below 60%",
            "Launch loyalty program with 10K members in 90 days",
        ],
    ),
    "finance": VerticalConfig(
        industry="finance",
        roas_range=(1.2, 3.5),
        ctr_range=(0.004, 0.018),
        cpa_range=(80.0, 400.0),
        conversion_rate_range=(0.003, 0.015),
        cpm_range=(18.0, 75.0),
        monthly_budget_range=(25_000, 120_000),
        primary_channels=["google_search", "linkedin", "display", "meta", "native"],
        tone_keywords=["secure", "trusted", "competitive rates", "no fees", "financial freedom"],
        competitors=["WealthEdge", "SecureBank", "PrimeFinance", "ClearCapital"],
        business_objectives=[
            "Acquire 1,000 new account holders per month",
            "Reduce cost-per-acquisition below $150",
            "Increase product cross-sell rate to 25%",
            "Build brand trust with 40+ NPS score",
        ],
    ),
}

# ---------------------------------------------------------------------------
# Segment data pools per vertical
# ---------------------------------------------------------------------------
SEGMENT_POOLS: dict[str, list[dict]] = {
    "retail": [
        {"name": "Deal Seekers 18-24", "age": "18-24", "gender": "all", "platform": "tiktok",
         "interests": ["fashion", "deals", "streetwear", "trending products"]},
        {"name": "Female Shoppers 25-34", "age": "25-34", "gender": "female", "platform": "meta",
         "interests": ["home decor", "fashion", "beauty", "lifestyle"]},
        {"name": "Homeowners 35-44", "age": "35-44", "gender": "all", "platform": "meta",
         "interests": ["home improvement", "gardening", "family", "DIY"]},
        {"name": "Premium Buyers 45-54", "age": "45-54", "gender": "all", "platform": "google_search",
         "interests": ["luxury goods", "quality brands", "travel", "health"]},
        {"name": "Bargain Hunters 25-44", "age": "25-44", "gender": "all", "platform": "email",
         "interests": ["coupons", "cashback", "comparison shopping", "deals"]},
        {"name": "Tech-Savvy Shoppers 18-35", "age": "18-35", "gender": "all", "platform": "google_shopping",
         "interests": ["electronics", "gadgets", "tech reviews", "innovation"]},
        {"name": "Parents 30-45", "age": "30-45", "gender": "all", "platform": "meta",
         "interests": ["parenting", "children's products", "education", "family activities"]},
        {"name": "Fitness Enthusiasts 22-40", "age": "22-40", "gender": "all", "platform": "meta",
         "interests": ["fitness", "sports", "health food", "wellness"]},
        {"name": "Loyal Customers", "age": "25-55", "gender": "all", "platform": "email",
         "interests": ["brand loyalty", "rewards programs", "repeat purchase"]},
        {"name": "Lookalike - Top Buyers", "age": "25-54", "gender": "all", "platform": "meta",
         "interests": ["high intent", "lookalike", "purchase behavior"]},
    ],
    "saas": [
        {"name": "SMB Decision Makers", "age": "28-45", "gender": "all", "platform": "linkedin",
         "interests": ["business software", "productivity", "startup", "SaaS"]},
        {"name": "Enterprise IT Directors", "age": "35-55", "gender": "all", "platform": "linkedin",
         "interests": ["enterprise software", "digital transformation", "IT management", "security"]},
        {"name": "Marketing Managers", "age": "25-40", "gender": "all", "platform": "meta",
         "interests": ["marketing automation", "CRM", "analytics", "campaigns"]},
        {"name": "Startup Founders", "age": "22-40", "gender": "all", "platform": "linkedin",
         "interests": ["startups", "growth hacking", "product-market fit", "funding"]},
        {"name": "Operations Leads 30-50", "age": "30-50", "gender": "all", "platform": "google_search",
         "interests": ["workflow automation", "process optimization", "project management"]},
        {"name": "Competitor Users", "age": "25-50", "gender": "all", "platform": "google_search",
         "interests": ["alternative software", "competitor comparison", "switching"]},
        {"name": "Trial Abandoners Retarget", "age": "25-45", "gender": "all", "platform": "display",
         "interests": ["retargeting", "trial", "re-engagement"]},
        {"name": "Developer Audience", "age": "22-38", "gender": "all", "platform": "display",
         "interests": ["API", "developers", "integration", "automation"]},
        {"name": "Finance VPs", "age": "35-55", "gender": "all", "platform": "linkedin",
         "interests": ["financial software", "reporting", "forecasting", "CFO"]},
        {"name": "Mid-Market Companies", "age": "30-50", "gender": "all", "platform": "linkedin",
         "interests": ["mid-market", "200-1000 employees", "scaling", "efficiency"]},
    ],
    "ecommerce": [
        {"name": "Eco-Conscious Millennials", "age": "22-35", "gender": "all", "platform": "meta",
         "interests": ["sustainability", "eco-friendly", "organic", "green living"]},
        {"name": "Gen Z Trendsetters", "age": "18-25", "gender": "all", "platform": "tiktok",
         "interests": ["trends", "viral products", "social shopping", "influencers"]},
        {"name": "Female Wellness 28-42", "age": "28-42", "gender": "female", "platform": "pinterest",
         "interests": ["wellness", "beauty", "self-care", "health products"]},
        {"name": "Gift Buyers Holiday", "age": "25-55", "gender": "all", "platform": "google_shopping",
         "interests": ["gifts", "holiday shopping", "wish lists", "premium gifts"]},
        {"name": "Subscription Buyers", "age": "25-45", "gender": "all", "platform": "email",
         "interests": ["subscriptions", "recurring delivery", "convenience", "subscription boxes"]},
        {"name": "High-Value Customers", "age": "30-50", "gender": "all", "platform": "meta",
         "interests": ["premium products", "luxury", "quality-focused", "brand loyalty"]},
        {"name": "New Customer Acquisition", "age": "20-40", "gender": "all", "platform": "meta",
         "interests": ["prospecting", "new brands", "discovery", "first purchase"]},
        {"name": "Cart Abandoners", "age": "22-45", "gender": "all", "platform": "display",
         "interests": ["retargeting", "abandoned cart", "re-engagement", "dynamic ads"]},
        {"name": "Seasonal Shoppers", "age": "25-50", "gender": "all", "platform": "google_shopping",
         "interests": ["seasonal", "deals", "holiday", "back-to-school"]},
        {"name": "Influencer Followers", "age": "18-30", "gender": "female", "platform": "tiktok",
         "interests": ["influencer content", "reviews", "unboxing", "trending"]},
    ],
    "finance": [
        {"name": "Young Professionals 25-34", "age": "25-34", "gender": "all", "platform": "meta",
         "interests": ["investing", "financial planning", "career growth", "savings"]},
        {"name": "High Net Worth 45-65", "age": "45-65", "gender": "all", "platform": "google_search",
         "interests": ["wealth management", "retirement", "investment portfolio", "estate planning"]},
        {"name": "Small Business Owners", "age": "30-55", "gender": "all", "platform": "linkedin",
         "interests": ["business banking", "loans", "payroll", "business credit"]},
        {"name": "First-Time Investors 22-35", "age": "22-35", "gender": "all", "platform": "meta",
         "interests": ["beginner investing", "ETFs", "robo-advisor", "passive income"]},
        {"name": "Mortgage Seekers 28-45", "age": "28-45", "gender": "all", "platform": "google_search",
         "interests": ["home buying", "mortgage rates", "refinancing", "real estate"]},
        {"name": "Retirees 55-70", "age": "55-70", "gender": "all", "platform": "display",
         "interests": ["retirement income", "fixed income", "annuities", "social security"]},
        {"name": "Debt Consolidation Seekers", "age": "25-45", "gender": "all", "platform": "google_search",
         "interests": ["debt management", "personal loans", "credit consolidation", "financial relief"]},
        {"name": "Premium Credit Card Users", "age": "30-50", "gender": "all", "platform": "native",
         "interests": ["travel rewards", "premium cards", "cashback", "concierge services"]},
        {"name": "Corporate Executives", "age": "40-60", "gender": "all", "platform": "linkedin",
         "interests": ["corporate finance", "executive compensation", "stock options", "M&A"]},
        {"name": "Competitor Bank Customers", "age": "25-55", "gender": "all", "platform": "google_search",
         "interests": ["switching banks", "better rates", "alternatives", "comparison"]},
    ],
}

# ---------------------------------------------------------------------------
# Ad name patterns per channel
# ---------------------------------------------------------------------------
CAMPAIGN_NAME_TEMPLATES: dict[str, list[str]] = {
    "meta": [
        "{objective} — Meta Social {quarter}",
        "Facebook Prospecting — {audience}",
        "Instagram Stories — {product} {quarter}",
        "Meta Retargeting — {audience} {year}",
        "FB Advantage+ — {objective}",
    ],
    "google_search": [
        "Google Search — {product} Keywords {quarter}",
        "Brand Defense — {quarter}",
        "Competitor Conquest — {product}",
        "Non-Brand Search — {audience}",
        "Performance Max — {objective} {quarter}",
    ],
    "google_shopping": [
        "Shopping — {product} Feed {quarter}",
        "Smart Shopping — {audience}",
        "Google Shopping Standard — {product}",
    ],
    "tiktok": [
        "TikTok Spark Ads — {audience} {quarter}",
        "TikTok TopView — {product} Launch",
        "TikTok In-Feed — {objective}",
    ],
    "linkedin": [
        "LinkedIn Sponsored Content — {audience}",
        "LinkedIn InMail — {objective} {quarter}",
        "LinkedIn Lead Gen — {product}",
        "LinkedIn Thought Leadership — {quarter}",
    ],
    "email": [
        "Email Nurture — {audience} Sequence",
        "Email Promotional — {product} {quarter}",
        "Email Re-engagement — {audience}",
        "Email Welcome Series — New Subscribers",
    ],
    "display": [
        "Display Prospecting — {audience} {quarter}",
        "Programmatic Display — {objective}",
        "Retargeting Display — {audience}",
    ],
    "pinterest": [
        "Pinterest Shopping — {product} Pins",
        "Pinterest Awareness — {audience} {quarter}",
    ],
    "native": [
        "Native Content — {product} {quarter}",
        "Native Sponsored — {audience}",
    ],
}

QUARTERS = ["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024", "Q1 2025", "Q2 2025"]
YEARS = ["2024", "2025"]
OBJECTIVES = ["Brand Awareness", "Lead Generation", "Conversions", "Retargeting", "Retention"]
PRODUCTS = {
    "retail": ["Summer Collection", "Clearance Sale", "New Arrivals", "Holiday Gifts", "Essentials"],
    "saas": ["Platform Demo", "Free Trial", "Enterprise Plan", "Pro Tier", "API Access"],
    "ecommerce": ["Bestsellers", "New Collection", "Flash Sale", "Bundles", "Subscriptions"],
    "finance": ["Savings Account", "Investment Portfolio", "Personal Loan", "Credit Card", "Mortgage"],
}

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def make_campaign_id(client_prefix: str, index: int) -> str:
    return f"{client_prefix.upper()[:4]}-{index:03d}"


def make_segment_id(client_prefix: str, index: int) -> str:
    return f"SEG-{client_prefix.upper()[:3]}-{index:02d}"


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def rand_float(lo: float, hi: float) -> float:
    return _rng.uniform(lo, hi)


def rand_int(lo: int, hi: int) -> int:
    return _rng.randint(lo, hi)


def rand_choice(seq: list) -> object:
    return _rng.choice(seq)


def rand_sample(seq: list, k: int) -> list:
    return _rng.sample(seq, min(k, len(seq)))


def weighted_date_range(
    base_year: int = 2024,
    status: str = "active",
) -> tuple[date, date]:
    """Generate start/end dates consistent with campaign status."""
    today = date(2025, 3, 21)
    if status == "completed":
        # Ended in the past
        end = date(base_year, rand_int(1, 12), rand_int(1, 28))
        duration = rand_int(14, 90)
        start = end - timedelta(days=duration)
    elif status == "active":
        # Started recently, ends in future
        start_days_ago = rand_int(7, 60)
        start = today - timedelta(days=start_days_ago)
        end = today + timedelta(days=rand_int(14, 90))
    else:  # paused
        # Started in past, end date in future (paused mid-flight)
        start = today - timedelta(days=rand_int(30, 120))
        end = today + timedelta(days=rand_int(10, 60))
    return start, end


def generate_campaign_name(channel: str, industry: str, audience_name: str) -> str:
    templates = CAMPAIGN_NAME_TEMPLATES.get(channel, ["{objective} — {channel} {quarter}"])
    template = rand_choice(templates)
    products = PRODUCTS.get(industry, ["Product"])
    return template.format(
        objective=rand_choice(OBJECTIVES),
        audience=audience_name.split(" ")[0] + " " + audience_name.split(" ")[-1],
        product=rand_choice(products),
        quarter=rand_choice(QUARTERS),
        year=rand_choice(YEARS),
        channel=channel.replace("_", " ").title(),
    )


