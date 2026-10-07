"""
Agent 6: Master ESG Scorer
Combines all agent outputs to generate final ESG risk scores

This agent:
1. Loads outputs from all previous agents (1-5)
2. Calculates category scores (Environmental, Social, Governance)
3. Applies weighted scoring formula
4. Generates final ESG risk scores and rankings
5. Creates esg_master_scores.csv

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

from utils.config import (
    BASE_DIR,
    BRSR_PDF_DIR,
    COMPANIES,
    DATA_PATHS,
    PROCESSED_DATA_DIR,
    OUTPUT_FILES,
    SCORING_WEIGHTS,
    get_risk_level,
)
from utils.lineage_tracker import save_run_metadata


class MasterESGScorer:
    """Agent for calculating final ESG scores"""
    
    def __init__(self):
        self.companies = COMPANIES
        self.output_dir = PROCESSED_DATA_DIR
        self.weights = SCORING_WEIGHTS
        self.master_scores = []
        self.cross_validation_results = []
        self.quality_results = []
        self.benchmark_results = []

    def _safe_float(self, value, default=np.nan):
        """Safely convert a value to float."""
        try:
            if pd.isna(value):
                return default
            return float(value)
        except Exception:
            return default

    def _severity_penalty(self, severity: str) -> int:
        """Map contradiction severity to score penalty."""
        mapping = {'High': 3, 'Medium': 2, 'Low': 1}
        return mapping.get(severity, 0)

    def evaluate_cross_validation(self, company_code: str, datasets: Dict) -> Dict:
        """Detect contradictions across sources and compute consistency score."""
        contradictions = []

        # Gather relevant slices.
        company_brsr = datasets['brsr'][datasets['brsr']['Company_Code'] == company_code] if not datasets['brsr'].empty else pd.DataFrame()
        company_env = datasets['environmental'][datasets['environmental']['Company_Code'] == company_code] if not datasets['environmental'].empty else pd.DataFrame()
        company_gw = datasets['greenwashing'][datasets['greenwashing']['Company_Code'] == company_code] if not datasets['greenwashing'].empty else pd.DataFrame()
        company_sent = datasets['sentiment'][datasets['sentiment']['Company_Code'] == company_code] if not datasets['sentiment'].empty else pd.DataFrame()

        # Rule CV-001: High renewable claim + low environmental score.
        renewable_val = np.nan
        env_score = np.nan
        if not company_brsr.empty:
            renewable = company_brsr[company_brsr['Metric_Name'] == 'Renewable Energy Percentage']['Metric_Value']
            if not renewable.empty:
                renewable_val = self._safe_float(renewable.iloc[0])
        if not company_env.empty:
            env_score = self._safe_float(company_env['Environmental_Risk_Score'].mean())

        if not np.isnan(renewable_val) and not np.isnan(env_score):
            if renewable_val >= 70 and env_score < 5:
                contradictions.append({
                    'Rule_ID': 'CV-001',
                    'Severity': 'High',
                    'Description': 'High renewable claim but low environmental score',
                    'Evidence': f'renewable={renewable_val:.1f}%, env_score={env_score:.2f}'
                })
            elif renewable_val >= 50 and env_score < 6:
                contradictions.append({
                    'Rule_ID': 'CV-001',
                    'Severity': 'Medium',
                    'Description': 'Moderately high renewable claim with weak environmental score',
                    'Evidence': f'renewable={renewable_val:.1f}%, env_score={env_score:.2f}'
                })

        # Rule CV-002: Strong governance claim + low transparency.
        independent_val = np.nan
        transparency_score = np.nan
        if not company_brsr.empty:
            independent = company_brsr[company_brsr['Metric_Name'] == 'Independent Directors Percentage']['Metric_Value']
            if not independent.empty:
                independent_val = self._safe_float(independent.iloc[0])
        if not company_gw.empty:
            total_metrics = len(company_gw)
            disclosed_metrics = len(company_gw[company_gw['Claim_Verified'] != 'Not Disclosed'])
            transparency_score = (disclosed_metrics / total_metrics) * 10 if total_metrics > 0 else np.nan

        if not np.isnan(independent_val) and not np.isnan(transparency_score):
            if independent_val >= 50 and transparency_score < 5:
                contradictions.append({
                    'Rule_ID': 'CV-002',
                    'Severity': 'High',
                    'Description': 'Strong governance claim but low disclosure transparency',
                    'Evidence': f'independent_directors={independent_val:.1f}%, transparency={transparency_score:.2f}/10'
                })
            elif independent_val >= 40 and transparency_score < 6:
                contradictions.append({
                    'Rule_ID': 'CV-002',
                    'Severity': 'Medium',
                    'Description': 'Moderate governance claim with weak transparency',
                    'Evidence': f'independent_directors={independent_val:.1f}%, transparency={transparency_score:.2f}/10'
                })

        # Rule CV-003: Highly positive sentiment + multiple suspicious greenwashing flags.
        if not company_sent.empty and not company_gw.empty:
            if 'Is_ESG_Relevant' in company_sent.columns:
                company_sent = company_sent[company_sent['Is_ESG_Relevant'] == True]
            total_articles = len(company_sent)
            positive_ratio = ((company_sent['Sentiment_Class'] == 'Positive').sum() / total_articles) if total_articles > 0 else np.nan
            suspicious_count = len(company_gw[company_gw['Claim_Verified'] == 'Suspicious'])
            if not np.isnan(positive_ratio):
                if positive_ratio >= 0.70 and suspicious_count >= 2:
                    contradictions.append({
                        'Rule_ID': 'CV-003',
                        'Severity': 'Medium',
                        'Description': 'Very positive ESG sentiment but multiple suspicious claims',
                        'Evidence': f'positive_ratio={positive_ratio:.2f}, suspicious_claims={suspicious_count}'
                    })

        # Summarize consistency.
        contradiction_count = len(contradictions)
        total_penalty = sum(self._severity_penalty(item['Severity']) for item in contradictions)
        consistency_score = max(0.0, 10.0 - total_penalty)

        highest_severity = 'None'
        if any(c['Severity'] == 'High' for c in contradictions):
            highest_severity = 'High'
        elif any(c['Severity'] == 'Medium' for c in contradictions):
            highest_severity = 'Medium'
        elif any(c['Severity'] == 'Low' for c in contradictions):
            highest_severity = 'Low'

        summary = 'No contradictions detected' if contradiction_count == 0 else '; '.join([c['Rule_ID'] for c in contradictions])

        for item in contradictions:
            self.cross_validation_results.append({
                'Company_Code': company_code,
                'Rule_ID': item['Rule_ID'],
                'Severity': item['Severity'],
                'Description': item['Description'],
                'Evidence': item['Evidence'],
                'Analysis_Date': datetime.now().strftime('%Y-%m-%d')
            })

        if contradiction_count == 0:
            self.cross_validation_results.append({
                'Company_Code': company_code,
                'Rule_ID': 'NONE',
                'Severity': 'None',
                'Description': 'No contradiction detected',
                'Evidence': 'Cross-validation checks passed for available data',
                'Analysis_Date': datetime.now().strftime('%Y-%m-%d')
            })

        return {
            'consistency_score': consistency_score,
            'contradiction_count': contradiction_count,
            'highest_contradiction_severity': highest_severity,
            'contradiction_summary': summary,
        }
        
    def load_all_agent_outputs(self) -> Dict[str, pd.DataFrame]:
        """Load outputs from all previous agents"""
        
        datasets = {}
        
        # Agent 1: BRSR Metrics
        try:
            df_brsr = pd.read_csv(self.output_dir / OUTPUT_FILES['brsr_metrics'])
            datasets['brsr'] = df_brsr
        except Exception as e:
            datasets['brsr'] = pd.DataFrame()
        
        # Agent 2: Environmental Risk
        try:
            df_env = pd.read_csv(self.output_dir / OUTPUT_FILES['environmental_risk'])
            datasets['environmental'] = df_env
        except Exception as e:
            datasets['environmental'] = pd.DataFrame()
        
        # Agent 3: News Sentiment
        try:
            df_sentiment = pd.read_csv(self.output_dir / OUTPUT_FILES['news_sentiment'])
            datasets['sentiment'] = df_sentiment
        except Exception as e:
            datasets['sentiment'] = pd.DataFrame()
        
        # Agent 4: Stock Correlation
        try:
            df_stock = pd.read_csv(self.output_dir / OUTPUT_FILES['stock_correlation'])
            datasets['stock'] = df_stock
        except Exception as e:
            datasets['stock'] = pd.DataFrame()
        
        # Agent 5: Greenwashing Detection
        try:
            df_greenwash = pd.read_csv(self.output_dir / OUTPUT_FILES['greenwashing'])
            datasets['greenwashing'] = df_greenwash
        except Exception as e:
            datasets['greenwashing'] = pd.DataFrame()
        
        # Apply centralized quality gate before scoring.
        datasets = self.apply_quality_gate(datasets)

        return datasets

    def apply_quality_gate(self, datasets: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Validate input quality, classify missingness, and filter low-quality records."""
        brsr = datasets.get('brsr', pd.DataFrame()).copy()
        sentiment = datasets.get('sentiment', pd.DataFrame()).copy()
        environmental = datasets.get('environmental', pd.DataFrame()).copy()
        stock = datasets.get('stock', pd.DataFrame()).copy()
        greenwashing = datasets.get('greenwashing', pd.DataFrame()).copy()

        # Keep only ESG-relevant sentiment rows (if field exists).
        if not sentiment.empty and 'Is_ESG_Relevant' in sentiment.columns:
            sentiment = sentiment[sentiment['Is_ESG_Relevant'] == True].copy()

        # Quality filter for BRSR records: exclude rows flagged for manual review from scoring input.
        if not brsr.empty:
            if 'Needs_Manual_Review' in brsr.columns:
                brsr_for_scoring = brsr[brsr['Needs_Manual_Review'] != True].copy()
            else:
                brsr_for_scoring = brsr.copy()
        else:
            brsr_for_scoring = brsr

        # Build company-level quality report.
        self.quality_results = []
        for company_code, company_info in self.companies.items():
            company_brsr_all = brsr[brsr['Company_Code'] == company_code] if not brsr.empty else pd.DataFrame()
            company_brsr_scoring = brsr_for_scoring[brsr_for_scoring['Company_Code'] == company_code] if not brsr_for_scoring.empty else pd.DataFrame()
            company_green = greenwashing[greenwashing['Company_Code'] == company_code] if not greenwashing.empty else pd.DataFrame()
            company_sent = sentiment[sentiment['Company_Code'] == company_code] if not sentiment.empty else pd.DataFrame()
            company_env = environmental[environmental['Company_Code'] == company_code] if not environmental.empty else pd.DataFrame()
            company_stock = stock[stock['Company_Code'] == company_code] if not stock.empty else pd.DataFrame()

            total_brsr_metrics = len(company_brsr_all)
            extracted_brsr = int(company_brsr_all['Metric_Value'].notna().sum()) if total_brsr_metrics > 0 else 0
            completeness_pct = (extracted_brsr / total_brsr_metrics * 100) if total_brsr_metrics > 0 else 0.0

            extraction_failed_count = int((company_brsr_all['Extraction_Method'] == 'not_found').sum()) if 'Extraction_Method' in company_brsr_all.columns else 0
            review_flag_count = int(company_brsr_all['Needs_Manual_Review'].fillna(False).astype(bool).sum()) if 'Needs_Manual_Review' in company_brsr_all.columns else 0

            not_disclosed_count = int((company_green['Claim_Verified'] == 'Not Disclosed').sum()) if 'Claim_Verified' in company_green.columns else 0

            not_available_sources = 0
            if company_env.empty:
                not_available_sources += 1
            if company_sent.empty:
                not_available_sources += 1
            if company_stock.empty:
                not_available_sources += 1
            if company_green.empty:
                not_available_sources += 1

            # Quality score (0-10): completeness and review pressure based.
            completeness_score = completeness_pct / 10.0
            review_penalty = (review_flag_count / total_brsr_metrics * 5.0) if total_brsr_metrics > 0 else 2.5
            source_availability_score = max(0.0, 10.0 - (not_available_sources * 2.0))
            quality_score = max(0.0, min(10.0, (completeness_score * 0.6) + (source_availability_score * 0.4) - review_penalty))

            quality_gate_status = 'Pass' if quality_score >= 5.0 else 'Low-Quality Warning'

            self.quality_results.append({
                'Company_Code': company_code,
                'Company_Name': company_info['full_name'],
                'BRSR_Total_Metrics': total_brsr_metrics,
                'BRSR_Extracted_Metrics': extracted_brsr,
                'BRSR_Completeness_Pct': round(completeness_pct, 2),
                'Missing_Extraction_Failed_Count': extraction_failed_count,
                'Missing_Not_Disclosed_Count': not_disclosed_count,
                'Missing_Not_Available_Sources': not_available_sources,
                'Review_Flag_Count': review_flag_count,
                'BRSR_Records_Used_For_Scoring': len(company_brsr_scoring),
                'Sentiment_Records_Used': len(company_sent),
                'Environmental_Records_Used': len(company_env),
                'Stock_Records_Used': len(company_stock),
                'Quality_Score': round(quality_score, 2),
                'Quality_Gate_Status': quality_gate_status,
                'Analysis_Date': datetime.now().strftime('%Y-%m-%d')
            })

        datasets['brsr'] = brsr_for_scoring
        datasets['sentiment'] = sentiment
        return datasets

    def get_company_quality(self, company_code: str) -> Dict:
        """Fetch quality metrics for a company from computed quality report."""
        for item in self.quality_results:
            if item['Company_Code'] == company_code:
                return {
                    'quality_score': item['Quality_Score'],
                    'quality_gate_status': item['Quality_Gate_Status'],
                    'brsr_completeness_pct': item['BRSR_Completeness_Pct'],
                    'review_flag_count': item['Review_Flag_Count'],
                    'missing_extraction_failed_count': item['Missing_Extraction_Failed_Count'],
                    'missing_not_disclosed_count': item['Missing_Not_Disclosed_Count'],
                    'missing_not_available_sources': item['Missing_Not_Available_Sources'],
                }
        return {
            'quality_score': 5.0,
            'quality_gate_status': 'Unknown',
            'brsr_completeness_pct': 0.0,
            'review_flag_count': 0,
            'missing_extraction_failed_count': 0,
            'missing_not_disclosed_count': 0,
            'missing_not_available_sources': 0,
        }
        
    def calculate_environmental_score(self, company_code: str, datasets: Dict) -> Dict:
        """Calculate Environmental pillar score"""
        
        scores = []
        details = {}
        
        # From BRSR metrics (Agent 1)
        if not datasets['brsr'].empty:
            company_brsr = datasets['brsr'][
                (datasets['brsr']['Company_Code'] == company_code) &
                (datasets['brsr']['Metric_Category'] == 'Environmental')
            ]
            
            # Check renewable energy percentage
            renewable = company_brsr[company_brsr['Metric_Name'] == 'Renewable Energy Percentage']['Metric_Value'].values
            if len(renewable) > 0 and pd.notna(renewable[0]):
                renewable_val = float(renewable[0])
                # Convert percentage to 0-10 scale
                renewable_score = (renewable_val / 100) * 10
                scores.append(renewable_score)
                details['renewable_energy_pct'] = renewable_val
                details['renewable_score'] = renewable_score
            
            # Check water recycled percentage
            water = company_brsr[company_brsr['Metric_Name'] == 'Water Recycled Percentage']['Metric_Value'].values
            if len(water) > 0 and pd.notna(water[0]):
                water_val = float(water[0])
                water_score = (water_val / 100) * 10
                scores.append(water_score)
                details['water_recycled_pct'] = water_val
                details['water_score'] = water_score
        
        # From Environmental Risk (Agent 2)
        if not datasets['environmental'].empty:
            company_env = datasets['environmental'][datasets['environmental']['Company_Code'] == company_code]
            if not company_env.empty:
                env_score = company_env['Environmental_Risk_Score'].mean()
                scores.append(env_score)
                details['location_environmental_score'] = env_score
        
        # From Greenwashing Detection (Agent 5) - Trust score
        if not datasets['greenwashing'].empty:
            company_gw = datasets['greenwashing'][datasets['greenwashing']['Company_Code'] == company_code]
            if not company_gw.empty:
                trust_score = company_gw['Trust_Score'].values[0]
                scores.append(trust_score)
                details['transparency_trust_score'] = trust_score
        
        # Calculate average
        if scores:
            final_score = np.mean(scores)
        else:
            final_score = 5.0  # Neutral default
        
        details['final_environmental_score'] = final_score
        details['component_count'] = len(scores)
        
        return details
        
    def calculate_social_score(self, company_code: str, datasets: Dict) -> Dict:
        """Calculate Social pillar score"""
        
        scores = []
        details = {}
        
        # From BRSR metrics (Agent 1)
        if not datasets['brsr'].empty:
            company_brsr = datasets['brsr'][
                (datasets['brsr']['Company_Code'] == company_code) &
                (datasets['brsr']['Metric_Category'] == 'Social')
            ]
            
            # Check female employee percentage
            female = company_brsr[company_brsr['Metric_Name'] == 'Female Employee Percentage']['Metric_Value'].values
            if len(female) > 0 and pd.notna(female[0]):
                female_val = float(female[0])
                # Higher percentage = better score
                # Industry benchmark: ~30-40% is good for IT
                if female_val >= 40:
                    female_score = 10.0
                elif female_val >= 30:
                    female_score = 8.0
                elif female_val >= 20:
                    female_score = 6.0
                else:
                    female_score = 4.0
                scores.append(female_score)
                details['female_employee_pct'] = female_val
                details['diversity_score'] = female_score
            
            # Check training hours per employee
            training = company_brsr[company_brsr['Metric_Name'] == 'Training Hours per Employee']['Metric_Value'].values
            if len(training) > 0 and pd.notna(training[0]):
                training_val = float(training[0])
                # More training = better score
                # Benchmark: 40+ hours is excellent
                if training_val >= 40:
                    training_score = 10.0
                elif training_val >= 30:
                    training_score = 8.0
                elif training_val >= 20:
                    training_score = 6.0
                else:
                    training_score = 4.0
                scores.append(training_score)
                details['training_hours'] = training_val
                details['training_score'] = training_score
        
        # From News Sentiment (Agent 3)
        if not datasets['sentiment'].empty:
            company_sent = datasets['sentiment'][datasets['sentiment']['Company_Code'] == company_code]
            if 'Is_ESG_Relevant' in company_sent.columns:
                company_sent = company_sent[company_sent['Is_ESG_Relevant'] == True]
            if not company_sent.empty:
                # Calculate sentiment score from article-level data
                positive_count = (company_sent['Sentiment_Class'] == 'Positive').sum()
                negative_count = (company_sent['Sentiment_Class'] == 'Negative').sum()
                total_articles = len(company_sent)
                
                # Sentiment score: 0-10 based on positive ratio
                positive_ratio = positive_count / total_articles if total_articles > 0 else 0.5
                sentiment_score = positive_ratio * 10
                
                scores.append(sentiment_score)
                details['news_sentiment_score'] = sentiment_score
                details['positive_articles'] = positive_count
                details['negative_articles'] = negative_count
                details['total_articles'] = total_articles
        
        # Calculate average
        if scores:
            final_score = np.mean(scores)
        else:
            final_score = 5.0  # Neutral default
        
        details['final_social_score'] = final_score
        details['component_count'] = len(scores)
        
        return details
        
    def calculate_governance_score(self, company_code: str, datasets: Dict) -> Dict:
        """Calculate Governance pillar score"""
        
        scores = []
        details = {}
        
        # From BRSR metrics (Agent 1)
        if not datasets['brsr'].empty:
            company_brsr = datasets['brsr'][
                (datasets['brsr']['Company_Code'] == company_code) &
                (datasets['brsr']['Metric_Category'] == 'Governance')
            ]
            
            # Check independent directors percentage
            independent = company_brsr[company_brsr['Metric_Name'] == 'Independent Directors Percentage']['Metric_Value'].values
            if len(independent) > 0 and pd.notna(independent[0]):
                independent_val = float(independent[0])
                # SEBI requirement: min 50% for listed companies
                if independent_val >= 50:
                    independent_score = 10.0
                elif independent_val >= 40:
                    independent_score = 7.0
                else:
                    independent_score = 4.0
                scores.append(independent_score)
                details['independent_directors_pct'] = independent_val
                details['independence_score'] = independent_score
            
            # Check female directors percentage
            female_directors = company_brsr[company_brsr['Metric_Name'] == 'Female Directors Percentage']['Metric_Value'].values
            if len(female_directors) > 0 and pd.notna(female_directors[0]):
                female_dir_val = float(female_directors[0])
                # SEBI requirement: min 1 female director
                # Good practice: 20%+
                if female_dir_val >= 20:
                    female_dir_score = 10.0
                elif female_dir_val >= 10:
                    female_dir_score = 7.0
                else:
                    female_dir_score = 5.0
                scores.append(female_dir_score)
                details['female_directors_pct'] = female_dir_val
                details['board_diversity_score'] = female_dir_score
        
        # From Stock Performance (Agent 4) - proxy for governance quality
        if not datasets['stock'].empty:
            company_stock = datasets['stock'][datasets['stock']['Company_Code'] == company_code]
            if not company_stock.empty:
                stock_score = company_stock['Stock_Performance_Score'].values[0]
                # Good stock performance often correlates with good governance
                scores.append(stock_score)
                details['stock_performance_score'] = stock_score
        
        # From Greenwashing Detection (Agent 5) - Transparency score
        if not datasets['greenwashing'].empty:
            company_gw = datasets['greenwashing'][datasets['greenwashing']['Company_Code'] == company_code]
            if not company_gw.empty:
                # Calculate transparency from metric-level data
                total_metrics = len(company_gw)
                disclosed_metrics = len(company_gw[company_gw['Claim_Verified'] != 'Not Disclosed'])
                transparency = (disclosed_metrics / total_metrics) * 10 if total_metrics > 0 else 5.0
                
                # Average trust score
                avg_trust = company_gw['Trust_Score'].mean()
                
                # Combined governance score from transparency
                governance_from_transparency = (transparency + avg_trust) / 2
                scores.append(governance_from_transparency)
                details['disclosure_transparency_score'] = transparency
                details['avg_trust_score'] = avg_trust
        
        # Calculate average
        if scores:
            final_score = np.mean(scores)
        else:
            final_score = 5.0  # Neutral default
        
        details['final_governance_score'] = final_score
        details['component_count'] = len(scores)
        
        return details
        
    def calculate_master_score(self, env_score: float, social_score: float,
                              gov_score: float, consistency_score: float = 10.0,
                              quality_score: float = 5.0) -> Dict:
        """Calculate weighted master ESG score"""
        
        # Apply weights from config
        base_master_score = (
            env_score * self.weights['Environmental'] +
            social_score * self.weights['Social'] +
            gov_score * self.weights['Governance']
        )

        # Integrate cross-validation consistency and data quality confidence into final score.
        master_score = (base_master_score * 0.75) + (consistency_score * 0.15) + (quality_score * 0.10)
        
        # Get risk level
        risk_level = get_risk_level(master_score)
        
        return {
            'base_master_esg_score': base_master_score,
            'master_esg_score': master_score,
            'risk_level': risk_level
        }
        
    def process_all_companies(self, datasets: Dict) -> pd.DataFrame:
        """Process all companies and calculate master scores"""
        print("\n" + "="*70)
        print("CALCULATING MASTER ESG SCORES")
        print("="*70)
        
        for company_code, company_info in self.companies.items():
            print(f"\n🏆 {company_info['full_name']} ({company_code})")
            
            # Calculate pillar scores
            env_details = self.calculate_environmental_score(company_code, datasets)
            social_details = self.calculate_social_score(company_code, datasets)
            gov_details = self.calculate_governance_score(company_code, datasets)
            
            print(f"   Environmental Score: {env_details['final_environmental_score']:.2f}/10")
            print(f"   Social Score: {social_details['final_social_score']:.2f}/10")
            print(f"   Governance Score: {gov_details['final_governance_score']:.2f}/10")

            # Cross-validation consistency
            cross_validation = self.evaluate_cross_validation(company_code, datasets)
            print(f"   Consistency Score: {cross_validation['consistency_score']:.2f}/10")
            print(f"   Contradictions: {cross_validation['contradiction_count']} ({cross_validation['highest_contradiction_severity']})")

            # Data quality context
            quality = self.get_company_quality(company_code)
            print(f"   Quality Score: {quality['quality_score']:.2f}/10 ({quality['quality_gate_status']})")
            
            # Calculate master score
            master = self.calculate_master_score(
                env_details['final_environmental_score'],
                social_details['final_social_score'],
                gov_details['final_governance_score'],
                cross_validation['consistency_score'],
                quality['quality_score']
            )
            
            print(f"   ⭐ MASTER ESG SCORE: {master['master_esg_score']:.2f}/10")
            print(f"   Risk Level: {master['risk_level']}")
            
            # Store complete result
            self.master_scores.append({
                'Company_Code': company_code,
                'Company_Name': company_info['full_name'],
                'Environmental_Score': env_details['final_environmental_score'],
                'Social_Score': social_details['final_social_score'],
                'Governance_Score': gov_details['final_governance_score'],
                'Master_ESG_Score': master['master_esg_score'],
                'Master_ESG_Score_Base': master['base_master_esg_score'],
                'Risk_Level': master['risk_level'],
                'Consistency_Score': cross_validation['consistency_score'],
                'Contradiction_Count': cross_validation['contradiction_count'],
                'Highest_Contradiction_Severity': cross_validation['highest_contradiction_severity'],
                'Contradiction_Summary': cross_validation['contradiction_summary'],
                'Quality_Score': quality['quality_score'],
                'Quality_Gate_Status': quality['quality_gate_status'],
                'BRSR_Completeness_Pct': quality['brsr_completeness_pct'],
                'Review_Flag_Count': quality['review_flag_count'],
                'Missing_Extraction_Failed_Count': quality['missing_extraction_failed_count'],
                'Missing_Not_Disclosed_Count': quality['missing_not_disclosed_count'],
                'Missing_Not_Available_Sources': quality['missing_not_available_sources'],
                'Environmental_Weight': self.weights['Environmental'],
                'Social_Weight': self.weights['Social'],
                'Governance_Weight': self.weights['Governance'],
                'Analysis_Date': datetime.now().strftime('%Y-%m-%d'),
                **env_details,
                **social_details,
                **gov_details
            })
        
        df = pd.DataFrame(self.master_scores)
        
        print("\n" + "="*70)
        print("MASTER SCORING COMPLETE")
        print("="*70)
        print(f"Companies scored: {len(df)}")
        
        return df

    def save_cross_validation_report(self) -> Path:
        """Save contradiction-level cross-validation report."""
        output_path = self.output_dir / OUTPUT_FILES['cross_validation']
        pd.DataFrame(self.cross_validation_results).to_csv(output_path, index=False)
        return output_path

    def save_quality_report(self) -> Path:
        """Save company-level data quality report."""
        output_path = self.output_dir / OUTPUT_FILES['data_quality']
        pd.DataFrame(self.quality_results).to_csv(output_path, index=False)
        return output_path

    def build_external_benchmark_report(self, df_master: pd.DataFrame, datasets: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Build external proxy benchmark and compare ranks with project scores."""
        benchmark_rows = []

        stock_df = datasets.get('stock', pd.DataFrame())
        sentiment_df = datasets.get('sentiment', pd.DataFrame())
        green_df = datasets.get('greenwashing', pd.DataFrame())

        for company_code, company_info in self.companies.items():
            company_stock = stock_df[stock_df['Company_Code'] == company_code] if not stock_df.empty else pd.DataFrame()
            company_sent = sentiment_df[sentiment_df['Company_Code'] == company_code] if not sentiment_df.empty else pd.DataFrame()
            company_green = green_df[green_df['Company_Code'] == company_code] if not green_df.empty else pd.DataFrame()

            market_proxy = float(company_stock['Stock_Performance_Score'].mean()) if (not company_stock.empty and 'Stock_Performance_Score' in company_stock.columns) else np.nan

            if not company_sent.empty and 'Sentiment_Class' in company_sent.columns:
                positive_ratio = (company_sent['Sentiment_Class'] == 'Positive').mean()
                reputation_proxy = float(positive_ratio * 10.0)
            else:
                reputation_proxy = np.nan

            if not company_green.empty and 'Claim_Verified' in company_green.columns:
                total_claims = len(company_green)
                disclosed_claims = len(company_green[company_green['Claim_Verified'] != 'Not Disclosed'])
                disclosure_proxy = float((disclosed_claims / total_claims) * 10.0) if total_claims > 0 else np.nan
            else:
                disclosure_proxy = np.nan

            # External proxy benchmark score (0-10) based on public market/news/disclosure signals.
            components = [
                0.4 * market_proxy if not np.isnan(market_proxy) else np.nan,
                0.3 * reputation_proxy if not np.isnan(reputation_proxy) else np.nan,
                0.3 * disclosure_proxy if not np.isnan(disclosure_proxy) else np.nan,
            ]
            valid_components = [value for value in components if not np.isnan(value)]
            benchmark_score = float(sum(valid_components)) if valid_components else 5.0

            benchmark_rows.append({
                'Company_Code': company_code,
                'Company_Name': company_info['full_name'],
                'Benchmark_Market_Proxy': round(market_proxy, 3) if not np.isnan(market_proxy) else np.nan,
                'Benchmark_Reputation_Proxy': round(reputation_proxy, 3) if not np.isnan(reputation_proxy) else np.nan,
                'Benchmark_Disclosure_Proxy': round(disclosure_proxy, 3) if not np.isnan(disclosure_proxy) else np.nan,
                'External_Benchmark_Score': round(benchmark_score, 3),
                'Benchmark_Method': '0.4*Market + 0.3*Reputation + 0.3*Disclosure',
                'Analysis_Date': datetime.now().strftime('%Y-%m-%d')
            })

        benchmark_df = pd.DataFrame(benchmark_rows)

        # Rank comparison: project rank vs benchmark rank.
        project_rank_df = df_master[['Company_Code', 'Master_ESG_Score']].copy()
        project_rank_df = project_rank_df.sort_values('Master_ESG_Score', ascending=False).reset_index(drop=True)
        project_rank_df['Project_Rank'] = project_rank_df.index + 1

        benchmark_rank_df = benchmark_df[['Company_Code', 'External_Benchmark_Score']].copy()
        benchmark_rank_df = benchmark_rank_df.sort_values('External_Benchmark_Score', ascending=False).reset_index(drop=True)
        benchmark_rank_df['Benchmark_Rank'] = benchmark_rank_df.index + 1

        comparison = benchmark_df.merge(project_rank_df[['Company_Code', 'Project_Rank']], on='Company_Code', how='left')
        comparison = comparison.merge(benchmark_rank_df[['Company_Code', 'Benchmark_Rank']], on='Company_Code', how='left')
        comparison['Rank_Deviation'] = (comparison['Project_Rank'] - comparison['Benchmark_Rank']).abs()
        comparison['Rank_Alignment_Status'] = np.where(
            comparison['Rank_Deviation'] <= 1,
            'Aligned',
            'Deviation-Review'
        )

        if len(comparison) > 1:
            rank_corr = project_rank_df.merge(benchmark_rank_df, on='Company_Code')
            spearman_corr = rank_corr['Project_Rank'].corr(rank_corr['Benchmark_Rank'], method='spearman')
            comparison['Rank_Spearman_Correlation'] = round(float(spearman_corr), 3) if pd.notna(spearman_corr) else np.nan
        else:
            comparison['Rank_Spearman_Correlation'] = np.nan

        self.benchmark_results = comparison.to_dict('records')
        return comparison

    def save_benchmark_report(self, benchmark_df: pd.DataFrame) -> Path:
        """Save external benchmarking report."""
        output_path = self.output_dir / OUTPUT_FILES['external_benchmark']
        benchmark_df.to_csv(output_path, index=False)
        return output_path
        
    def save_to_csv(self, df: pd.DataFrame) -> Path:
        """Save master scores to CSV"""
        output_path = self.output_dir / OUTPUT_FILES['master_scores']
        df.to_csv(output_path, index=False)
        
        print(f"\n💾 Saved to: {output_path}")
        print(f"   Rows: {len(df)}")
        print(f"   Columns: {len(df.columns)}")
        
        return output_path
        
    def display_summary(self, df: pd.DataFrame):
        """Display summary and rankings"""
        print("\n" + "="*70)
        print("FINAL ESG RANKINGS")
        print("="*70)
        
        df_sorted = df.sort_values('Master_ESG_Score', ascending=False)
        
        print("\n🏆 OVERALL RANKINGS:")
        for rank, (_, row) in enumerate(df_sorted.iterrows(), 1):
            medal = "🥇" if rank == 1 else ( "🥈" if rank == 2 else ("🥉" if rank == 3 else "  "))
            print(f"{medal} #{rank} {row['Company_Name']}")
            print(f"      ESG Score: {row['Master_ESG_Score']:.2f}/10 ({row['Risk_Level']} Risk)")
            print(f"      E: {row['Environmental_Score']:.1f} | S: {row['Social_Score']:.1f} | G: {row['Governance_Score']:.1f}")
        
        print(f"\n📊 STATISTICS:")
        print(f"  Average ESG Score: {df['Master_ESG_Score'].mean():.2f}/10")
        print(f"  Highest Score: {df['Master_ESG_Score'].max():.2f}/10")
        print(f"  Lowest Score: {df['Master_ESG_Score'].min():.2f}/10")
        print(f"  Standard Deviation: {df['Master_ESG_Score'].std():.2f}")
        
        print(f"\n🎯 RISK DISTRIBUTION:")
        risk_counts = df['Risk_Level'].value_counts()
        for risk_level, count in risk_counts.items():
            print(f"  {risk_level}: {count} companies")


def main():
    """Main execution function"""
    print("\nAGENT 6: MASTER ESG SCORER")
    
    # Initialize agent
    agent = MasterESGScorer()
    
    # Load all agent outputs
    datasets = agent.load_all_agent_outputs()
    
    # Check if we have minimum required data
    if datasets['brsr'].empty:
        print("\nError: BRSR metrics not available. Run Agent 1 first.\n")
        return
    
    company_names = [info['full_name'] for info in agent.companies.values()]
    print(f"Processing: {', '.join(company_names)}...")
    
    # Process all companies
    df_master = agent.process_all_companies(datasets)

    # Build external benchmark comparison and merge key fields into master output.
    benchmark_df = agent.build_external_benchmark_report(df_master, datasets)
    df_master = df_master.merge(
        benchmark_df[
            [
                'Company_Code',
                'External_Benchmark_Score',
                'Project_Rank',
                'Benchmark_Rank',
                'Rank_Deviation',
                'Rank_Alignment_Status',
                'Rank_Spearman_Correlation'
            ]
        ],
        on='Company_Code',
        how='left'
    )
    
    # Save results
    output_path = agent.save_to_csv(df_master)
    cross_validation_path = agent.save_cross_validation_report()
    quality_report_path = agent.save_quality_report()
    benchmark_report_path = agent.save_benchmark_report(benchmark_df)

    # Save run metadata snapshot for reproducibility and lineage.
    run_metadata_path = PROCESSED_DATA_DIR / OUTPUT_FILES['run_metadata']
    input_files = {
        'raw_air_quality_city_day': DATA_PATHS['air_quality_city_day'],
        'raw_air_quality_realtime': DATA_PATHS['air_quality_realtime'],
        'raw_stock_companies': DATA_PATHS['stock_nifty_companies'],
        'raw_esg_news': DATA_PATHS['esg_news'],
        'processed_brsr_metrics': PROCESSED_DATA_DIR / OUTPUT_FILES['brsr_metrics'],
        'processed_environmental_risk': PROCESSED_DATA_DIR / OUTPUT_FILES['environmental_risk'],
        'processed_news_sentiment': PROCESSED_DATA_DIR / OUTPUT_FILES['news_sentiment'],
        'processed_stock_correlation': PROCESSED_DATA_DIR / OUTPUT_FILES['stock_correlation'],
        'processed_greenwashing': PROCESSED_DATA_DIR / OUTPUT_FILES['greenwashing'],
    }
    output_files = {
        'master_scores': output_path,
        'cross_validation': cross_validation_path,
        'data_quality': quality_report_path,
        'external_benchmark': benchmark_report_path,
    }
    run_record = save_run_metadata(
        metadata_path=run_metadata_path,
        repo_root=BASE_DIR,
        input_files=input_files,
        output_files=output_files,
        source_directory=BRSR_PDF_DIR,
    )
    
    # Display summary
    print(f"\nFile created: {output_path}")
    print(f"Rows: {len(df_master)} | Columns: {len(df_master.columns)}\n")
    print(f"Cross-validation report: {cross_validation_path}")
    print(f"Cross-validation rows: {len(agent.cross_validation_results)}\n")
    print(f"Data quality report: {quality_report_path}")
    print(f"Quality rows: {len(agent.quality_results)}\n")
    print(f"External benchmark report: {benchmark_report_path}")
    print(f"Benchmark rows: {len(benchmark_df)}\n")
    print(f"Run metadata: {run_metadata_path}")
    print(f"Run ID: {run_record['run_id']}\n")


if __name__ == "__main__":
    main()
