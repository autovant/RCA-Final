# Features Showcase Page

## Overview

The Features Showcase page provides a comprehensive, user-friendly interface for exploring all capabilities of the RCA Insight Engine. It features a sidebar navigation menu for easy feature selection and detailed information panels for each feature.

## Location

- **Route**: `/features`
- **File**: `ui/src/app/features/page.tsx`
- **Navigation**: Accessible from the main header navigation bar

## Design Philosophy

The page follows the existing UI/UX patterns established in the RCA application:

- **Fluent Design System**: Matches Microsoft Fluent Design aesthetics with acrylic effects, elevation, and smooth animations
- **Dark Theme**: Consistent with the executive dark palette (`#0f172a` base)
- **Responsive**: Mobile-first design with collapsible sidebar on smaller screens
- **Accessible**: ARIA labels, semantic HTML, and keyboard navigation support

## Features Included

The showcase highlights 12 key platform capabilities:

1. **Conversational RCA Engine** - Multi-turn LLM reasoning with full traceability
2. **Multi-Provider LLM Support** - Ollama, OpenAI, AWS Bedrock integration
3. **PII & Data Redaction** - Compliance-ready sensitive data sanitization
4. **ITSM Ticketing Integration** - ServiceNow and Jira automation
5. **Intelligent File Watcher** - Automated log monitoring and processing
6. **Real-Time SSE Streaming** - Live job progress and event updates
7. **Structured RCA Outputs** - Markdown, HTML, and JSON reports
8. **Full Observability Stack** - Prometheus metrics and tracing
9. **Executive Control Plane** - Modern React/Next.js dashboard
10. **Intelligent Platform Detection** - Auto-detect automation platforms
11. **Archive Format Support** - ZIP, TAR, compressed file handling
12. **Enterprise Security** - Zero-trust architecture and compliance

## Component Structure

### Sidebar Navigation
- Fixed position with sticky behavior on larger screens
- Collapsible on mobile devices (toggle button)
- Active state highlighting with gradient background
- Icon + label format for each feature
- Status badges (Stable, Beta, New)

### Content Area
- Animated transitions between features
- Four main sections per feature:
  - **Header**: Icon, title, description, and status badge
  - **Key Benefits**: Grid layout with checkmark icons
  - **Technical Capabilities**: Tag-style capability pills
  - **Common Use Cases**: List with contextual icons
- **Call-to-Action**: Quick links to Investigation and Documentation pages

## Styling

### Colors
- Primary: `fluent-blue-500` (#0078d4)
- Info: `fluent-info` (#38bdf8)
- Success: `fluent-success` (#00c853)
- Warning: `fluent-warning` (#ffb900)
- Background: `dark-bg-primary` (#0f172a)
- Text: `dark-text-primary` (#f8fafc)

### Effects
- Backdrop blur with `backdrop-blur-2xl`
- Acrylic cards with gradient overlays
- Hover animations with `hover:-translate-y-0.5`
- Smooth transitions with `transition-all duration-200`
- Fluent shadows: `shadow-fluent`, `shadow-fluent-lg`

## Usage

### Accessing the Page

Users can access the Features page through:
1. Main navigation header - "Features" link
2. Dashboard card - "View All Features" button
3. Direct URL - `/features`

### Interacting with Features

1. Click any feature in the sidebar to view details
2. Scroll through benefits, capabilities, and use cases
3. Use "Try Now" button to navigate to Investigation page
4. Use "Documentation" button for detailed guides
5. Mobile users can toggle sidebar visibility

## Adding New Features

To add a new feature to the showcase:

```typescript
{
  id: "feature-id",
  title: "Feature Name",
  icon: <svg>...</svg>, // SVG icon
  description: "Brief description...",
  benefits: [
    "Benefit 1",
    "Benefit 2",
    // ...
  ],
  capabilities: [
    "Capability 1",
    "Capability 2",
    // ...
  ],
  useCases: [
    "Use case 1",
    "Use case 2",
    // ...
  ],
  status: "stable" | "beta" | "new" // optional
}
```

## Responsive Behavior

### Desktop (≥1024px)
- Sidebar visible and fixed (3-column layout)
- Content area takes 9 columns
- Smooth scrolling with sticky sidebar

### Tablet (768px-1023px)
- Same layout as desktop
- Slightly reduced padding

### Mobile (<768px)
- Sidebar collapses by default
- Toggle button shows/hides sidebar
- Full-width content area
- Stacked card layouts

## Accessibility

- Semantic HTML5 structure
- ARIA labels for all interactive elements
- Keyboard navigation support
- Focus indicators for interactive elements
- Screen reader friendly descriptions
- Sufficient color contrast ratios (WCAG AA compliant)

## Performance

- Client-side rendering with React state management
- No external API calls (static content)
- Optimized SVG icons
- Lazy loading of content sections
- Minimal re-renders with `useState`

## Future Enhancements

Potential improvements for future iterations:

1. **Search Functionality**: Filter features by keyword
2. **Category Grouping**: Organize features by category (Security, Integration, etc.)
3. **Interactive Demos**: Embed live demos or videos
4. **User Feedback**: Rating system for features
5. **Feature Comparison**: Side-by-side feature comparison tool
6. **Bookmarking**: Save favorite features for quick access
7. **Deep Linking**: Direct links to specific features
8. **Analytics**: Track which features users explore most

## Integration Points

The Features page integrates with:
- **Header Component**: Navigation link in main menu
- **Dashboard Page**: Featured card with CTA button
- **Investigation Page**: "Try Now" button destination
- **Docs Page**: "Documentation" button destination

## Testing

To test the Features page:

1. Start the development server: `npm run dev`
2. Navigate to `http://localhost:3000/features`
3. Test sidebar navigation on different screen sizes
4. Verify all feature content displays correctly
5. Check responsive behavior on mobile devices
6. Test keyboard navigation and accessibility
7. Verify links to Investigation and Docs pages work

## Maintenance

When updating the application:
- Update feature descriptions when capabilities change
- Add new features as they are developed
- Update status badges (beta → stable)
- Keep use cases current with real-world scenarios
- Ensure consistency with main documentation
