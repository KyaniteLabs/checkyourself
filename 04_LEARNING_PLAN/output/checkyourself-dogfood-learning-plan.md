# CheckYourself Dogfood Learning Plan

Generated from the CheckYourself self-audit and remediation pass.

## Inferred current level

Advanced enough to build a useful diagnostic system and validation layer; next
growth area is turning local launch confidence into repeatable public proof.

## Language and accessibility mode

| Signal | Detected value | Evidence | Output choice |
|---|---|---|---|
| User language | English with Spanish context | KyaniteLabs public site exposes an `ES` route and this product is intended for mixed-skill users | English first, Spanish support |
| Project language | Mostly English | Public CheckYourself docs are English | Keep technical labels in English |
| Accessibility need | ADHD/autism/dyslexia-friendly | Product rules require plain-language learning | Short sections, concrete actions, visible success signals |

## Top concepts to learn next

### 1. Keep generated files out of the public repo

**Plain English:** Some tools make temporary files while they work. Those files
can be useful for you, but confusing or risky for everyone else if they get
published by accident.

**Español claro:** Algunas herramientas crean archivos temporales mientras
trabajan. Pueden servirte a ti, pero pueden confundir o exponer cosas privadas
si terminan publicados.

**Triggered by:** `CY-P2-001`, scanner-generated context output.

**Do this next:** Run each Creator Kit script once. After each run, check
whether it created a new file. If the file is only for local use, either ignore
it or write it into an output folder.

**Haz esto ahora:** Ejecuta cada script del Creator Kit una vez. Después mira si
creó archivos nuevos. Si son solo para uso local, ignóralos o mándalos a una
carpeta de salida.

**Success signal:** `git status --short` shows only intentional source changes.

**Learn from:** [GitHub Docs: Ignoring files](https://docs.github.com/en/get-started/getting-started-with-git/ignoring-files)

**Watch:** [Git Crash Course #9 - .gitignore File](https://www.youtube.com/watch?v=Oh6SeuOMnV4)

**Video trust note:** The Net Ninja is an established programming educator; the
GitHub Docs link remains the canonical source.

### 2. Make one place the source of truth

**Plain English:** If the README says one thing, the manifest says another, and
the dashboard guide says a third thing, an AI assistant may follow the wrong
instruction. Treat these files like signs in an airport: they all need to point
to the same gate.

**Español claro:** Si el README dice una cosa, el manifiesto otra, y la guía del
dashboard otra, un asistente de IA puede seguir la señal equivocada. Todas las
señales deben apuntar al mismo sitio.

**Triggered by:** `CY-P2-002`, dashboard path drift between docs and manifest.

**Do this next:** Pick the canonical answer for each workflow: where to start,
where reports go, and which dashboard template is the default. Then compare
`README.md`, `CONTEXT.md`, `10_DASHBOARD/CONTEXT.md`, and
`checkyourself.manifest.json` for contradictions.

**Haz esto ahora:** Decide una respuesta oficial para cada flujo: dónde empezar,
dónde guardar reportes, y cuál dashboard se usa. Luego compara los archivos de
contexto y el manifiesto para quitar contradicciones.

**Success signal:** A new agent can answer "which file do I use?" without
choosing between conflicting instructions.

**Learn from:** [Diataxis: Start here](https://diataxis.fr/start-here/)

**Watch:** [DjangoCon 2020 | What You Need to Know About Your Documentation - Daniele Procida](https://www.youtube.com/watch?v=qC1OYK5oqDo)

**Video trust note:** Daniele Procida created Diátaxis; the talk is from an
official conference channel.

### 3. Make CI prove the same things you prove locally

**Plain English:** CI is the robot checklist that runs when you push changes.
If you use five checks to say "this is ready" on your laptop, but GitHub only
runs one of them, the public repo is less protected than your local folder.

**Español claro:** CI es una lista automática que corre cuando subes cambios. Si
en tu máquina haces cinco pruebas, pero GitHub solo hace una, el repositorio
público queda menos protegido.

**Triggered by:** `CY-P2-003`, CI was narrower than the dogfood verification
suite.

**Do this next:** List every command you trust before launch. Put the safe,
repeatable ones in `.github/workflows/validate.yml`. Keep truly local checks in
the launch checklist.

**Haz esto ahora:** Haz una lista de los comandos que usas antes de lanzar. Pon
los repetibles en `.github/workflows/validate.yml`. Deja los locales en la lista
manual de lanzamiento.

**Success signal:** A bad Markdown link, broken JSON file, Python syntax error,
or accidental generated file fails before release.

**Learn from:** [GitHub Docs: Quickstart for GitHub Actions](https://docs.github.com/en/actions/get-started/quickstart)

**Watch:** [How to use GitHub Actions | GitHub for Beginners](https://www.youtube.com/watch?v=BQrohJ3PT7I)

**Video trust note:** Official GitHub channel.

### 4. Separate "works here" from "published and proven"

**Plain English:** A clean local repo is a good sign. It is not the same as a
public repo with a passing GitHub Actions run, a readable README, visible images,
and a release people can download.

**Español claro:** Que funcione en tu máquina es buena señal. Pero no es lo
mismo que un repo público con Actions en verde, README legible, imágenes que se
ven, y una release que otra persona puede usar.

**Triggered by:** `CY-P2-004`, public GitHub launch is not proven yet.

**Do this next:** After publishing, open the repo as a visitor would. Confirm
the README renders, the workflow image appears, Actions passes, and the release
notes match the actual version.

**Haz esto ahora:** Después de publicar, abre el repo como visitante. Revisa que
el README se vea bien, las imágenes carguen, Actions esté en verde, y las notas
de release coincidan con la versión real.

**Success signal:** The public GitHub page can be used by a stranger without
private context from this workspace.

**Learn from:** [GitHub Docs: Managing releases in a repository](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)

**Watch:** [How to automatically generate release notes for your project #Shorts](https://www.youtube.com/watch?v=8ryjj5x6FlQ)

**Video trust note:** Official GitHub channel; short format, so pair it with the
written docs.

### 5. Test the AI with one known-bad example

**Plain English:** If CheckYourself is supposed to catch risky app patterns, it
needs at least one fake risky app to practice on. That is what the dogfood
fixture is for.

**Español claro:** Si CheckYourself debe detectar patrones peligrosos, necesita
un ejemplo falso con errores conocidos para practicar. Para eso existe el
fixture de dogfood.

**Triggered by:** `CY-P3-004`, no lightweight eval fixture.

**Do this next:** Give `samples/dogfood-fixture-broken-app.md` to one AI tool
with the CheckYourself prompt. Check whether the answer includes all 20 coverage
rows, a complete backlog, approval gates, and a learning plan.

**Haz esto ahora:** Dale `samples/dogfood-fixture-broken-app.md` a una
herramienta de IA con el prompt de CheckYourself. Revisa si responde con las 20
superficies, backlog completo, aprobación antes de cambios, y plan de
aprendizaje.

**Success signal:** The AI does not stop at "top three issues" and does not
start fixing before approval.

**Learn from:** [OpenAI Cookbook: Getting started with OpenAI Evals](https://cookbook.openai.com/examples/evaluation/getting_started_with_openai_evals)

**Watch:** [Evals in Action: From Frontier Research to Production Applications](https://www.youtube.com/watch?v=YEaKXjHENyQ)

**Video trust note:** Official OpenAI channel.

### 6. Check visual outputs like a user, not only like a file

**Plain English:** An HTML dashboard can be valid code and still be hard to read.
Open it, look at it, and confirm a normal person can understand the score,
findings, next step, and learning priorities.

**Español claro:** Un dashboard puede ser HTML válido y aun así ser difícil de
leer. Ábrelo y confirma que una persona normal entiende el puntaje, los
hallazgos, el siguiente paso y las prioridades de aprendizaje.

**Triggered by:** `CY-P3-005`, dashboard smoke-check gap.

**Do this next:** Open the generated dashboard, compare it to the Markdown
report, and save a screenshot when the dashboard is part of launch proof.

**Haz esto ahora:** Abre el dashboard generado, compáralo con el reporte en
Markdown, y guarda una captura si el dashboard forma parte de la prueba de
lanzamiento.

**Success signal:** The screenshot shows the score, finding counts, backlog,
and learning section without broken layout.

**Learn from:** [Chrome for Developers: Lighthouse overview](https://developer.chrome.com/docs/lighthouse)

**Watch:** [Lighthouse - Totally Tooling Tips](https://www.youtube.com/watch?v=d98CAgQNeaM)

**Video trust note:** Official Chrome for Developers channel.

## Seven-day plan

1. Run one Creator Kit script and confirm any generated file is ignored or intentional.
2. Compare README, `CONTEXT.md`, dashboard docs, and manifest for one workflow.
3. Add or confirm one CI check that matches a local launch check.
4. Open the generated dashboard and compare its counts against the Markdown report.
5. Run the broken-app fixture through one AI tool and mark what it missed.
6. Tighten the prompt or context file around the missed behavior.
7. Re-run the self-audit and update the remediation log.

## What to ignore for now

- Full enterprise compliance workflows.
- Multi-page dashboard systems.
- Heavy automated browser regression unless the dashboard becomes a primary product surface.
