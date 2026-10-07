"""Central configuration for the Phase 3 explainable multi-agent ESG system.

The Phase 3 cohort is loaded from the 50-company target list. Raw V1 datasets
are retained; BRSR PDFs are the primary company-level ESG source for FY 2024-25.
"""

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "raw-datasets"
PROCESSED_DATA_DIR = BASE_DIR / "processed-data"
BRSR_PDF_DIR = BASE_DIR / "brsr-pdfs"
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
BRSR_PDF_DIR.mkdir(parents=True, exist_ok=True)

TARGET_FINANCIAL_YEAR = "2024-25"
TARGET_COMPANY_COUNT = 50

# For the first five V1 companies, the original V1 office locations are kept.
# For the 15 Phase 3 additions, only a representative headquarters location is
# used unless additional locations are explicitly documented. This avoids
# inventing a large office footprint and keeps AQI scoring conservative.

COMPANIES = {
    "TCS": {
        "full_name": 'Tata Consultancy Services',
        "ticker": 'TCS.NS',
        "brsr_file": 'TCS_BR_24-25.pdf',
        "headquarters": {'city': 'Mumbai', 'area': 'Fort'},
        "major_offices": [{'city': 'Mumbai', 'area': 'Andheri East'}, {'city': 'Bangalore', 'area': 'Electronic City'}, {'city': 'Pune', 'area': 'Hinjewadi'}, {'city': 'Chennai', 'area': 'Sholinganallur'}, {'city': 'Hyderabad', 'area': 'Gachibowli'}, {'city': 'Noida', 'area': 'Sector 62'}],
    },
    "INFY": {
        "full_name": 'Infosys',
        "ticker": 'INFY.NS',
        "brsr_file": 'INFY_BR_24-25.pdf',
        "headquarters": {'city': 'Bangalore', 'area': 'Electronics City'},
        "major_offices": [{'city': 'Pune', 'area': 'Hinjewadi'}, {'city': 'Chennai', 'area': 'Mahindra World City'}, {'city': 'Hyderabad', 'area': 'HITEC City'}, {'city': 'Mysore', 'area': 'Infosys Campus'}, {'city': 'Mumbai', 'area': 'Powai'}, {'city': 'Noida', 'area': 'Sector 135'}],
    },
    "WIPRO": {
        "full_name": 'Wipro',
        "ticker": 'WIPRO.NS',
        "brsr_file": 'WIPRO_BR_24-25.pdf',
        "headquarters": {'city': 'Bangalore', 'area': 'Sarjapur Road'},
        "major_offices": [{'city': 'Bangalore', 'area': 'Electronic City'}, {'city': 'Mumbai', 'area': 'Goregaon East'}, {'city': 'Pune', 'area': 'Hinjewadi'}, {'city': 'Hyderabad', 'area': 'Madhapur'}, {'city': 'Chennai', 'area': 'Sholinganallur'}, {'city': 'Gurugram', 'area': 'Cyber City'}, {'city': 'Kochi', 'area': 'Infopark'}],
    },
    "HCLTECH": {
        "full_name": 'HCL Technologies',
        "ticker": 'HCLTECH.NS',
        "brsr_file": 'HCLTECH_BR_24-25.pdf',
        "headquarters": {'city': 'Noida', 'area': 'Sector 3'},
        "major_offices": [{'city': 'Noida', 'area': 'Sector 126'}, {'city': 'Bangalore', 'area': 'Nagawara'}, {'city': 'Chennai', 'area': 'Siruseri IT Park'}, {'city': 'Pune', 'area': 'Kharadi'}, {'city': 'Hyderabad', 'area': 'Madhapur'}, {'city': 'Mumbai', 'area': 'Andheri'}, {'city': 'Gurugram', 'area': 'Udyog Vihar'}],
    },
    "TECHM": {
        "full_name": 'Tech Mahindra',
        "ticker": 'TECHM.NS',
        "brsr_file": 'TECHM_BR_24-25.pdf',
        "headquarters": {'city': 'Pune', 'area': 'Shivajinagar'},
        "major_offices": [{'city': 'Pune', 'area': 'Talawade'}, {'city': 'Bangalore', 'area': 'Whitefield'}, {'city': 'Hyderabad', 'area': 'HITEC City'}, {'city': 'Chennai', 'area': 'Sholinganallur'}, {'city': 'Mumbai', 'area': 'Mahape'}, {'city': 'Gurugram', 'area': 'Sector 74'}, {'city': 'Chandigarh', 'area': 'IT Park'}],
    },
    "LTIM": {
        "full_name": 'LTIMindtree',
        "ticker": 'LTIM.NS',
        "brsr_file": 'LTIM_BR_24-25.pdf',
        "headquarters": {'city': 'Mumbai', 'area': 'Powai'},
        "major_offices": [],
    },
    "MPHASIS": {
        "full_name": 'Mphasis',
        "ticker": 'MPHASIS.NS',
        "brsr_file": 'MPHASIS_BR_24-25.pdf',
        "headquarters": {'city': 'Bangalore', 'area': 'Kadubeesanahalli'},
        "major_offices": [],
    },
    "PERSISTENT": {
        "full_name": 'Persistent Systems',
        "ticker": 'PERSISTENT.NS',
        "brsr_file": 'PERSISTENT_BR_24-25.pdf',
        "headquarters": {'city': 'Pune', 'area': 'Hinjewadi'},
        "major_offices": [],
    },
    "COFORGE": {
        "full_name": 'Coforge',
        "ticker": 'COFORGE.NS',
        "brsr_file": 'COFORGE_BR_24-25.pdf',
        "headquarters": {'city': 'Noida', 'area': 'Sector 62'},
        "major_offices": [],
    },
    "LTTS": {
        "full_name": 'L&T Technology Services',
        "ticker": 'LTTS.NS',
        "brsr_file": 'LTTS_BR_24-25.pdf',
        "headquarters": {'city': 'Mumbai', 'area': 'Powai'},
        "major_offices": [],
    },
    "TATAELXSI": {
        "full_name": 'Tata Elxsi',
        "ticker": 'TATAELXSI.NS',
        "brsr_file": 'TATAELXSI_BR_24-25.pdf',
        "headquarters": {'city': 'Bangalore', 'area': 'Electronics City'},
        "major_offices": [],
    },
    "OFSS": {
        "full_name": 'Oracle Financial Services Software',
        "ticker": 'OFSS.NS',
        "brsr_file": 'OFSS_BR_24-25.pdf',
        "headquarters": {'city': 'Mumbai', 'area': 'Goregaon East'},
        "major_offices": [],
    },
    "KPITTECH": {
        "full_name": 'KPIT Technologies',
        "ticker": 'KPITTECH.NS',
        "brsr_file": 'KPITTECH_BR_24-25.pdf',
        "headquarters": {'city': 'Pune', 'area': 'Hinjewadi'},
        "major_offices": [],
    },
    "CYIENT": {
        "full_name": 'Cyient',
        "ticker": 'CYIENT.NS',
        "brsr_file": 'CYIENT_BR_24-25.pdf',
        "headquarters": {'city': 'Hyderabad', 'area': 'Madhapur'},
        "major_offices": [],
    },
    "BSOFT": {
        "full_name": 'Birlasoft',
        "ticker": 'BSOFT.NS',
        "brsr_file": 'BSOFT_BR_24-25.pdf',
        "headquarters": {'city': 'Noida', 'area': 'Sector 62'},
        "major_offices": [],
    },
    "ZENSARTECH": {
        "full_name": 'Zensar Technologies',
        "ticker": 'ZENSARTECH.NS',
        "brsr_file": 'ZENSARTECH_BR_24-25.pdf',
        "headquarters": {'city': 'Pune', 'area': 'Kharadi'},
        "major_offices": [],
    },
    "TATATECH": {
        "full_name": 'Tata Technologies',
        "ticker": 'TATATECH.NS',
        "brsr_file": 'TATATECH_BR_24-25.pdf',
        "headquarters": {'city': 'Pune', 'area': 'Hinjewadi'},
        "major_offices": [],
    },
    "HAPPSTMNDS": {
        "full_name": 'Happiest Minds Technologies',
        "ticker": 'HAPPSTMNDS.NS',
        "brsr_file": 'HAPPSTMNDS_BR_24-25.pdf',
        "headquarters": {'city': 'Bangalore', 'area': 'Bengaluru'},
        "major_offices": [],
    },
    "SONATSOFTW": {
        "full_name": 'Sonata Software',
        "ticker": 'SONATSOFTW.NS',
        "brsr_file": 'SONATSOFTW_BR_24-25.pdf',
        "headquarters": {'city': 'Bangalore', 'area': 'Ulsoor'},
        "major_offices": [],
    },
    "HEXAWARE": {
        "full_name": 'Hexaware Technologies',
        "ticker": 'HEXAWARE.NS',
        "brsr_file": 'HEXAWARE_BR_24-25.pdf',
        "headquarters": {'city': 'Navi Mumbai', 'area': 'Ghansoli'},
        "major_offices": [],
    }
}


def _load_target_companies() -> dict:
    """Merge the target list with detailed metadata for configured companies."""
    target_file = BASE_DIR / "config" / "target_companies_50.csv"
    companies = dict(COMPANIES)

    with target_file.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            code = row["company_code"].strip()
            existing = companies.get(code, {})
            city = row["headquarters_city"].strip()
            companies[code] = {
                "full_name": row["company_name"].strip(),
                "ticker": row["ticker"].strip(),
                "brsr_file": f"{code}_BR_24-25.pdf",
                "headquarters": existing.get("headquarters", {"city": city, "area": city}),
                "major_offices": existing.get("major_offices", []),
            }

    if len(companies) != TARGET_COMPANY_COUNT:
        raise ValueError(
            f"Expected {TARGET_COMPANY_COUNT} target companies, found {len(companies)}"
        )
    return companies


COMPANIES = _load_target_companies()

# ============================================================
# ESG METRICS TO EXTRACT FROM BRSR
# ============================================================

ESG_METRICS = {

    # --------------------------------------------------------
    # ENVIRONMENTAL
    # --------------------------------------------------------

    "Environmental": [

        {
            "name": "Total Energy Consumption",
            "unit": "GWh",
            "description": "Total energy consumed across all operations",
            "typical_section": "Essential Indicators - Principle 6"
        },

        {
            "name": "Renewable Energy Percentage",
            "unit": "%",
            "description": "Percentage of energy from renewable sources",
            "typical_section": "Essential Indicators - Principle 6"
        },

        {
            "name": "Total Water Consumption",
            "unit": "KL",
            "description": "Total water withdrawn for operations",
            "typical_section": "Essential Indicators - Principle 6"
        },

        {
            "name": "Water Recycled Percentage",
            "unit": "%",
            "description": "Percentage of water recycled/reused",
            "typical_section": "Essential Indicators - Principle 6"
        },

        {
            "name": "Total Waste Generated",
            "unit": "MT",
            "description": "Total waste generated (hazardous + non-hazardous)",
            "typical_section": "Essential Indicators - Principle 6"
        },

        {
            "name": "Waste Recycled Percentage",
            "unit": "%",
            "description": "Percentage of waste recycled",
            "typical_section": "Essential Indicators - Principle 6"
        }
    ],


    # --------------------------------------------------------
    # SOCIAL
    # --------------------------------------------------------

    "Social": [

        {
            "name": "Total Employees",
            "unit": "Count",
            "description": "Total permanent employees",
            "typical_section": "Essential Indicators - Principle 3"
        },

        {
            "name": "Female Employee Percentage",
            "unit": "%",
            "description": "Percentage of female employees",
            "typical_section": "Essential Indicators - Principle 3"
        },

        {
            "name": "Employee Turnover Rate",
            "unit": "%",
            "description": "Percentage of employees who left",
            "typical_section": "Essential Indicators - Principle 3"
        },

        {
            "name": "Training Hours per Employee",
            "unit": "Hours",
            "description": "Average training hours per employee",
            "typical_section": "Essential Indicators - Principle 3"
        },

        {
            "name": "Health and Safety Incidents",
            "unit": "Count",
            "description": "Number of work-related injuries/fatalities",
            "typical_section": "Essential Indicators - Principle 3"
        },

        {
            "name": "CSR Expenditure",
            "unit": "Crores INR",
            "description": "Corporate Social Responsibility spending",
            "typical_section": "Essential Indicators - Principle 8"
        }
    ],


    # --------------------------------------------------------
    # GOVERNANCE
    # --------------------------------------------------------

    "Governance": [

        {
            "name": "Board Size",
            "unit": "Count",
            "description": "Total number of board directors",
            "typical_section": "Section A - Leadership"
        },

        {
            "name": "Independent Directors Percentage",
            "unit": "%",
            "description": "Percentage of independent directors",
            "typical_section": "Section A - Leadership"
        },

        {
            "name": "Female Directors Percentage",
            "unit": "%",
            "description": "Percentage of female board members",
            "typical_section": "Section A - Leadership"
        },

        {
            "name": "Board Meeting Frequency",
            "unit": "Count",
            "description": "Number of board meetings per year",
            "typical_section": "Section A - Leadership"
        },

        {
            "name": "Audit Committee Size",
            "unit": "Count",
            "description": "Number of audit committee members",
            "typical_section": "Section A - Leadership"
        },

        {
            "name": "Ethics Policy Violations",
            "unit": "Count",
            "description": "Number of reported ethics violations",
            "typical_section": "Essential Indicators - Principle 1"
        }
    ]
}


# ============================================================
# OUTPUT FILE NAMES
# ============================================================

OUTPUT_FILES = {

    "brsr_metrics": "brsr_extracted_metrics.csv",

    "environmental_risk":
        "company_location_environmental_risk.csv",

    "news_sentiment":
        "esg_news_sentiment.csv",

    "news_rejected":
        "esg_news_rejected_articles.csv",

    "cross_validation":
        "cross_validation_report.csv",

    "data_quality":
        "data_quality_report.csv",

    "external_benchmark":
        "external_benchmark_report.csv",

    "run_metadata":
        "run_metadata.json",

    "stock_correlation":
        "stock_esg_correlation.csv",

    "greenwashing":
        "greenwashing_detection.csv",

    "master_scores":
        "esg_master_scores.csv",

    "explanations":
        "multi_agent_explanations.csv"
}


# ============================================================
# ESG NEWS RELEVANCE FILTERING KEYWORDS
# Used by Agent 3
# ============================================================

ESG_INCLUDE_KEYWORDS = [

    "emission",
    "emissions",
    "carbon",
    "pollution",
    "air quality",
    "aqi",
    "waste",
    "water",
    "renewable",
    "sustainability",
    "sustainable",
    "climate",
    "environment",
    "esg",
    "green energy",
    "net zero",
    "decarbonization",
    "labor",
    "safety",
    "injury",
    "employee wellbeing",
    "diversity",
    "inclusion",
    "governance",
    "compliance",
    "ethics",
    "penalty",
    "violation",
    "csr"
]


ESG_EXCLUDE_KEYWORDS = [

    "share price",
    "stock price",
    "target price",
    "buy call",
    "sell call",
    "brokerage",
    "intraday",
    "technical chart",
    "candlestick",
    "resistance",
    "support level",
    "q1 results",
    "q2 results",
    "q3 results",
    "q4 results",
    "earnings beat",
    "trading volume",
    "nifty",
    "sensex"
]


# ============================================================
# DATA FILE PATHS
# ============================================================
#
# These paths are retained from the V1 implementation.
# We are NOT replacing the V1 raw datasets.
# ============================================================

DATA_PATHS = {

    "air_quality_city_day":
        RAW_DATA_DIR
        / "Air Quality Data in India (2015 - 2024)"
        / "city_day.csv",

    "air_quality_realtime":
        RAW_DATA_DIR
        / "Real-Time Air Quality Index (AQI) India 2023–2025"
        / "AQI.csv",

    "stock_nifty_companies":
        RAW_DATA_DIR
        / "Stock Market Sensex & Nifty All-time Dataset"
        / "NIFTY_50_COMPANIES.csv",

    "esg_news":
        RAW_DATA_DIR
        / "Zenodo ESG News Dataset_Indian Stock Market News Dataset.csv"
}


# ============================================================
# ESG SCORING WEIGHTS
# ============================================================

SCORING_WEIGHTS = {
    "Environmental": 0.33,
    "Social": 0.33,
    "Governance": 0.34
}


# ============================================================
# RISK LEVEL THRESHOLDS
# ============================================================

RISK_THRESHOLDS = {
    "Low": 8.0,
    "Low-Medium": 7.0,
    "Medium": 6.0,
    "Medium-High": 5.0,
    "High": 0.0
}


# ============================================================
# RISK LEVEL FUNCTION
# ============================================================

def get_risk_level(score):
    """Convert ESG score to risk level."""

    if score >= RISK_THRESHOLDS["Low"]:
        return "Low"

    elif score >= RISK_THRESHOLDS["Low-Medium"]:
        return "Low-Medium"

    elif score >= RISK_THRESHOLDS["Medium"]:
        return "Medium"

    elif score >= RISK_THRESHOLDS["Medium-High"]:
        return "Medium-High"

    else:
        return "High"


# ============================================================
# DIRECT EXECUTION TEST
# ============================================================

if __name__ == "__main__":

    print("ESG Multi-Agent System Configuration")
    print(f"Base Directory: {BASE_DIR}")
    print(f"Companies: {len(COMPANIES)}")

    total_metrics = (
        len(ESG_METRICS["Environmental"])
        + len(ESG_METRICS["Social"])
        + len(ESG_METRICS["Governance"])
    )

    print(f"Total ESG Metrics: {total_metrics}")

    print("\nConfigured Companies:")

    for code, details in COMPANIES.items():
        print(
            f"  {code:<12} "
            f"{details['full_name']:<45} "
            f"{details['ticker']}"
        )