# 04 — Bespoke Learning Plan

CheckYourself should not only fix the app. It should help the user learn from what the app revealed.

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

If the user or codebase is not English-only, put the user's/project language
first and include English labels for common production terms. If language
evidence is mixed, make the learning plan bilingual.

Write for ADHD, autism, and dyslexia:

- one idea per section;
- short paragraphs;
- concrete verbs;
- visible success signals;
- glossary for jargon;
- no shame language;
- no dense curriculum dumps.

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
