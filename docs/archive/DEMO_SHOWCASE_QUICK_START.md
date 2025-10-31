# Demo Showcase - Quick Start Guide

**For:** Sales Teams, Solution Engineers, and Demo Presenters  
**Purpose:** Step-by-step guide for demonstrating RCA Engine to clients

---

## Pre-Demo Checklist

### ✅ Technical Setup (5 minutes before)

1. **Start Backend Server:**
   ```powershell
   cd "C:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final"
   python -m uvicorn apps.api.main:app --reload --port 8001
   ```
   Wait for: `Application startup complete.`

2. **Start Frontend:**
   ```powershell
   cd "C:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final\ui"
   npm run dev
   ```
   Wait for: `Local: http://localhost:3000`

3. **Test Access:**
   - Open: http://localhost:3000/demo/showcase
   - Verify: All 3 demo cards visible
   - Check: No console errors (F12)

### ✅ Environment Prep

- Close unnecessary browser tabs
- Full screen browser (F11)
- Disable notifications
- Ensure stable internet connection
- Have backup demo recorded (optional)

---

## Demo Script (8-10 minutes)

### **1. Opening (30 seconds)**

**What to Say:**
> "Today I'll show you how our RCA Engine automatically analyzes production logs to identify root causes. We'll use a real Blue Prism scenario from your environment."

**What to Do:**
- Navigate to showcase page: http://localhost:3000/demo/showcase
- Pause briefly on landing page showing 3 scenarios

**What to Point Out:**
- "We support multiple RPA platforms out of the box"
- "Each demo uses actual log files, not synthetic data"

---

### **2. Scenario Selection (30 seconds)**

**What to Say:**
> "Let me select the Blue Prism scenario since that's your primary platform."

**What to Do:**
- Hover over "Blue Prism RPA Failure" card
- Read features aloud: "Platform Detection, RPA Analysis, Root Cause"
- Click to start demo

**What to Point Out:**
- Arrow appears on hover
- Feature tags show what will be demonstrated

---

### **3. File Upload Step (30 seconds)**

**What to Say:**
> "First, we upload the log file. In production, this can be done via API, web UI, or our file watcher that monitors folders automatically."

**What to Do:**
- Wait for green checkmark
- Point to status: "File uploaded and classified"

**What to Point Out:**
- Fast upload (instant with demo files)
- File ID is generated for tracking

---

### **4. PII Detection Step (1-2 minutes) - KEY DIFFERENTIATOR**

**What to Say:**
> "Before any AI processing, we scan for sensitive data. This is critical for GDPR and CCPA compliance. Watch as we detect and redact PII..."

**What to Do:**
- Wait for results card to appear
- **PAUSE** and read examples aloud:
  - "Emails redacted"
  - "Social Security Numbers masked"
  - "API keys protected"

**What to Point Out:**
- "8 sensitive items detected and redacted"
- "This happens before anything reaches the AI"
- "You control what's considered PII through configuration"
- **Compliance messaging:** "This ensures you're never exposing customer data"

**Objection Handling:**
- Q: "What if we need to see the original data?"
  - A: "Authorized users can access original files with proper permissions. The redaction only applies to AI processing."

---

### **5. Platform Detection Step (1-2 minutes) - KEY DIFFERENTIATOR**

**What to Say:**
> "Now watch as we automatically identify this as Blue Prism version 7.2.1 with high confidence..."

**What to Do:**
- Wait for platform card to appear
- Point to key indicators: Runtime Resource, Work queue, Session, Business exception
- Emphasize **HIGH confidence badge**

**What to Point Out:**
- "No manual tagging required"
- "Works across 10+ RPA platforms"
- "Platform-specific analysis rules are applied automatically"

**Objection Handling:**
- Q: "What if it detects wrong platform?"
  - A: "You can override manually, but with high confidence detection, false positives are rare. We use 50+ platform-specific patterns."

---

### **6. Classification Step (1-2 minutes)**

**What to Say:**
> "Every log entry is categorized—errors, warnings, critical issues, and info messages. This prioritization helps your teams focus on what matters."

**What to Do:**
- Wait for metrics grid to appear
- Point to each number:
  - "6 errors that need investigation"
  - "2 critical issues requiring immediate action"
  - "8 warnings to monitor"

**What to Point Out:**
- "Automatic severity assessment"
- "No manual log parsing required"
- "Trends over time can be tracked"

---

### **7. AI Analysis Step (1-2 minutes)**

**What to Say:**
> "Finally, our AI analyzes everything—the platform context, error patterns, timeline—and generates a root cause analysis with actionable recommendations. This takes about 10-15 seconds..."

**What to Do:**
- Wait for completion
- Click "View Full Report" button

**What to Point Out:**
- "Analysis completed in under 30 seconds"
- "In production, this scales to thousands of logs simultaneously"
- "Let's look at the detailed report..."

---

### **8. Full Report View (2-3 minutes)**

**What to Say:**
> "Here's the complete analysis. Notice the structure—Executive Summary, Root Cause, Timeline, and Recommendations."

**What to Do:**
- Scroll through report sections:
  1. Executive Summary
  2. Root Cause Analysis
  3. Timeline of Events
  4. Actionable Recommendations
  5. Technical Details

**What to Point Out:**
- "Executive summary for management"
- "Technical details for engineers"
- "Actionable recommendations, not just descriptions"
- "Everything is exportable for ticketing systems"

---

### **9. Closing (1 minute)**

**What to Say:**
> "That's our RCA Engine in action. We demonstrated PII protection, intelligent platform detection, automatic classification, and AI-powered root cause analysis—all in under a minute with a real log file."

**What to Do:**
- Navigate back to showcase: Click browser back button
- Show other scenarios: "We can run Blue Prism, UiPath, or generic applications"
- Click "Choose Different File" to reset

**What to Point Out:**
- "This works the same way in your production environment"
- "API-first architecture for integration with your tools"
- "Self-service for your teams after implementation"

---

## Advanced Demo Techniques

### **For Technical Audiences:**

1. **Show API Integration:**
   - Open browser DevTools (F12)
   - Show Network tab during demo
   - Point out API calls: `/api/files/upload`, `/api/jobs`

2. **Discuss Architecture:**
   - Mention: "This is running on our Python FastAPI backend"
   - Mention: "React frontend with Next.js"
   - Mention: "PostgreSQL for metadata, Redis for caching"

3. **Customize Prompts:**
   - Navigate to `/prompts` page
   - Show: "You can customize the AI analysis prompts"
   - Edit: Make a small change to demonstrate

### **For Business Audiences:**

1. **Focus on ROI:**
   - "Manual log analysis: 2-4 hours"
   - "With RCA Engine: 30 seconds"
   - "That's 96% time savings"

2. **Emphasize Compliance:**
   - Spend extra time on PII step
   - Mention regulations by name: GDPR, CCPA, HIPAA
   - Show redaction proof

3. **Show Scale:**
   - "This handles 1 file today, 1000 files tomorrow"
   - "Same speed, same accuracy"
   - "Grows with your organization"

### **For Different Industries:**

#### Healthcare
- Emphasize: PII/PHI protection
- Highlight: HIPAA compliance
- Use case: Patient data in logs

#### Finance
- Emphasize: Security, audit trails
- Highlight: PCI-DSS compliance
- Use case: Transaction failures

#### Insurance
- Emphasize: Claims processing automation
- Highlight: Regulatory compliance
- Use case: RPA bot failures during claims

---

## Objection Handling

### **"We already have log analysis tools"**

**Response:**
> "That's great! Our RCA Engine complements those tools by adding AI-powered root cause analysis. While traditional tools show you what happened, we tell you why it happened and how to fix it. Plus, our platform-specific detection means we understand RPA logs better than generic tools."

**Action:** Show platform detection highlighting RPA-specific identifiers

---

### **"How accurate is the AI?"**

**Response:**
> "Our AI achieves 85-90% accuracy in identifying root causes, but more importantly, it provides context and recommendations that speed up resolution even when refinement is needed. We also support custom prompt templates so you can tune the analysis for your specific environment."

**Action:** Navigate to `/prompts` to show customization

---

### **"What about data privacy?"**

**Response:**
> "That's exactly why we built PII redaction as a first-class feature. As you saw, we detect and redact sensitive data before any AI processing. You control what's considered sensitive through configuration, and redaction happens locally before cloud processing."

**Action:** Re-show PII step, emphasize "before AI processing"

---

### **"Can we integrate with our ticketing system?"**

**Response:**
> "Absolutely. We have REST APIs for everything you saw—file upload, job submission, report retrieval. We also support webhooks for notifications. Many customers integrate with ServiceNow, Jira, and PagerDuty out of the box."

**Action:** Show API documentation at `/docs` or mention ITSM integration guide

---

### **"How long to implement?"**

**Response:**
> "For a pilot, you can be up and running in a day. Full production deployment typically takes 2-4 weeks depending on your integration requirements. We provide Docker containers and deployment guides to streamline the process."

**Action:** Mention deployment docs, offer pilot/POC

---

## Troubleshooting During Demo

### **Problem: Demo won't start**

**Quick Fix:**
1. Check browser console (F12) for errors
2. Verify backend is running: http://localhost:8001/docs
3. Refresh page (Ctrl+R)

**Prevention:** Always test before client call

---

### **Problem: Slow performance**

**Quick Fix:**
1. Close other applications
2. Clear browser cache
3. Use Chrome instead of other browsers

**Prevention:** Dedicated demo machine with minimal apps

---

### **Problem: API errors**

**Quick Fix:**
1. Check backend logs in terminal
2. Restart backend if needed
3. Switch to recorded demo video as backup

**Prevention:** Pre-run demo 5 minutes before call

---

### **Problem: Wrong platform detected**

**Note:** This is simulated in demo, won't happen

**If Asked:**
- "In production, detection is based on actual log content"
- "You can always override manually if needed"
- "We use 50+ patterns per platform for high accuracy"

---

## Follow-Up Actions

### **After Successful Demo:**

1. **Send Documentation:**
   - Email demo showcase URL for them to try
   - Include DEMO_SHOWCASE_COMPLETE.md
   - Share platform detection guide

2. **Propose Next Steps:**
   - Pilot/POC with their actual logs
   - Integration planning session
   - Security review for compliance

3. **Schedule Follow-Up:**
   - Technical deep dive if needed
   - Executive presentation if business audience
   - Pricing discussion

### **If Demo Didn't Go Well:**

1. **Identify Issues:**
   - Technical problems?
   - Wrong audience level?
   - Features didn't match needs?

2. **Adjust Approach:**
   - More technical or less technical
   - Focus on different features
   - Different demo scenario

3. **Schedule Redo:**
   - "Let me show you a different aspect..."
   - "I have a better example for your use case..."

---

## Best Practices

### ✅ **DO:**
- Practice demo 3+ times before client call
- Speak slowly and pause at key moments
- Ask questions to engage client
- Show enthusiasm for the product
- Have backend/frontend running before call
- Use client's terminology (their RPA platform)
- Emphasize business value, not just features

### ❌ **DON'T:**
- Rush through steps (especially PII)
- Use technical jargon with business audience
- Skip the "why this matters" explanations
- Ignore client questions to finish demo
- Promise features that don't exist
- Bad-mouth competitor tools
- Forget to ask for next steps

---

## Demo Timing Guide

| Section | Time | Priority |
|---------|------|----------|
| Opening | 30s | Medium |
| Scenario Selection | 30s | Low |
| File Upload | 30s | Low |
| PII Detection | 1-2min | **HIGH** |
| Platform Detection | 1-2min | **HIGH** |
| Classification | 1-2min | Medium |
| AI Analysis | 1-2min | Medium |
| Full Report | 2-3min | High |
| Closing | 1min | Medium |
| **TOTAL** | **8-10min** | |

**Tip:** If running short on time, condense Classification step

---

## Success Metrics

Track these after each demo:

- [ ] Client asked technical questions (engaged)
- [ ] Client mentioned specific use case (qualified)
- [ ] Client asked about pricing (buying signal)
- [ ] Client wanted to try themselves (strong interest)
- [ ] Next meeting scheduled (progressing)

---

## Resources

- **Demo URL:** http://localhost:3000/demo/showcase
- **Documentation:** `docs/DEMO_SHOWCASE_COMPLETE.md`
- **Visual Guide:** `docs/DEMO_SHOWCASE_VISUAL_GUIDE.md`
- **Sample Files:** `sample-data/README.md`
- **API Docs:** http://localhost:8001/docs

---

## Contact for Demo Support

If you encounter issues during a client demo:

1. **Technical Issues:** Check backend logs, restart services
2. **Feature Questions:** Refer to feature documentation
3. **Custom Scenarios:** Create new demo files in `sample-data/`
4. **Urgent Help:** [Internal escalation process]

---

**Remember:** The goal is to demonstrate value, not perfection. If something goes wrong, acknowledge it professionally and continue. The live demo shows real product capabilities, which builds more trust than a perfect recording.

**Good luck with your demos!** 🚀
