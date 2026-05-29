# 04 - Bespoke Learning Plan

CheckYourself should not only fix the app. It should help the user learn from
what the app revealed, without turning the report into homework soup.

The learning plan is generated after the diagnostic and updated after remediation.

## Principle

Do not create a generic course.

Every learning item must tie back to:

- a diagnostic finding;
- a remediation step;
- an unknown that mattered;
- a repeated mistake pattern;
- a production concept the user needs for this app.

## User-level adaptation

If the user's level is unknown, infer it gently from context and label confidence.

Use three explanation layers:

1. **Beginner:** What this means and why it matters.
2. **Builder:** How it appears in this project.
3. **Advanced:** Edge cases, tradeoffs, and deeper patterns.

## Language and accessibility

Detect language from:

- the user's prompt;
- README/docs and UI strings;
- locale files such as `es.json`, `i18n/`, `locales/`, or translation tables;
- comments and domain vocabulary in the codebase.

Identify:

- primary output language;
- candidate second language;
- evidence for the candidate;
- whether the user explicitly requested or confirmed it.

If the user explicitly named the second language, use it. If the candidate is
only inferred from mixed language, region, locale files, audience, or domain
signals, ask before making the learning plan bilingual. If no useful candidate
is found, write in the primary language and offer a bilingual version.

Write for ADHD, autism, and dyslexia:

- one idea per section;
- short paragraphs;
- concrete verbs;
- visible success signals;
- glossary for jargon;
- no shame language;
- no dense curriculum dumps.

## Source reliability

For each top learning priority, record:

- source type: official docs, standards body, original author, official vendor,
  conference/community, or established educator;
- authority_level: high, medium, or supplemental;
- why_this_source_is_trusted;
- checked_at date;
- whether the video is canonical or only a practical companion.

Authority levels:

- high: official docs, standards bodies, original authors, or official vendor
  channels for that exact topic;
- medium: respected conference talks, documentation communities, or well-known
  maintainers explaining their own domain;
- supplemental: useful educator content that helps a beginner act, but should
  be paired with a stronger written source.

The written source is the canonical learning reference unless the video is from
the same official or original-author source.

## Required sections

Use [`../05_OUTPUT_TEMPLATES/bespoke-learning-plan.md`](../05_OUTPUT_TEMPLATES/bespoke-learning-plan.md).

The plan must include:

- inferred current level;
- top concepts to learn next;
- findings that triggered each concept;
- 7-day practical plan;
- 30-day deeper plan;
- project-based exercises;
- one live source or video link for each top learning priority;
- one real relevant YouTube video from a trusted source for each top priority
  when a suitable video exists;
- terms glossary;
- what to ignore for now;
- recommended next diagnostic after learning.
