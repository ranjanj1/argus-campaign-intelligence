// Design tokens extracted from argus-ui.jsx prototype

export const AMBER = "#EAB308";
export const AMBER_DIM = "#92710A";
export const BG = "#080C14";
export const SURFACE = "#0E1420";
export const SURFACE2 = "#141C2C";
export const BORDER = "#1E2A3A";
export const TEXT_DIM = "#6B7A8F";
export const TEXT_MID = "#9CAABA";
export const TEXT = "#E8E4D9";
export const TEXT_BODY = "#C4BFAF";

export const COLLECTIONS = [
  { id: "campaign_performance", label: "Campaign Performance", color: "#3B82F6" },
  { id: "ad_copy_library", label: "Ad Copy Library", color: "#8B5CF6" },
  { id: "audience_segments", label: "Audience Segments", color: "#EC4899" },
  { id: "monthly_reports", label: "Monthly Reports", color: "#10B981" },
  { id: "client_strategy_briefs", label: "Strategy Briefs", color: AMBER },
  { id: "budget_allocations", label: "Budget Allocations", color: "#F97316" },
] as const;

export type CollectionId = (typeof COLLECTIONS)[number]["id"];

// Skills — ids match ClientSkill enum values in argus/utils/skills.py exactly
export const SKILLS = [
  { id: "all_campaigns", label: "All Campaigns", icon: "◈", color: AMBER },
  { id: "single_client", label: "Own Campaigns", icon: "◉", color: "#3B82F6" },
  { id: "creative", label: "Ad Copy Review", icon: "◐", color: "#8B5CF6" },
  { id: "executive", label: "Strategy Docs", icon: "◑", color: "#10B981" },
  { id: "budget", label: "Budget Data", icon: "◒", color: "#F97316" },
  { id: "performance", label: "Performance", icon: "◓", color: "#EC4899" },
] as const;

export type SkillId = (typeof SKILLS)[number]["id"];

export const CLIENTS = [
  { id: "acme_corp", label: "Acme Corp (Retail)" },
  { id: "techflow", label: "TechFlow (SaaS)" },
  { id: "greenleaf", label: "GreenLeaf (Ecommerce)" },
  { id: "northstar", label: "NorthStar (Finance)" },
] as const;

export type ClientId = (typeof CLIENTS)[number]["id"];
