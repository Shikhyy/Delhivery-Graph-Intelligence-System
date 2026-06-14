from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

prs = Presentation()

def set_dark_bg(slide):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(30, 30, 35) # Slightly lighter dark for more premium feel
    
    # Add a top red accent bar
    top_bar = slide.shapes.add_shape(
        1, 0, 0, Inches(10), Inches(0.15) # 1 is MSO_SHAPE.RECTANGLE
    )
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = RGBColor(255, 75, 75)
    top_bar.line.fill.background()

# 1. Title Slide
slide = prs.slides.add_slide(prs.slide_layouts[0])
set_dark_bg(slide)
title = slide.shapes.title
subtitle = slide.placeholders[1]
title.text = "Delhivery Graph Intelligence"
title.text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 75, 75)
title.text_frame.paragraphs[0].font.bold = True
title.text_frame.paragraphs[0].font.size = Pt(44)
subtitle.text = "Predicting Delays & Identifying Structural Bottlenecks\n\nPrepared by Shikhar Verma"
subtitle.text_frame.paragraphs[0].font.color.rgb = RGBColor(230, 230, 230)
subtitle.text_frame.paragraphs[0].font.size = Pt(24)

def add_title(slide, text):
    title = slide.shapes.title
    title.text = text
    title.text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 75, 75)
    title.text_frame.paragraphs[0].font.bold = True
    title.text_frame.paragraphs[0].font.size = Pt(36)

def style_content(content):
    for p in content.text_frame.paragraphs:
        p.font.color.rgb = RGBColor(230, 230, 230)
        p.font.size = Pt(22)
        p.space_after = Pt(14)

# 2. The Problem
slide = prs.slides.add_slide(prs.slide_layouts[1])
set_dark_bg(slide)
add_title(slide, "The Strategic Challenge")
content = slide.placeholders[1]
content.text = ("• Delhivery uses OSRM (shortest path) to estimate delivery times.\n"
               "• Real-world logistics is messy: dwell times, congestion, and operational constraints cause deviations.\n\n"
               "The Result:\n"
               "A 95%+ SLA Breach Rate on chronic routes, breaking downstream capacity planning.")
style_content(content)

# 3. The Solution
slide = prs.slides.add_slide(prs.slide_layouts[1])
set_dark_bg(slide)
add_title(slide, "Our Graph-Based Solution")
content = slide.placeholders[1]
content.text = ("We modeled the logistics network not as isolated trips, but as a living Directed Graph to find structural flaws.\n\n"
               "Network Scale:\n"
               "• 1,657 Connected Facilities (Nodes)\n"
               "• 2,783 Logistics Corridors (Edges)\n"
               "• 2,617 Chronic Delay Corridors Identified")
style_content(content)

# 4. Network Map
slide = prs.slides.add_slide(prs.slide_layouts[5])
set_dark_bg(slide)
add_title(slide, "Mapping the Bottlenecks")
img_path = "outputs/figures/network_bottleneck.png"
slide.shapes.add_picture(img_path, Inches(1.5), Inches(1.5), height=Inches(5.5))

# 5. Top 5 Hubs
slide = prs.slides.add_slide(prs.slide_layouts[5])
set_dark_bg(slide)
add_title(slide, "The Top 5 Critical Hubs")
img_path = "outputs/figures/top_hubs.png"
slide.shapes.add_picture(img_path, Inches(0.5), Inches(2.0), width=Inches(9))

# 6. ML ETA Models
slide = prs.slides.add_slide(prs.slide_layouts[5])
set_dark_bg(slide)
add_title(slide, "Smarter ETAs via Node2Vec")
img_path = "outputs/figures/model_comparison.png"
slide.shapes.add_picture(img_path, Inches(0.5), Inches(1.5), width=Inches(9))
txBox = slide.shapes.add_textbox(Inches(1), Inches(6.3), Inches(8), Inches(1))
p = txBox.text_frame.paragraphs[0]
p.text = "Result: +8.57% improvement in 15%-Accuracy over OSRM Baseline"
p.font.color.rgb = RGBColor(76, 175, 80)
p.font.bold = True
p.font.size = Pt(22)
p.alignment = PP_ALIGN.CENTER

# 7. FTL Optimization
slide = prs.slides.add_slide(prs.slide_layouts[5])
set_dark_bg(slide)
add_title(slide, "FTL vs Carting Framework")
img_path = "outputs/figures/ftl_decision_boundary.png"
slide.shapes.add_picture(img_path, Inches(1.5), Inches(1.5), height=Inches(5.5))

# 8. Business Value
slide = prs.slides.add_slide(prs.slide_layouts[1])
set_dark_bg(slide)
add_title(slide, "Strategic Recommendations")
content = slide.placeholders[1]
content.text = ("• Infrastructure Interventions: Upgrade capacity at Gurgaon Bilaspur HB and Bangalore Nelmngla. These are single points of failure causing massive ripple effects.\n"
               "• Financial Impact: Upgrading the top 3 bottleneck hubs to the network median delay recovers an estimated ₹1.05 Crore in revenue at risk.\n"
               "• Product Deployment: Integrate the Graph-Enhanced XGBoost model into the customer-facing tracking app to drastically improve consumer transparency.")
style_content(content)

# 9. Thank You
slide = prs.slides.add_slide(prs.slide_layouts[0])
set_dark_bg(slide)
title = slide.shapes.title
title.text = "Thank You"
title.text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 75, 75)
title.text_frame.paragraphs[0].font.size = Pt(54)
subtitle = slide.placeholders[1]
subtitle.text = "Explore the Live Dashboard:\ndelhivery-graph-intelligence-system.streamlit.app"
subtitle.text_frame.paragraphs[0].font.color.rgb = RGBColor(230, 230, 230)
subtitle.text_frame.paragraphs[0].font.size = Pt(24)

prs.save("Pitch_Deck.pptx")
print("Presentation saved as Pitch_Deck.pptx")
