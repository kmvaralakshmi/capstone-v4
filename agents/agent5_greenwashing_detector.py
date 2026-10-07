"""
Agent 5: Greenwashing Detector
Detects inconsistencies between ESG claims and actual performance

This agent:
1. Loads BRSR metrics (claimed performance)
2. Loads environmental risk data (actual performance)
3. Compares claimed vs actual environmental performance
4. Detects significant discrepancies (greenwashing indicators)
5. Generates greenwashing_detection.csv

Author: Multi-Agent ESG System
Date: 2026-02-12
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.config import COMPANIES, PROCESSED_DATA_DIR, OUTPUT_FILES


class GreenwashingDetector:
    """Agent for detecting greenwashing in ESG reporting"""
    
    def __init__(self):
        self.companies = COMPANIES
        self.output_dir = PROCESSED_DATA_DIR
        self.detection_results = []
        
    def load_brsr_metrics(self) -> pd.DataFrame:
        """Load BRSR extracted metrics"""
        try:
            brsr_path = self.output_dir / OUTPUT_FILES['brsr_metrics']
            df_brsr = pd.read_csv(brsr_path)
            return df_brsr
            
        except Exception as e:
            print(f"Error loading BRSR metrics: {e}")
            return pd.DataFrame()
            
    def load_environmental_risk(self) -> pd.DataFrame:
        """Load environmental risk data"""
        try:
            env_path = self.output_dir / OUTPUT_FILES['environmental_risk']
            df_env = pd.read_csv(env_path)
            return df_env
            
        except Exception as e:
            print(f"Error loading environmental risk data: {e}")
            return pd.DataFrame()
            
    def load_news_sentiment(self) -> pd.DataFrame:
        """Load news sentiment data"""
        try:
            sentiment_path = self.output_dir / OUTPUT_FILES['news_sentiment']
            df_sentiment = pd.read_csv(sentiment_path)
            return df_sentiment
        except:
            return pd.DataFrame()
            
    def detect_metric_greenwashing(self, company_code: str, metric_name: str,
                                  metric_value: float, metric_category: str,
                                  df_env: pd.DataFrame, df_sentiment: pd.DataFrame) -> Dict:
        """Detect greenwashing for a specific metric"""
        
        # Get company's actual environmental performance
        company_env = df_env[df_env['Company_Code'] == company_code]
        actual_env_score = company_env['Environmental_Risk_Score'].mean() if not company_env.empty else None
        
        # Initialize detection result
        claim_verified = 'Unknown'
        discrepancy_detected = False
        discrepancy_level = 'None'
        verification_details = 'Metric reported'
        trust_score = 5.0  # Neutral default
        
        # Verify specific metrics against actual data
        if metric_category == 'Environmental' and actual_env_score:
            if 'Renewable Energy' in metric_name:
                # High renewable claims should correlate with better environmental scores
                if metric_value > 70:
                    if actual_env_score >= 7:
                        claim_verified = 'Verified'
                        verification_details = f"High renewable claim ({metric_value}%) supported by good env score ({actual_env_score:.1f}/10)"
                        trust_score = 9.0
                    elif actual_env_score < 5:
                        claim_verified = 'Suspicious'
                        discrepancy_detected = True
                        discrepancy_level = 'High'
                        verification_details = f"Claims {metric_value}% renewable but low env score ({actual_env_score:.1f}/10)"
                        trust_score = 2.0
                    else:
                        claim_verified = 'Partially Verified'
                        verification_details = f"Renewable claim {metric_value}% with moderate env score ({actual_env_score:.1f}/10)"
                        trust_score = 6.0
                elif metric_value > 40:
                    if actual_env_score >= 5:
                        claim_verified = 'Verified'
                        verification_details = f"Moderate renewable claim ({metric_value}%) matches env score ({actual_env_score:.1f}/10)"
                        trust_score = 7.0
                    else:
                        claim_verified = 'Suspicious'
                        discrepancy_detected = True
                        discrepancy_level = 'Medium'
                        verification_details = f"Claims {metric_value}% renewable but poor env score ({actual_env_score:.1f}/10)"
                        trust_score = 4.0
                else:
                    claim_verified = 'Verified'
                    verification_details = f"Low renewable claim ({metric_value}%) consistent with env score ({actual_env_score:.1f}/10)"
                    trust_score = 6.0
                    
            elif 'GHG' in metric_name or 'Emission' in metric_name:
                # Lower emissions should correlate with better environmental scores
                if metric_value < 50000:  # Low emissions
                    if actual_env_score >= 6:
                        claim_verified = 'Verified'
                        verification_details = f"Low emissions ({metric_value}) supported by good env score ({actual_env_score:.1f}/10)"
                        trust_score = 8.0
                    else:
                        claim_verified = 'Suspicious'
                        discrepancy_detected = True
                        discrepancy_level = 'Medium'
                        verification_details = f"Claims low emissions ({metric_value}) but poor env score ({actual_env_score:.1f}/10)"
                        trust_score = 4.0
                else:
                    claim_verified = 'Reported'
                    verification_details = f"High emissions ({metric_value}) reported"
                    trust_score = 5.0
            else:
                claim_verified = 'Reported'
                verification_details = f"Environmental metric: {metric_value}"
                trust_score = 6.0
        else:
            # Non-environmental metrics or no actual data to compare
            claim_verified = 'Reported'
            verification_details = f"{metric_category} metric: {metric_value}"
            trust_score = 6.0
        
        # Check news sentiment for additional validation
        if not df_sentiment.empty:
            company_sent = df_sentiment[df_sentiment['Company_Code'] == company_code]
            if not company_sent.empty:
                negative_ratio = (company_sent['Sentiment_Class'] == 'Negative').sum() / len(company_sent)
                if negative_ratio > 0.3 and discrepancy_detected:
                    trust_score -= 1  # Reduce trust if negative news + discrepancy
        
        return {
            'claim_verified': claim_verified,
            'discrepancy_detected': discrepancy_detected,
            'discrepancy_level': discrepancy_level,
            'verification_details': verification_details,
            'trust_score': max(0, min(10, trust_score)),
            'actual_env_score': actual_env_score
        }
        
    def calculate_metric_risk_score(self, detection_result: Dict) -> float:
        """Calculate risk score for a specific metric"""
        
        risk_score = 0
        
        if detection_result['discrepancy_level'] == 'High':
            risk_score = 8
        elif detection_result['discrepancy_level'] == 'Medium':
            risk_score = 5
        elif detection_result['discrepancy_level'] == 'Low':
            risk_score = 3
        else:
            risk_score = 1
        
        return risk_score
        
    def process_all_companies(self, df_brsr: pd.DataFrame,
                             df_env: pd.DataFrame,
                             df_sentiment: pd.DataFrame) -> pd.DataFrame:
        """Process all companies and metrics for greenwashing detection"""
        company_names = [info['full_name'] for info in self.companies.values()]
        print(f"Processing: {', '.join(company_names)} (checking all metrics)...")
        
        # Iterate through each BRSR metric
        for idx, row in df_brsr.iterrows():
            company_code = row['Company_Code']
            company_name = row['Company_Name']
            metric_name = row['Metric_Name']
            metric_category = row['Metric_Category']
            metric_value = row['Metric_Value']
            metric_unit = row.get('Unit', '')
            
            # Check if metric has a value
            if pd.notna(metric_value):
                # Detect greenwashing for this specific metric
                detection = self.detect_metric_greenwashing(
                    company_code, metric_name, float(metric_value),
                    metric_category, df_env, df_sentiment
                )
                
                # Calculate risk score
                risk_score = self.calculate_metric_risk_score(detection)
                
                # Store results
                self.detection_results.append({
                    'Company_Code': company_code,
                    'Company_Name': company_name,
                    'Metric_Category': metric_category,
                    'Metric_Name': metric_name,
                    'Claimed_Value': metric_value,
                    'Metric_Unit': metric_unit,
                    'Claim_Verified': detection['claim_verified'],
                    'Verification_Details': detection['verification_details'],
                    'Discrepancy_Detected': detection['discrepancy_detected'],
                    'Discrepancy_Level': detection['discrepancy_level'],
                    'Trust_Score': detection['trust_score'],
                    'Risk_Score': risk_score,
                    'Actual_Environmental_Score': detection['actual_env_score'],
                    'Analysis_Date': datetime.now().strftime('%Y-%m-%d')
                })
            else:
                # Missing data - transparency issue
                self.detection_results.append({
                    'Company_Code': company_code,
                    'Company_Name': company_name,
                    'Metric_Category': metric_category,
                    'Metric_Name': metric_name,
                    'Claimed_Value': None,
                    'Metric_Unit': row.get('Unit', ''),
                    'Claim_Verified': 'Not Disclosed',
                    'Verification_Details': 'Metric not reported - transparency concern',
                    'Discrepancy_Detected': False,
                    'Discrepancy_Level': 'None',
                    'Trust_Score': 3.0,  # Low trust for missing data
                    'Risk_Score': 2,
                    'Actual_Environmental_Score': None,
                    'Analysis_Date': datetime.now().strftime('%Y-%m-%d')
                })
        
        df = pd.DataFrame(self.detection_results)
        
        return df
        
    def save_to_csv(self, df: pd.DataFrame) -> Path:
        """Save greenwashing detection results to CSV"""
        output_path = self.output_dir / OUTPUT_FILES['greenwashing']
        df.to_csv(output_path, index=False)
        
        return output_path
        
    def display_summary(self, df: pd.DataFrame):
        """Display summary statistics"""
        pass


def main():
    """Main execution function"""
    print("\nAGENT 5: GREENWASHING DETECTOR")
    
    # Initialize agent
    agent = GreenwashingDetector()
    
    # Load required data
    df_brsr = agent.load_brsr_metrics()
    df_env = agent.load_environmental_risk()
    df_sentiment = agent.load_news_sentiment()
    
    if df_brsr.empty:
        print("\nError: BRSR metrics not available. Run Agent 1 first.\n")
        return
    
    if df_env.empty:
        print("\nError: Environmental risk data not available. Run Agent 2 first.\n")
        return
    
    # Process all companies
    df_greenwashing = agent.process_all_companies(df_brsr, df_env, df_sentiment)
    
    # Save results
    output_path = agent.save_to_csv(df_greenwashing)
    
    # Display summary
    print(f"\nFile created: {output_path}")
    print(f"Rows: {len(df_greenwashing)} | Columns: {len(df_greenwashing.columns)}\n")


if __name__ == "__main__":
    main()
