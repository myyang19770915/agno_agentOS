from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

try:
    os.makedirs('downloads', exist_ok=True)

    # Canvas settings (A4 at 300 DPI)
    W, H = 2480, 3508
    bg_color = (250, 247, 243)  # warm off-white
    img = Image.new('RGB', (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # Load fonts
    try:
        font_sans = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 36)
        font_sans_thin = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
        font_serif_bold = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf', 64)
    except Exception as e:
        print('Font load error:', e)
        font_sans = ImageFont.load_default()
        font_sans_thin = ImageFont.load_default()
        font_serif_bold = ImageFont.load_default()

    # Draw a subtle grid of nodes (suggesting an agent network) as repeated marks
    margin_x = int(W * 0.12)
    margin_y = int(H * 0.12)
    cols = 6
    rows = 9
    cell_w = (W - margin_x * 2) // (cols - 1)
    cell_h = (H - margin_y * 2) // (rows - 1)

    # Draw connecting lines and circles with careful spacing
    for r in range(rows):
        for c in range(cols):
            x = margin_x + c * cell_w
            y = margin_y + r * cell_h
            # offset for organic feel
            xo = int(((c - cols/2) * 0.8) + (r % 2) * 6)
            yo = int(((r - rows/2) * 0.6))
            cx = x + xo
            cy = y + yo
            # circle shadow
            shadow_color = (230, 227, 223)
            draw.ellipse((cx-26, cy-26, cx+26, cy+26), fill=shadow_color)
            # core dot
            core_color = (31, 47, 76) if (r+c) % 3 == 0 else (14, 107, 150)
            draw.ellipse((cx-12, cy-12, cx+12, cy+12), fill=core_color)

    # Draw a large geometric form (anchoring mass) - a softened rectangle with mask
    anchor = Image.new('RGBA', (W, H), (0,0,0,0))
    ad = ImageDraw.Draw(anchor)
    rect_w = int(W * 0.58)
    rect_h = int(H * 0.28)
    rect_x = int(W * 0.19)
    rect_y = int(H * 0.18)
    # rounded rect via ellipse corners
    radius = 48
    ad.rounded_rectangle((rect_x, rect_y, rect_x+rect_w, rect_y+rect_h), radius=radius, fill=(20,30,55,230))
    # translucent overlay
    anchor = anchor.filter(ImageFilter.GaussianBlur(0.6))
    img.paste(anchor, (0,0), anchor)

    # Add layered thin stripes across anchor (signal-like)
    stripe = Image.new('RGBA', (rect_w, rect_h), (0,0,0,0))
    sd = ImageDraw.Draw(stripe)
    for i in range(0, rect_h, 18):
        alpha = 26 if (i//18) % 4 in (0,1) else 14
        sd.rectangle((0, i, rect_w, i+6), fill=(255,255,255,alpha))
    img.paste(stripe, (rect_x, rect_y), stripe)

    # Add subtle diagonal guide lines for rhythm
    for i in range(-6, 10):
        x1 = int(W * -0.05 + i * 220)
        y1 = 0
        x2 = x1 + 120
        y2 = H
        draw.line((x1, y1, x2, y2), fill=(240,238,236), width=2)

    # Small typographic anchors - minimal
    title_text = 'AGNO'
    subtitle = 'agent • artifact'
    # place title in bottom-left, small and restrained
    tx = int(W * 0.12)
    ty = int(H * 0.86)
    draw.text((tx, ty), title_text, font=font_serif_bold, fill=(14,107,150))
    draw.text((tx, ty+84), subtitle, font=font_sans_thin, fill=(95,90,86))

    # Add a tiny caption top-right (discreet label)
    cap = 'prototype study — meticulously crafted'
    w_cap, h_cap = draw.textsize(cap, font=font_sans_thin)
    draw.text((W - int(W*0.12) - w_cap, int(H*0.08)), cap, font=font_sans_thin, fill=(95,90,86))

    # Final micro-detail: a small matrix of dots near anchor to suggest data
    md_x = rect_x + rect_w - 220
    md_y = rect_y + rect_h - 160
    for rr in range(6):
        for cc in range(10):
            dotx = md_x + cc * 14
            doty = md_y + rr * 14
            color = (200,200,200) if (rr+cc)%3==0 else (180,180,180)
            draw.ellipse((dotx-3,doty-3,dotx+3,doty+3), fill=color)

    # Save as high-quality PDF
    out_pdf = 'downloads/agno_agent_poster.pdf'
    img.save(out_pdf, 'PDF', resolution=300)

    # Create design philosophy markdown
    philosophy_md = """# Movement: Algorithmic Relics

Algorithmic Relics treats composition as the archive of process. It believes that form, in its patient repetitions and structural echoes, holds memory — not in literal narrative but through the accumulated pattern of decisions. Space is not an absence but an inscription: margins, gestures, and measured pauses become the language by which the piece speaks. The visual intent is to make the viewer feel they are reading a ledger of choices performed with the slow certainty of a master craftsman.

Color and material are instruments of clarity: a reduced, carefully chosen palette that conveys weight and cadence. Hues act as operators, not decorations; each tint, tone, and contrast is the result of painstaking calibration. The final artifact should read as if every hue were adjusted in a controlled studio light, the product of deep expertise and meticulous testing. This work is the product of deep expertise, painstaking attention, and master-level execution.

Form and rhythm embrace iterative logic: repeated marks, measured nodes, and structural anchors that suggest systems rather than narratives. Composition favors large, deliberate gestures balanced by quiet microstructures — small dots, thin lines, and restrained typographic accents. Negative space is used as a precise instrument; the silence around objects is as meaningful as the objects themselves. Every alignment and proportion must feel like the result of countless refinements.

Typographic elements are minimal and integrated: words serve as punctuations or field labels, never explanations. Text whispers context, it does not narrate; it is calibrated with the same care as any shape or color. The design must feel meticulously crafted — the product of patient labor and master-level execution — so that viewers sense not only aesthetic intent but the hand of an expert who labored over every decision.

The movement leaves interpretive room: abstract yet deliberate, it invites viewers to discover latent references through proximity and repetition. The work should feel like an artifact from an imaginary discipline — clinical in clarity, human in its fineness — an object that rewards sustained attention and reveals its depth only to those willing to look closely.
"""
    md_path = 'downloads/design_philosophy_algorithmic_relics.md'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(philosophy_md)

    print('Created files:')
    print(out_pdf)
    print(md_path)

except Exception as e:
    print('Error during creation:', e)

print('Done')