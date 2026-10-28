# Export tdd4 talk to HTML and PowerPoint

## Request

“I created a new presentation in tdd4. Create again the presentations for them tdd4-talk.html and tdd4-talk.pptx”

## Scope

Use `tdd4.md`, preserve its talk content and hierarchy, and reuse the established July-style HTML presentation and editable PowerPoint export. Exclude preparation TODOs before `# TDD Talk`. Use content-bearing sections as slides and `+++` as additional presentation stops. Embed `red-green-refactor.png` and the XP practices image stored in `xp-practices.md`. Keep outputs self-contained and preserve Markdown source excerpts in PowerPoint notes.

## Regenerate

`python export_tdd.py --source tdd4.md --output tdd4-talk --section-pages`

## Acceptance

Both requested files exist, contain the same talk in the same order, include both images and the unit diagram, retain navigation and keyboard controls in HTML, and pass content coverage, PowerPoint package/shape checks and browser verification.
