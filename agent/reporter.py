import json
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'usage_log.json')
REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'reports')

DARK_BG   = colors.HexColor('#0F172A')
PRIMARY   = colors.HexColor('#6366F1')
SUCCESS   = colors.HexColor('#10B981')
WARNING   = colors.HexColor('#F59E0B')
DANGER    = colors.HexColor('#EF4444')
TEXT      = colors.HexColor('#1E293B')
MUTED     = colors.HexColor('#64748B')

def generate_daily_report():
    return _generate_report('daily')

def generate_weekly_report():
    return _generate_report('weekly')

def _generate_report(period='daily'):
    os.makedirs(REPORTS_DIR, exist_ok=True)

    if not os.path.exists(LOG_PATH):
        return {"error": "No usage data found"}

    try:
        with open(LOG_PATH) as f:
            data = json.load(f)
    except Exception:
        return {"error": "Failed to load usage data"}

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'DigiWell_{period.capitalize()}_Report_{timestamp}.pdf'
    filepath = os.path.join(REPORTS_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                             rightMargin=0.75*inch, leftMargin=0.75*inch,
                             topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story  = []

    # Title style
    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                  fontSize=28, textColor=PRIMARY,
                                  spaceAfter=6, fontName='Helvetica-Bold')
    sub_style   = ParagraphStyle('Sub', parent=styles['Normal'],
                                  fontSize=12, textColor=MUTED, spaceAfter=20)
    h2_style    = ParagraphStyle('H2', parent=styles['Heading2'],
                                  fontSize=16, textColor=TEXT,
                                  fontName='Helvetica-Bold', spaceAfter=8)
    body_style  = ParagraphStyle('Body', parent=styles['Normal'],
                                  fontSize=11, textColor=TEXT, leading=16)

    # Header
    story.append(Paragraph('🧠 DigiWell', title_style))
    story.append(Paragraph(f'{period.capitalize()} Screen Time Report — {datetime.now().strftime("%B %d, %Y")}', sub_style))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))
    story.append(Spacer(1, 20))

    # Summary stats
    apps = data.get('apps', {})
    total_mins = data.get('total_seconds', 0) // 60
    total_hrs  = total_mins / 60
    top_app    = max(apps, key=lambda k: apps[k]['seconds'], default='N/A') if apps else 'N/A'
    high_risk_apps = [a for a, v in apps.items() if v.get('risk') == 'high']

    story.append(Paragraph('Summary', h2_style))
    summary_data = [
        ['Metric', 'Value', 'Status'],
        ['Total Screen Time', f'{total_hrs:.1f} hours ({total_mins} mins)',
         '✅ Healthy' if total_hrs < 4 else '⚠️ Moderate' if total_hrs < 7 else '🔴 Excessive'],
        ['Most Used App', top_app, f'{apps[top_app]["seconds"]//60} mins' if top_app != 'N/A' else '-'],
        ['High Risk Apps Used', str(len(high_risk_apps)), ', '.join(high_risk_apps[:3]) or 'None'],
        ['Total Apps Tracked', str(len(apps)), '-'],
        ['Report Date', data.get('date', 'N/A'), '-'],
    ]
    summary_table = Table(summary_data, colWidths=[2.2*inch, 2.5*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 10),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING',    (0,0), (-1,-1), 8),
        ('ALIGN',      (0,0), (-1,-1), 'LEFT'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 24))

    # App breakdown table
    story.append(Paragraph('App Usage Breakdown', h2_style))
    sorted_apps = sorted(apps.items(), key=lambda x: x[1]['seconds'], reverse=True)
    app_data = [['App', 'Category', 'Time Spent', 'Risk Level']]
    for app_name, info in sorted_apps[:15]:
        mins = info['seconds'] // 60
        risk = info.get('risk', 'medium')
        risk_label = '🔴 High' if risk == 'high' else '🟡 Medium' if risk == 'medium' else '🟢 Low'
        app_data.append([app_name, info.get('category','Other'), f'{mins} mins', risk_label])

    if len(app_data) > 1:
        app_table = Table(app_data, colWidths=[2.2*inch, 1.5*inch, 1.3*inch, 1.7*inch])
        app_table.setStyle(TableStyle([
            ('BACKGROUND',  (0,0), (-1,0), PRIMARY),
            ('TEXTCOLOR',   (0,0), (-1,0), colors.white),
            ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0,0), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('GRID',        (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING',     (0,0), (-1,-1), 7),
        ]))
        story.append(app_table)
    else:
        story.append(Paragraph('No app usage recorded yet.', body_style))
    story.append(Spacer(1, 24))

    # Wellness score
    story.append(Paragraph('Wellness Assessment', h2_style))
    score = max(0, min(100, int(100 - (total_hrs / 12 * 100))))
    color = '🟢 Good' if score > 70 else '🟡 Moderate' if score > 40 else '🔴 Poor'
    story.append(Paragraph(f'Your Digital Wellness Score: <b>{score}/100</b> — {color}', body_style))
    story.append(Spacer(1, 10))

    # Recommendations
    story.append(Paragraph('Personalized Recommendations', h2_style))
    recs = []
    if total_hrs > 6:
        recs.append('• Reduce total screen time — aim for under 4 hours daily')
    if any(a in apps for a in ['Discord','Steam','Spotify']):
        recs.append('• Set time limits on high-risk entertainment apps')
    if not recs:
        recs.append('• Great habits! Maintain your current screen time balance')
    recs.append('• Use DigiWell Focus Mode during study/work sessions')
    recs.append('• Apply the 20-20-20 rule: every 20 mins, look 20 feet away for 20 seconds')
    for rec in recs:
        story.append(Paragraph(rec, body_style))
    story.append(Spacer(1, 8))

    # Footer
    story.append(HRFlowable(width='100%', thickness=0.5, color=MUTED))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f'Generated by DigiWell on {datetime.now().strftime("%Y-%m-%d %H:%M")}', sub_style))

    doc.build(story)
    return {"status": "success", "filepath": filepath, "filename": filename}
