# Export tdd5 talk with same-page reveal steps

## Request and clarification

“create one for tdd5.md that is the new version”

“the continued should be on the same page. and should display more”

“the ideea is that a presentation is having steps even though the same page display a lot of content”

“in the menu on the left add pages as a suffix with gray aligned to right. because some titles have their own chapter numbers”

## Implementation

Export `tdd5.md` to `tdd5-talk.html` and `tdd5-talk.pptx` using the existing exporter and presentation style. Start at `# TDD Talk`; preparation, invitation and survey are outside the talk. Content-bearing sections are pages. Each `+++` adds a click-to-reveal step on the same page, preserving earlier content. Dense HTML pages scroll. The sidebar preserves source chapter numbers and displays separate gray, right-aligned page numbers. Include editable Java code, both embedded illustrations, the unit diagram and accompanying text, references, and source excerpts in PowerPoint notes.

## Regenerate

`python export_tdd.py --source tdd5.md --output tdd5-talk --section-pages`

## Verification

20 pages, 25 presentation steps. Source/body/code coverage, notes, embedded images, PowerPoint XML/package integrity, slide bounds, and five native click-build definitions checked. HTML same-page cumulative reveals, keyboard navigation, gray aligned page suffixes, loaded embedded images, desktop rendering, mobile overflow, and console checked. PowerPoint animations were checked structurally, not played in the PowerPoint application.
