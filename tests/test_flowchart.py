#!/usr/bin/env python3
"""
Test script to verify the flowchart generation produces valid Mermaid syntax.
This tests the fixes made to remove HTML-like tags and use direct color values.
"""

from __future__ import annotations

from bd_stockevaluator.core.service import generate_flowchart_definition
from bd_stockevaluator.evaluator import StockEvaluator

def test_flowchart_generation():
    """Test flowchart generation with multiple scenarios"""
    
    test_scenarios = [
        {
            'name': 'Strong Buy Scenario',
            'data': {
                'trailingPE': 15.0,
                'returnOnEquity': 0.25,
                'profitMargins': 0.20,
                'debtToEquity': 30.0,
                'quickRatio': 2.0,
                'revenueGrowth': 0.15,
                'longName': 'Strong Company Inc.'
            }
        },
        {
            'name': 'Do Not Buy Scenario',
            'data': {
                'trailingPE': 35.0,
                'returnOnEquity': 0.08,
                'profitMargins': 0.05,
                'debtToEquity': 80.0,
                'quickRatio': 0.8,
                'revenueGrowth': 0.03,
                'longName': 'Weak Company Inc.'
            }
        },
        {
            'name': 'Edge Case with None Values',
            'data': {
                'trailingPE': None,
                'returnOnEquity': 0.18,
                'profitMargins': None,
                'debtToEquity': 45.0,
                'quickRatio': 1.2,
                'revenueGrowth': 0.12,
                'longName': 'Incomplete Data Company'
            }
        },
        {
            'name': 'Special Characters Test',
            'data': {
                'trailingPE': 25.0,
                'returnOnEquity': 0.18,
                'profitMargins': 0.15,
                'debtToEquity': 45.0,
                'quickRatio': 1.2,
                'revenueGrowth': 0.12,
                'longName': 'Test & "Special" <Company> Inc.'
            }
        }
    ]
    
    all_tests_passed = True
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {scenario['name']}")
        print('='*60)
        
        # Create evaluator and get evaluation results
        evaluator = StockEvaluator(scenario['data'])
        result, path, _ = evaluator.evaluate()
        
        # Generate flowchart definition
        flowchart_def = generate_flowchart_definition(evaluator, result, path)
        
        print(f"Result: {result}")
        print(f"Path length: {len(path)}")
        print("\n--- GENERATED MERMAID DEFINITION ---")
        print(flowchart_def)
        print("\n--- VALIDATION CHECKS ---")
        
        # Basic validation checks
        checks = [
            ("Contains 'graph TD'", "graph TD" in flowchart_def),
            ("Contains proper line breaks", "<br/>" in flowchart_def),
            ("No CSS variables (var(--", "var(--" not in flowchart_def),
            ("Contains direct color values", "#" in flowchart_def and "fill:" in flowchart_def),
            ("Contains classDef definitions", "classDef" in flowchart_def),
            ("Valid arrow syntax", "-->" in flowchart_def and "|" in flowchart_def),
            ("Contains node connections", "-->" in flowchart_def),
            ("Contains decision nodes", "{" in flowchart_def and "}" in flowchart_def),
            ("No unescaped quotes in node text", '""' not in flowchart_def),
            ("Proper node syntax", all(line.strip().endswith(';') or line.strip().startswith('classDef') or line.strip().startswith('class') or line.strip().startswith('%%') or line.strip() == '' for line in flowchart_def.split('\n') if line.strip() and not line.strip().startswith('graph'))),
        ]
        
        scenario_passed = True
        for check_name, passed in checks:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status}: {check_name}")
            if not passed:
                scenario_passed = False
                all_tests_passed = False
        
        print(f"\n--- SCENARIO RESULT ---")
        if scenario_passed:
            print("✓ All validation checks passed for this scenario!")
        else:
            print("✗ Some validation checks failed for this scenario.")
    
    print(f"\n{'='*60}")
    print("OVERALL TEST RESULT")
    print('='*60)
    if all_tests_passed:
        print("✓ All test scenarios passed! Flowchart syntax generation is working correctly.")
    else:
        print("✗ Some test scenarios failed. Review the generated syntax.")

    assert all_tests_passed, "Flowchart generation validation failed; see log for details."

if __name__ == "__main__":
    try:
        test_flowchart_generation()
    except AssertionError:
        sys.exit(1)
    else:
        sys.exit(0)
