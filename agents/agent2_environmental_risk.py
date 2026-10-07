"""
Agent 2: Environmental Risk Validator
Maps company locations to environmental data (AQI) to assess location-based risk

This agent:
1. Reads company locations from config
2. Matches locations to Air Quality data
3. Calculates average AQI for each city
4. Assigns environmental risk scores to companies
5. Creates company_location_environmental_risk.csv

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

from utils.config import COMPANIES, DATA_PATHS, PROCESSED_DATA_DIR, OUTPUT_FILES


class EnvironmentalRiskValidator:
    """Agent for validating environmental risk based on company locations"""
    
    def __init__(self):
        self.companies = COMPANIES
        self.output_dir = PROCESSED_DATA_DIR
        self.risk_data = []
        
    def load_air_quality_data(self) -> pd.DataFrame:
        """Load and combine air quality datasets"""
        
        # Load city-level historical data (2015-2024)
        try:
            historical_path = DATA_PATHS['air_quality_city_day']
            df_historical = pd.read_csv(historical_path)
        except Exception as e:
            df_historical = pd.DataFrame()
            
        # Load real-time AQI data (2023-2025)
        try:
            realtime_path = DATA_PATHS['air_quality_realtime']
            df_realtime = pd.read_csv(realtime_path)
        except Exception as e:
            df_realtime = pd.DataFrame()
            
        return df_historical, df_realtime
        
    def calculate_city_aqi_score(self, df_historical: pd.DataFrame, 
                                  df_realtime: pd.DataFrame, 
                                  city: str) -> Dict:
        """Calculate average AQI and risk score for a city"""
        
        # Try to find city in historical data
        city_data_hist = df_historical[
            df_historical['City'].str.contains(city, case=False, na=False)
        ]
        
        # Try to find city in realtime data
        city_data_rt = df_realtime[
            df_realtime['city'].str.contains(city, case=False, na=False)
        ] if 'city' in df_realtime.columns else pd.DataFrame()
        
        result = {
            'city': city,
            'historical_records': len(city_data_hist),
            'realtime_records': len(city_data_rt),
            'avg_aqi': None,
            'max_aqi': None,
            'min_aqi': None,
            'risk_score': None,
            'risk_level': None
        }
        
        # Calculate from historical data
        if not city_data_hist.empty and 'AQI' in city_data_hist.columns:
            result['avg_aqi'] = city_data_hist['AQI'].mean()
            result['max_aqi'] = city_data_hist['AQI'].max()
            result['min_aqi'] = city_data_hist['AQI'].min()
        
        # If no historical data, try realtime
        elif not city_data_rt.empty and 'AQI' in city_data_rt.columns:
            result['avg_aqi'] = city_data_rt['AQI'].mean()
            result['max_aqi'] = city_data_rt['AQI'].max()
            result['min_aqi'] = city_data_rt['AQI'].min()
        
        # Calculate risk score (0-10, higher is better)
        if result['avg_aqi'] is not None:
            # AQI ranges: 0-50 Good, 51-100 Moderate, 101-200 Poor, 201-300 Very Poor, 301+ Severe
            # Convert to risk score (inverted: low AQI = high score)
            if result['avg_aqi'] <= 50:
                result['risk_score'] = 10.0
                result['risk_level'] = 'Very Low'
            elif result['avg_aqi'] <= 100:
                result['risk_score'] = 8.0
                result['risk_level'] = 'Low'
            elif result['avg_aqi'] <= 150:
                result['risk_score'] = 6.0
                result['risk_level'] = 'Medium'
            elif result['avg_aqi'] <= 200:
                result['risk_score'] = 4.0
                result['risk_level'] = 'High'
            elif result['avg_aqi'] <= 300:
                result['risk_score'] = 2.0
                result['risk_level'] = 'Very High'
            else:
                result['risk_score'] = 1.0
                result['risk_level'] = 'Severe'
        
        return result
        
    def process_all_companies(self, df_historical: pd.DataFrame, 
                             df_realtime: pd.DataFrame) -> pd.DataFrame:
        """Process all companies and calculate environmental risk"""
        
        for company_code, company_info in self.companies.items():
            print(f"Processing: {company_info['full_name']}...")
            
            # Process headquarters
            hq_info = company_info['headquarters']
            hq_city = hq_info['city']
            hq_area = hq_info['area']
            
            hq_risk = self.calculate_city_aqi_score(
                df_historical, df_realtime, hq_city
            )
            
            self.risk_data.append({
                'Company_Code': company_code,
                'Company_Name': company_info['full_name'],
                'Location_Type': 'Headquarters',
                'City': hq_city,
                'Area': hq_area,
                'Avg_AQI': hq_risk['avg_aqi'],
                'Max_AQI': hq_risk['max_aqi'],
                'Min_AQI': hq_risk['min_aqi'],
                'Environmental_Risk_Score': hq_risk['risk_score'],
                'Risk_Level': hq_risk['risk_level'],
                'Data_Records': hq_risk['historical_records'] + hq_risk['realtime_records'],
                'Analysis_Date': datetime.now().strftime('%Y-%m-%d')
            })
            
            # Process major offices
            office_risks = []
            for office in company_info['major_offices']:
                office_city = office['city']
                office_area = office['area']
                
                office_risk = self.calculate_city_aqi_score(
                    df_historical, df_realtime, office_city
                )
                office_risks.append(office_risk['risk_score'])
                
                self.risk_data.append({
                    'Company_Code': company_code,
                    'Company_Name': company_info['full_name'],
                    'Location_Type': 'Major Office',
                    'City': office_city,
                    'Area': office_area,
                    'Avg_AQI': office_risk['avg_aqi'],
                    'Max_AQI': office_risk['max_aqi'],
                    'Min_AQI': office_risk['min_aqi'],
                    'Environmental_Risk_Score': office_risk['risk_score'],
                    'Risk_Level': office_risk['risk_level'],
                    'Data_Records': office_risk['historical_records'] + office_risk['realtime_records'],
                    'Analysis_Date': datetime.now().strftime('%Y-%m-%d')
                })
            
            # Calculate overall company score (average of all locations)
            all_scores = [hq_risk['risk_score']] + [r for r in office_risks if r is not None]
            valid_scores = [s for s in all_scores if s is not None]
        
        df = pd.DataFrame(self.risk_data)
        return df
        
    def save_to_csv(self, df: pd.DataFrame) -> Path:
        """Save environmental risk data to CSV"""
        output_path = self.output_dir / OUTPUT_FILES['environmental_risk']
        df.to_csv(output_path, index=False)
        return output_path
        
    def display_summary(self, df: pd.DataFrame):
        """Display summary statistics"""
        print("\n" + "="*70)
        print("ENVIRONMENTAL RISK SUMMARY")
        print("="*70)
        
        print("\nBy Company (Overall Average):")
        company_summary = df.groupby('Company_Name')['Environmental_Risk_Score'].mean()
        for company, score in company_summary.items():
            print(f"  • {company}: {score:.2f}/10")
            
        print("\nWorst Air Quality Cities (Lowest Scores):")
        worst_cities = df.nsmallest(5, 'Environmental_Risk_Score')[
            ['City', 'Avg_AQI', 'Environmental_Risk_Score', 'Risk_Level']
        ]
        for _, row in worst_cities.iterrows():
            print(f"  • {row['City']}: AQI {row['Avg_AQI']:.1f} (Score: {row['Environmental_Risk_Score']}/10)")
            
        print("\nBest Air Quality Cities (Highest Scores):")
        best_cities = df.nlargest(5, 'Environmental_Risk_Score')[
            ['City', 'Avg_AQI', 'Environmental_Risk_Score', 'Risk_Level']
        ]
        for _, row in best_cities.iterrows():
            print(f"  • {row['City']}: AQI {row['Avg_AQI']:.1f} (Score: {row['Environmental_Risk_Score']}/10)")


def main():
    """Main execution function"""
    print("\nAGENT 2: ENVIRONMENTAL RISK VALIDATOR")
    
    # Initialize agent
    agent = EnvironmentalRiskValidator()
    
    # Load air quality data
    df_historical, df_realtime = agent.load_air_quality_data()
    
    if df_historical.empty and df_realtime.empty:
        print("\nError: No air quality data available.\n")
        return
    
    # Process all companies
    df_risk = agent.process_all_companies(df_historical, df_realtime)
    
    # Save results
    output_path = agent.save_to_csv(df_risk)
    
    # Display summary
    print(f"\nFile created: {output_path}")
    print(f"Rows: {len(df_risk)} | Columns: {len(df_risk.columns)}\n")


if __name__ == "__main__":
    main()
