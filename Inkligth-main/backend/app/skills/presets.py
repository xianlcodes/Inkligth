"""
预置技能模板

提供 9 个通用学术写作技能模板，对应 social-science-paper-writing 的 9 个操作模式，
剥离了课程特定规则，保留通用框架。在首次部署时安装到数据库。
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SkillPreset:
    name: str
    label_cn: str
    description: str
    desc_cn: str
    layer: str
    content: str
    match_topic: Optional[str] = None
    category: str = "general"
    priority: int = 0


PRESETS: list[SkillPreset] = [
    # -- 1. Topic Diagnosis --
    SkillPreset(
        name="topic_diagnosis",
        label_cn="选题诊断",
        description="Evaluate whether a research topic is viable, focused, and researchable",
        desc_cn="评估选题是否具有研究价值、是否可行、范围是否适当",
        layer="agents",
        match_topic="topic-diagnosis",
        priority=10,
        content="""You are evaluating whether a research topic is viable. Follow these guidelines:

## Evaluation Criteria
1. **Usefulness**: Does the topic address a real research problem or gap?
2. **Feasibility**: Can the topic be investigated with available time, resources, and access?
3. **Focus**: Is the scope narrow enough for the intended paper length and evidence?
4. **Field Relevance**: Does the topic fit within the intended academic field?
5. **Evidence Availability**: Is there sufficient existing or collectible evidence?

## Protocol
1. Extract the topic, object, field, scope, available materials, and intended paper type.
2. Rate each criterion and assign problem labels.
3. Output 2-4 revised topic directions and list missing information.

## Common Problem Labels
- **Topic Summary**: The topic describes a field without identifying a research problem.
- **Weak Problem Consciousness**: The topic gestures at an issue but does not pose a research question.
- **Scope Too Broad**: The topic cannot be addressed within the available space or evidence.
- **Missing Evidence Foundation**: The topic lacks observable, documentable, or collectible evidence.""",
    ),

    # -- 2. Research Question Formulation --
    SkillPreset(
        name="research_question_formulation",
        label_cn="研究问题设计",
        description="Refine a topic into specific, researchable questions",
        desc_cn="将宽泛选题转化为具体、可操作的研究问题",
        layer="agents",
        match_topic="research-question",
        priority=9,
        content="""You are refining a topic into research questions. Follow these guidelines:

## Protocol
1. Extract the core topic, available evidence, method constraints, and paper type.
2. Generate 2-4 candidate research questions that target different aspects or approaches.
3. Evaluate each candidate using the criteria below.
4. Output the refined question(s) with rationale and tradeoffs.

## Evaluation Criteria
A good research question:
- It is **specific** enough to guide method and evidence choices.
- It is **researchable** with available time, data, and resources.
- It is **small enough to answer** within the paper's scope and word limit.
- It **fits the available method and data**.
- It does **not require unavailable materials**.

## Output Format
For each candidate question, provide:
- The refined question itself.
- Scope boundary (what it covers and excludes).
- Evidence or data needed to answer it.
- Key tradeoff vs. alternatives.
- Risk flag if the question may be unanswerable.""",
    ),

    # -- 3. Outline Building --
    SkillPreset(
        name="outline_building",
        label_cn="论文大纲构建",
        description="Build or repair a paper outline from title to conclusion",
        desc_cn="从标题到结论，构建或优化论文的整体结构框架",
        layer="agents",
        match_topic="outline-building",
        priority=8,
        content="""You are building or repairing a paper outline. Follow these guidelines:

## Protocol
1. Identify title keywords, research question, tentative answer (thesis), method/material, and contribution.
2. Build sections from introduction through conclusion, giving each section one job.
3. Check whether literature, theory, method, analysis, and conclusion all return to the research question.
4. Mark drift as **Structure Drift**.

## Standard Structure
1. **Introduction**: research question, puzzle, stakes, thesis, contribution, roadmap.
2. **Literature Review**: organize prior work into debates, show the gap or tension.
3. **Theory or Framework**: define core concepts, explain expected relationships.
4. **Methodology**: design, case selection, data, measurement, analysis, limitations.
5. **Analysis**: present evidence in an order that tests or develops the argument.
6. **Discussion**: interpret findings, address alternatives, connect back to theory.
7. **Conclusion**: restate answer, contribution, limitations, future research.

## Title Checklist
- Research object is clear.
- Scope is focused enough for the paper length and evidence.
- Relationship, puzzle, method, or case is visible when needed.
- Title keywords match the paper body.

## Missing Information Rule
When information is missing, state: what is missing, why it matters, what the user should provide, and what limited work can still be done without it.""",
    ),

    # -- 4. Literature Review Planning --
    SkillPreset(
        name="literature_review_planning",
        label_cn="文献综述规划",
        description="Plan search scope, source clusters, synthesis logic, and gap statement",
        desc_cn="规划文献检索范围、主题聚类、综合逻辑和研究空白",
        layer="agents",
        match_topic="literature-review",
        priority=7,
        content="""You are planning a literature review. Follow these guidelines:

## Protocol
1. Define literature clusters by: debate (competing explanations), concept (how a concept evolved), variable/mechanism (known relationships), method (different approaches), school (theoretical traditions), case (comparative analysis), or period (how findings changed over time).
2. Define inclusion logic -- what criteria qualify a source for inclusion or exclusion.
3. Identify important source types needed (classic works, recent advances, field-specific studies).
4. Formulate synthesis questions -- what the review needs to establish for each cluster.
5. Draft a gap statement and show how it leads to the research question.

## Quality Checklist
- Review is organized by analytic logic, not author-by-author listing.
- Sources are relevant, direct, important, and preferably first-hand.
- The review includes evaluation, not only summary.
- The research gap is explicit.
- The review justifies the paper's question or hypothesis.
- Missing source clusters are marked as **Evidence Gap**.

## Output
- Literature clusters with rationale.
- Inclusion/exclusion logic.
- Gap statement connecting to the research question.
- Risk flags for missing or hard-to-access sources.""",
    ),

    # -- 5. Literature Search to Review --
    SkillPreset(
        name="literature_search_to_review",
        label_cn="文献检索与综述撰写",
        description="Search literature, create structured notes, build synthesis matrix, and draft review",
        desc_cn="检索文献、做结构化笔记、构建综合矩阵并撰写综述",
        layer="agents",
        match_topic="literature-search",
        priority=6,
        content="""You are helping search for literature, create structured source notes, and draft a literature review. Follow these guidelines:

## Protocol
1. Extract the paper topic, research question, keywords (including synonyms), case/region terms, method terms, time range, and exclusion terms.
2. Search literature through available databases and tools. State which tools were used and any blockers.
3. Screen results for relevance, directness, importance, authority/recency, and first-hand status.
4. Produce structured notes for each source.
5. Build a synthesis matrix from structured notes.
6. Draft the literature review from verified notes, ending with a gap-to-question transition.

## Structured Note Format
For each source, document: metadata, research question, theory/concepts, method/data, main finding, contribution, limitation, relation to this paper, cluster assignment, and any citation risks.

## Source Status Labels
- **candidate source**: found but not yet screened.
- **metadata only**: bibliographic record available only.
- **abstract only**: abstract read but not full text.
- **full text read**: full content reviewed.

## Important Rules
- Never fabricate authors, titles, years, journals, or other publication metadata.
- Do not use a source for detailed findings or methods unless the abstract, full text, or user-provided excerpts support those details.
- Metadata-only records can support only bibliographic traceability and rough relevance.
- Mark missing or unverifiable sources as **Citation Risk**.

## Synthesis Matrix
Organize by cluster, listing sources, shared claims, disagreements/limits, and relation to the paper.""",
    ),

    # -- 6. Draft Review --
    SkillPreset(
        name="draft_review",
        label_cn="论文初稿评审",
        description="Diagnose a whole paper draft for argument, structure, evidence, and method",
        desc_cn="从论点、结构、证据、方法等方面全面诊断论文初稿",
        layer="agents",
        match_topic="draft-review",
        priority=5,
        content="""You are diagnosing a whole paper draft. Follow these guidelines:

## Protocol
1. Identify the paper's research question, thesis/answer, structure, method, data/materials, evidence, and citation status.
2. Apply the **Pass / Partial / Fail** scale to each relevant area.
3. Assign diagnosis labels with evidence from the draft.
4. Output priority fixes before optional improvements.

## Pass / Partial / Fail Scale
- **Pass**: The item is explicit, specific, supported, and integrated.
- **Partial**: The item is present but vague, late, under-supported, inconsistent, or not yet integrated.
- **Fail**: The item is absent, contradicted, unsupported, fabricated, or impossible to assess.

## Areas to Evaluate
- **Argument**: Clear research question? Thesis answers it? Each section advances the thesis?
- **Structure**: Clear section jobs? Logical flow? Strong topic sentences?
- **Literature**: Organized analytically? Sources synthesized? Gap explicit?
- **Theory**: Concepts defined? Framework guides analysis? Not merely decorative?
- **Method**: Fits the question? Data/materials described? Limitations acknowledged?
- **Evidence**: Claims supported? Appropriate analysis? Clear interpretation?

## Common Diagnosis Labels
Topic Summary, Weak Problem Consciousness, Research Question Missing, Literature Listing, Missing Research Gap, Theory Decoration, Conceptual Ambiguity, Method Mismatch, Evidence Gap, Causal Overclaim, Citation Risk, Structure Drift, Conclusion Overreach.

For each **Partial** or **Fail**, give an actionable fix with: target location, operation, and expected improvement.""",
    ),

    # -- 7. Section Revision --
    SkillPreset(
        name="section_revision",
        label_cn="章节修订优化",
        description="Rewrite one section while preserving claims and marking evidence gaps",
        desc_cn="重写或修订论文的某一章节，保留原有论点并标注证据缺口",
        layer="agents",
        match_topic="section-revision",
        priority=4,
        content="""You are revising a specific section of an academic paper. Follow these guidelines:

## Protocol
1. Identify the section's job in the whole paper (e.g., introduction frames the problem, literature review establishes the gap, analysis tests the argument, conclusion answers the question).
2. Diagnose the section using relevant criteria from argument, structure, evidence, and style.
3. Rewrite only claims supported by provided information -- preserve the user's verifiable claims.
4. Mark placeholders for missing evidence, citations, data, or concept definitions.

## Revision Output Format
```markdown
## Revision Goal
[What is being fixed.]

## Revised Section
[Text.]

## Change Log
- Claim clarified:
- Structure changed:
- Evidence gap marked:
- Citation risk marked:
```

## Principles
- Do not add new unsupported claims.
- When evidence is missing, mark it as a placeholder rather than fabricating.
- Make topic sentences argumentative -- state the analytic claim.
- Add transitions that explain logical movement, not just sequence.""",
    ),

    # -- 8. Citation and Evidence Check --
    SkillPreset(
        name="citation_and_evidence_check",
        label_cn="引用与证据核查",
        description="Check citations, data claims, quotations, and evidence support",
        desc_cn="检查引用准确性、数据来源、引文格式和证据支撑情况",
        layer="agents",
        match_topic="citation-check",
        priority=3,
        content="""You are checking citations, evidence support, and data claims in an academic paper. Follow these guidelines:

## Protocol
1. Extract each claim, its current support, source metadata, quotations, data claims, and causal verbs.
2. For each claim, assess: Is it supported by a verifiable source? Is the citation accurate? Is the quotation exact and paginated? Is the data provenance clear?
3. Assign risk labels and provide safe rewording suggestions.

## Risk Labels
- **Citation Risk**: Citation missing, unverifiable, second-hand, or mismatched with the claim.
- **Evidence Gap**: Claim requires evidence but no source or data provided.
- **Causal Overclaim**: Causal language exceeds what the design or evidence supports.
- **Quotation Risk**: Direct quotation lacks exact wording, quotation marks, or page numbers.
- **Data Provenance Gap**: Statistic, dataset, or document source is unclear.

## Output Format
| Claim | Current support | Risk label | Needed evidence | Safe wording now |
|---|---|---|---|---|

## Golden Rules
- Never fabricate authors, titles, years, journals, page numbers, or reference entries.
- Never fabricate data, interviews, survey responses, or statistical findings.
- Mark borrowed ideas, paraphrases, and quotations needing citation support.
- Check whether each citation actually supports the attached claim.
- Require quotation marks and page numbers for direct quotations when available.
- Prefer original sources over second-hand citations.
- Do not silently normalize incomplete references -- mark missing fields.""",
    ),

    # -- 9. Pre-submission Check --
    SkillPreset(
        name="pre_submission_check",
        label_cn="投稿前终审检查",
        description="Final readiness review: blockers, polish, and submit judgment",
        desc_cn="投稿前全面检查，区分阻塞性问题与可优化项，给出是否可投稿的判断",
        layer="agents",
        match_topic="pre-submission",
        priority=2,
        content="""You are performing a final readiness review before paper submission. Follow these guidelines:

## Protocol
1. Run a final checklist across all areas.
2. Separate **blockers** (must-fix issues) from **polish** (nice-to-have improvements).
3. Identify any unverified source, data, page number, quotation, or method claim.
4. Output a **submit** or **revise-before-submit** judgment.

## Final Checklist by Area
- **Research Question**: Clearly stated? A real problem, not just a topic?
- **Structure**: All sections return to the question? Transitions clear?
- **Literature**: Gap explicit? All sources verified and cited correctly?
- **Theory**: Concepts defined? Framework actively guides the analysis?
- **Method**: Design fits the question? Data sources clear? Limitations acknowledged?
- **Evidence**: All major claims supported? Sources verifiable?
- **Citations**: All references traceable? No fabricated or incomplete entries?
- **Style**: Language precise and formal? Consistent formatting throughout?
- **Conclusion**: Direct answer present? Contribution stated? No new unsupported claims?

## Blocker Examples
Missing evidence for a central claim, fabricated citation, method does not fit the research question, unsupported causal claims, incomplete data provenance.

## Polish Examples
Weak transitions, uneven paragraph length, minor formatting inconsistencies, optional additional citations.

## Output Format
Provide a summary table of all findings, marked as blocker or polish, then give the final submission judgment with rationale.""",
    ),
]


def get_presets() -> list[SkillPreset]:
    """获取预置技能模板列表"""
    return PRESETS


def get_preset(name: str) -> Optional[SkillPreset]:
    """按名称获取预置技能"""
    for p in PRESETS:
        if p.name == name:
            return p
    return None
