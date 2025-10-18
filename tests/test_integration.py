#!/usr/bin/env python3
"""
Integration test to verify the complete flowchart generation workflow.
Tests the Flask app's flowchart generation without starting the web server.
"""

from __future__ import annotations

import sys

from bd_stockevaluator.core.service import generate_flowchart_definition
from bd_stockevaluator.evaluator import StockEvaluator

def test_mermaid_syntax_validation():
    """Test that generated Mermaid syntax is valid and renders properly"""
    
    # Test data representing a typical stock evaluation
    test_stock_info = {
        'trailingPE': 22.5,
        'returnOnEquity': 0.16,
        'profitMargins': 0.12,
        'debtToEquity': 55.0,
        'quickRatio': 1.3,
        'revenueGrowth': 0.11,
        'longName': 'Integration Test Company'
    }
    
    print("=== INTEGRATION TEST: MERMAID SYNTAX VALIDATION ===")
    
    # Create evaluator and generate flowchart
    evaluator = StockEvaluator(test_stock_info)
    result, path, _ = evaluator.evaluate()
    flowchart_def = generate_flowchart_definition(evaluator, result, path)
    
    print(f"Stock: {test_stock_info['longName']}")
    print(f"Evaluation Result: {result}")
    print(f"Decision Path Length: {len(path)}")
    
    print("\n--- GENERATED MERMAID FLOWCHART ---")
    print(flowchart_def)
    
    # Advanced syntax validation
    print("\n--- ADVANCED SYNTAX VALIDATION ---")
    
    lines = flowchart_def.split('\n')
    issues = []
    
    # Check for proper graph declaration
    if not any(line.strip().startswith('graph TD') for line in lines):
        issues.append("Missing 'graph TD' declaration")
    
    # Check for balanced braces in decision nodes
    for line in lines:
        if '{{' in line and '}}' not in line:
            issues.append(f"Unbalanced braces in line: {line.strip()}")
        if '{{' in line and line.count('{{') != line.count('}}'):
            issues.append(f"Mismatched brace count in line: {line.strip()}")
    
    # Check for proper node connections
    connection_count = sum(1 for line in lines if '-->' in line)
    if connection_count < 5:  # Should have multiple connections
        issues.append(f"Too few node connections found: {connection_count}")
    
    # Check for class definitions
    class_def_count = sum(1 for line in lines if line.strip().startswith('classDef'))
    if class_def_count < 3:  # Should have pass, fail, close_fail
        issues.append(f"Missing class definitions: found {class_def_count}, expected at least 3")
    
    # Check for class applications
    class_app_count = sum(1 for line in lines if line.strip().startswith('class '))
    if class_app_count < 3:  # Should have multiple class applications
        issues.append(f"Too few class applications: {class_app_count}")
    
    # Check for proper color syntax
    color_lines = [line for line in lines if 'fill:' in line and 'stroke:' in line]
    for line in color_lines:
        if not ('#' in line and 'fill:#' in line and 'stroke:#' in line):
            issues.append(f"Invalid color syntax in line: {line.strip()}")
    
    # Check for problematic characters
    problematic_chars = ['<br>', '<b>', '</b>', 'var(--', '""']
    for char_seq in problematic_chars:
        if char_seq in flowchart_def:
            issues.append(f"Found problematic character sequence: {char_seq}")
    
    # Report results
    if issues:
        print("✗ VALIDATION ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✓ ALL ADVANCED VALIDATION CHECKS PASSED!")
        print("  - Proper graph structure")
        print("  - Balanced node syntax")
        print("  - Adequate node connections")
        print("  - Complete class definitions")
        print("  - Valid color syntax")
        print("  - No problematic characters")

    assert not issues, "Mermaid syntax validation failed; see log for details."

def test_different_outcomes():
    """Test flowchart generation for different evaluation outcomes"""
    
    print("\n=== TESTING DIFFERENT EVALUATION OUTCOMES ===")
    
    scenarios = [
        {
            'name': 'BUY Scenario',
            'data': {
                'trailingPE': 18.0,
                'returnOnEquity': 0.22,
                'profitMargins': 0.18,
                'debtToEquity': 25.0,
                'quickRatio': 2.1,
                'revenueGrowth': 0.14,
                'longName': 'Excellent Company'
            }
        },
        {
            'name': 'BUY with Caution Scenario',
            'data': {
                'trailingPE': 20.0,
                'returnOnEquity': 0.16,
                'profitMargins': 0.12,
                'debtToEquity': 45.0,
                'quickRatio': 1.4,  # Just below threshold
                'revenueGrowth': 0.11,
                'longName': 'Borderline Company'
            }
        }
    ]
    
    all_passed = True
    
    for scenario in scenarios:
        print(f"\n--- {scenario['name']} ---")
        
        evaluator = StockEvaluator(scenario['data'])
        result, path, _ = evaluator.evaluate()
        flowchart_def = generate_flowchart_definition(evaluator, result, path)
        
        print(f"Result: {result}")
        
        # Check that the flowchart reflects the correct outcome
        if "BUY" in result and "BUY" not in flowchart_def:
            print("✗ FAIL: BUY result not reflected in flowchart")
            all_passed = False
        elif "Do Not Buy" in result and "Do Not Buy" not in flowchart_def:
            print("✗ FAIL: Do Not Buy result not reflected in flowchart")
            all_passed = False
        elif "Caution" in result and "Caution" not in flowchart_def:
            print("✗ FAIL: Caution result not reflected in flowchart")
            all_passed = False
        else:
            print("✓ PASS: Result correctly reflected in flowchart")

    assert all_passed, "Flowchart outcome validation failed; see log for details."

if __name__ == "__main__":
    print("Starting Integration Tests for Mermaid Flowchart Generation")
    print("=" * 70)

    try:
        test_mermaid_syntax_validation()
        test1_passed = True
    except AssertionError:
        test1_passed = False

    try:
        test_different_outcomes()
        test2_passed = True
    except AssertionError:
        test2_passed = False

    print("\n" + "=" * 70)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 70)

    if test1_passed and test2_passed:
        print("✓ ALL INTEGRATION TESTS PASSED!")
        print("  The Mermaid flowchart generation is working correctly.")
        print("  Syntax is valid and outcomes are properly reflected.")
        sys.exit(0)
    else:
        print("✗ SOME INTEGRATION TESTS FAILED!")
        print("  Review the output above for specific issues.")
        sys.exit(1)
