import type { LucideIcon } from "lucide-react";
import {
  Gauge,
  Layers,
  FileBarChart2,
  Workflow,
  FileSearch,
  ShieldCheck,
  Sparkles,
  Lock,
  Building2,
  ShieldAlert,
  HardHat,
  Factory,
  Landmark,
  HeartPulse,
  Zap,
  Flame,
  Shield,
  Radio,
  Briefcase,
  BookOpen,
  FileText,
  HelpCircle,
  Cloud,
  FileUp,
  Monitor,
  Users,
} from "lucide-react";

// Content for the marketing landing page only -- lives here rather than
// inline in components so the (fairly long) copy for each nav dropdown
// panel is easy to review/edit without wading through JSX. Per the
// explicit brief: no fabricated customer counts, no invented pricing, no
// lorem ipsum -- every string below is either a real product capability
// or an honest "not yet available" statement.

export interface DropdownCard {
  icon: LucideIcon;
  title: string;
  description: string;
  details: string[];
}

export const solutions: DropdownCard[] = [
  {
    icon: Gauge,
    title: "AI Tender Evaluation",
    description: "Automatically evaluate tender requirements against organizational capabilities.",
    details: [
      "Requirement extraction from raw tender PDFs, page by page",
      "Compliance matching against your capability records",
      "Evidence generation for every match, not just a verdict",
      "An executive GO / NO-GO recommendation with a confidence score",
    ],
  },
  {
    icon: Layers,
    title: "Capability Library",
    description: "Convert certifications, resumes, project records and company documents into a searchable capability database.",
    details: [
      "AI extraction of structured data from unstructured documents",
      "Automatic categorization by entity type (certifications, staff, projects, equipment, financials)",
      "Reusable capability records shared across every tender evaluation",
      "Freshness tracking so stale certifications get flagged automatically",
    ],
  },
  {
    icon: FileBarChart2,
    title: "Executive Reports",
    description: "Generate executive-ready GO / NO-GO reports with transparent evidence.",
    details: [
      "A one-page decision summary for leadership review",
      "The full compliance matrix behind the recommendation",
      "A gap analysis listing every unmet or at-risk requirement",
      "One-click PDF export for offline circulation",
    ],
  },
  {
    icon: Workflow,
    title: "Enterprise Workspace",
    description: "Manage tenders from upload to final recommendation.",
    details: [
      "A shared workspace per tender, from first upload to final call",
      "Status tracking across every stage of the evaluation",
      "An approval pipeline before a recommendation is finalized",
      "Company-scoped access so tenants never see each other's data",
    ],
  },
];

export const features: DropdownCard[] = [
  {
    icon: FileSearch,
    title: "AI Requirement Extraction",
    description: "Reads real tender PDFs and pulls out every requirement, page-attributed.",
    details: [
      "Handles both text-based and scanned (OCR) tender documents",
      "Preserves the source page for every extracted requirement",
      "Distinguishes mandatory requirements from informational clauses",
    ],
  },
  {
    icon: Layers,
    title: "Capability Matching",
    description: "Matches tender requirements against your certifications, staff, projects, equipment and financials.",
    details: [
      "Covers five capability record types out of the box",
      "Flags partial or conditional matches, not just yes/no",
      "Surfaces the exact record used as evidence for each match",
    ],
  },
  {
    icon: ShieldCheck,
    title: "Evidence-backed Decisions",
    description: "Every recommendation links directly to the document and clause behind it.",
    details: [
      "No verdict without a traceable source",
      "A full evidence trail from recommendation back to the original document",
      "Built for audit and internal review, not just a black-box score",
    ],
  },
  {
    icon: FileBarChart2,
    title: "Executive Reports",
    description: "A decision-ready report your leadership can act on in minutes, not hours.",
    details: [
      "Executive summary, confidence breakdown, and full compliance matrix",
      "Exportable as a shareable PDF",
      "Written for a non-technical reader, not just the bid team",
    ],
  },
  {
    icon: Sparkles,
    title: "Explainable AI",
    description: "Every AI judgment comes with the reasoning behind it, in plain language.",
    details: [
      "No opaque scores -- every status is paired with a written reason",
      "Confidence is broken down by document, entity, and matching stage",
      "Designed to be reviewed and challenged by a human, not just trusted blindly",
    ],
  },
  {
    icon: Lock,
    title: "Secure Document Storage",
    description: "Tender documents and company records are stored with access scoped to your organization.",
    details: [
      "Every document request is scoped to the authenticated company",
      "Uploads are validated before processing",
      "No document is ever visible across organizational boundaries",
    ],
  },
  {
    icon: Building2,
    title: "Multi-company Workspace",
    description: "Built as a multi-tenant platform from the ground up, not retrofitted.",
    details: [
      "Strict tenant isolation across documents, tenders, missions and evaluations",
      "Each organization sees only its own capability library and history",
      "Covered by an automated regression suite that protects this guarantee",
    ],
  },
  {
    icon: ShieldAlert,
    title: "Enterprise Security",
    description: "Rate limiting, authenticated access, and encrypted transport by default.",
    details: [
      "Rate limiting on every AI-cost-incurring and authentication endpoint",
      "Token-based authentication on every protected route",
      "Encrypted transport (TLS) for all traffic",
    ],
  },
];

// The Solutions mega-panel groups by industry vertical, not by abstract
// feature -- matches the founder's approved reference layout exactly.
// Same DropdownCard shape as everything else so it works with the same
// expand-in-place "Learn more" pattern used throughout the site.
export const solutionVerticals: DropdownCard[] = [
  {
    icon: HardHat,
    title: "Construction & Infrastructure",
    description: "Evaluate complex construction tenders with clause-level analysis and compliance intelligence.",
    details: [
      "Handles multi-phase infrastructure and EPC tender documents",
      "Flags mandatory eligibility gaps (turnover, prior projects, certifications) automatically",
      "Matches against your project completion and certification records",
    ],
  },
  {
    icon: Factory,
    title: "Manufacturing",
    description: "Assess technical and commercial requirements against your capabilities and certifications.",
    details: [
      "Matches quality and production certifications against tender requirements",
      "Tracks equipment and facility records as reusable capability evidence",
    ],
  },
  {
    icon: Monitor,
    title: "IT & Technology Services",
    description: "Simplify RFP evaluation for IT projects, software, cloud, and managed services.",
    details: [
      "Matches technical delivery history and staff qualifications against RFP scope",
      "Handles multi-phase software/services deliverable requirements",
    ],
  },
  {
    icon: HeartPulse,
    title: "Healthcare",
    description: "Ensure compliance and quality standards in medical equipment, hospital projects, and health sector tenders.",
    details: [
      "Matches regulatory and clinical-grade compliance requirements",
      "Tracks equipment and safety certifications as reusable capability records",
    ],
  },
  {
    icon: Flame,
    title: "Oil, Gas & Energy",
    description: "Evaluate EPC, O&M, and supply tenders with advanced risk scoring and technical compliance.",
    details: [
      "Handles high-compliance safety and operational-history criteria",
      "Matches technical delivery track record against tender scope",
    ],
  },
  {
    icon: Shield,
    title: "Defence & Aerospace",
    description: "Manage sensitive procurement with secure, traceable, and evidence-backed evaluation workflows.",
    details: [
      "Every recommendation carries a full evidence trail back to source documents",
      "Strict tenant isolation keeps sensitive procurement data scoped to your organization",
    ],
  },
  {
    icon: Landmark,
    title: "Government Contractors",
    description: "Meet public procurement requirements with transparency, auditability, and policy compliance.",
    details: [
      "Navigates mandatory eligibility criteria common in public-sector tenders",
      "Full audit trail from recommendation back to the original clause",
    ],
  },
  {
    icon: Users,
    title: "Enterprise Procurement",
    description: "Scale tender evaluations across teams with role-based access, collaboration, and centralized insights.",
    details: [
      "Company-scoped workspace shared across your evaluation team",
      "Status tracking and an approval pipeline before a recommendation is finalized",
    ],
  },
];

export const howItWorks: DropdownCard[] = [
  {
    icon: FileUp,
    title: "1. Upload",
    description: "Upload tender documents and company capability records -- certifications, resumes, project history, equipment, financials.",
    details: [
      "Handles both text-based and scanned (OCR) PDFs",
      "Company documents build a reusable capability library, not a one-time upload",
      "Every document stays scoped to your organization",
    ],
  },
  {
    icon: Sparkles,
    title: "2. Extract",
    description: "AI reads every page and extracts structured, page-attributed requirements and capability data.",
    details: [
      "Distinguishes mandatory requirements from informational clauses",
      "Preserves the exact source page for every extracted item",
      "Categorizes capability records automatically by entity type",
    ],
  },
  {
    icon: Layers,
    title: "3. Match",
    description: "Every requirement is matched against your capability records, with evidence attached.",
    details: [
      "Flags partial or conditional matches, not just yes/no",
      "Surfaces the exact record used as evidence for each match",
      "Bounded, concurrent matching keeps evaluation fast on large tenders",
    ],
  },
  {
    icon: FileBarChart2,
    title: "4. Decide",
    description: "Get an explainable GO / NO-GO recommendation with a full evidence trail, exportable as a report.",
    details: [
      "Executive summary, confidence breakdown, and full compliance matrix",
      "Every verdict is paired with a written reason, not a black-box score",
      "One-click PDF export for offline circulation",
    ],
  },
];

export interface Industry {
  icon: LucideIcon;
  name: string;
  description: string;
}

export const industries: Industry[] = [
  { icon: HardHat, name: "Construction", description: "Evaluate public and private works tenders against your project and compliance history." },
  { icon: Building2, name: "Infrastructure", description: "Match large-scale infrastructure RFPs against certifications and delivery track record." },
  { icon: Factory, name: "EPC", description: "Handle multi-phase engineering, procurement and construction tender requirements." },
  { icon: Factory, name: "Manufacturing", description: "Assess supply and production tenders against equipment and quality certifications." },
  { icon: Landmark, name: "Government", description: "Navigate mandatory eligibility criteria common in public-sector procurement." },
  { icon: HeartPulse, name: "Healthcare", description: "Evaluate tenders that require regulatory, safety and clinical-grade compliance." },
  { icon: Zap, name: "Energy", description: "Match capability records against energy-sector technical and safety requirements." },
  { icon: Flame, name: "Oil & Gas", description: "Handle high-compliance tenders with strict safety and operational-history criteria." },
  { icon: Shield, name: "Defence", description: "Work with tenders that carry stringent eligibility and security-clearance requirements." },
  { icon: Radio, name: "Telecom", description: "Evaluate network and infrastructure tenders against technical delivery history." },
  { icon: Briefcase, name: "Consulting", description: "Match advisory and services tenders against staff qualifications and past engagements." },
];

export interface ResourceItem {
  icon: LucideIcon;
  title: string;
  description: string;
}

export const resources: ResourceItem[] = [
  { icon: BookOpen, title: "Documentation", description: "Step-by-step guidance on using BidOps AI. Coming soon." },
  { icon: FileText, title: "Product Overview", description: "A walkthrough of the platform end to end. Coming soon." },
  { icon: HelpCircle, title: "FAQ", description: "Answers to common questions about the platform. Coming soon." },
  { icon: ShieldCheck, title: "Security", description: "Details on how BidOps AI handles data and access. Coming soon." },
  { icon: Sparkles, title: "Release Notes", description: "What's new in BidOps AI, as it ships. Coming soon." },
];

export const trustStatements: { icon: LucideIcon; label: string }[] = [
  { icon: ShieldCheck, label: "Enterprise Grade Security" },
  { icon: Lock, label: "End-to-End Encryption" },
  { icon: Sparkles, label: "Google AI Powered" },
  { icon: Cloud, label: "Hosted on Google Cloud" },
  { icon: Briefcase, label: "Designed for Procurement Teams" },
  { icon: FileSearch, label: "Explainable AI Decisions" },
];
