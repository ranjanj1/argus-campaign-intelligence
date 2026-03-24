from __future__ import annotations

import pandas as pd

from scripts.generators.base import (
    VERTICAL_CONFIGS,
    fake,
    rand_choice,
    rand_float,
    rand_int,
    rand_sample,
)
from scripts.models.client_context import ClientProfile

# CTA options per channel type
CTAS: dict[str, list[str]] = {
    "meta": ["Shop Now", "Learn More", "Get Offer", "Sign Up", "Book Now"],
    "google_search": ["Get a Free Quote", "Call Today", "Start Free Trial", "Shop Now", "Learn More"],
    "google_shopping": ["Buy Now", "Shop Now", "See Price", "Add to Cart"],
    "tiktok": ["Shop Now", "Learn More", "Download", "Watch Now"],
    "linkedin": ["Download Now", "Register", "Learn More", "Get Started", "Request Demo"],
    "email": ["Shop Now", "Redeem Offer", "View Collection", "Claim Your Discount"],
    "display": ["Learn More", "Get Started", "Shop Now", "Discover"],
    "pinterest": ["Shop the Look", "Save & Shop", "Learn More", "Visit Site"],
    "native": ["Read More", "Learn More", "Discover", "Find Out How"],
}

HEADLINE_PREFIXES: dict[str, list[str]] = {
    "retail": [
        "Save {pct}% on {product}",
        "New {product} — Limited Stock",
        "{pct}% Off Today Only",
        "Free Shipping on {product}",
        "Shop {product} — Best Prices",
        "Trending Now: {product}",
        "{season} Sale — Up to {pct}% Off",
        "Top-Rated {product} You'll Love",
    ],
    "saas": [
        "Try {product} Free for 14 Days",
        "{product} — Built for Teams Like Yours",
        "See Why 10,000+ Teams Use {product}",
        "Automate {task} with {product}",
        "{product}: {pct}% Faster {task}",
        "Cut {task} Costs by {pct}%",
        "{product} — No Credit Card Required",
        "The {adjective} Way to {task}",
    ],
    "ecommerce": [
        "Shop {product} — Ships Today",
        "{pct}% Off Your First Order",
        "Eco-Friendly {product} You'll Love",
        "New {product} Just Dropped",
        "Members Save {pct}% — Join Free",
        "The {adjective} {product} Collection",
        "Free Returns on All {product}",
        "{product} — As Seen On TikTok",
    ],
    "finance": [
        "Earn {pct}% APY — No Fees",
        "{product} — Trusted by 1M+ Customers",
        "Apply in 3 Minutes — Get {product}",
        "Competitive Rates on {product}",
        "{product}: Secure, Simple, Smart",
        "No Hidden Fees — Just {product}",
        "{product} — Start with $0",
        "Your Financial Future Starts Here",
    ],
}

BODY_TEMPLATES: dict[str, list[str]] = {
    "retail": [
        "Shop our exclusive {product} collection with free shipping on orders over $50. Limited time offer.",
        "Discover top-rated {product} at unbeatable prices. {pct}% off this week only — don't miss out.",
        "Your style, your way. Browse {product} with fast delivery and hassle-free returns.",
    ],
    "saas": [
        "Join thousands of teams using {product} to streamline workflows and boost productivity. Start free.",
        "{product} integrates with your existing tools in minutes. No IT required. Try it today.",
        "Cut manual {task} by {pct}%. See how {product} transforms your team's output.",
    ],
    "ecommerce": [
        "Shop {product} with fast, eco-friendly shipping. New arrivals every week. Members get {pct}% off.",
        "Discover our curated {product} collection — sustainably sourced and designed to last.",
        "Free returns, fast delivery, and products you'll love. Shop {product} today.",
    ],
    "finance": [
        "Open your {product} in minutes. No fees, no minimums — just smart banking built for you.",
        "Earn more on your savings with our {product}. FDIC insured. Apply in under 3 minutes.",
        "Get the {product} that works as hard as you do. Competitive rates, zero hidden fees.",
    ],
}

SEASONS = ["Summer", "Winter", "Spring", "Fall", "Holiday", "Back-to-School"]
ADJECTIVES = ["Smarter", "Faster", "Better", "Effortless", "Modern", "Powerful"]
TASKS = ["reporting", "project management", "invoicing", "team collaboration", "data analysis"]
PRODUCTS_AD = {
    "retail": ["activewear", "home goods", "accessories", "electronics", "fashion"],
    "saas": ["platform", "dashboard", "workspace", "suite", "solution"],
    "ecommerce": ["collection", "bundles", "essentials", "bestsellers", "new arrivals"],
    "finance": ["savings account", "credit card", "loan", "investment account", "mortgage"],
}


def _fill_template(template: str, industry: str) -> str:
    product = rand_choice(PRODUCTS_AD.get(industry, ["product"]))
    return template.format(
        product=product,
        pct=rand_int(10, 50),
        season=rand_choice(SEASONS),
        adjective=rand_choice(ADJECTIVES),
        task=rand_choice(TASKS),
    )


def generate_ad_copy_library_df(profile: ClientProfile) -> pd.DataFrame:
    """Return DataFrame with 20 ad copy variants referencing existing campaign IDs."""
    industry = profile.industry
    config = VERTICAL_CONFIGS[industry]

    # Sample campaigns to reference (with repetition — multiple variants per campaign)
    campaign_pool = profile.campaigns
    rows = []

    for i in range(20):
        # Pick a parent campaign — bias toward active ones
        active = [c for c in campaign_pool if c.status == "active"]
        parent = rand_choice(active if active else campaign_pool)

        channel = parent.channel
        variant = "A" if i % 2 == 0 else "B"

        # Headline
        headline_templates = HEADLINE_PREFIXES.get(industry, ["{product} — Learn More"])
        raw_headline = _fill_template(rand_choice(headline_templates), industry)
        headline = raw_headline[:60]

        # Body
        body_templates = BODY_TEMPLATES.get(industry, ["Discover {product} today."])
        raw_body = _fill_template(rand_choice(body_templates), industry)
        body_copy = raw_body[:150]

        # CTA
        cta_pool = CTAS.get(channel, CTAS["display"])
        cta = rand_choice(cta_pool)

        # CTR within ±20% of parent campaign CTR
        parent_ctr = parent.clicks / max(parent.impressions, 1)
        ctr_factor = rand_float(0.8, 1.2)
        ctr = round(clamp_ctr(parent_ctr * ctr_factor, config.ctr_range), 4)

        # Conversion rate within ±20% of parent
        parent_cvr = parent.conversions / max(parent.clicks, 1)
        cvr_factor = rand_float(0.8, 1.2)
        cvr = round(max(0.001, parent_cvr * cvr_factor), 4)

        rows.append({
            "ad_id": f"AD-{profile.client_id[:3].upper()}-{i + 1:03d}",
            "campaign_id": parent.campaign_id,
            "client_id": profile.client_id,
            "channel": channel,
            "a_b_variant": variant,
            "headline": headline,
            "body_copy": body_copy,
            "cta": cta,
            "ctr": ctr,
            "conversion_rate": cvr,
        })

    return pd.DataFrame(rows)


def clamp_ctr(value: float, ctr_range: tuple[float, float]) -> float:
    return max(ctr_range[0] * 0.5, min(ctr_range[1] * 1.5, value))
