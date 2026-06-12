from dataclasses import dataclass
from string import Formatter
from typing import Literal

PromptName = Literal[
    "draft_section",
    "continue_draft",
    "polish_selection",
    "revise_latex",
    "summarize_references",
    "suggest_citations",
]


class PromptRenderError(ValueError):
    pass


@dataclass(frozen=True)
class PromptTemplate:
    name: PromptName
    system: str
    user: str

    @property
    def variables(self) -> set[str]:
        names: set[str] = set()
        for template in (self.system, self.user):
            for _, field_name, _, _ in Formatter().parse(template):
                if field_name:
                    names.add(field_name)
        return names

    def render(self, values: dict[str, str]) -> "RenderedPrompt":
        expected = self.variables
        missing = sorted(name for name in expected if not values.get(name))
        if missing:
            raise PromptRenderError(
                f"Missing prompt variables for {self.name}: {', '.join(missing)}"
            )
        extras = sorted(name for name in values if name not in expected)
        if extras:
            raise PromptRenderError(
                f"Unexpected prompt variables for {self.name}: {', '.join(extras)}"
            )
        return RenderedPrompt(
            name=self.name,
            system=self.system.format(**values),
            user=self.user.format(**values),
        )


@dataclass(frozen=True)
class RenderedPrompt:
    name: PromptName
    system: str
    user: str


PROMPT_TEMPLATES: dict[PromptName, PromptTemplate] = {
    "draft_section": PromptTemplate(
        name="draft_section",
        system=(
            "You are a careful academic writing assistant. Produce concise, "
            "publication-ready LaTeX that matches the paper's existing voice. "
            "Return only LaTeX source unless the user explicitly asks otherwise."
        ),
        user=(
            "Paper title:\n{paper_title}\n\n"
            "Target section:\n{section_title}\n\n"
            "Relevant context:\n{context}\n\n"
            "Draft requirements:\n{requirements}"
        ),
    ),
    "continue_draft": PromptTemplate(
        name="continue_draft",
        system=(
            "You continue academic LaTeX manuscripts. Match the existing voice, "
            "preserve valid LaTeX syntax, and return only the continuation text."
        ),
        user=(
            "Paper title:\n{paper_title}\n\n"
            "Draft context before the cursor:\n{draft_context}\n\n"
            "Relevant reference context:\n{reference_context}\n\n"
            "Continuation length:\n{target_length}\n\n"
            "Author instruction:\n{instruction}"
        ),
    ),
    "polish_selection": PromptTemplate(
        name="polish_selection",
        system=(
            "You polish academic LaTeX text. Preserve technical meaning, citations, "
            "labels, commands, math, and environments. Return only the edited text."
        ),
        user=(
            "Paper title:\n{paper_title}\n\n"
            "Edit operation:\n{operation}\n\n"
            "Author instruction:\n{instruction}\n\n"
            "Surrounding draft context:\n{surrounding_context}\n\n"
            "Relevant reference context:\n{reference_context}\n\n"
            "Selected text to edit:\n{selected_text}"
        ),
    ),
    "revise_latex": PromptTemplate(
        name="revise_latex",
        system=(
            "You revise LaTeX manuscripts while preserving scientific meaning. "
            "Keep commands, labels, citations, equations, and tables valid."
        ),
        user=(
            "Revision goal:\n{revision_goal}\n\n"
            "Current LaTeX:\n{latex_source}\n\n"
            "Return the revised LaTeX only."
        ),
    ),
    "summarize_references": PromptTemplate(
        name="summarize_references",
        system=(
            "You summarize source material for an academic paper. Distinguish "
            "claims supported by the supplied references from interpretation."
        ),
        user=(
            "Paper topic:\n{paper_topic}\n\n"
            "Reference excerpts:\n{reference_excerpts}\n\n"
            "Summarize the evidence and list the most useful citation targets."
        ),
    ),
    "suggest_citations": PromptTemplate(
        name="suggest_citations",
        system=(
            "You recommend citations from a provided reference library. Use only "
            "the references in the prompt and do not invent bibliographic details. "
            "Summarize each recommended reference's relevance before suggesting "
            "how it should be cited."
        ),
        user=(
            "Manuscript passage:\n{passage}\n\n"
            "Available references:\n{reference_summaries}\n\n"
            "Author instruction:\n{instruction}\n\n"
            "Return concise reference summaries, citation suggestions, and a short "
            "rationale for each suggestion."
        ),
    ),
}


def render_prompt(name: PromptName, **values: str) -> RenderedPrompt:
    try:
        template = PROMPT_TEMPLATES[name]
    except KeyError as exc:
        raise PromptRenderError(f"Unknown prompt template: {name}") from exc
    return template.render(values)
