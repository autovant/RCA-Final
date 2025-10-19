# Visual Regression Testing Configuration

This document outlines the visual regression testing strategy for the RCA application UI components, with focus on the newly implemented Unified Ingestion features.

## Recommended Tool: Chromatic

**Chromatic** is recommended for visual regression testing because it:
- Integrates seamlessly with Storybook
- Provides pixel-perfect diff detection
- Supports CI/CD integration
- Offers UI review workflows
- Maintains snapshot history

### Alternative: Percy

Percy (by BrowserStack) is another excellent option with similar features.

---

## Setup Instructions

### 1. Install Chromatic

```bash
cd ui
npm install --save-dev chromatic
```

### 2. Create Storybook Stories

Create stories for critical components in `ui/src/components/**/*.stories.tsx`:

```typescript
// Example: PlatformDetectionCard.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import { PlatformDetectionCard } from './PlatformDetectionCard';

const meta: Meta<typeof PlatformDetectionCard> = {
  title: 'Jobs/PlatformDetectionCard',
  component: PlatformDetectionCard,
  parameters: {
    layout: 'padded',
    backgrounds: {
      default: 'dark',
      values: [
        { name: 'dark', value: '#0f172a' },
      ],
    },
  },
};

export default meta;
type Story = StoryObj<typeof PlatformDetectionCard>;

export const Default: Story = {
  args: {
    data: {
      detected_platform: 'blue_prism',
      confidence_score: 0.92,
      detection_method: 'parser',
      parser_executed: true,
      parser_version: '1.2.0',
      extracted_entities: [
        { entity_type: 'process', value: 'MainProcess', source_file: 'main.xml' },
        { entity_type: 'object', value: 'EmailHandler', source_file: 'objects/email.xml' },
        { entity_type: 'data_item', value: 'CustomerID', source_file: 'main.xml' },
      ],
    },
  },
};

export const LowConfidence: Story = {
  args: {
    data: {
      detected_platform: 'uipath',
      confidence_score: 0.45,
      detection_method: 'heuristic',
      parser_executed: false,
      parser_version: null,
      extracted_entities: [],
    },
  },
};

export const Loading: Story = {
  args: {
    loading: true,
    data: null,
  },
};

export const Empty: Story = {
  args: {
    data: null,
    loading: false,
  },
};

export const ManyEntities: Story = {
  args: {
    data: {
      detected_platform: 'uipath',
      confidence_score: 0.98,
      detection_method: 'parser',
      parser_executed: true,
      parser_version: '2.1.0',
      extracted_entities: Array.from({ length: 50 }, (_, i) => ({
        entity_type: i % 3 === 0 ? 'workflow' : i % 3 === 1 ? 'activity' : 'variable',
        value: `Entity_${i + 1}`,
        source_file: `file${Math.floor(i / 10)}.xaml`,
      })),
    },
  },
};
```

### 3. Run Chromatic

```bash
# Get project token from chromatic.com
npx chromatic --project-token=<your-project-token>
```

### 4. Add to CI/CD Pipeline

```yaml
# .github/workflows/chromatic.yml
name: 'Chromatic'

on: 
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  chromatic:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: 18
      
      - name: Install dependencies
        run: |
          cd ui
          npm ci
      
      - name: Run Chromatic
        uses: chromaui/action@v1
        with:
          projectToken: ${{ secrets.CHROMATIC_PROJECT_TOKEN }}
          workingDir: ui
          buildScriptName: build-storybook
```

---

## Critical Test Scenarios

### Platform Detection Card

1. **All Platform Variants**
   - Blue Prism (blue badge)
   - UiPath (orange badge)
   - Appian (purple badge)
   - Automation Anywhere (red badge)
   - Pega (green badge)
   - Unknown (gray badge)

2. **Confidence Levels**
   - 0% confidence
   - 25% confidence (warning threshold)
   - 50% confidence
   - 75% confidence
   - 100% confidence

3. **Entity Counts**
   - 0 entities (with parser executed)
   - 1-5 entities
   - 10-20 entities
   - 50+ entities (overflow test)

4. **Parser States**
   - Parser not executed (heuristic detection)
   - Parser executed successfully
   - Different parser versions

5. **Loading & Empty States**
   - Loading skeleton
   - No data available
   - Error state (if implemented)

### Related Incidents List

1. **Item Counts**
   - Empty state (0 incidents)
   - Single incident
   - 5 incidents
   - 20+ incidents (scroll test)

2. **Relevance Scores**
   - Low relevance (< 50%)
   - Medium relevance (50-80%)
   - High relevance (> 80%)

3. **Platform Variants**
   - All platform badge colors
   - Unknown platforms

4. **Fingerprint States**
   - All fingerprint status variants
   - Mixed states in list

5. **Safeguards**
   - No safeguards
   - 1-3 safeguards
   - Many safeguards (overflow)

6. **Responsive Layouts**
   - Mobile (375px)
   - Tablet (768px)
   - Desktop (1280px)
   - Wide (1920px)

7. **Loading & Empty States**
   - Loading spinner
   - Empty state with icon
   - Error state (if implemented)

### Progress Bar Component

1. **All Variants**
   - Primary (blue-cyan gradient)
   - Success (green gradient)
   - Warning (yellow-orange gradient)
   - Error (red gradient)
   - Info (sky-blue gradient)

2. **All Sizes**
   - Small (h-1)
   - Medium (h-2)
   - Large (h-3)

3. **Value Ranges**
   - 0% (empty)
   - 25%
   - 50%
   - 75%
   - 100% (full)

4. **Label Options**
   - With label
   - Without label
   - Custom label format

### Entity Pill Component

1. **All Variants**
   - Default
   - Primary (blue)
   - Success (green)
   - Warning (yellow)
   - Error (red)
   - Info (cyan)

2. **All Sizes**
   - Small
   - Medium
   - Large

3. **Interactive States**
   - Non-interactive (no onClick)
   - Interactive (with onClick)
   - Hover state (interactive)

4. **Content Tests**
   - Short label (1 word)
   - Medium label (2-3 words)
   - Long label (5+ words, overflow)
   - With tooltip
   - Without tooltip

---

## Viewport Testing

Test all components at these breakpoints:

| Breakpoint | Width | Description |
|------------|-------|-------------|
| Mobile Small | 375px | iPhone SE |
| Mobile Large | 414px | iPhone Pro Max |
| Tablet | 768px | iPad |
| Desktop Small | 1024px | Small laptop |
| Desktop | 1280px | Standard laptop |
| Desktop Large | 1920px | Full HD monitor |

---

## Accessibility Testing

In addition to visual regression, test:

1. **Keyboard Navigation**
   - Tab order
   - Focus indicators
   - Interactive element access

2. **Screen Reader**
   - ARIA labels
   - Role attributes
   - Alt text

3. **Color Contrast**
   - WCAG AA compliance (4.5:1)
   - WCAG AAA compliance (7:1)

4. **Motion**
   - Respects `prefers-reduced-motion`
   - Animations can be disabled

---

## Baseline Snapshots

After implementing stories, create baseline snapshots:

```bash
# Build Storybook
cd ui
npm run build-storybook

# Run Chromatic to establish baselines
npx chromatic --project-token=<token>
```

Review and approve all initial snapshots in the Chromatic dashboard.

---

## Review Workflow

### For Pull Requests:

1. Developer creates PR with UI changes
2. Chromatic runs automatically via GitHub Actions
3. Visual differences highlighted in PR comments
4. Reviewer approves or rejects visual changes
5. Approved changes become new baselines

### Approval Process:

- **Intentional changes:** Approve as new baseline
- **Unintentional regressions:** Reject and fix
- **Browser rendering differences:** Mark as acceptable variance

---

## Maintenance

### Weekly Tasks:
- Review Chromatic snapshot history
- Update baselines for approved changes
- Check for flaky tests

### Monthly Tasks:
- Audit coverage of critical components
- Add stories for new components
- Update viewport test matrix

### Quarterly Tasks:
- Review and optimize snapshot count
- Evaluate Chromatic usage costs
- Update visual regression strategy

---

## Integration with Existing Tests

Visual regression tests **complement** existing test suites:

| Test Type | Purpose | Tool |
|-----------|---------|------|
| Unit Tests | Component logic | Jest + React Testing Library |
| Integration Tests | Component interactions | Jest + Testing Library |
| Visual Regression | Visual appearance | Chromatic |
| E2E Tests | Full user flows | Playwright/Cypress |

**Do not replace** existing tests with visual regression tests. Use them together for comprehensive coverage.

---

## Cost Considerations

**Chromatic Pricing (as of 2025):**
- Free tier: 5,000 snapshots/month
- Paid tiers: Starting at $149/month for 35,000 snapshots

**Cost Optimization:**
- Limit snapshots to critical components
- Use viewport-specific snapshots sparingly
- Exclude decorative/non-functional components
- Review snapshot usage monthly

---

## Resources

- [Chromatic Documentation](https://www.chromatic.com/docs/)
- [Storybook Documentation](https://storybook.js.org/docs)
- [Percy Documentation](https://docs.percy.io/)
- [Visual Testing Best Practices](https://www.chromatic.com/blog/visual-testing-best-practices/)

---

## Implementation Status

- [ ] Install Chromatic/Percy
- [ ] Create Storybook stories for PlatformDetectionCard
- [ ] Create Storybook stories for RelatedIncidentList
- [ ] Create Storybook stories for ProgressBar
- [ ] Create Storybook stories for EntityPill
- [ ] Set up CI/CD integration
- [ ] Establish baseline snapshots
- [ ] Document review workflow
- [ ] Train team on visual regression process

---

*Document Version: 1.0*  
*Last Updated: October 18, 2025*  
*Owner: Engineering Team*
