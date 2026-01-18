"""Analysis module for AI-powered company intelligence.

This module provides:
- Content analysis prompts for Claude API
- Analysis synthesis and summary generation
- Section-based analysis processing
"""

from app.analysis.prompts import get_analysis_prompt, AnalysisSection, ANALYSIS_SECTIONS
from app.analysis.synthesis import AnalysisSynthesizer, analysis_synthesizer

__all__ = [
    'get_analysis_prompt',
    'AnalysisSection',
    'ANALYSIS_SECTIONS',
    'AnalysisSynthesizer',
    'analysis_synthesizer',
]
