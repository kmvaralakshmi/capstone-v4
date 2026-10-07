"""
Agent 4: Stock Correlation Analyzer
Analyzes correlation between ESG metrics and stock performance

This agent:
1. Loads stock market data (Nifty 50)
2. Matches companies to stock prices
3. Calculates stock performance metrics
4. Creates hypothetical correlation with ESG scores
5. Generates stock_esg_correlation.csv

Author: Multi-Agent ESG System
Date: 2026-02-12
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.config import COMPANIES, DATA_PATHS, PROCESSED_DATA_DIR, OUTPUT_FILES


class StockCorrelationAnalyzer:
    """Agent for analyzing stock performance and ESG correlation"""
    
    def __init__(self):
        self.companies = COMPANIES
        self.output_dir = PROCESSED_DATA_DIR
        self.correlation_data = []
        
    def load_stock_data(self) -> tuple:
        """Load stock market data"""
        try:
            # Load Nifty 50 companies data with historical prices
            companies_path = DATA_PATHS['stock_nifty_companies']
            df_stocks = pd.read_csv(companies_path)
            
            # Convert Date to datetime
            df_stocks['Date'] = pd.to_datetime(df_stocks['Date'])
            
            # Filter for last 12 months only
            latest_date = df_stocks['Date'].max()
            twelve_months_ago = latest_date - pd.DateOffset(months=12)
            df_stocks = df_stocks[df_stocks['Date'] >= twelve_months_ago]
            
            return df_stocks
            
        except Exception as e:
            print(f"Error loading stock data: {e}")
            return pd.DataFrame()
            
    def match_company_ticker(self, company_code: str) -> str:
        """Match company code to stock ticker"""
        # Our companies use .NS suffix (NSE - National Stock Exchange)
        return self.companies[company_code]['ticker']
        
    def calculate_monthly_metrics(self, df_month: pd.DataFrame) -> Dict:
        """Calculate stock performance metrics for a month"""
        
        if df_month.empty:
            return {
                'current_price': None,
                'month_high': None,
                'month_low': None,
                'monthly_return': None,
                'volatility': None,
                'performance_score': 7.0
            }
        
        # Calculate monthly metrics
        company_stocks = df_month
        
        # Calculate metrics
        if 'Close' in company_stocks.columns and len(company_stocks) > 0:
            current_price = company_stocks['Close'].iloc[-1]
            month_high = company_stocks['Close'].max()
            month_low = company_stocks['Close'].min()
            
            # Calculate monthly return
            if len(company_stocks) > 1:
                first_price = company_stocks['Close'].iloc[0]
                monthly_return = ((current_price - first_price) / first_price) * 100
            else:
                monthly_return = 0
            
            # Calculate volatility
            if len(company_stocks) > 1:
                returns = company_stocks['Close'].pct_change()
                volatility = returns.std() * np.sqrt(21) * 100  # Monthly annualized
            else:
                volatility = 0
            
            # Performance score (0-10, based on monthly returns)
            if monthly_return >= 10:
                performance_score = 10.0
            elif monthly_return >= 5:
                performance_score = 9.0
            elif monthly_return >= 2:
                performance_score = 8.0
            elif monthly_return >= 0:
                performance_score = 7.0
            elif monthly_return >= -5:
                performance_score = 6.0
            elif monthly_return >= -10:
                performance_score = 4.0
            else:
                performance_score = 2.0
                
            return {
                'current_price': current_price,
                'month_high': month_high,
                'month_low': month_low,
                'monthly_return': monthly_return,
                'volatility': volatility,
                'performance_score': performance_score
            }
        
        return {
            'current_price': None,
            'month_high': None,
            'month_low': None,
            'monthly_return': None,
            'volatility': None,
            'performance_score': 7.0
        }
        
    def simulate_esg_correlation(self, performance_score: float) -> Dict:
        """Simulate ESG-Stock correlation (for demonstration)"""
        
        # In real implementation, this would calculate actual correlation
        # between ESG scores and stock performance over time
        # For now, we simulate a positive correlation
        
        # Hypothesis: Better ESG -> Better stock performance (long-term)
        # Correlation coefficient: 0.6 (moderate positive)
        
        correlation_coefficient = 0.65
        
        # Simulated ESG influence score
        esg_influence = performance_score * correlation_coefficient + np.random.normal(0, 0.5)
        esg_influence = max(0, min(10, esg_influence))  # Clip to 0-10
        
        return {
            'esg_stock_correlation': correlation_coefficient,
            'esg_influence_score': esg_influence
        }
        
    def process_all_companies(self, df_stocks: pd.DataFrame) -> pd.DataFrame:
        """Process all companies with monthly data"""
        company_names = [info['full_name'] for info in self.companies.values()]
        print(f"Processing: {', '.join(company_names)} (monthly data)...")
        
        for company_code, company_info in self.companies.items():
            ticker = self.match_company_ticker(company_code)
            
            # Filter stock data for this company
            company_stocks = df_stocks[df_stocks['Ticker'] == ticker]
            
            if company_stocks.empty:
                continue
            
            # Group by month
            company_stocks['YearMonth'] = company_stocks['Date'].dt.to_period('M')
            
            # Process each month
            for period, month_data in company_stocks.groupby('YearMonth'):
                # Calculate stock metrics for this month
                stock_metrics = self.calculate_monthly_metrics(month_data)
                
                # Simulate ESG correlation
                correlation_metrics = self.simulate_esg_correlation(
                    stock_metrics['performance_score']
                )
                
                # Store results
                self.correlation_data.append({
                    'Company_Code': company_code,
                    'Company_Name': company_info['full_name'],
                    'Stock_Ticker': ticker,
                    'Month': str(period),
                    'Current_Price': stock_metrics['current_price'],
                    'Month_High': stock_metrics['month_high'],
                    'Month_Low': stock_metrics['month_low'],
                    'Monthly_Return_Pct': stock_metrics['monthly_return'],
                    'Volatility_Pct': stock_metrics['volatility'],
                    'Stock_Performance_Score': stock_metrics['performance_score'],
                    'ESG_Stock_Correlation': correlation_metrics['esg_stock_correlation'],
                    'ESG_Influence_Score': correlation_metrics['esg_influence_score']
                })
        
        df = pd.DataFrame(self.correlation_data)
        
        return df
        
    def save_to_csv(self, df: pd.DataFrame) -> Path:
        """Save correlation data to CSV"""
        output_path = self.output_dir / OUTPUT_FILES['stock_correlation']
        df.to_csv(output_path, index=False)

        return output_path
        
    def display_summary(self, df: pd.DataFrame):
        """Display summary statistics"""
        pass


def main():
    """Main execution function"""
    print("\nAGENT 4: STOCK CORRELATION ANALYZER")
    
    # Initialize agent
    agent = StockCorrelationAnalyzer()
    
    # Load stock data
    df_stocks = agent.load_stock_data()
    
    if df_stocks.empty:
        print("\nError: No stock data available.\n")
        return
    
    # Process all companies
    df_correlation = agent.process_all_companies(df_stocks)
    
    # Save results
    output_path = agent.save_to_csv(df_correlation)
    
    # Display summary
    print(f"\nFile created: {output_path}")
    print(f"Rows: {len(df_correlation)} | Columns: {len(df_correlation.columns)}\n")


if __name__ == "__main__":
    main()
