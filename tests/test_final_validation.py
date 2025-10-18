#!/usr/bin/env python3
"""
Final validation test to ensure Task 1 requirements are fully met.
This test specifically validates the requirements from the task specification.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bd_stockevaluator.core.service import generate_flowchart_definition
from bd_stockevaluator.evaluator import StockEvaluator

def test_task_1_requirements():
    """
    Test all specific requirements from Task 1:
    - Remove HTML-like tags (<br><b>) from node text
    - Replace CSS variable references with direct color values
    - Simplify node text to prevent parsing errors while maintaining readability
    - Test with simple text formatting that Mermaid can properly parse
    """
    
    print("=== TASK 1 FINAL VALIDATION TEST ===")
    print("Testing all specific requirements from the task specification")
    print()
    
    # Test with various scenarios to ensure robustness
    test_scenarios = [
        {
            'name': 'Standard Case',
            'data': {
                'trailingPE': 20.0,
                'returnOnEquity': 0.18,
                'profitMargins': 0.15,
                'debtToEquity': 40.0,
                'quickRatio': 1.6,
                'revenueGrowth': 0.12,
                'longName': 'Standard Test Company'
            }
        },
        {
            'name': 'Edge Case with Extreme Values',
            'data': {
                'trailingPE': 100.0,
                'returnOnEquity': 0.01,
                'profitMargins': 0.001,
                'debtToEquity': 200.0,
                'quickRatio': 0.1,
                'revenueGrowth': -0.05,
                'longName': 'Extreme Values Company'
            }
        },
        {
            'name': 'Missing Data Case',
            'data': {
                'trailingPE': None,
                'returnOnEquity': None,
                'profitMargins': 0.15,
                'debtToEquity': 40.0,
                'quickRatio': None,
                'revenueGrowth': 0.12,
                'longName': 'Missing Data Company'
            }
        }
    ]
    
    all_requirements_met = True
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"--- Testing Scenario {i}: {scenario['name']} ---")
        
        # Generate flowchart
        evaluator = StockEvaluator(scenario['data'])
        result, path, _ = evaluator.evaluate()
        flowchart_def = generate_flowchart_definition(evaluator, result, path)
        
        print(f"Generated flowchart for: {scenario['data']['longName']}")
        print(f"Evaluation result: {result}")
        
        # REQUIREMENT 1: Remove HTML-like tags (<br><b>) from node text
        # Note: We need to distinguish between HTML tags and valid comparison operators
        html_tags_found = []
        html_patterns = [r'<br>', r'<b>', r'</b>', r'<div>', r'</div>', r'<span>', r'</span>']
        for pattern in html_patterns:
            matches = re.findall(pattern, flowchart_def, re.IGNORECASE)
            if matches:
                html_tags_found.extend(matches)
        
        req1_passed = len(html_tags_found) == 0
        print(f"✓ REQUIREMENT 1 - No HTML tags: {'PASS' if req1_passed else 'FAIL'}")
        if not req1_passed:
            print(f"  Found HTML tags: {html_tags_found}")
            all_requirements_met = False
        
        # REQUIREMENT 2: Replace CSS variable references with direct color values
        css_vars_found = re.findall(r'var\(--[^)]+\)', flowchart_def)
        direct_colors_found = re.findall(r'fill:#[0-9a-fA-F]{6}', flowchart_def)
        
        req2_passed = len(css_vars_found) == 0 and len(direct_colors_found) >= 3
        print(f"✓ REQUIREMENT 2 - Direct colors, no CSS vars: {'PASS' if req2_passed else 'FAIL'}")
        if not req2_passed:
            print(f"  CSS variables found: {css_vars_found}")
            print(f"  Direct colors found: {len(direct_colors_found)}")
            all_requirements_met = False
        
        # REQUIREMENT 3: Simplify node text to prevent parsing errors while maintaining readability
        # Check for problematic characters that could cause parsing issues
        # Note: < and > are valid comparison operators in Mermaid, so we exclude them
        problematic_chars = ['""', '\n\n', '\r']
        problematic_found = []
        for char in problematic_chars:
            if char in flowchart_def:
                problematic_found.append(char)
        
        # Check that text is still readable (contains actual values and thresholds)
        readable_elements = ['Actual:', '%', '?', 'Growth', 'P/E', 'ROE']
        readable_count = sum(1 for element in readable_elements if element in flowchart_def)
        
        req3_passed = len(problematic_found) == 0 and readable_count >= 4
        print(f"✓ REQUIREMENT 3 - Simplified but readable text: {'PASS' if req3_passed else 'FAIL'}")
        if not req3_passed:
            print(f"  Problematic characters found: {problematic_found}")
            print(f"  Readable elements found: {readable_count}/6")
            all_requirements_met = False
        
        # REQUIREMENT 4: Test with simple text formatting that Mermaid can properly parse
        # Check for valid Mermaid syntax elements
        decision_nodes_present = '{' in flowchart_def and '}' in flowchart_def
        mermaid_syntax_checks = [
            ('Graph declaration', 'graph TD' in flowchart_def),
            ('Decision nodes', decision_nodes_present),
            ('Node connections', '-->' in flowchart_def),
            ('Class definitions', 'classDef' in flowchart_def),
            ('Class applications', flowchart_def.count('class ') >= 3),
            ('Proper semicolons', flowchart_def.count(';') >= 10),
            ('Balanced braces', flowchart_def.count('{') == flowchart_def.count('}')),
        ]
        
        syntax_failures = [check[0] for check in mermaid_syntax_checks if not check[1]]
        req4_passed = len(syntax_failures) == 0
        print(f"✓ REQUIREMENT 4 - Valid Mermaid syntax: {'PASS' if req4_passed else 'FAIL'}")
        if not req4_passed:
            print(f"  Syntax failures: {syntax_failures}")
            all_requirements_met = False
        
        print()
    
    # Final summary
    print("=" * 60)
    print("TASK 1 REQUIREMENTS VALIDATION SUMMARY")
    print("=" * 60)
    
    if all_requirements_met:
        print("✅ ALL TASK 1 REQUIREMENTS SUCCESSFULLY MET!")
        print()
        print("✓ HTML-like tags removed from node text")
        print("✓ CSS variable references replaced with direct color values")
        print("✓ Node text simplified to prevent parsing errors while maintaining readability")
        print("✓ Simple text formatting that Mermaid can properly parse")
        print()
        print("The Mermaid flowchart syntax generation has been successfully fixed!")
    else:
        print("❌ SOME TASK 1 REQUIREMENTS NOT MET!")
        print("Review the detailed output above for specific issues.")

    assert all_requirements_met, "Task 1 requirements validation failed; see log for details."

if __name__ == "__main__":
    try:
        test_task_1_requirements()
    except AssertionError:
        sys.exit(1)
    else:
        sys.exit(0)
