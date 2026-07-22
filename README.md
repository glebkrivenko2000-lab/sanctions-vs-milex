# Assessing the Causal Impact of International Sanctions on Military Spending

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Econometrics](https://img.shields.io/badge/Methodology-2SLS%20%7C%20PPML%20%7C%20TWFE-success.svg)](#empirical-strategy)

This repository contains the data pipeline and econometric codebase for my Master's Thesis: *"Assessing the Impact of International Sanctions on Military Spending of Warring Countries"*. 

The study investigates a fundamental question in political economy: Do economic sanctions successfully constrain a target state's military capabilities, or do they trigger a "rally-around-the-flag" effect, paradoxically increasing defense outlays? To overcome severe endogeneity and selection bias, this project develops a novel identification strategy combining structural gravity models of trade with a Two-Stage Least Squares (2SLS) approach.

📄 **[Read the full Master's Thesis (PDF)](Master_Thesis_Krivenko.pdf)**

## 📊 Data Sources
The analysis relies on a complex dyadic-to-country-year data pipeline, merging six major international datasets:
* **SIPRI Military Expenditure Database:** Absolute defense spending and military burden (Share of GDP).
* **Global Sanctions Data Base (GSDB):** Dyadic sanction data categorized by type (trade, financial, military, etc.) and intensity (partial vs. complete).
* **Correlates of War (COW):** Bilateral trade flows and Militarized Interstate Disputes (MID).
* **CEPII GeoDist:** Exogenous geographic and historical bilateral frictions.
* **UN General Assembly Voting Records:** Political misalignment/distance between states.
* **Polity V Project:** Institutional and regime characteristics.

## 🔬 Empirical Strategy & Code Highlights
The codebase demonstrates advanced panel-data methods and causal inference techniques:

1. **Structural Gravity Model (PPML):** Actual trade flows decline mechanically when sanctions are imposed. To measure a target's true economic vulnerability, `02_Exogenous_Weights_and_Political_Distance.ipynb` estimates a gravity model using the Poisson Pseudo-Maximum Likelihood (PPML) estimator. This generates "natural" trade weights strictly driven by exogenous geographic and historical determinants.
2. **Zero-Stage Dyadic Prediction (LPM):** Predicts the probability of sanction imposition at the sender-target-year level using the sender's leave-one-out historical aggressiveness and lagged UNGA political distance.
3. **Instrumental Variables (2SLS):** The dyadic probabilities are aggregated and weighted by the exogenous PPML trade shares to construct a robust instrument for sanction intensity.
4. **Custom TWFE Implementation:** The `03_Main_2SLS_Analysis.ipynb` notebook implements Two-Way Fixed Effects (Country and Year FEs) manually via the Frisch-Waugh-Lovell theorem by demeaning the data. This allows for flexible and computationally efficient robust standard error estimation (HC1).

## 📁 Repository Structure

```text
├── data/
│   ├── raw/                 # Raw datasets (see data/DATA_README.md for download links)
│   └── cleaned/             # Processed datasets ready for estimation
├── 01_data_preparation.py   # Data wrangling, ISO3 mapping, and merging pipeline
├── 02_Exogenous_Weights_and_Political_Distance.ipynb  # PPML gravity models & UNGA distance
├── 03_Main_2SLS_Analysis.ipynb                        # 2SLS IV estimation & custom TWFE
├── Master_Thesis_Krivenko.pdf                         # Full thesis document
├── requirements.txt         # Python dependencies
└── README.md
```

## 🚀 How to Run

1. Clone the repository:
   ```bash
   git clone https://github.com/glebkrivenko2000-lab/sanctions-vs-milex.git
   cd sanctions-vs-milex
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Follow the instructions in `data/DATA_README.md` to download the raw datasets into `data/raw/`.
4. Run the data preparation script:
   ```bash
   python 01_data_preparation.py
   ```
5. Execute the Jupyter notebooks sequentially to reproduce the gravity weights and the main 2SLS results.

## 👨‍💻 Author
**Gleb Krivenko**  
*MA in Economics, New Economic School (NES)*  
Contact: [gkrivenko@nes.ru]
