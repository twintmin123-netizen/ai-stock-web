"""
PDF Report Generator for AI Analysis Reports
Generates a structured PDF with Korean text support using ReportLab.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import datetime
import os


class PDFReportGenerator:
    """Generate PDF reports for stock analysis with Korean text support."""
    
    def __init__(self):
        """Initialize PDF generator with Korean font."""
        # Register Korean font (Malgun Gothic)
        self.font_name = 'Helvetica'
        self.font_name_bold = 'Helvetica-Bold'
        
        try:
            # Try to register Malgun Gothic
            font_path = 'C:/Windows/Fonts/malgun.ttf'
            font_bold_path = 'C:/Windows/Fonts/malgunbd.ttf'
            
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('MalgunGothic', font_path))
                self.font_name = 'MalgunGothic'
                print(f"✅ Loaded Korean font: {font_path}")
                
                if os.path.exists(font_bold_path):
                    pdfmetrics.registerFont(TTFont('MalgunGothic-Bold', font_bold_path))
                    self.font_name_bold = 'MalgunGothic-Bold'
                    print(f"✅ Loaded Korean bold font: {font_bold_path}")
                else:
                    self.font_name_bold = 'MalgunGothic'
                    print(f"⚠️ Bold font not found, using regular font")
            else:
                print(f"⚠️ Korean font not found at {font_path}, using Helvetica (Korean text may not display)")
                
        except Exception as e:
            print(f"⚠️ Failed to load Korean font: {e}")
            print("Using Helvetica as fallback (Korean text may not display properly)")
    
    def _create_styles(self):
        """Create custom paragraph styles for the report."""
        styles = getSampleStyleSheet()
        
        # Title style
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontName=self.font_name_bold,
            fontSize=24,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Section header style
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontName=self.font_name_bold,
            fontSize=16,
            textColor=colors.HexColor('#3b82f6'),
            spaceAfter=12,
            spaceBefore=20
        ))
        
        # Agent name style
        styles.add(ParagraphStyle(
            name='AgentName',
            parent=styles['Heading3'],
            fontName=self.font_name_bold,
            fontSize=14,
            textColor=colors.HexColor('#059669'),
            spaceAfter=10,
            spaceBefore=15
        ))
        
        # Body text style
        styles.add(ParagraphStyle(
            name='KoreanBody',
            parent=styles['BodyText'],
            fontName=self.font_name,
            fontSize=10,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=10
        ))
        
        # Small text style
        styles.add(ParagraphStyle(
            name='SmallText',
            parent=styles['BodyText'],
            fontName=self.font_name,
            fontSize=8,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=5
        ))
        
        return styles
    
    def _clean_text(self, text):
        """Clean and format text for PDF rendering."""
        if not text:
            return ""
        
        # Handle non-string types (dict, list, etc.)
        if not isinstance(text, str):
            import json
            try:
                # Convert to JSON string with proper formatting
                text = json.dumps(text, ensure_ascii=False, indent=2)
            except:
                # Fallback to string conversion
                text = str(text)
        
        # Remove markdown bold markers
        text = text.replace('**', '')
        
        # Replace newlines with <br/> for Paragraph
        text = text.replace('\n', '<br/>')
        
        return text
    
    def _extract_agent_logs(self, agent_logs):
        """Extract and organize agent logs by role."""
        agents = {
            'market': None,
            'news': None,
            'strategy': None,
            'risk': None
        }
        
        for log in agent_logs:
            step_name = log.get('step_name', '').lower()
            
            # More precise matching to avoid conflicts
            if 'market' in step_name and 'data analyst' in step_name:
                agents['market'] = log
            elif 'news' in step_name and 'analyst' in step_name:
                agents['news'] = log
            elif 'trading' in step_name and 'strategy' in step_name:
                agents['strategy'] = log
            elif 'risk' in step_name and 'advisor' in step_name:
                # Make sure it's NOT the report writer
                if 'report' not in step_name and 'writer' not in step_name:
                    agents['risk'] = log
        
        return agents
    
    def _translate_text(self, text):
        """Translate text to Korean using the translation API."""
        try:
            from utils.common import _translate_with_deepl
            
            if not text or len(text.strip()) == 0:
                return text
            
            # Split into paragraphs for better translation
            if len(text) > 3000:
                paragraphs = text.split('\n\n')
                translated_paragraphs = []
                
                for para in paragraphs:
                    if para.strip():
                        try:
                            translated = _translate_with_deepl(para)
                            translated_paragraphs.append(translated)
                        except:
                            translated_paragraphs.append(para)
                
                return '\n\n'.join(translated_paragraphs)
            else:
                return _translate_with_deepl(text)
        except Exception as e:
            print(f"⚠️ Translation failed: {e}")
            return text  # Return original if translation fails
    
    def generate_report(self, analysis_data, ticker):
        """
        Generate PDF report from analysis data.
        
        Args:
            analysis_data: Dict containing analysis results
            ticker: Stock ticker symbol
            
        Returns:
            BytesIO: PDF file in memory
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        styles = self._create_styles()
        story = []
        
        # Get data
        company_name = analysis_data.get('company_name', ticker)
        action = analysis_data.get('action', '현상 유지')
        market_score = analysis_data.get('market_score', 5)
        company_score = analysis_data.get('company_score', 5)
        outlook_score = analysis_data.get('outlook_score', 5)
        agent_logs = analysis_data.get('agent_logs', [])
        
        # Parse overall_comment (might be string or dict)
        overall_comment = analysis_data.get('overall_comment', {})
        if isinstance(overall_comment, str):
            import json
            try:
                overall_comment = json.loads(overall_comment)
            except:
                overall_comment = {}
        
        # ===== COVER PAGE =====
        story.append(Spacer(1, 3*cm))
        story.append(Paragraph("AI 에이전틱 분석 리포트", styles['CustomTitle']))
        story.append(Spacer(1, 1*cm))
        
        # Stock info table
        stock_info_data = [
            ['종목명', company_name],
            ['티커', ticker],
            ['투자 판단', action],
            ['생성 일시', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
        
        stock_info_table = Table(stock_info_data, colWidths=[4*cm, 10*cm])
        stock_info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('FONTNAME', (0, 0), (0, -1), self.font_name_bold),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e293b')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(stock_info_table)
        story.append(Spacer(1, 1*cm))
        
        # Scores table
        scores_data = [
            ['평가 항목', '점수'],
            ['시장 점수', f'{market_score}/10'],
            ['종목 점수', f'{company_score}/10'],
            ['3개월 전망', f'{outlook_score}/10']
        ]
        
        scores_table = Table(scores_data, colWidths=[7*cm, 7*cm])
        scores_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('FONTNAME', (0, 0), (-1, 0), self.font_name_bold),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1e293b')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(scores_table)
        story.append(PageBreak())
        
        # ===== AGENT LOGS PAGES =====
        agents = self._extract_agent_logs(agent_logs)
        
        # Page 1: Market Data Analyst
        if agents['market']:
            story.append(Paragraph("Market Data Analyst", styles['SectionHeader']))
            story.append(Paragraph("시장 데이터 분석가", styles['AgentName']))
            story.append(Spacer(1, 0.5*cm))
            
            # Translate the market data analyst log to Korean
            original_text = agents['market'].get('output', '분석 로그가 없습니다.')
            translated_text = self._translate_text(original_text)
            log_text = self._clean_text(translated_text)
            
            story.append(Paragraph(log_text, styles['KoreanBody']))
            story.append(PageBreak())
        
        # Page 2: Market News Analyst
        if agents['news']:
            story.append(Paragraph("Market News Analyst", styles['SectionHeader']))
            story.append(Paragraph("시장 뉴스 분석가", styles['AgentName']))
            story.append(Spacer(1, 0.5*cm))
            
            # Translate the news analyst log to Korean
            original_text = agents['news'].get('output', '분석 로그가 없습니다.')
            translated_text = self._translate_text(original_text)
            log_text = self._clean_text(translated_text)
            
            story.append(Paragraph(log_text, styles['KoreanBody']))
            story.append(PageBreak())
        
        # Page 3: Trading Strategy Developer
        if agents['strategy']:
            story.append(Paragraph("Trading Strategy Developer", styles['SectionHeader']))
            story.append(Paragraph("트레이딩 전략 개발자", styles['AgentName']))
            story.append(Spacer(1, 0.5*cm))
            
            # Translate the strategy log to Korean
            original_text = agents['strategy'].get('output', '분석 로그가 없습니다.')
            translated_text = self._translate_text(original_text)
            log_text = self._clean_text(translated_text)
            
            story.append(Paragraph(log_text, styles['KoreanBody']))
            story.append(PageBreak())
        
        
        # Page 4: Risk & Investment Advisor
        if agents['risk']:
            story.append(Paragraph("Risk & Investment Advisor", styles['SectionHeader']))
            story.append(Paragraph("리스크 및 투자 자문가", styles['AgentName']))
            story.append(Spacer(1, 0.5*cm))
            
            # Translate the risk advisor log to Korean
            original_text = agents['risk'].get('output', '분석 로그가 없습니다.')
            translated_text = self._translate_text(original_text)
            log_text = self._clean_text(translated_text)
            
            story.append(Paragraph(log_text, styles['KoreanBody']))
            story.append(PageBreak())
        
        # ===== FINAL CONCLUSION PAGE =====
        story.append(Paragraph("최종 결론", styles['SectionHeader']))
        story.append(Spacer(1, 0.5*cm))
        
        # Summary
        if overall_comment.get('summary'):
            story.append(Paragraph("종합 요약", styles['AgentName']))
            summary_text = self._clean_text(overall_comment['summary'])
            story.append(Paragraph(summary_text, styles['KoreanBody']))
            story.append(Spacer(1, 0.3*cm))
        
        # Market Environment
        if overall_comment.get('market_env'):
            story.append(Paragraph("시장 환경", styles['AgentName']))
            market_text = self._clean_text(overall_comment['market_env'])
            story.append(Paragraph(market_text, styles['KoreanBody']))
            story.append(Spacer(1, 0.3*cm))
        
        # Company Summary
        if overall_comment.get('company_summary'):
            story.append(Paragraph("종목 분석", styles['AgentName']))
            company_text = self._clean_text(overall_comment['company_summary'])
            story.append(Paragraph(company_text, styles['KoreanBody']))
            story.append(Spacer(1, 0.3*cm))
        
        # 3-Month Outlook
        if overall_comment.get('outlook_3m'):
            story.append(Paragraph("3개월 전망 (단기)", styles['AgentName']))
            outlook_text = self._clean_text(overall_comment['outlook_3m'])
            story.append(Paragraph(outlook_text, styles['KoreanBody']))
            story.append(Spacer(1, 0.3*cm))
        
        # Long-term perspective (if available)
        if overall_comment.get('long_term'):
            story.append(Paragraph("장기 전망", styles['AgentName']))
            long_term_text = self._clean_text(overall_comment['long_term'])
            story.append(Paragraph(long_term_text, styles['KoreanBody']))
            story.append(Spacer(1, 0.3*cm))
        
        # Risks
        if overall_comment.get('risks'):
            story.append(Paragraph("주요 리스크", styles['AgentName']))
            risks_text = self._clean_text(overall_comment['risks'])
            story.append(Paragraph(risks_text, styles['KoreanBody']))
            story.append(Spacer(1, 0.3*cm))
        
        # Suggestion
        if overall_comment.get('suggestion'):
            story.append(Paragraph("투자 제안", styles['AgentName']))
            suggestion_text = self._clean_text(overall_comment['suggestion'])
            story.append(Paragraph(suggestion_text, styles['KoreanBody']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer
