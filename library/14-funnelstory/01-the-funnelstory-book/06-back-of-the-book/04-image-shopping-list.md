# Image shopping list

The book uses three sources of images. This list says what each chapter wants, where to get it, and what the file should be called. Save collected files into the book's `img/` folder with exactly these names, and the chapter can reference them.

## The three sources

1. **Drawn diagrams (SVG).** Written by hand into the book's `img/` folder. Done: 13 figures, listed at the bottom. They explain mechanisms and need no outside source.
2. **Screenshots.** From FunnelStory's public surfaces and customers' public websites. Collected through Chrome.
3. **Generated illustrations (ChatGPT).** Mood and metaphor images for story openings. Generic only.

> [!NOTE] Two hard limits on images
> **Never upload a customer workspace screenshot, a transcript or a flow to ChatGPT or any outside tool.** Prompts below describe generic scenes only, with no product, customer or people names. And **never screenshot a customer's logged-in workspace into the book** unless you are sure it contains nothing the NDA covers. Public marketing pages and docs are fine.

## Screenshots (public sources only)

**Status, 2026-11-11: 16 of 18 collected and placed.** ClickUp and Trellix home pages could not be captured (bot protection), and were left out. All art and screenshots are saved as `.jpg` to stay light.

Filenames are `shot-<chapter>-<name>.png`.

| File | Where | Chapter |
|---|---|---|
| shot-1-1-homepage.jpg | funnelstory.ai home page | 1.1 |
| shot-1-1-company.jpg | funnelstory.ai/company | 1.1 |
| shot-1-3-docs-home.jpg | docs.funnelstory.ai start page | 1.3 |
| shot-1-3-graph-docs.jpg | Docs page on the Customer Intelligence Graph | 1.3 |
| shot-2-1-connections-docs.jpg | Docs page listing the connectors | 2.1 |
| shot-2-4-needle-movers-docs.jpg | Docs page on needle movers | 2.4 |
| shot-2-5-dossier-docs.jpg | Docs page on the Account Dossier | 2.5 |
| shot-3-1-mcp-docs.jpg | Docs page on the MCP server | 3.1 |
| shot-3-2-flow-docs.jpg | Docs page on the flow builder | 3.2 |
| shot-1-1-release-notes.jpg | Latest month in the public release notes | 1.1 |
| shot-2-7-status.jpg | funnelstory.statuspage.io | 2.7 |
| shot-4-1-greyorange-site.jpg | GreyOrange's public website home page | 4.1 |
| shot-4-5-showpad-site.jpg | Showpad's public home page | 4.5 |
| shot-4-6-descope-site.jpg | Descope's public home page | 4.6 |
| shot-4-7-docusign-site.jpg | DocuSign's public home page | 4.7 |
| shot-4-8-aviz-site.jpg | Aviz Networks' public home page | 4.8 |

## ChatGPT illustrations (generic, no names). All 17 done and placed

Use one consistent style so the book looks like one thing. Add to every prompt: "flat vector illustration, soft colours, white background, no text, no logos, square, simple shapes".

| File | Prompt (add the style line) | Chapter |
|---|---|---|
| art-saturday.jpg | A person at a desk late in the evening, pulling dates from a spreadsheet into presentation slides, a cup of tea going cold | 1.1 |
| art-six-products.jpg | One large puzzle made of six coloured pieces, five in place, one lifted away | 1.2 |
| art-analyst.jpg | A robot assistant standing in front of a tall messy pile of folders, looking lost | 1.3 |
| art-silent-pipe.jpg | A pipe carrying glowing blocks from left to right, with a section in the middle that has gone dark, and a green light still showing on the control panel | 2.1 |
| art-polite-letter.jpg | A neat envelope with a smiley sticker, but a red storm cloud inside the envelope | 2.2 |
| art-six-zeros.jpg | Six identical small gauges, all with needles pointing at zero, next to a calendar with a tick on it | 2.3 |
| art-needle.jpg | A large gauge with a needle starting to move, and a person with binoculars looking at it from far away | 2.4 |
| art-four-screens.jpg | Four small screens on a wall, each showing a different shape for the same object | 2.5 |
| art-empty-result.jpg | A magnifying glass over an empty table, with a locked door in the background | 2.6 |
| art-law.jpg | A tall library with each shelf labelled by a single icon, and a librarian holding one key | 2.7 |
| art-two-agents.jpg | Two robots side by side, one wearing a hard hat and labelled by a toolbox, the other holding a blank scroll | 3.1 |
| art-gate.jpg | A big gate with a padlock and a green stop sign, a small robot waiting politely in front of it | 3.4 |
| art-950.jpg | A very large crowd of tiny figures all gathered at one door that is not the door they were pointed to | 3.6 |
| art-22-cards.jpg | Twenty-two small cards in a neat row on a desk, completely untouched, with dust on them | 3.7 |
| art-two-ids.jpg | Two keys that look similar but have different shapes, and one lock | 4.1 |
| art-alert-bell.jpg | A bell with a speech bubble containing a small calendar, ringing once, with many other bells silent behind it | 4.2 |
| art-aws.jpg | A staircase that leads up to a cloud with a large tag attached to the front door | 4.7 |

## Drawn diagrams already in the book

| File | Chapter |
|---|---|
| get-set-go.svg | 1.3 |
| product-path.svg | 2.1 |
| impact-sentiment.svg | 2.2 |
| score-from-50.svg | 2.3 |
| needle-lifecycle.svg | 2.4 |
| four-surfaces.svg | 2.5 |
| vtable-buckets.svg | 2.6 |
| flow-limits.svg | 3.3 |
| draft-gate.svg | 3.4 |
| surfaces.svg | 3.6 |
| value-ladder.svg | 3.7 |
| diagnostic-order.svg | 4.0 |
| alert-agent.svg | 4.2 |

## How to add one to a chapter

Put the file in `img/` and add a line in the chapter, alone on its own line, like this:

```
![what it shows](../img/art-gate.jpg "Figure N. The caption")
```

The reader shows it as a figure, and a tap opens it full screen. Keep each image under about 200 KB so the offline build stays light.
