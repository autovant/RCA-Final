# Epic H – Frontend Modernisation

## Goal
Refresh the Executive Console UI with the described glassmorphic design system, accessibility improvements, and responsive interactions.

## Constraints
- Remain within the current Next.js + Tailwind setup; build design tokens atop existing configuration.
- Avoid introducing heavy new animation or state libraries unless already part of the repo.

## Checklist
- [ ] Inventory current Tailwind tokens/utilities; design expanded token set covering colors, spacing, typography, motion.
- [ ] Implement glassmorphic backgrounds, gradient layers, and elevation treatments in shared components.
- [ ] Update key pages (dashboard, job detail, related incidents) to use the new design system.
- [ ] Improve accessibility (contrast, keyboard navigation, focus states); run manual audits.
- [ ] Add motion/animation primitives (CSS or lightweight JS) for hover/transition effects.
- [ ] Ensure layouts remain responsive across breakpoints; verify touch-target sizes.
- [ ] Introduce Storybook-style documentation or component gallery if feasible within existing tooling.
- [ ] Write UI regression tests (Playwright or React Testing Library) for critical flows.
- [ ] Document design tokens, component usage guidelines, and accessibility checklist.

## Dependencies
- Benefits from backend work (Epics A/B/D/G) to surface richer data; coordinate for new UI states.

## Open Questions
- Do we require theme toggling (light/dark) in this pass? (Confirm before implementing.)
