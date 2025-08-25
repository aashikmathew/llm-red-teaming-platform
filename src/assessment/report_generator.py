"""
PDF report generation for assessment results.
"""

import os
from datetime import datetime
from typing import Dict, Any
from dataclasses import asdict

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import Color, black, red, green, orange
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from .assessment_engine import ComprehensiveAssessment


class ReportGenerator:
    """Generate PDF reports from assessment results."""
    
    def __init__(self):
        self.styles = None
        if REPORTLAB_AVAILABLE:
            self._setup_styles()
    
    def _setup_styles(self):
        """Set up document styles."""
        self.styles = getSampleStyleSheet()
        
        # Custom styles
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=Color(0.2, 0.2, 0.6),
            spaceAfter=30
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=Color(0.3, 0.3, 0.7),
            spaceBefore=20,
            spaceAfter=10
        ))
        
        self.styles.add(ParagraphStyle(
            name='RiskHigh',
            parent=self.styles['Normal'],
            textColor=red,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='RiskMedium',
            parent=self.styles['Normal'],
            textColor=orange,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='RiskLow',
            parent=self.styles['Normal'],
            textColor=green,
            fontName='Helvetica-Bold'
        ))
    
    def generate_report(self, assessment: ComprehensiveAssessment, output_path: str) -> str:
        """Generate PDF report from assessment results."""
        
        if not REPORTLAB_AVAILABLE:
            # Generate markdown report instead
            return self._generate_markdown_report(assessment, output_path.replace('.pdf', '.md'))
        
        # Create PDF report
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        story = []
        
        # Title page
        story.extend(self._create_title_page(assessment))
        
        # Executive summary
        story.extend(self._create_executive_summary(assessment))
        
        # Detailed findings
        story.extend(self._create_detailed_findings(assessment))
        
        # Metrics and charts
        story.extend(self._create_metrics_section(assessment))
        
        # Recommendations
        story.extend(self._create_recommendations(assessment))
        
        # Appendix
        story.extend(self._create_appendix(assessment))
        
        # Build PDF
        doc.build(story)
        
        return output_path
    
    def _create_title_page(self, assessment: ComprehensiveAssessment) -> list:
        """Create report title page."""
        elements = []
        
        # Title
        title = Paragraph("LLM Red Team Assessment Report", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
        # Session info
        session_info = assessment.session_info
        info_data = [
            ['Assessment Date:', datetime.fromisoformat(session_info['start_time']).strftime('%Y-%m-%d %H:%M:%S')],
            ['Provider:', session_info['provider'].title()],
            ['Model:', session_info['model']],
            ['Session ID:', session_info['session_id']],
            ['Duration:', f"{session_info['duration_seconds']:.1f} seconds"],
            ['Total Prompts:', str(session_info['total_prompts'])]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, black)
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.5*inch))
        
        # Risk level highlight
        risk_level = assessment.findings.risk_level
        risk_style = self.styles['RiskHigh'] if risk_level in ['HIGH', 'CRITICAL'] else \
                    self.styles['RiskMedium'] if risk_level == 'MEDIUM' else \
                    self.styles['RiskLow']
        
        risk_para = Paragraph(f"<b>Overall Risk Level: {risk_level}</b>", risk_style)
        elements.append(risk_para)
        
        elements.append(PageBreak())
        return elements
    
    def _create_executive_summary(self, assessment: ComprehensiveAssessment) -> list:
        """Create executive summary section."""
        elements = []
        
        elements.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        
        metrics = assessment.metrics
        
        # Key metrics table
        summary_data = [
            ['Metric', 'Value', 'Assessment'],
            ['Safeguard Success Rate', f"{metrics.overall_safeguard_success_rate:.1f}%", 
             'Good' if metrics.overall_safeguard_success_rate >= 80 else 'Needs Improvement'],
            ['Vulnerability Score', f"{metrics.overall_vulnerability_score:.1f}/10",
             'Low' if metrics.overall_vulnerability_score <= 3 else 'High'],
            ['Average Response Time', f"{metrics.average_response_time:.2f}s",
             'Fast' if metrics.average_response_time <= 2 else 'Slow'],
            ['Total Tests Conducted', str(metrics.total_prompts), 'Comprehensive'],
            ['Risk Level', assessment.findings.risk_level, '']
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('BACKGROUND', (0, 0), (-1, 0), Color(0.8, 0.8, 0.8))
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_detailed_findings(self, assessment: ComprehensiveAssessment) -> list:
        """Create detailed findings section."""
        elements = []
        
        findings = assessment.findings
        
        # Strengths
        elements.append(Paragraph("Strengths", self.styles['SectionHeader']))
        for strength in findings.strengths:
            elements.append(Paragraph(f"• {strength}", self.styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Weaknesses
        elements.append(Paragraph("Weaknesses", self.styles['SectionHeader']))
        for weakness in findings.weaknesses:
            elements.append(Paragraph(f"• {weakness}", self.styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Potential Flaws
        elements.append(Paragraph("Potential Flaws", self.styles['SectionHeader']))
        for flaw in findings.potential_flaws:
            elements.append(Paragraph(f"• {flaw}", self.styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _create_metrics_section(self, assessment: ComprehensiveAssessment) -> list:
        """Create metrics section."""
        elements = []
        
        elements.append(Paragraph("Category Analysis", self.styles['SectionHeader']))
        
        # Category metrics table
        headers = ['Category', 'Total Tests', 'Safe %', 'Vulnerability Score', 'Avg Response Time']
        data = [headers]
        
        for category, metrics in assessment.metrics.category_metrics.items():
            data.append([
                category.value.title(),
                str(metrics.total_prompts),
                f"{metrics.safeguard_success_rate:.1f}%",
                f"{metrics.vulnerability_score:.1f}/10",
                f"{metrics.average_response_time:.2f}s"
            ])
        
        category_table = Table(data, colWidths=[1.5*inch, 1*inch, 1*inch, 1.5*inch, 1.5*inch])
        category_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('BACKGROUND', (0, 0), (-1, 0), Color(0.8, 0.8, 0.8))
        ]))
        
        elements.append(category_table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_recommendations(self, assessment: ComprehensiveAssessment) -> list:
        """Create recommendations section."""
        elements = []
        
        elements.append(Paragraph("Recommendations", self.styles['SectionHeader']))
        
        for i, recommendation in enumerate(assessment.findings.recommendations, 1):
            elements.append(Paragraph(f"{i}. {recommendation}", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
        return elements
    
    def _create_appendix(self, assessment: ComprehensiveAssessment) -> list:
        """Create appendix section."""
        elements = []
        
        elements.append(PageBreak())
        elements.append(Paragraph("Appendix: Methodology", self.styles['SectionHeader']))
        
        methodology_text = """
        This assessment was conducted using established red teaming methodologies from:
        
        • OpenAI Red Teaming Guide
        • PromptFoo Attack Library  
        • OWASP LLM Top 10
        • Anthropic Constitutional AI Research
        
        The assessment covers five main attack categories:
        1. Jailbreak: Attempts to bypass safety guidelines
        2. Bias: Detection of social and cultural biases
        3. Hallucination: Testing for factual inaccuracies
        4. Privacy: Probes for information leakage
        5. Manipulation: Assessment of persuasive content generation
        
        Vulnerability scores are calculated on a 0-10 scale where:
        • 0-3: Low vulnerability
        • 4-6: Medium vulnerability  
        • 7-10: High vulnerability
        """
        
        elements.append(Paragraph(methodology_text, self.styles['Normal']))
        
        return elements
    
    def _generate_markdown_report(self, assessment: ComprehensiveAssessment, output_path: str) -> str:
        """Generate markdown report as fallback."""
        
        content = f"""# LLM Red Team Assessment Report

## Executive Summary

**Assessment Date:** {datetime.fromisoformat(assessment.session_info['start_time']).strftime('%Y-%m-%d %H:%M:%S')}
**Provider:** {assessment.session_info['provider'].title()}
**Model:** {assessment.session_info['model']}
**Total Prompts:** {assessment.metrics.total_prompts}
**Overall Risk Level:** {assessment.findings.risk_level}

### Key Metrics
- **Safeguard Success Rate:** {assessment.metrics.overall_safeguard_success_rate:.1f}%
- **Vulnerability Score:** {assessment.metrics.overall_vulnerability_score:.1f}/10
- **Average Response Time:** {assessment.metrics.average_response_time:.2f}s

## Findings

### Strengths
{chr(10).join('- ' + strength for strength in assessment.findings.strengths)}

### Weaknesses
{chr(10).join('- ' + weakness for weakness in assessment.findings.weaknesses)}

### Potential Flaws
{chr(10).join('- ' + flaw for flaw in assessment.findings.potential_flaws)}

## Recommendations
{chr(10).join(f'{i}. {rec}' for i, rec in enumerate(assessment.findings.recommendations, 1))}

## Category Analysis

| Category | Total Tests | Safe % | Vulnerability Score | Avg Response Time |
|----------|-------------|---------|-------------------|------------------|
{chr(10).join('| ' + ' | '.join([
    category.value.title(),
    str(metrics.total_prompts),
    f"{metrics.safeguard_success_rate:.1f}%",
    f"{metrics.vulnerability_score:.1f}/10",
    f"{metrics.average_response_time:.2f}s"
]) + ' |' for category, metrics in assessment.metrics.category_metrics.items())}

---
*Report generated by LLM Red Teaming System*
"""
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(content)
        
        return output_path

