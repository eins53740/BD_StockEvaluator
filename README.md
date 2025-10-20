# Stock Evaluator

This project is a full-stack stock evaluation tool with a Python backend and a native Android client.

- **Backend:** A powerful Python application using FastAPI and Flask to provide stock analysis, risk assessment, trend analysis, and more. It features dynamic flowchart visualizations of the evaluation process.
- **Android Client:** A native Android application built with Kotlin, Jetpack Compose, and MVVM architecture to consume the backend API and display stock evaluations on a mobile device.

## What's New? 🎉

Your Stock Evaluator has been significantly enhanced with professional-grade features:

- **🎯 Advanced Risk Assessment** - Multi-factor risk scoring with actionable recommendations
- **🌍 Macro Dashboard** - FRED-powered macro backdrop with recession and sentiment signals
- **📈 Trend Analysis** - Multi-timeframe momentum and consistency analysis  
- **🔍 Comparative Analysis** - Industry benchmarking and peer comparison
- **💰 Dividend Analysis** - Yield attractiveness and sustainability assessment
- **🎨 Animated Flowcharts** - Dynamic visualizations with status-based coloring
- **📱 Mobile Ready** - PWA support and Android APK deployment capability

## Project Structure

- `src/bd_stockevaluator`: The Python backend source code.
- `android-client`: The Android client source code.
- `docs`: Project documentation.

## Quick Setup (2 minutes) ⚡

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Web UI (Flask)
```bash
python src/bd_stockevaluator/app.py
```

### 3. Run the REST API (FastAPI)
```bash
uvicorn src.bd_stockevaluator.api.main:app --reload
```

### 4. Open the Web UI
Navigate to: `http://localhost:5000`

### 5. Hit the API (optional)
Try `http://localhost:8000/health` or `POST http://localhost:8000/evaluate` with a JSON body:
```json
{"ticker": "MSFT", "include_opinion": true}
```

## How to Use 📖

### Basic Stock Analysis
1. Enter any stock ticker (e.g., `MSFT`, `AAPL`, `GOOGL`)
2. Click "Evaluate" 
3. View the animated decision flowchart
4. Review the comprehensive analysis sections below

### Understanding the Results

#### 🎯 Risk Assessment
- **Risk Score**: 0-100% (lower is better)
- **Risk Level**: Low/Moderate/High/Very High Risk
- **Recommendations**: Specific actions based on risk factors

#### 📈 Trend Analysis  
- **Multi-timeframe Returns**: 1mo, 3mo, 6mo, 1y performance
- **Momentum Score**: Weighted momentum across timeframes
- **Trend Consistency**: How consistent trends are across periods

#### 🔍 Comparative Analysis
- **Market Cap Category**: Micro/Small/Mid/Large/Mega Cap
- **Valuation**: Under/Fairly/Over-valued vs typical ranges
- **Growth**: High/Moderate/Low/Declining growth profile
- **Profitability**: Profitability vs industry standards

#### 💰 Dividend Analysis
- **Current Yield**: Annual dividend as % of price
- **Sustainability**: Very Sustainable to At Risk
- **Attractiveness**: Very Low to High Yield rating

## Advanced Features 🔧

### Animated Flowcharts
- Nodes appear sequentially with smooth animations
- Status-based coloring: Green (Pass), Red (Fail), Yellow (Close)
- Interactive hover tooltips with detailed information
- Risk indicators and visual feedback

### Mobile Support
- **Progressive Web App**: Install on mobile devices
- **Responsive Design**: Optimized for all screen sizes
- **Offline Capability**: View cached results without internet
- **Android APK**: Convert to native mobile app (see DEPLOYMENT_GUIDE.md)

## Testing Your Setup 🧪

### Run Demo
```bash
python src/bd_stockevaluator/demo.py
```
This demonstrates all features with sample data.

### Run Tests
```bash
# Test flowchart generation
python tests/test_flowchart.py

# Test integration
python tests/test_integration.py
```

## Customization Options ⚙️

### Modify Evaluation Thresholds
Edit `src/bd_stockevaluator/evaluator.py` THRESHOLDS dictionary:
```python
THRESHOLDS = {
    "rev_growth": 0.10,  # 10% revenue growth
    "pe": 25,            # P/E ratio threshold
    "roe": 0.15,         # 15% ROE threshold
    # ... customize as needed
}
```

### Add New Risk Factors
Extend `src/bd_stockevaluator/features.py` StockAnalysisFeatures class with new analysis methods.

### Customize UI Colors
Modify CSS variables in `src/bd_stockevaluator/templates/index.html`:
```css
:root {
    --color-primary: #007bff;    /* Change primary color */
    --color-pass: #198754;       /* Success color */
    --color-fail: #dc3545;       /* Failure color */
}
```

## Troubleshooting 🔧

### Common Issues

**"Module not found" errors**
```bash
pip install -r requirements.txt
```

**API key issues**
- Ensure `config/api_keys.txt` exists
- Add your Google AI Studio API key: `api_key_aistudio_google=your_key_here`
- Add your FRED API key: `FRED_API_KEY=your_key_here` in `.env` or `config/api_keys.txt`

**Flowchart not rendering**
- Check browser console for JavaScript errors
- Ensure internet connection for Mermaid CDN
- Try refreshing the page

**Mobile features not working**
```bash
python src/bd_stockevaluator/mobile_config.py  # Regenerate mobile files
```

## Dependencies

Python dependencies are managed using `pyproject.toml`. For development, install the optional dependencies:
```bash
pip install -e .[dev]
```