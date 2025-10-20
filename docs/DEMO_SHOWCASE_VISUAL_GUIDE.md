# Demo Showcase - Visual Guide

This guide shows what clients will see when experiencing the Interactive Feature Showcase.

---

## Landing Page

```
╔══════════════════════════════════════════════════════════════════════════╗
║  🎭 Feature Showcase                                                     ║
║  Interactive demonstration of RCA Engine capabilities with real log files║
╚══════════════════════════════════════════════════════════════════════════╝

┌────────────────────────────────────────────────────────────────────────┐
│ Select a Demo Scenario                                                 │
│ Choose a real-world log file to see our intelligent analysis in action│
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────┐│
│  │ Application Logs     │  │ Blue Prism RPA      │  │ UiPath Sel.. ││
│  │ with PII             │  │ Failure             │  │ Error        ││
│  ├──────────────────────┤  ├──────────────────────┤  ├──────────────┤│
│  │ Real application     │  │ Blue Prism auto...  │  │ UiPath robot ││
│  │ logs containing      │  │ failure with conn.. │  │ selector tim.││
│  │ sensitive data       │  │                      │  │              ││
│  │                      │  │                      │  │              ││
│  │ [PII Redaction]      │  │ [Platform Detection] │  │ [Platform D..││
│  │ [Classification]     │  │ [RPA Analysis]       │  │ [Retry Ana...││
│  │ [Error Detection]    │  │ [Root Cause]         │  │ [Screenshot..││
│  │                      │  │                      │  │              ││
│  │         →            │  │         →            │  │      →       ││
│  └──────────────────────┘  └──────────────────────┘  └──────────────┘│
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│ What This Demo Shows                                                   │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  🛡️ PII Protection          🖥️ Platform Detection                     │
│  Automatic detection        Auto-identify RPA platforms                │
│  and redaction                                                         │
│                                                                        │
│  🔍 Smart Classification    ✅ AI Analysis                             │
│  Categorize errors          Root cause identification                 │
│  and events                                                            │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## After Selecting "Application Logs with PII"

```
╔══════════════════════════════════════════════════════════════════════════╗
║  Application Logs with PII                                               ║
║  Real application logs containing sensitive customer data                ║
║                                             [Choose Different File]      ║
╚══════════════════════════════════════════════════════════════════════════╝

┌────────────────────────────────────────────────────────────────────────┐
│ Analysis Progress                                                      │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ✅  File Upload & Classification                                     │
│  │   Uploading and analyzing file structure                           │
│  │                                                                     │
│  ├── [File ID: abc123, Size: 2.1KB]                                   │
│  │                                                                     │
│  │                                                                     │
│  🟢  PII Detection & Redaction                                        │
│  │   Scanning for sensitive data (emails, SSNs, phone numbers...)     │
│  │                                                                     │
│  ├── ┌─────────────────────────────────────────────────────────────┐ │
│  │   │ 🛡️ 8 Sensitive Items Detected & Redacted                    │ │
│  │   ├─────────────────────────────────────────────────────────────┤ │
│  │   │ Email     john.doe@acmecorp.com → [EMAIL_REDACTED]          │ │
│  │   │ SSN       123-45-6789 → [SSN_REDACTED]                      │ │
│  │   │ Phone     +1-555-123-4567 → [PHONE_REDACTED]                │ │
│  │   │ API Key   sk_live_51Hx... → [API_KEY_REDACTED]              │ │
│  │   └─────────────────────────────────────────────────────────────┘ │
│  │                                                                     │
│  │                                                                     │
│  🔵  Platform Auto-Detection                                          │
│  │   Identifying automation platform and version                      │
│  │   ⏳ Analyzing...                                                  │
│  │                                                                     │
│  │                                                                     │
│  ⚪  Intelligent Classification                                       │
│      Categorizing errors, warnings, and critical events                │
│                                                                        │
│  ⚪  AI Root Cause Analysis                                           │
│      Generating actionable insights and recommendations                │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Platform Detection Complete (Blue Prism Scenario)

```
│  ✅  Platform Auto-Detection                                          │
│  │   Identifying automation platform and version                      │
│  │                                                                     │
│  ├── ┌─────────────────────────────────────────────────────────────┐ │
│  │   │ 🖥️ Platform Identified: Blue Prism                          │ │
│  │   ├─────────────────────────────────────────────────────────────┤ │
│  │   │ Version:     7.2.1                                          │ │
│  │   │ Confidence:  HIGH ✅                                         │ │
│  │   │                                                              │ │
│  │   │ Key Indicators:                                             │ │
│  │   │ [Runtime Resource] [Work queue] [Session]                   │ │
│  │   │ [Business exception]                                        │ │
│  │   └─────────────────────────────────────────────────────────────┘ │
```

---

## Classification Complete

```
│  ✅  Intelligent Classification                                       │
│  │   Categorizing errors, warnings, and critical events               │
│  │                                                                     │
│  ├── ┌─────────────────────────────────────────────────────────────┐ │
│  │   │ 🔍 Log Analysis Complete                                    │ │
│  │   ├─────────────────────────────────────────────────────────────┤ │
│  │   │                                                              │ │
│  │   │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │ │
│  │   │  │    6    │  │    8    │  │    2    │  │   24    │       │ │
│  │   │  │ Errors  │  │ Warnings│  │ Critical│  │  Info   │       │ │
│  │   │  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │ │
│  │   │                                                              │ │
│  │   └─────────────────────────────────────────────────────────────┘ │
```

---

## Analysis Complete

```
│  ✅  AI Root Cause Analysis                                           │
│  │   Generating actionable insights and recommendations               │
│  │                                                                     │
│  └── ┌─────────────────────────────────────────────────────────────┐ │
│      │ ✅ Root Cause Analysis Complete                              │ │
│      ├─────────────────────────────────────────────────────────────┤ │
│      │                                                              │ │
│      │  ┌───────────────────────────────────────────────────┐      │ │
│      │  │  👁️  View Full Report                              │      │ │
│      │  └───────────────────────────────────────────────────┘      │ │
│      │                                                              │ │
│      └─────────────────────────────────────────────────────────────┘ │
```

---

## Key Features Demonstrated Section

```
┌────────────────────────────────────────────────────────────────────────┐
│ Key Features Demonstrated                                              │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────────────────┐  ┌──────────────────────────┐          │
│  │ ⚠️ Real-time Processing  │  │ 🛡️ Enterprise Security   │          │
│  ├──────────────────────────┤  ├──────────────────────────┤          │
│  │ Watch as each analysis   │  │ GDPR/CCPA compliant PII │          │
│  │ step executes with live  │  │ redaction before AI     │          │
│  │ status updates           │  │ processing              │          │
│  └──────────────────────────┘  └──────────────────────────┘          │
│                                                                        │
│  ┌──────────────────────────┐  ┌──────────────────────────┐          │
│  │ 🖥️ Intelligent Detection │  │ 🔍 Deep Analysis         │          │
│  ├──────────────────────────┤  ├──────────────────────────┤          │
│  │ Automatically identifies │  │ AI-powered root cause   │          │
│  │ RPA platforms (Blue      │  │ identification with     │          │
│  │ Prism, UiPath, AA)       │  │ actionable recs         │          │
│  └──────────────────────────┘  └──────────────────────────┘          │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Mobile/Responsive View

For smaller screens, the layout adapts:

```
┌─────────────────────────┐
│ Select a Demo Scenario  │
├─────────────────────────┤
│                         │
│ ┌─────────────────────┐ │
│ │ Application Logs    │ │
│ │ with PII            │ │
│ │                     │ │
│ │ [PII Redaction]     │ │
│ │ [Classification]    │ │
│ │                     │ │
│ │       →             │ │
│ └─────────────────────┘ │
│                         │
│ ┌─────────────────────┐ │
│ │ Blue Prism RPA      │ │
│ │ Failure             │ │
│ │                     │ │
│ │ [Platform Detection]│ │
│ │ [RPA Analysis]      │ │
│ │                     │ │
│ │       →             │ │
│ └─────────────────────┘ │
│                         │
│ ┌─────────────────────┐ │
│ │ UiPath Selector     │ │
│ │ Error               │ │
│ │                     │ │
│ │ [Platform Detection]│ │
│ │ [Retry Analysis]    │ │
│ │                     │ │
│ │       →             │ │
│ └─────────────────────┘ │
│                         │
└─────────────────────────┘
```

---

## Animation States

### Progress Indicators:
- **Pending (⚪):** Gray circle, static
- **Running (🔵):** Blue circle, pulsing animation
- **Complete (✅):** Green circle with checkmark

### Visual Feedback:
- **Smooth transitions** between steps
- **Fade-in animations** for result cards
- **Hover effects** on scenario cards
- **Button states** (disabled during processing)

---

## Color Scheme

| Feature | Color | Purpose |
|---------|-------|---------|
| PII Detection | Green | Security/Safety |
| Platform Detection | Blue | Intelligence/Technology |
| Classification | Purple | Analysis/Categorization |
| AI Analysis | Cyan | Innovation/Intelligence |
| Errors | Red | Critical Issues |
| Warnings | Yellow | Caution |
| Info | Blue | Information |

---

## Interactive Elements

### Clickable Areas:
1. **Demo scenario cards** → Starts demo workflow
2. **"Choose Different File"** button → Returns to selection
3. **"View Full Report"** link → Navigates to job details
4. **Navigation "Showcase"** link → Access from any page

### Hover States:
- Scenario cards: Border highlights, arrow appears
- Buttons: Background color darkens
- Links: Underline appears

---

## Screen Sizes Support

✅ **Desktop (1920x1080):** Full 3-column layout  
✅ **Tablet (768x1024):** 2-column layout with wrapping  
✅ **Mobile (375x812):** Single column stack  

All features remain accessible and readable across all sizes.

---

## Accessibility Features

- **Keyboard Navigation:** All elements accessible via Tab
- **Screen Readers:** Proper ARIA labels and semantic HTML
- **Color Contrast:** WCAG AA compliant text contrast
- **Focus Indicators:** Clear visual focus states
- **Reduced Motion:** Respects prefers-reduced-motion

---

## Performance

- **Initial Load:** < 500ms (excluding API calls)
- **Demo Execution:** ~30 seconds total
- **Step Transitions:** 1-3 seconds each
- **API Calls:** Real backend integration
- **Animations:** 60fps CSS transitions

---

## Browser Support

✅ Chrome 90+  
✅ Firefox 88+  
✅ Safari 14+  
✅ Edge 90+  

---

This visual guide demonstrates the polished, professional UI that clients will experience when exploring the RCA Engine's capabilities through the Interactive Feature Showcase.
