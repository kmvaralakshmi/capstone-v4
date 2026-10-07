"""
PHASE 3 - BRSR SOURCE MANIFEST
==============================

Target:
    FY 2024-25

Company set:
    50 target companies

Source priority:
    1. NSE
    2. BSE
    3. Company Official Website

Rules:
    - One company + one financial year = one active PDF.
    - Never replace a valid canonical PDF.
    - Failed sources move to the next source.
    - Mphasis has an official standalone BRSR fallback.
    - LTIMindtree has its verified NSE Annual Report fallback.
    - Hexaware remains in the 50-company target set.
"""

import csv
from pathlib import Path

BRSR_MANIFEST = {

    # ========================================================
    # 1. TCS
    # ========================================================

    "TCS": {
        "company_name": "Tata Consultancy Services",
        "aliases": [
            "tata consultancy services",
            "tata consultancy services limited",
            "tcs"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": (
                    "https://nsearchives.nseindia.com/"
                    "corporate/"
                    "TCS_CORPCS_27052025233643_"
                    "BRSRSEint27052025_signed.pdf"
                )
            }
        ]
    },

    # ========================================================
    # 2. INFOSYS
    # ========================================================

    "INFY": {
        "company_name": "Infosys",
        "aliases": [
            "infosys",
            "infosys limited"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": (
                    "https://nsearchives.nseindia.com/"
                    "corporate/"
                    "Infosys_02062025172921_infosys-ar-2025.pdf"
                )
            }
        ]
    },

    # ========================================================
    # 3. WIPRO
    # ========================================================

    "WIPRO": {
        "company_name": "Wipro",
        "aliases": [
            "wipro",
            "wipro limited"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": None
            },
            {
                "priority": 2,
                "name": "BSE",
                "url": None
            },
            {
                "priority": 3,
                "name": "Wipro Official",
                "url": (
                    "https://www.wipro.com/content/dam/"
                    "nexus/en/investor/annual-reports/"
                    "2024-2025/"
                    "Integrated-annual-report-2024-25.pdf"
                )
            }
        ]
    },

    # ========================================================
    # 4. HCL TECHNOLOGIES
    # ========================================================

    "HCLTECH": {
        "company_name": "HCL Technologies",
        "aliases": [
            "hcl technologies",
            "hcl technologies limited",
            "hcltech"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": None
            }
        ]
    },

    # ========================================================
    # 5. TECH MAHINDRA
    # ========================================================

    "TECHM": {
        "company_name": "Tech Mahindra",
        "aliases": [
            "tech mahindra",
            "tech mahindra limited",
            "techm"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": (
                    "https://nsearchives.nseindia.com/"
                    "corporate/"
                    "Apekshakhemka_23062025233414_"
                    "StockExchangeIntimationBRSR_S.pdf"
                )
            }
        ]
    },

    # ========================================================
    # 6. LTIMINDTREE
    # ========================================================

    "LTIM": {
        "company_name": "LTIMindtree",
        "aliases": [
            "ltimindtree",
            "ltimindtree limited",
            "lti mindtree",
            "lti"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE BRSR",
                "url": None
            },
            {
                "priority": 2,
                "name": "NSE Annual Report",
                "url": (
                    "https://nsearchives.nseindia.com/"
                    "annual_reports/"
                    "AR_26433_LTIM_2024_2025_A_"
                    "07052025121730.pdf"
                )
            },
            {
                "priority": 3,
                "name": "BSE",
                "url": None
            },
            {
                "priority": 4,
                "name": "LTIMindtree Official",
                "url": None
            }
        ]
    },

    # ========================================================
    # 7. MPHASIS
    # ========================================================

    "MPHASIS": {
        "company_name": "Mphasis",
        "aliases": [
            "mphasis",
            "mphasis limited",
            "mphasis ltd"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE Annual Report",
                "url": (
                    "https://nsearchives.nseindia.com/"
                    "annual_reports/"
                    "AR_26670_MPHASIS_2024_2025_A_"
                    "01072025190655.pdf"
                )
            },
            {
                "priority": 2,
                "name": "Mphasis Official BRSR",
                "url": (
                    "https://www.mphasis.com/"
                    "content/dam/mphasis-com/global/en/"
                    "investors/annual-reports/2025/"
                    "business-responsibility-report-2025.pdf"
                )
            }
        ]
    },

    # ========================================================
    # 8. PERSISTENT SYSTEMS
    # ========================================================

    "PERSISTENT": {
        "company_name": "Persistent Systems",
        "aliases": [
            "persistent systems",
            "persistent systems limited",
            "persistent"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": (
                    "https://nsearchives.nseindia.com/"
                    "corporate/"
                    "PERSISTENTUSER1_23062025235235_"
                    "PSLBusinessResponsibilityandSustainability"
                    "Report2025signed.pdf"
                )
            }
        ]
    },

    # ========================================================
    # 9. COFORGE
    # ========================================================

    "COFORGE": {
        "company_name": "Coforge",
        "aliases": [
            "coforge",
            "coforge limited",
            "coforge ltd"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": None
            },
            {
                "priority": 2,
                "name": "BSE",
                "url": None
            },
            {
                "priority": 3,
                "name": "Coforge Official",
                "url": None
            }
        ]
    },

    # ========================================================
    # 10. LTTS
    # ========================================================

    "LTTS": {
        "company_name": "L&T Technology Services",
        "aliases": [
            "l&t technology services",
            "l&t technology services limited",
            "l&t technology",
            "ltts"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": None
            }
        ]
    },

    # ========================================================
    # 11. TATA ELXSI
    # ========================================================

    "TATAELXSI": {
        "company_name": "Tata Elxsi",
        "aliases": [
            "tata elxsi",
            "tata elxsi limited",
            "tataelxsi"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": None
            }
        ]
    },

    # ========================================================
    # 12. OFSS
    # ========================================================

    "OFSS": {
        "company_name": "Oracle Financial Services Software",
        "aliases": [
            "oracle financial services software",
            "oracle financial services",
            "ofss"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": None
            }
        ]
    },

    # ========================================================
    # 13. KPIT TECHNOLOGIES
    # ========================================================

    "KPITTECH": {
        "company_name": "KPIT Technologies",
        "aliases": [
            "kpit technologies",
            "kpit technologies limited",
            "kpit"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": None
            }
        ]
    },

    # ========================================================
    # 14. CYIENT
    # ========================================================

    "CYIENT": {
        "company_name": "Cyient",
        "aliases": [
            "cyient",
            "cyient limited"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": None
            }
        ]
    },

    # ========================================================
    # 15. BIRLASOFT
    # ========================================================

    "BSOFT": {
        "company_name": "Birlasoft",
        "aliases": [
            "birlasoft",
            "birlasoft limited",
            "birlasoft ltd"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": None
            }
        ]
    },

    # ========================================================
    # 16. ZENSAR TECHNOLOGIES
    # ========================================================

    "ZENSARTECH": {
        "company_name": "Zensar Technologies",
        "aliases": [
            "zensar technologies",
            "zensar technologies limited",
            "zensar"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": None
            }
        ]
    },

    # ========================================================
    # 17. TATA TECHNOLOGIES
    # ========================================================

    "TATATECH": {
        "company_name": "Tata Technologies",
        "aliases": [
            "tata technologies",
            "tata technologies limited"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": (
                    "https://nsearchives.nseindia.com/"
                    "corporate/"
                    "TTLNSE_28052025200521_"
                    "BRSR.pdf"
                )
            }
        ]
    },

    # ========================================================
    # 18. HAPPIEST MINDS
    # ========================================================

    "HAPPSTMNDS": {
        "company_name": "Happiest Minds Technologies",
        "aliases": [
            "happiest minds",
            "happiest minds technologies",
            "happiest minds technologies limited"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": None
            },
            {
                "priority": 2,
                "name": "BSE",
                "url": None
            },
            {
                "priority": 3,
                "name": "Happiest Minds Official",
                "url": (
                    "https://www.happiestminds.com/"
                    "investors/Annual%20Report/"
                    "2024-2025-Q4/"
                    "HappiestMindsBRSR04072025.pdf"
                )
            }
        ]
    },

    # ========================================================
    # 19. SONATA SOFTWARE
    # ========================================================

    "SONATSOFTW": {
        "company_name": "Sonata Software",
        "aliases": [
            "sonata software",
            "sonata software limited"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": (
                    "https://nsearchives.nseindia.com/"
                    "corporate/"
                    "SONATSOFTW_04072025194537_"
                    "Sefilingbrsr.pdf"
                )
            }
        ]
    },

    # ========================================================
    # 20. HEXAWARE
    # ========================================================

    "HEXAWARE": {
        "company_name": "Hexaware Technologies",
        "aliases": [
            "hexaware",
            "hexaware technologies",
            "hexaware technologies limited"
        ],
        "financial_year": "2024-25",
        "sources": [
            {
                "priority": 1,
                "name": "NSE",
                "url": None
            },
            {
                "priority": 2,
                "name": "BSE",
                "url": None
            },
            {
                "priority": 3,
                "name": "Hexaware Official",
                "url": None
            }
        ]
    },
}


_target_file = Path(__file__).resolve().parent.parent / "config" / "target_companies_50.csv"
with _target_file.open("r", encoding="utf-8-sig", newline="") as file:
    for row in csv.DictReader(file):
        code = row["company_code"].strip()
        if code in BRSR_MANIFEST:
            continue
        company_name = row["company_name"].strip()
        BRSR_MANIFEST[code] = {
            "company_name": company_name,
            "aliases": [
                company_name.lower(),
                row["search_alias"].strip().lower(),
                code.lower(),
            ],
            "financial_year": "2024-25",
            "ticker": row["ticker"].strip(),
            "sources": [
                {
                    "priority": 1,
                    "name": "NSE BRSR",
                    "url": "AUTO",
                }
            ],
        }

if len(BRSR_MANIFEST) != 50:
    raise ValueError(f"Expected 50 BRSR manifest entries, found {len(BRSR_MANIFEST)}")