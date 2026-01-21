Below is a **brand foundation and UI design reference** for the **Circular Bioeconomy Alliance** (based on the organisation’s website content, structure and inferred visual style) that can be fed into an LLM or UI/UX team to tailor a UI design. The recommendations are *practical, structured and actionable*.

---

# Circular Bioeconomy Alliance — Branding & UI Design Guidelines

## 1. Brand Essence

**Mission alignment**

* Focus on *nature-first economic transition*, *harmonious growth*, *restorative ecological action*, *community resilience* and *global impact* as core narrative pillars. ([The Circular Bioeconomy Alliance][1])

**Core values**

* **Regenerative by design**
* **Science + indigenous knowledge**
* **Inclusivity & equity**
* **Transparency & clarity**
* **Global-local connectivity**

Design language should reflect these through calm, grounded, organic visuals, and structured organisation of content.

---

## 2. Color Palette

*Inferred from the theme (forest, ecosystem, circular bioeconomy) and typical sustainability branding (no official palette was found via HTML analysis). Use these colours to evoke nature, trust, growth and neutrality.*

### Core Brand Colours

| Role                                | Hex       | Usage                                           |
| ----------------------------------- | --------- | ----------------------------------------------- |
| **Forest Green (Primary)**          | `#2F5233` | Primary headers, high-impact CTAs, brand blocks |
| **Leaf Green (Accent)**             | `#6DAE58` | Secondary CTAs, highlights, icon accents        |
| **Earth Brown (Support)**           | `#8C6E4A` | Footers, borders, grounding elements            |
| **Sky/Water Blue (Neutral Accent)** | `#5CA4CF` | Links, info tags, subtle buttons                |
| **Off-White (Background)**          | `#F8F7F2` | Page background, large surfaces                 |
| **Dark Charcoal (Text)**            | `#212121` | Primary body text                               |

*Rationale*: Greens signal nature, sustainability and growth; brown grounds the palette in earth/ecology; off-white keeps contrast soft and readable; blue adds clarity and trust.

---

## 3. Typography

**Primary Typeface**

* *Serif for headings* — elegant, established tone (e.g., *Merriweather*, *Playfair Display*)
* *Sans-serif for body* — clean, legible for long reads (e.g., *Source Sans Pro*, *Roboto*)

**Hierarchy**

* **H1**: Serif — large, weight 700
* **H2**: Serif — weight 600
* **H3 / Section Titles**: Sans-serif — weight 600
* **Body text**: Sans-serif — weight 400, relaxed line spacing

*Guiding principle*: clear readability for narrative content, with serif lending weight to key thematic statements.

---

## 4. Design Language / Style

### Visual Metaphors

* **Circular motifs** — align with “circular bioeconomy” concept. Use soft overlapping circles in headers, icons, section dividers. ([Ideamatic Digital Experiences][2])
* **Organic shapes** — flowing curves rather than sharp angles; suggests ecosystems and cycles.

### Iconography

* **Line-based icons** with subtle fills
* Natural themes (leaf, globe, ecosystem, community, data/network)
* Use a consistent stroke weight across UI

### Imagery

* **Photography focus**: landscapes, communities, indigenous partners, regeneration in action
* **Colour tone**: muted, natural light, not oversaturated
* Avoid generic stock business photos; prioritise *authentic ecosystem and people images*

### Layout & White Space

* Generous white space around blocks to give content *breathing room*
* Modular “cards” for publications, team members and news entries
* Hierarchical sectioning for dense content (e.g., mission, work pillars, labs)

---

## 5. UI Components

### Navigation

* Sticky top nav with clear categories: **About | Members | Our Work | News | Resources**
* Secondary menus for subcategories
* Search input in header

### Buttons & CTAs

* **Primary Button**: Forest Green background, white text
* **Secondary Button**: Leaf Green border, transparent fill
* **Tertiary Buttons/Links**: Sky Blue text underline on hover

*Example:*

```css
.btn-primary {
    background: #2F5233;
    color: #FFFFFF;
}
.btn-secondary {
    border: 2px solid #6DAE58;
    color: #2F5233;
}
```

### Cards

* Soft rounded edges (8px)
* Slight shadow for depth
* Title, date/author, brief summary, CTA link

---

## 6. Tone & Messaging Style

* **Clear, authoritative, educational**
* Use **active voice**
* Values-first messaging (emphasise collaboration, ecosystems, regeneration)
* Short expert teaser headlines, deeper narrative body

**Example UI headline styles**

* *“Accelerating nature-first economies worldwide”*
* *“Living Labs: regenerative action in context”*

---

## 7. Accessibility & Contrast

* Ensure WCAG 2.1 AA compliance

  * Text minimum contrast 4.5:1
  * Button text contrast > 3:1
* Avoid overly bright contrasts; prefer *calm, natural tone*

---

## 8. Sample Style Tokens (for developer handoff)

```json
{
  "colors": {
    "primary": "#2F5233",
    "accent": "#6DAE58",
    "support": "#8C6E4A",
    "neutral": "#5CA4CF",
    "background": "#F8F7F2",
    "text": "#212121"
  },
  "font": {
    "heading": "Merriweather, serif",
    "body": "Source Sans Pro, sans-serif"
  },
  "button": {
    "primaryBg": "#2F5233",
    "primaryText": "#FFFFFF",
    "secondaryBorder": "#6DAE58",
    "secondaryText": "#2F5233"
  }
}
```

---

## 9. Application Examples

### Homepage

* Hero with large circular graphic, mission statement
* Featured news and Living Labs highlights (“cards”)
* Quick access to *About*, *Our Work*, *Resources*

### Resources Index

* Search + filters
* Card list with tag labels (Nature Finance, Publications, What is…)

### Member Directory

* Grid with logos + brief description

---

## 10. Design Principles Summary

1. **Nature first, clarity always.**
2. **Organise complexity into intuitive blocks.**
3. **Use circular/organic shapes as signature elements.**
4. **Prioritise readability and accessibility.**
5. **Visual identity must reflect *regeneration*, not extraction.**
