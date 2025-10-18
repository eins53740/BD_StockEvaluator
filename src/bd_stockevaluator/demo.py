#!/usr/bin/env python3
"""
Stock Evaluator - Feature Demo Script
Demonstrates the enhanced features and capabilities.
"""

from __future__ import annotations

import json

from .core.service import fmt, generate_flowchart_definition
from .evaluator import StockEvaluator
from .features import StockAnalysisFeatures

def demo_enhanced_features():
    """Demonstrate the enhanced stock evaluation features"""
    
    print("🚀 Stock Evaluator - Enhanced Features Demo")
    print("=" * 60)
    
    # Sample stock data for demonstration
    demo_stocks = {
        'STRONG_STOCK': {
            'longName': 'Strong Growth Company Inc.',
            'trailingPE': 18.5,
            'returnOnEquity': 0.22,
            'profitMargins': 0.18,
            'debtToEquity': 25.0,
            'quickRatio': 2.1,
            'revenueGrowth': 0.15,
            'marketCap': 50_000_000_000,
            'sector': 'Technology',
            'industry': 'Software',
            'beta': 1.2,
            'averageVolume': 2_000_000,
            'currentPrice': 125.50,
            'dividendYield': 0.025,
            'payoutRatio': 0.35
        },
        'RISKY_STOCK': {
            'longName': 'High Risk Ventures Ltd.',
            'trailingPE': 45.0,
            'returnOnEquity': 0.08,
            'profitMargins': 0.05,
            'debtToEquity': 85.0,
            'quickRatio': 0.9,
            'revenueGrowth': 0.03,
            'marketCap': 1_000_000_000,
            'sector': 'Energy',
            'industry': 'Oil & Gas',
            'beta': 2.1,
            'averageVolume': 500_000,
            'currentPrice': 15.25,
            'dividendYield': 0.08,
            'payoutRatio': 0.95
        }
    }
    
    for stock_name, stock_data in demo_stocks.items():
        print(f"\n📊 Analyzing: {stock_data['longName']}")
        print("-" * 50)
        
        # Basic evaluation
        evaluator = StockEvaluator(stock_data)
        result, path, _ = evaluator.evaluate()
        
        print(f"Basic Evaluation Result: {result}")
        print(f"Decision Path Length: {len(path)}")
        
        # Enhanced features analysis
        features = StockAnalysisFeatures(stock_name, stock_data)
        
        # Risk Assessment
        print("\n🎯 Risk Assessment:")
        risk_assessment = features.get_risk_assessment()
        if 'error' not in risk_assessment:
            print(f"  Overall Risk Score: {risk_assessment['overall_risk_score']}%")
            print(f"  Risk Level: {risk_assessment['risk_level']}")
            print("  Risk Factors:")
            for factor, score in risk_assessment['risk_factors'].items():
                if score is not None:
                    print(f"    - {factor.replace('_', ' ').title()}: {score:.1f}")
            print("  Recommendations:")
            for rec in risk_assessment['recommendations']:
                print(f"    • {rec}")
        
        # Comparative Analysis
        print("\n🔍 Comparative Analysis:")
        comp_analysis = features.get_comparative_analysis()
        if 'error' not in comp_analysis:
            print(f"  Sector: {comp_analysis['sector']}")
            print(f"  Market Cap Category: {comp_analysis['market_cap_category']}")
            print(f"  Valuation vs Peers: {comp_analysis['valuation_vs_peers']}")
            print(f"  Growth vs Peers: {comp_analysis['growth_vs_peers']}")
            print(f"  Profitability vs Peers: {comp_analysis['profitability_vs_peers']}")
        
        # Dividend Analysis
        print("\n💰 Dividend Analysis:")
        div_analysis = features.get_dividend_analysis()
        if 'error' not in div_analysis:
            if div_analysis['current_yield']:
                print(f"  Current Yield: {div_analysis['current_yield']:.2%}")
                print(f"  Yield Attractiveness: {div_analysis['yield_attractiveness']}")
                if div_analysis['payout_ratio']:
                    print(f"  Payout Ratio: {div_analysis['payout_ratio']:.1%}")
                    print(f"  Sustainability: {div_analysis['dividend_sustainability']}")
            else:
                print("  No dividend information available")
        
        # Generate flowchart
        print("\n📈 Flowchart Generation:")
        flowchart_def = generate_flowchart_definition(evaluator, result, path)
        print(f"  Flowchart generated successfully ({len(flowchart_def)} characters)")
        print(f"  Contains {flowchart_def.count('class ')} styled nodes")
        
        print("\n" + "=" * 60)

def demo_flowchart_features():
    """Demonstrate flowchart generation capabilities"""
    
    print("\n🎨 Flowchart Features Demo")
    print("=" * 40)
    
    # Test different scenarios
    scenarios = [
        {
            'name': 'Perfect Stock',
            'data': {
                'trailingPE': 15.0, 'returnOnEquity': 0.25, 'profitMargins': 0.20,
                'debtToEquity': 20.0, 'quickRatio': 2.5, 'revenueGrowth': 0.18
            }
        },
        {
            'name': 'Borderline Stock',
            'data': {
                'trailingPE': 24.0, 'returnOnEquity': 0.16, 'profitMargins': 0.11,
                'debtToEquity': 45.0, 'quickRatio': 1.4, 'revenueGrowth': 0.11
            }
        },
        {
            'name': 'Poor Stock',
            'data': {
                'trailingPE': 35.0, 'returnOnEquity': 0.05, 'profitMargins': 0.03,
                'debtToEquity': 90.0, 'quickRatio': 0.8, 'revenueGrowth': -0.02
            }
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📊 {scenario['name']}:")
        evaluator = StockEvaluator(scenario['data'])
        result, path, _ = evaluator.evaluate()
        
        print(f"  Result: {result}")
        print(f"  Metrics evaluated: {len(path)}")
        
        # Count pass/fail status
        pass_count = sum(1 for _, _, _, status in path if status == 'PASS')
        fail_count = sum(1 for _, _, _, status in path if status == 'FAIL')
        close_count = sum(1 for _, _, _, status in path if status == 'CLOSE_FAIL')
        
        print(f"  ✅ Passed: {pass_count}, ❌ Failed: {fail_count}, ⚠️ Close: {close_count}")

def demo_mobile_features():
    """Demonstrate mobile and PWA features"""
    
    print("\n📱 Mobile & PWA Features Demo")
    print("=" * 40)
    
    # Check if mobile files exist
    mobile_files = [
        'static/manifest.json',
        'static/sw.js',
        'config.xml'
    ]
    
    print("Mobile deployment files:")
    for file_path in mobile_files:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"  ✅ {file_path} ({file_size:,} bytes)")
        else:
            print(f"  ❌ {file_path} (missing)")
    
    # Check manifest content
    manifest_path = 'static/manifest.json'
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        print(f"\nPWA Manifest Details:")
        print(f"  App Name: {manifest.get('name', 'N/A')}")
        print(f"  Short Name: {manifest.get('short_name', 'N/A')}")
        print(f"  Display Mode: {manifest.get('display', 'N/A')}")
        print(f"  Theme Color: {manifest.get('theme_color', 'N/A')}")
        print(f"  Icons: {len(manifest.get('icons', []))} sizes")

def main():
    """Run the complete demo"""
    
    print("🎯 Stock Evaluator - Complete Feature Demonstration")
    print("=" * 70)
    print("This demo showcases all the enhanced features and capabilities")
    print("of your upgraded Stock Evaluator application.")
    print("=" * 70)
    
    try:
        # Demo enhanced analysis features
        demo_enhanced_features()
        
        # Demo flowchart capabilities
        demo_flowchart_features()
        
        # Demo mobile features
        demo_mobile_features()
        
        print("\n🎉 Demo completed successfully!")
        print("\nNext steps:")
        print("1. Run 'python app.py' to start the web application")
        print("2. Test the mobile features by accessing from a mobile device")
        print("3. Follow DEPLOYMENT_GUIDE.md for mobile app creation")
        print("4. Review ENHANCEMENT_SUMMARY.md for complete feature list")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        print("Please ensure all dependencies are installed:")
        print("pip install -r requirements.txt")

if __name__ == "__main__":
    main()
