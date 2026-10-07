"""
Agent 7: Explainable AI Agent
Generates human-readable explanations for ESG scores and risk assessments

This agent:
1. Loads all agent outputs including master scores
2. Analyzes scoring components for each company
3. Generates detailed explanations for scores
4. Identifies strengths and weaknesses
5. Provides actionable recommendations
6. Creates multi_agent_explanations.csv

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


class ExplainableAIAgent:
    """Agent for generating explainable AI insights"""
    
    def __init__(self):
        self.companies = COMPANIES
        self.output_dir = PROCESSED_DATA_DIR
        self.explanations = []
        
    def load_master_scores(self) -> pd.DataFrame:
        """Load master ESG scores"""
        try:
            df_master = pd.read_csv(self.output_dir / OUTPUT_FILES['master_scores'])
            return df_master
        except Exception as e:
            print(f"Error loading master scores: {e}")
            print("Please run Agent 6 first.")
            return pd.DataFrame()
            
    def generate_score_explanation(self, company_code: str, 
                                   row: pd.Series) -> str:
        """Generate explanation for the overall ESG score"""
        
        company_name = row['Company_Name']
        master_score = row['Master_ESG_Score']
        risk_level = row['Risk_Level']
        
        # Start explanation
        explanation = f"{company_name} has an overall ESG score of {master_score:.2f}/10, "
        explanation += f"indicating {risk_level} ESG risk. "
        
        # Explain pillar contributions
        env_score = row['Environmental_Score']
        social_score = row['Social_Score']
        gov_score = row['Governance_Score']
        
        # Find strongest pillar
        pillars = {
            'Environmental': env_score,
            'Social': social_score,
            'Governance': gov_score
        }
        
        strongest = max(pillars, key=pillars.get)
        weakest = min(pillars, key=pillars.get)
        
        explanation += f"The company performs strongest in {strongest} ({pillars[strongest]:.1f}/10) "
        explanation += f"and weakest in {weakest} ({pillars[weakest]:.1f}/10). "

        if 'Consistency_Score' in row and pd.notna(row['Consistency_Score']):
            explanation += f"Cross-validation consistency is {row['Consistency_Score']:.1f}/10. "
        if 'Contradiction_Count' in row and pd.notna(row['Contradiction_Count']):
            contradiction_count = int(row['Contradiction_Count'])
            if contradiction_count > 0:
                severity = row.get('Highest_Contradiction_Severity', 'Unknown')
                explanation += f"Detected {contradiction_count} contradiction(s), highest severity {severity}. "

        if 'Quality_Score' in row and pd.notna(row['Quality_Score']):
            explanation += f"Data quality confidence is {row['Quality_Score']:.1f}/10. "

        if 'External_Benchmark_Score' in row and pd.notna(row['External_Benchmark_Score']):
            explanation += f"External benchmark proxy score is {row['External_Benchmark_Score']:.1f}/10. "
        if 'Rank_Deviation' in row and pd.notna(row['Rank_Deviation']):
            deviation = int(row['Rank_Deviation'])
            if deviation > 1:
                explanation += f"Project vs benchmark rank deviation is {deviation}, suggesting further review. "
            else:
                explanation += "Project ranking is closely aligned with benchmark ranking. "
        
        return explanation
        
    def identify_strengths(self, company_code: str, row: pd.Series) -> List[str]:
        """Identify company strengths"""
        
        strengths = []
        
        # Environmental strengths
        if 'renewable_score' in row and pd.notna(row['renewable_score']):
            if row['renewable_score'] >= 7:
                pct = row.get('renewable_energy_pct', 70)
                strengths.append(f"High renewable energy usage ({pct:.0f}%)")
        
        if 'location_environmental_score' in row and pd.notna(row['location_environmental_score']):
            if row['location_environmental_score'] >= 7:
                strengths.append("Good air quality at office locations")
        
        # Social strengths
        if 'diversity_score' in row and pd.notna(row['diversity_score']):
            if row['diversity_score'] >= 7:
                pct = row.get('female_employee_pct', 30)
                strengths.append(f"Strong gender diversity ({pct:.0f}% female employees)")
        
        if 'training_score' in row and pd.notna(row['training_score']):
            if row['training_score'] >= 7:
                hours = row.get('training_hours', 30)
                strengths.append(f"Excellent employee training ({hours:.0f} hours per employee)")
        
        if 'news_sentiment_score' in row and pd.notna(row['news_sentiment_score']):
            if row['news_sentiment_score'] >= 7:
                strengths.append("Positive media coverage and reputation")
        
        # Governance strengths
        if 'independence_score' in row and pd.notna(row['independence_score']):
            if row['independence_score'] >= 7:
                pct = row.get('independent_directors_pct', 50)
                strengths.append(f"Strong board independence ({pct:.0f}%)")
        
        if 'disclosure_transparency_score' in row and pd.notna(row['disclosure_transparency_score']):
            if row['disclosure_transparency_score'] >= 7:
                strengths.append("High transparency in ESG reporting")
        
        if not strengths:
            strengths.append("Maintains baseline ESG standards")
        
        return strengths
        
    def identify_weaknesses(self, company_code: str, row: pd.Series) -> List[str]:
        """Identify areas for improvement"""
        
        weaknesses = []
        
        # Environmental weaknesses
        if 'renewable_score' in row and pd.notna(row['renewable_score']):
            if row['renewable_score'] < 5:
                pct = row.get('renewable_energy_pct', 30)
                weaknesses.append(f"Low renewable energy usage ({pct:.0f}%)")
        
        if 'location_environmental_score' in row and pd.notna(row['location_environmental_score']):
            if row['location_environmental_score'] < 5:
                weaknesses.append("Poor air quality at some office locations")
        
        # Social weaknesses
        if 'diversity_score' in row and pd.notna(row['diversity_score']):
            if row['diversity_score'] < 5:
                pct = row.get('female_employee_pct', 20)
                weaknesses.append(f"Limited gender diversity ({pct:.0f}% female employees)")
        
        if 'training_score' in row and pd.notna(row['training_score']):
            if row['training_score'] < 5:
                hours = row.get('training_hours', 15)
                weaknesses.append(f"Insufficient employee training ({hours:.0f} hours per employee)")
        
        if 'news_sentiment_score' in row and pd.notna(row['news_sentiment_score']):
            if row['news_sentiment_score'] < 5:
                weaknesses.append("Negative media coverage or controversies")
        
        # Governance weaknesses
        if 'independence_score' in row and pd.notna(row['independence_score']):
            if row['independence_score'] < 5:
                pct = row.get('independent_directors_pct', 40)
                weaknesses.append(f"Inadequate board independence ({pct:.0f}%)")
        
        if 'disclosure_transparency_score' in row and pd.notna(row['disclosure_transparency_score']):
            if row['disclosure_transparency_score'] < 5:
                weaknesses.append("Low transparency in ESG disclosure")
        
        # Check for greenwashing indicators
        if 'transparency_trust_score' in row and pd.notna(row['transparency_trust_score']):
            if row['transparency_trust_score'] < 6:
                weaknesses.append("Potential greenwashing concerns")

        if 'Contradiction_Count' in row and pd.notna(row['Contradiction_Count']):
            if int(row['Contradiction_Count']) > 0:
                severity = row.get('Highest_Contradiction_Severity', 'Unknown')
                weaknesses.append(f"Cross-validation contradictions detected (severity: {severity})")

        if 'Quality_Score' in row and pd.notna(row['Quality_Score']):
            if float(row['Quality_Score']) < 5:
                weaknesses.append("Low data quality confidence for scoring inputs")
        
        if not weaknesses:
            weaknesses.append("No major weaknesses identified")
        
        return weaknesses
        
    def generate_recommendations(self, company_code: str, 
                                row: pd.Series,
                                weaknesses: List[str]) -> List[str]:
        """Generate actionable recommendations"""
        
        recommendations = []
        
        # Recommendations based on weaknesses
        if any('renewable' in w.lower() for w in weaknesses):
            recommendations.append("Increase investment in renewable energy sources and set ambitious targets")
        
        if any('air quality' in w.lower() for w in weaknesses):
            recommendations.append("Implement air quality improvement measures at affected locations")
        
        if any('diversity' in w.lower() for w in weaknesses):
            recommendations.append("Enhance diversity hiring programs and create inclusive workplace policies")
        
        if any('training' in w.lower() for w in weaknesses):
            recommendations.append("Expand employee training and development programs")
        
        if any('media' in w.lower() or 'negative' in w.lower() for w in weaknesses):
            recommendations.append("Improve stakeholder communication and address public concerns proactively")
        
        if any('independence' in w.lower() for w in weaknesses):
            recommendations.append("Appoint more independent directors to strengthen board governance")
        
        if any('transparency' in w.lower() or 'greenwashing' in w.lower() for w in weaknesses):
            recommendations.append("Enhance ESG disclosure completeness and third-party verification")

        if any('cross-validation contradictions' in w.lower() for w in weaknesses):
            recommendations.append("Resolve contradiction flags by reconciling BRSR claims with external performance data")

        if any('low data quality confidence' in w.lower() for w in weaknesses):
            recommendations.append("Improve data completeness and resolve review-flagged metrics before final decisions")

        if 'Rank_Deviation' in row and pd.notna(row['Rank_Deviation']):
            if int(row['Rank_Deviation']) > 1:
                recommendations.append("Investigate benchmark rank deviation and document reasons for score differences")
        
        # General recommendations based on score
        master_score = row['Master_ESG_Score']
        
        if master_score < 6:
            recommendations.append("Conduct comprehensive ESG audit and develop improvement roadmap")
        elif master_score < 8:
            recommendations.append("Focus on continuous improvement in identified weak areas")
        else:
            recommendations.append("Maintain current ESG excellence and share best practices")
        
        return recommendations[:5]  # Limit to top 5 recommendations
        
    def generate_comparative_insight(self, company_code: str,
                                    df_master: pd.DataFrame) -> str:
        """Generate insight comparing company to peers"""
        
        company_row = df_master[df_master['Company_Code'] == company_code].iloc[0]
        company_score = company_row['Master_ESG_Score']
        
        # Calculate rank
        df_sorted = df_master.sort_values('Master_ESG_Score', ascending=False)
        rank = df_sorted.index.get_loc(company_row.name) + 1
        total = len(df_master)
        
        # Calculate percentile
        percentile = ((total - rank + 1) / total) * 100
        
        # Compare to average
        avg_score = df_master['Master_ESG_Score'].mean()
        diff = company_score - avg_score
        
        insight = f"Ranks #{rank} out of {total} IT companies analyzed ({percentile:.0f}th percentile). "
        
        if diff > 0.5:
            insight += f"Performs {diff:.1f} points above industry average. "
        elif diff < -0.5:
            insight += f"Performs {abs(diff):.1f} points below industry average. "
        else:
            insight += "Performs in line with industry average. "
        
        # Identify closest peer
        df_no_self = df_master[df_master['Company_Code'] != company_code].copy()
        df_no_self['score_diff'] = abs(df_no_self['Master_ESG_Score'] - company_score)
        closest_peer = df_no_self.nsmallest(1, 'score_diff').iloc[0]
        
        insight += f"Most similar ESG profile to {closest_peer['Company_Name']} "
        insight += f"(score: {closest_peer['Master_ESG_Score']:.2f})."

        if 'Project_Rank' in company_row and 'Benchmark_Rank' in company_row and pd.notna(company_row['Project_Rank']) and pd.notna(company_row['Benchmark_Rank']):
            insight += f" Project rank is {int(company_row['Project_Rank'])} vs benchmark rank {int(company_row['Benchmark_Rank'])}."
        
        return insight
        
    def process_all_companies(self, df_master: pd.DataFrame) -> pd.DataFrame:
        """Generate explanations for all companies"""
        
        for _, row in df_master.iterrows():
            company_code = row['Company_Code']
            company_name = row['Company_Name']
            
            # Generate overall explanation
            score_explanation = self.generate_score_explanation(company_code, row)
            
            # Identify strengths and weaknesses
            strengths = self.identify_strengths(company_code, row)
            weaknesses = self.identify_weaknesses(company_code, row)
            
            # Generate recommendations
            recommendations = self.generate_recommendations(company_code, row, weaknesses)
            
            # Generate comparative insight
            comparative = self.generate_comparative_insight(company_code, df_master)
            
            # Store result
            self.explanations.append({
                'Company_Code': company_code,
                'Company_Name': company_name,
                'Master_ESG_Score': row['Master_ESG_Score'],
                'Risk_Level': row['Risk_Level'],
                'Score_Explanation': score_explanation,
                'Strengths': ' | '.join(strengths),
                'Strengths_Count': len(strengths),
                'Weaknesses': ' | '.join(weaknesses),
                'Weaknesses_Count': len(weaknesses),
                'Recommendations': ' | '.join(recommendations),
                'Recommendations_Count': len(recommendations),
                'Comparative_Insight': comparative,
                'Analysis_Date': datetime.now().strftime('%Y-%m-%d')
            })
        
        df = pd.DataFrame(self.explanations)
        
        return df
        
    def save_to_csv(self, df: pd.DataFrame) -> Path:
        """Save explanations to CSV"""
        output_path = self.output_dir / OUTPUT_FILES['explanations']
        df.to_csv(output_path, index=False)
        
        return output_path
        
    def display_sample_explanation(self, df: pd.DataFrame):
        """Display sample explanation for top-ranked company"""
        if df.empty:
            return
        top_company = df.sort_values('Master_ESG_Score', ascending=False).iloc[0]
        print("\nTop Company Comparative Insight:")
        print(f"   {top_company['Comparative_Insight']}")


def main():
    """Main execution function"""
    print("\nAGENT 7: EXPLAINABLE AI AGENT")
    
    # Initialize agent
    agent = ExplainableAIAgent()
    
    # Load master scores
    df_master = agent.load_master_scores()
    
    if df_master.empty:
        print("\nError: Master scores not available. Run Agent 6 first.\n")
        return
    
    company_names = [info['full_name'] for info in agent.companies.values()]
    print(f"Processing: {', '.join(company_names)}...")
    
    # Generate explanations
    df_explanations = agent.process_all_companies(df_master)
    
    # Save results
    output_path = agent.save_to_csv(df_explanations)
    
    # Display summary
    print(f"\nFile created: {output_path}")
    print(f"Rows: {len(df_explanations)} | Columns: {len(df_explanations.columns)}\n")


if __name__ == "__main__":
    main()
