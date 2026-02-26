try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    import os

    os.makedirs('downloads', exist_ok=True)

    # Design philosophy markdown
    md_path = os.path.join('downloads', 'design_philosophy_agno_agent.md')
    md_content = '''# 設計理念：有序沉思 (Ordered Contemplation)

有序沉思是一種將理性系統化與感性直觀結合的視覺哲學。它偏好以精密的幾何、節奏性的重複與精確的留白來表達一個內在微小但重要的概念：在複雜系統中，一個細微的代理（agent）既可成為秩序的起點，也可能引發意想不到的關聯。作品呈現為嚴謹的構圖與柔和的意象之間的對話，讓觀者在視覺上感受探索與發現的過程。

空間與形態在此哲學中扮演語言的角色：矩形、弧形與軸線被當作信息載體，而非單純的裝飾。每一個形狀的尺寸、邊距與位置都經過精算，形成一種可讀的秩序。色塊之間的負空間像句點一樣，指示節奏與停頓。最終的畫面應呈現出工藝感——彷彿是經過無數次調整、仔細推敲而成：meticulously crafted、painstaking attention、master-level execution。

色彩與材質被精簡為有限的調色盤：以中性灰、冷金屬色與一到兩種強勢色作為視覺錨點。強勢色像是信號，悄然提示觀者去關注畫面中那個「代理」的存在。這些色彩的相互作用是有意義的編碼，而非僅僅情緒化的選擇。整體觸感應該像手工上色般的細緻，呈現出匠人般的深厚功力。

構圖的節奏與比例追求嚴格的平衡：大面積的緩慢呼吸與小而精準的節點交錯。文字極度精簡，僅作為視覺標記或標籤，從不解釋或冗述。視覺分層與節奏必須顯示時間與專注的痕跡——每一筆都像是長時間思考的結晶。作品應被感受為一件經由反覆琢磨而誕生的藝術品，令人產生一種被深厚專業功力所支撐的信任感。

在實作上，保留足夠的自由讓執行者以極高水準的工藝去詮釋本哲學：嚴謹，但有彈性；簡潔，但富含內涵。設計不在於說明，而在於讓形式自身陳述。最終的作品應像是一張由頂尖工匠耗費無數小時而打造的藝術品——每一處間距、每一種顏色的濃淡、每一處端點都彰顯出master-level execution與painstaking attention。'''

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    # Create PDF canvas
    pdf_path = os.path.join('downloads', 'agno_agent_artwork.pdf')
    c = canvas.Canvas(pdf_path, pagesize=A4)
    W, H = A4

    # Background
    c.setFillColor(colors.HexColor('#f6f6f8'))
    c.rect(0, 0, W, H, stroke=0, fill=1)

    # Large structural block (left)
    margin = 24 * mm
    c.setFillColor(colors.HexColor('#e6e9ee'))
    c.roundRect(margin, H*0.15, W*0.48, H*0.7, 8*mm, stroke=0, fill=1)

    # Thin vertical axis
    c.setStrokeColor(colors.HexColor('#cfd6dd'))
    c.setLineWidth(2)
    c.line(W*0.55, H*0.12, W*0.55, H*0.88)

    # Small signal circles representing 'agents'
    c.setFillColor(colors.HexColor('#2b6f9e'))
    for i, y in enumerate([0.78, 0.62, 0.48, 0.34]):
        c.circle(W*0.55, H*y, (6 - i) * mm, stroke=0, fill=1)

    # Subtle grid of dots (systematic observation feel)
    c.setFillColor(colors.HexColor('#d7dbe1'))
    dot_x_start = W*0.12
    dot_x_end = W*0.88
    dot_y_start = H*0.2
    dot_y_end = H*0.8
    cols = 12
    rows = 6
    for i in range(cols):
        for j in range(rows):
            x = dot_x_start + (dot_x_end - dot_x_start) * i / (cols-1)
            y = dot_y_start + (dot_y_end - dot_y_start) * j / (rows-1)
            c.circle(x, y, 0.9*mm, stroke=0, fill=1)

    # Accent rectangle (right top)
    c.setFillColor(colors.HexColor('#ffd7a6'))
    c.rect(W*0.68, H*0.65, W*0.18, H*0.18, stroke=0, fill=1)

    # Fine typographic labels (minimal)
    c.setFillColor(colors.HexColor('#222222'))
    c.setFont('Helvetica', 10)
    c.drawString(margin + 6*mm, H*0.12, 'AGNO • agent')
    c.setFont('Helvetica', 6)
    c.setFillColor(colors.HexColor('#555555'))
    c.drawString(margin + 6*mm, H*0.10, 'Ordered Contemplation — meticulously crafted')

    c.showPage()
    c.save()

    print(f"Success: Created files:\n - {md_path}\n - {pdf_path}")
except Exception as e:
    print(f"Error: {e}")