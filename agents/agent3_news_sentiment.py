"""
Agent 3: News Sentiment Analyzer
Analyzes ESG-related news sentiment for each company

This agent:
1. Loads ESG news dataset
2. Filters news for each company
3. Performs sentiment analysis using VADER and TextBlob
4. Calculates positive/negative/neutral ratios
5. Assigns sentiment-based risk scores
6. Creates esg_news_sentiment.csv

Author: Multi-Agent ESG System
Date: 2026-02-12
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.config import (
    COMPANIES,
    DATA_PATHS,
    PROCESSED_DATA_DIR,
    OUTPUT_FILES,
    ESG_INCLUDE_KEYWORDS,
    ESG_EXCLUDE_KEYWORDS,
)

# Import sentiment analysis libraries
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    print("⚠️  VADER sentiment not available. Install: pip install vaderSentiment")

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    print("⚠️  TextBlob not available. Install: pip install textblob")


class NewsSentimentAnalyzer:
    """Agent for analyzing ESG news sentiment"""
    
    def __init__(self):
        self.companies = COMPANIES
        self.output_dir = PROCESSED_DATA_DIR
        self.sentiment_data = []
        self.rejected_data = []
        self.esg_include_keywords = ESG_INCLUDE_KEYWORDS
        self.esg_exclude_keywords = ESG_EXCLUDE_KEYWORDS
        
        # Initialize sentiment analyzers
        if VADER_AVAILABLE:
            self.vader = SentimentIntensityAnalyzer()
        else:
            self.vader = None
            
    def load_news_data(self) -> pd.DataFrame:
        """Load ESG news dataset"""
        try:
            news_path = DATA_PATHS['esg_news']
            df_news = pd.read_csv(news_path)
            return df_news
        except Exception as e:
            print(f"Error loading news data: {e}")
            return pd.DataFrame()
            
    def analyze_sentiment_vader(self, text: str) -> Dict:
        """Analyze sentiment using VADER"""
        if not self.vader or pd.isna(text):
            return {'compound': 0, 'pos': 0, 'neg': 0, 'neu': 1}
        
        try:
            scores = self.vader.polarity_scores(str(text))
            return scores
        except:
            return {'compound': 0, 'pos': 0, 'neg': 0, 'neu': 1}
            
    def analyze_sentiment_textblob(self, text: str) -> Dict:
        """Analyze sentiment using TextBlob"""
        if not TEXTBLOB_AVAILABLE or pd.isna(text):
            return {'polarity': 0, 'subjectivity': 0}
        
        try:
            blob = TextBlob(str(text))
            return {
                'polarity': blob.sentiment.polarity,  # -1 to 1
                'subjectivity': blob.sentiment.subjectivity  # 0 to 1
            }
        except:
            return {'polarity': 0, 'subjectivity': 0}
            
    def classify_sentiment(self, compound_score: float) -> str:
        """Classify sentiment as Positive, Negative, or Neutral"""
        if compound_score >= 0.05:
            return 'Positive'
        elif compound_score <= -0.05:
            return 'Negative'
        else:
            return 'Neutral'

    def get_text_columns(self, df_news: pd.DataFrame) -> List[str]:
        """Find candidate text columns in incoming news dataset."""
        return [
            col for col in df_news.columns
            if any(term in col.lower() for term in ['title', 'headline', 'text', 'news', 'content'])
        ]

    def compute_esg_relevance(self, text: str) -> Tuple[int, bool, List[str], List[str]]:
        """Score ESG relevance using include and exclude keyword hits."""
        if pd.isna(text):
            return 0, False, [], []

        text_lower = str(text).lower()
        include_matches = [kw for kw in self.esg_include_keywords if kw in text_lower]
        exclude_matches = [kw for kw in self.esg_exclude_keywords if kw in text_lower]

        include_hits = len(include_matches)
        exclude_hits = len(exclude_matches)
        score = include_hits - exclude_hits
        is_relevant = include_hits >= 1 and score >= 1

        return score, is_relevant, include_matches, exclude_matches
            
    def filter_company_news(self, df_news: pd.DataFrame, company_code: str, 
                           company_name: str) -> pd.DataFrame:
        """Filter news articles for a specific company"""
        
        # Get company keywords
        keywords = [
            company_code,
            company_name,
            self.companies[company_code]['full_name']
        ]
        
        # Try to find news columns (title/headline/content etc.)
        text_columns = self.get_text_columns(df_news)
        
        if not text_columns:
            print(f"  ⚠️  No text column found in news data")
            return pd.DataFrame()
        
        # Filter by company keywords
        mask = pd.Series(False, index=df_news.index)
        for keyword in keywords:
            for col in text_columns:
                mask |= df_news[col].astype(str).str.contains(keyword, case=False, na=False)
        
        company_news = df_news[mask].copy()
        
        return company_news
        
    def process_company_sentiment(self, df_news: pd.DataFrame, 
                                  company_code: str) -> None:
        """Process sentiment for a single company - adds article-level records"""
        
        company_info = self.companies[company_code]
        company_news = self.filter_company_news(df_news, company_code, company_info['full_name'])
        
        print(f"Processing: {company_info['full_name']}...")
        
        if company_news.empty:
            # Add single row indicating no articles found
            self.sentiment_data.append({
                'Company_Code': company_code,
                'Company_Name': company_info['full_name'],
                'Article_Title': 'No articles found',
                'Article_Date': None,
                'Sentiment_Score': 0,
                'Sentiment_Class': 'Neutral',
                'Analysis_Date': datetime.now().strftime('%Y-%m-%d')
            })
            return
        
        # Find text columns
        text_columns = self.get_text_columns(company_news)
        text_col = text_columns[0] if text_columns else company_news.columns[0]
        
        # Find date column
        date_columns = [col for col in company_news.columns if 'date' in col.lower()]
        date_col = date_columns[0] if date_columns else None
        
        # Process each article individually
        for idx, row in company_news.iterrows():
            text_parts = [str(row[col]) for col in text_columns if pd.notna(row[col])]
            combined_text = " ".join(text_parts).strip() if text_parts else str(row[text_col])
            text = combined_text
            article_date = row[date_col] if date_col else None

            relevance_score, is_relevant, include_matches, exclude_matches = self.compute_esg_relevance(text)

            if not is_relevant:
                self.rejected_data.append({
                    'Company_Code': company_code,
                    'Company_Name': company_info['full_name'],
                    'Article_Title': str(text)[:200] if text else 'N/A',
                    'Article_Date': article_date,
                    'ESG_Relevance_Score': relevance_score,
                    'Is_ESG_Relevant': False,
                    'Matched_ESG_Keywords': ", ".join(include_matches),
                    'Matched_Non_ESG_Keywords': ", ".join(exclude_matches),
                    'Rejection_Reason': 'Low ESG relevance or finance-only context',
                    'Analysis_Date': datetime.now().strftime('%Y-%m-%d')
                })
                continue
            
            # VADER sentiment
            vader_scores = self.analyze_sentiment_vader(text)
            compound_score = vader_scores['compound']
            sentiment_class = self.classify_sentiment(compound_score)
            
            # Add one row for this article
            self.sentiment_data.append({
                'Company_Code': company_code,
                'Company_Name': company_info['full_name'],
                'Article_Title': str(text)[:200] if text else 'N/A',  # First 200 chars
                'Article_Date': article_date,
                'Sentiment_Score': compound_score,
                'Sentiment_Class': sentiment_class,
                'Positive_Score': vader_scores['pos'],
                'Negative_Score': vader_scores['neg'],
                'Neutral_Score': vader_scores['neu'],
                'ESG_Relevance_Score': relevance_score,
                'Is_ESG_Relevant': True,
                'Matched_ESG_Keywords': ", ".join(include_matches),
                'Matched_Non_ESG_Keywords': ", ".join(exclude_matches),
                'Analysis_Date': datetime.now().strftime('%Y-%m-%d')
            })
        
    def process_all_companies(self, df_news: pd.DataFrame) -> pd.DataFrame:
        """Process sentiment for all companies"""
        
        for company_code in self.companies.keys():
            self.process_company_sentiment(df_news, company_code)
        
        df = pd.DataFrame(self.sentiment_data)
        return df
        
    def save_to_csv(self, df: pd.DataFrame) -> Path:
        """Save sentiment data to CSV"""
        output_path = self.output_dir / OUTPUT_FILES['news_sentiment']
        df.to_csv(output_path, index=False)

        return output_path

    def save_rejected_to_csv(self) -> Path:
        """Save rejected non-ESG/low-relevance articles to CSV."""
        rejected_path = self.output_dir / OUTPUT_FILES['news_rejected']
        pd.DataFrame(self.rejected_data).to_csv(rejected_path, index=False)
        return rejected_path
        
    def display_summary(self, df: pd.DataFrame):
        """Display summary statistics"""
        pass


def main():
    """Main execution function"""
    print("\nAGENT 3: NEWS SENTIMENT ANALYZER")
    
    # Check if sentiment libraries available
    if not VADER_AVAILABLE:
        print("\nError: VADER not available. Install: pip install vaderSentiment\n")
        return
    
    # Initialize agent
    agent = NewsSentimentAnalyzer()
    
    # Load news data
    df_news = agent.load_news_data()
    
    if df_news.empty:
        print("\nError: No news data available.\n")
        return
    
    # Process all companies
    df_sentiment = agent.process_all_companies(df_news)
    
    # Save results
    output_path = agent.save_to_csv(df_sentiment)
    rejected_path = agent.save_rejected_to_csv()
    
    # Display summary
    print(f"\nFile created: {output_path}")
    print(f"Rows: {len(df_sentiment)} | Columns: {len(df_sentiment.columns)}\n")
    print(f"Rejected file: {rejected_path}")
    print(f"Rejected rows: {len(agent.rejected_data)}\n")


if __name__ == "__main__":
    main()
