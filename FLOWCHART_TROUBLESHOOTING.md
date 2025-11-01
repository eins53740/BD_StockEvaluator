# Flowchart Troubleshooting Guide

## 🔧 Common Flowchart Issues & Solutions

### Issue 1: Flowchart Not Rendering / Broken Layout

**Symptoms:**
- Flowchart appears as broken fragments
- Missing nodes or connections
- Text overlapping or cut off
- Empty flowchart area

**Solutions:**

#### 1. Check Browser Console
Open browser developer tools (F12) and check for JavaScript errors:
```javascript
// Common errors to look for:
- "Mermaid is not defined"
- "Failed to render mermaid diagram"
- "Invalid syntax"
```

#### 2. Test with Simple HTML File
Use the provided `test_flowchart.html` file:
```bash
# Open in browser to test basic rendering
open test_flowchart.html
```

#### 3. Clear Browser Cache
```bash
# Hard refresh the page
Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)
```

#### 4. Check Internet Connection
Mermaid loads from CDN - ensure you have internet access:
```html
<!-- CDN URL should be accessible -->
https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js
```

### Issue 2: Text Not Displaying Properly

**Symptoms:**
- Node text is cut off
- Overlapping text
- Missing actual values

**Solutions:**

#### 1. Enable HTML Labels
Ensure JavaScript configuration has:
```javascript
mermaid.initialize({
    flowchart: {
        htmlLabels: true,  // This is crucial
        useMaxWidth: true
    }
});
```

#### 2. Check Text Length
Very long text can cause issues:
```python
# In app.py, the clean_text function should limit length
def clean_text(text):
    text = str(text).replace('"', "'").replace('\n', ' ')
    # Limit text length if too long
    if len(text) > 50:
        text = text[:47] + "..."
    return text.strip()
```

### Issue 3: Colors Not Applying

**Symptoms:**
- All nodes are the same color
- Status colors (green/red/yellow) not showing

**Solutions:**

#### 1. Check Class Definitions
Ensure the flowchart includes proper classDef statements:
```mermaid
classDef pass fill:#d1e7dd,stroke:#198754,stroke-width:3px,color:#000;
classDef fail fill:#f8d7da,stroke:#dc3545,stroke-width:3px,color:#000;
```

#### 2. Verify Class Applications
Check that nodes have class assignments:
```mermaid
class B pass;
class D fail;
```

### Issue 4: Mobile Rendering Issues

**Symptoms:**
- Flowchart too small on mobile
- Horizontal scrolling required
- Text unreadable on small screens

**Solutions:**

#### 1. Enable Responsive Settings
```javascript
mermaid.initialize({
    flowchart: {
        useMaxWidth: true,
        nodeSpacing: 40,  // Smaller spacing for mobile
        rankSpacing: 40
    }
});
```

#### 2. Add CSS Media Queries
```css
@media (max-width: 768px) {
    .mermaid {
        font-size: 12px;
    }
    .mermaid svg {
        max-width: 100%;
        height: auto;
    }
}
```

### Issue 5: Performance Issues / Slow Rendering

**Symptoms:**
- Long loading times
- Browser freezing
- Memory issues

**Solutions:**

#### 1. Optimize Mermaid Settings
```javascript
mermaid.initialize({
    maxTextSize: 90000,
    maxEdges: 100,
    logLevel: 'error'  // Reduce console output
});
```

#### 2. Implement Fallback Content
The app includes automatic fallback for failed renders:
```javascript
// Fallback is automatically shown if rendering fails
displayFallbackContent(element, error);
```

## 🧪 Testing Your Fixes

### 1. Run Automated Tests
```bash
python test_flowchart.py
python test_integration.py
```

### 2. Test in Multiple Browsers
- Chrome/Chromium
- Firefox
- Safari
- Edge

### 3. Test on Different Devices
- Desktop (large screen)
- Tablet (medium screen)
- Mobile (small screen)

### 4. Test with Different Stocks
Try various ticker symbols to test different scenarios:
```bash
# Good stocks: MSFT, AAPL, GOOGL
# Risky stocks: Penny stocks, high volatility stocks
# Edge cases: Stocks with missing data
```

## 🔍 Advanced Debugging

### Enable Detailed Logging
```javascript
// In flowchart.js, temporarily change logLevel
mermaid.initialize({
    logLevel: 'debug'  // Shows detailed rendering info
});
```

### Check Generated Mermaid Syntax
```python
# In Python, print the generated flowchart definition
print("Generated Mermaid:")
print(flowchart_def)
```

### Validate Mermaid Syntax Online
Use the official Mermaid Live Editor:
1. Go to https://mermaid.live/
2. Paste your generated Mermaid code
3. Check if it renders correctly

## 📋 Quick Fixes Checklist

- [ ] Browser console shows no JavaScript errors
- [ ] Internet connection is working
- [ ] Mermaid CDN is accessible
- [ ] HTML labels are enabled in configuration
- [ ] Class definitions are present in flowchart
- [ ] Node classes are properly applied
- [ ] Text is not too long (under 50 characters per line)
- [ ] Responsive settings are enabled
- [ ] Browser cache has been cleared

## 🆘 If Nothing Works

### Fallback Options

1. **Use the Decision Table**: The app always shows a detailed table below the flowchart with all evaluation results.

2. **Check the Raw Data**: Look at the "Decision Path Details" table for complete information.

3. **Try a Different Browser**: Sometimes browser-specific issues occur.

4. **Disable JavaScript Temporarily**: The app will show a static message explaining the evaluation.

### Report the Issue

If problems persist, gather this information:
- Browser name and version
- Operating system
- Stock ticker that caused the issue
- JavaScript console errors
- Screenshot of the problem

The flowchart is an enhancement to the core functionality - the evaluation logic and results table will always work even if the flowchart fails to render.

## 🎯 Expected Results

When working correctly, you should see:
- Clean, well-spaced flowchart nodes
- Color-coded nodes (green=pass, red=fail, yellow=close)
- Multi-line text with actual stock values
- Smooth animations (if enabled)
- Responsive layout on all devices
- Interactive hover effects

The flowchart should clearly show the decision path and make it easy to understand why a stock received its evaluation result.
