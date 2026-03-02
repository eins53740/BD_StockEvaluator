console.log('Enhanced Flowchart.js loaded with animation support');

// Enhanced Error Logging and Debugging System
class FlowchartDebugger {
  constructor() {
    this.startTime = performance.now();
    this.renderTimes = [];
    this.errorLog = [];
    this.diagnosticInfo = this.collectDiagnosticInfo();
    this.logLevel = 'INFO'; // DEBUG, INFO, WARN, ERROR
  }

  collectDiagnosticInfo() {
    return {
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
        devicePixelRatio: window.devicePixelRatio || 1
      },
      screen: {
        width: screen.width,
        height: screen.height,
        colorDepth: screen.colorDepth
      },
      browser: {
        language: navigator.language,
        platform: navigator.platform,
        cookieEnabled: navigator.cookieEnabled,
        onLine: navigator.onLine
      },
      mermaidVersion: typeof mermaid !== 'undefined' ? mermaid.version || 'unknown' : 'not loaded',
      performance: {
        memory: performance.memory ? {
          usedJSHeapSize: performance.memory.usedJSHeapSize,
          totalJSHeapSize: performance.memory.totalJSHeapSize,
          jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
        } : 'not available'
      }
    };
  }

  log(level, message, data = null) {
    const timestamp = new Date().toISOString();
    const logEntry = {
      timestamp,
      level,
      message,
      data,
      context: this.diagnosticInfo
    };

    // Store in error log
    this.errorLog.push(logEntry);

    // Console output with appropriate level
    const consoleMethod = level.toLowerCase() === 'error' ? 'error' :
                         level.toLowerCase() === 'warn' ? 'warn' : 'log';

    console[consoleMethod](`[${timestamp}] [${level}] ${message}`, data || '');

    // Keep error log size manageable
    if (this.errorLog.length > 50) {
      this.errorLog = this.errorLog.slice(-25);
    }
  }

  startRenderTimer(diagramId) {
    this.renderStartTime = performance.now();
    this.log('DEBUG', `Starting render timer for diagram: ${diagramId}`);
  }

  endRenderTimer(diagramId, success = true) {
    if (this.renderStartTime) {
      const renderTime = performance.now() - this.renderStartTime;
      this.renderTimes.push({
        diagramId,
        renderTime,
        success,
        timestamp: new Date().toISOString()
      });

      this.log('INFO', `Render completed for ${diagramId}`, {
        renderTime: `${renderTime.toFixed(2)}ms`,
        success,
        averageRenderTime: this.getAverageRenderTime()
      });

      delete this.renderStartTime;
    }
  }

  getAverageRenderTime() {
    if (this.renderTimes.length === 0) return 0;
    const total = this.renderTimes.reduce((sum, entry) => sum + entry.renderTime, 0);
    return (total / this.renderTimes.length).toFixed(2);
  }

  logError(error, context = {}) {
    const errorInfo = {
      message: error.message,
      stack: error.stack,
      name: error.name,
      context,
      diagnostics: this.diagnosticInfo
    };

    this.log('ERROR', `Flowchart Error: ${error.message}`, errorInfo);
    return errorInfo;
  }

  generateDiagnosticReport() {
    return {
      summary: {
        totalErrors: this.errorLog.filter(entry => entry.level === 'ERROR').length,
        totalWarnings: this.errorLog.filter(entry => entry.level === 'WARN').length,
        averageRenderTime: this.getAverageRenderTime(),
        totalRenders: this.renderTimes.length,
        successfulRenders: this.renderTimes.filter(entry => entry.success).length
      },
      diagnostics: this.diagnosticInfo,
      recentErrors: this.errorLog.slice(-10),
      renderPerformance: this.renderTimes.slice(-10)
    };
  }

  displayDiagnosticInfo(element, error) {
    const report = this.generateDiagnosticReport();
    const diagnosticHtml = `
      <div class="diagnostic-info" style="margin-top: 1em; padding: 1em; background: #f8f9fa; border-radius: 4px; font-family: monospace; font-size: 0.8em;">
        <h5 style="margin: 0 0 0.5em 0; color: #495057;">Diagnostic Information</h5>
        <div><strong>Browser:</strong> ${this.diagnosticInfo.browser.platform} - ${this.diagnosticInfo.userAgent.split(' ')[0]}</div>
        <div><strong>Viewport:</strong> ${this.diagnosticInfo.viewport.width}x${this.diagnosticInfo.viewport.height}</div>
        <div><strong>Mermaid Version:</strong> ${this.diagnosticInfo.mermaidVersion}</div>
        <div><strong>Error Time:</strong> ${new Date().toLocaleString()}</div>
        <div><strong>Render Attempts:</strong> ${report.summary.totalRenders}</div>
        <div><strong>Success Rate:</strong> ${report.summary.totalRenders > 0 ?
          ((report.summary.successfulRenders / report.summary.totalRenders) * 100).toFixed(1) : 0}%</div>
        ${report.summary.averageRenderTime > 0 ?
          `<div><strong>Avg Render Time:</strong> ${report.summary.averageRenderTime}ms</div>` : ''}
        <details style="margin-top: 0.5em;">
          <summary style="cursor: pointer; color: #007bff;">Show Error Details</summary>
          <pre style="margin-top: 0.5em; padding: 0.5em; background: #fff; border: 1px solid #dee2e6; border-radius: 3px; overflow-x: auto; white-space: pre-wrap;">${error.message}

Stack Trace:
${error.stack || 'No stack trace available'}</pre>
        </details>
      </div>
    `;

    return diagnosticHtml;
  }
}

// Global debugger instance
const flowchartDebugger = new FlowchartDebugger();

document.addEventListener('DOMContentLoaded', () => {
  flowchartDebugger.log('INFO', 'DOM Content Loaded - Initializing Mermaid');
  // Initialize Mermaid with enhanced settings and animation support
  initializeMermaid();
});

// Re-render mermaid diagrams after HTMX swaps in new content
document.addEventListener('htmx:afterSettle', () => {
  const unrendered = document.querySelectorAll('.mermaid:not(.mermaid-rendered)');
  if (unrendered.length > 0) {
    flowchartDebugger.log('INFO', `HTMX swap detected — rendering ${unrendered.length} new mermaid diagram(s)`);
    renderMermaidDiagrams();
  }
});

function initializeMermaid() {
  try {
    flowchartDebugger.log('INFO', 'Starting Mermaid initialization');

    // Check if Mermaid is available
    if (typeof mermaid === 'undefined') {
      throw new Error('Mermaid library is not loaded');
    }

    // Configure Mermaid with enhanced settings for better rendering
    const config = {
      startOnLoad: false,
      theme: 'default',
      flowchart: {
        // Use responsive sizing to avoid huge empty areas
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'linear',
        padding: 20,
        nodeSpacing: 60,
        rankSpacing: 60,
        diagramPadding: 12
      },
      securityLevel: 'loose',
      logLevel: 'error',
      maxTextSize: 90000,
      maxEdges: 100,
      wrap: true,
      fontSize: 14
    };

    flowchartDebugger.log('DEBUG', 'Mermaid configuration', config);

    mermaid.initialize(config);

    flowchartDebugger.log('INFO', 'Mermaid initialized successfully with enhanced settings');

    // Render all .mermaid blocks with error handling and animation
    renderMermaidDiagrams();

  } catch (error) {
    const errorInfo = flowchartDebugger.logError(error, {
      phase: 'initialization',
      mermaidAvailable: typeof mermaid !== 'undefined'
    });

    // Show fallback for all mermaid elements if initialization fails
    const mermaidElements = document.querySelectorAll('.mermaid');
    mermaidElements.forEach(element => {
      displayFallbackContent(element, new Error('Mermaid initialization failed: ' + error.message));
    });
  }
}

async function renderMermaidDiagrams() {
  try {
    const mermaidElements = document.querySelectorAll('.mermaid');

    if (mermaidElements.length === 0) {
      console.log('No mermaid diagrams found to render');
      return;
    }

    console.log(`Found ${mermaidElements.length} mermaid diagram(s) to render`);

    for (let i = 0; i < mermaidElements.length; i++) {
      const element = mermaidElements[i];

      try {
        // Store original content for fallback
        const originalContent = element.textContent.trim();

        if (!originalContent) {
          console.warn('Empty mermaid diagram found, skipping');
          displayFallbackContent(element, new Error('Empty diagram content'));
          continue;
        }

        console.log('Rendering mermaid diagram:', originalContent.substring(0, 100) + '...');

        // Generate unique ID for this diagram
        const diagramId = `mermaid-diagram-${i}`;

        // Validate that mermaid is available and ready
        if (typeof mermaid === 'undefined' || !mermaid.render) {
          throw new Error('Mermaid library not properly loaded or initialized');
        }

        // Use modern mermaid.render() API with additional error handling
        const renderResult = await mermaid.render(diagramId, originalContent);

        if (!renderResult || !renderResult.svg) {
          throw new Error('Mermaid render returned invalid result');
        }

        // Replace element content with rendered SVG and fix sizing
        element.innerHTML = renderResult.svg;
        element.classList.add('mermaid-rendered');

        // Fix SVG sizing issues
        fixSVGSizing(element);

        // Add enhanced styling and animation after rendering
        enhanceFlowchartVisualization(element);

        console.log(`Mermaid diagram ${i + 1} rendered successfully`);

      } catch (error) {
        console.error(`Failed to render mermaid diagram ${i + 1}:`, error);

        // Display fallback content when rendering fails
        displayFallbackContent(element, error);
      }
    }

    console.log('Finished processing all mermaid diagrams');

  } catch (error) {
    console.error('Critical error in renderMermaidDiagrams:', error);

    // Fallback for critical errors - try to handle any remaining mermaid elements
    try {
      const mermaidElements = document.querySelectorAll('.mermaid:not(.mermaid-rendered)');
      mermaidElements.forEach((element, index) => {
        displayFallbackContent(element, new Error(`Critical rendering error: ${error.message}`));
      });
    } catch (fallbackError) {
      console.error('Failed to display fallback content:', fallbackError);
    }
  }
}

function displayFallbackContent(element, error) {
  try {
    console.log('Displaying fallback content for failed mermaid diagram');

    // Ensure we have a valid element and parent
    if (!element || !element.parentNode) {
      console.error('Invalid element provided to displayFallbackContent');
      return;
    }

    // Store original content for debugging
    const originalContent = element.textContent ? element.textContent.trim() : 'No content available';
    const errorMessage = error && error.message ? error.message : 'Unknown rendering error';

    // Create fallback content
    const fallbackDiv = document.createElement('div');
    fallbackDiv.className = 'mermaid-fallback';
    fallbackDiv.setAttribute('role', 'alert');
    fallbackDiv.setAttribute('aria-label', 'Flowchart rendering failed');

    fallbackDiv.style.cssText = `
      border: 2px dashed var(--color-border, #ccc);
      padding: 2em;
      text-align: center;
      background-color: var(--color-surface, #f8f9fa);
      color: var(--color-text-secondary, #6c757d);
      border-radius: 8px;
      margin: 1em 0;
      min-height: 200px;
      display: flex;
      flex-direction: column;
      justify-content: center;
    `;

    // Create safe HTML content
    const titleElement = document.createElement('h4');
    titleElement.style.cssText = 'color: var(--color-fail, #dc3545); margin-top: 0; margin-bottom: 1em;';
    titleElement.textContent = '⚠️ Flowchart Rendering Failed';

    const descriptionElement = document.createElement('p');
    descriptionElement.textContent = 'The decision flowchart could not be displayed due to a rendering error.';
    descriptionElement.style.marginBottom = '0.5em';

    const instructionElement = document.createElement('p');
    instructionElement.textContent = 'Please refer to the "Decision Path Details" table below for the evaluation results.';
    instructionElement.style.marginBottom = '1em';

    // Create collapsible technical details
    const detailsElement = document.createElement('details');
    detailsElement.style.cssText = 'margin-top: 1em; text-align: left;';

    const summaryElement = document.createElement('summary');
    summaryElement.style.cssText = 'cursor: pointer; color: var(--color-primary, #007bff); margin-bottom: 0.5em;';
    summaryElement.textContent = 'Show Technical Details';

    const preElement = document.createElement('pre');
    preElement.style.cssText = `
      background: var(--color-bg, #f8f9fa);
      padding: 1em;
      border-radius: 4px;
      margin-top: 0.5em;
      font-size: 0.8em;
      overflow-x: auto;
      white-space: pre-wrap;
      word-wrap: break-word;
    `;
    preElement.textContent = `Error: ${errorMessage}\n\nOriginal Mermaid Definition:\n${originalContent}`;

    // Assemble the fallback content
    detailsElement.appendChild(summaryElement);
    detailsElement.appendChild(preElement);

    fallbackDiv.appendChild(titleElement);
    fallbackDiv.appendChild(descriptionElement);
    fallbackDiv.appendChild(instructionElement);
    fallbackDiv.appendChild(detailsElement);

    // Replace the failed mermaid element with fallback content
    element.parentNode.replaceChild(fallbackDiv, element);

    console.log('Fallback content displayed successfully');

  } catch (fallbackError) {
    console.error('Failed to display fallback content:', fallbackError);

    // Last resort fallback - simple text replacement
    try {
      if (element && element.parentNode) {
        element.innerHTML = `
          <div style="padding: 2em; text-align: center; border: 1px solid #ccc; background: #f8f9fa;">
            <p style="color: #dc3545; font-weight: bold;">⚠️ Flowchart could not be displayed</p>
            <p>Please refer to the Decision Path Details table for evaluation results.</p>
          </div>
        `;
      }
    } catch (lastResortError) {
      console.error('Last resort fallback also failed:', lastResortError);
    }
  }
}
// Fix SVG sizing and viewport issues
function fixSVGSizing(element) {
  try {
    const svg = element.querySelector('svg');
    if (!svg) return;

    // Remove restrictive width/height attributes and let CSS handle sizing
    svg.removeAttribute('width');
    svg.removeAttribute('height');

    // Ensure proper viewBox is set
    const viewBox = svg.getAttribute('viewBox');
    if (!viewBox) {
      // Try to calculate viewBox from SVG content
      const bbox = svg.getBBox();
      svg.setAttribute('viewBox', `${bbox.x - 20} ${bbox.y - 20} ${bbox.width + 40} ${bbox.height + 40}`);
    }

    // Set responsive attributes
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    svg.style.width = '100%';
    svg.style.height = 'auto';
    svg.style.maxWidth = '1200px';
    svg.style.minHeight = '400px';

    console.log('SVG sizing fixed successfully');

  } catch (error) {
    console.error('Error fixing SVG sizing:', error);
  }
}

// Enhanced flowchart visualization with animations and dynamic styling
function enhanceFlowchartVisualization(element) {
  try {
    console.log('Enhancing flowchart visualization with animations');

    const svg = element.querySelector('svg');
    if (!svg) {
      console.warn('No SVG found in mermaid element for enhancement');
      return;
    }

    // Add CSS animations for the flowchart
    addFlowchartAnimations();

    // Animate the flowchart elements sequentially
    animateFlowchartElements(svg);

    // Add interactive hover effects
    addInteractiveEffects(svg);

    console.log('Flowchart visualization enhanced successfully');

  } catch (error) {
    console.error('Error enhancing flowchart visualization:', error);
  }
}

function addFlowchartAnimations() {
  // Check if animations are already added
  if (document.getElementById('flowchart-animations')) {
    return;
  }

  const style = document.createElement('style');
  style.id = 'flowchart-animations';
  style.textContent = `
    /* Flowchart Animation Styles */
    .flowchart-node {
      opacity: 0;
      /* Avoid applying CSS transforms to <g> nodes, which
         overrides Mermaid's translate() positioning. */
      animation: nodeAppear 0.6s ease-out forwards;
    }

    .flowchart-edge {
      stroke-dasharray: 1000;
      stroke-dashoffset: 1000;
      animation: drawPath 1.2s ease-out forwards;
    }

    .flowchart-pass {
      animation: pulseGreen 2s ease-in-out infinite;
    }

    .flowchart-fail {
      animation: pulseRed 2s ease-in-out infinite;
    }

    .flowchart-caution {
      animation: pulseYellow 2s ease-in-out infinite;
    }

    @keyframes nodeAppear { to { opacity: 1; } }

    @keyframes drawPath {
      to {
        stroke-dashoffset: 0;
      }
    }

    @keyframes pulseGreen {
      0%, 100% { filter: brightness(1); }
      50% { filter: brightness(1.2) drop-shadow(0 0 8px #198754); }
    }

    @keyframes pulseRed {
      0%, 100% { filter: brightness(1); }
      50% { filter: brightness(1.2) drop-shadow(0 0 8px #dc3545); }
    }

    @keyframes pulseYellow {
      0%, 100% { filter: brightness(1); }
      50% { filter: brightness(1.2) drop-shadow(0 0 8px #ffc107); }
    }

    /* Interactive hover effects */
    .flowchart-node:hover {
      /* Do not scale nodes to preserve layout */
      filter: brightness(1.05);
      transition: filter 0.2s ease;
      cursor: pointer;
    }

    .flowchart-edge:hover {
      stroke-width: 3px;
      transition: stroke-width 0.2s ease;
    }
  `;

  document.head.appendChild(style);
}

function animateFlowchartElements(svg) {
  try {
    // Find all nodes and edges in the SVG
    const nodes = svg.querySelectorAll('g.node');
    const edges = svg.querySelectorAll('g.edgePath path');

    // Animate nodes with staggered timing
    nodes.forEach((node, index) => {
      node.classList.add('flowchart-node');
      node.style.animationDelay = `${index * 0.2}s`;

      // Add status-based animations based on node classes
      const rect = node.querySelector('rect, circle, polygon');
      if (rect) {
        const fill = rect.getAttribute('fill') || '';
        if (fill.includes('#d1e7dd') || fill.includes('#198754')) {
          node.classList.add('flowchart-pass');
        } else if (fill.includes('#f8d7da') || fill.includes('#dc3545')) {
          node.classList.add('flowchart-fail');
        } else if (fill.includes('#fff3cd') || fill.includes('#ffc107')) {
          node.classList.add('flowchart-caution');
        }
      }
    });

    // Animate edges (arrows) with staggered timing
    edges.forEach((edge, index) => {
      edge.classList.add('flowchart-edge');
      edge.style.animationDelay = `${(nodes.length * 0.2) + (index * 0.1)}s`;
    });

    console.log(`Animated ${nodes.length} nodes and ${edges.length} edges`);

  } catch (error) {
    console.error('Error animating flowchart elements:', error);
  }
}

function addInteractiveEffects(svg) {
  try {
    const nodes = svg.querySelectorAll('g.node');

    nodes.forEach(node => {
      node.classList.add('flowchart-node');

      // Add tooltip functionality
      node.addEventListener('mouseenter', function(e) {
        showNodeTooltip(e, this);
      });

      node.addEventListener('mouseleave', function() {
        hideNodeTooltip();
      });
    });

    console.log(`Added interactive effects to ${nodes.length} nodes`);

  } catch (error) {
    console.error('Error adding interactive effects:', error);
  }
}

function showNodeTooltip(event, node) {
  try {
    // Remove existing tooltip
    hideNodeTooltip();

    // Get node text content
    const textElement = node.querySelector('text');
    if (!textElement) return;

    const nodeText = textElement.textContent.trim();
    if (!nodeText) return;

    // Create tooltip
    const tooltip = document.createElement('div');
    tooltip.id = 'flowchart-tooltip';
    tooltip.style.cssText = `
      position: absolute;
      background: var(--color-surface, #fff);
      border: 1px solid var(--color-border, #ccc);
      border-radius: 4px;
      padding: 8px 12px;
      font-size: 12px;
      color: var(--color-text-primary, #333);
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
      z-index: 1000;
      max-width: 200px;
      word-wrap: break-word;
      pointer-events: none;
    `;

    tooltip.textContent = nodeText;
    document.body.appendChild(tooltip);

    // Position tooltip
    const rect = tooltip.getBoundingClientRect();
    tooltip.style.left = `${event.pageX - rect.width / 2}px`;
    tooltip.style.top = `${event.pageY - rect.height - 10}px`;

  } catch (error) {
    console.error('Error showing node tooltip:', error);
  }
}

function hideNodeTooltip() {
  const tooltip = document.getElementById('flowchart-tooltip');
  if (tooltip) {
    tooltip.remove();
  }
}

// Risk Assessment Feature
function addRiskAssessmentIndicators(svg, evaluationData) {
  try {
    if (!evaluationData || !evaluationData.path) return;

    console.log('Adding risk assessment indicators');

    // Calculate overall risk score based on evaluation path
    let riskScore = 0;
    let totalChecks = 0;

    evaluationData.path.forEach(([name, value, threshold, status]) => {
      totalChecks++;
      if (status === 'FAIL') riskScore += 2;
      else if (status === 'CLOSE_FAIL') riskScore += 1;
    });

    const riskPercentage = Math.round((riskScore / (totalChecks * 2)) * 100);

    // Add risk indicator to the flowchart
    const riskIndicator = document.createElement('div');
    riskIndicator.className = 'risk-indicator';
    riskIndicator.style.cssText = `
      position: absolute;
      top: 10px;
      right: 10px;
      background: ${riskPercentage > 60 ? '#dc3545' : riskPercentage > 30 ? '#ffc107' : '#198754'};
      color: white;
      padding: 5px 10px;
      border-radius: 15px;
      font-size: 12px;
      font-weight: bold;
    `;
    riskIndicator.textContent = `Risk: ${riskPercentage}%`;

    const container = svg.closest('.mermaid');
    if (container) {
      container.style.position = 'relative';
      container.appendChild(riskIndicator);
    }

  } catch (error) {
    console.error('Error adding risk assessment indicators:', error);
  }
}
