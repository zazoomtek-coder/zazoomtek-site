#!/usr/bin/env python3
"""Generate two factual 1200x675 sharing previews, changing only HTML heads."""
from pathlib import Path
from html import escape
from io import BytesIO
import re
import json
from PIL import Image, ImageDraw, ImageFont, ImageOps

ORIGIN="https://zazoomtek.it"
SIZE=(1200,675)
PAGES={
  "guida-come-usare-playstation-2-tv-4k-moderna.html":("guida-ps2-cover-discover.webp","Come collegare PlayStation 2 a una TV 4K","guide"),
  "news-UgkxRIkkCOSKmYs0Irjj3gONuRScFsor9-qu.html":("gt6-community-cover-discover.webp","Avete già prenotato GT6?","community")
}
def font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"):
        if Path(path).exists(): return ImageFont.truetype(path,size)
    return ImageFont.load_default()

def graphic(root, name, title, kind):
    image=Image.new("RGB",SIZE,(21,25,36))
    draw=ImageDraw.Draw(image)
    for y in range(675):
        mix=y/675
        draw.line((0,y,1200,y),fill=(round(19+20*mix),round(24+7*mix),round(37+17*mix)))
    draw.rectangle((0,0,18,675),fill=(218,26,58))
    if kind=="guide":
        photo=root/"assets/special/guida-ps2-console-blu.webp"
        if not photo.is_file(): raise RuntimeError("Original PS2 artwork missing")
        with Image.open(photo) as original:
            visual=ImageOps.fit(original.convert("RGB"),(800,450),method=Image.Resampling.LANCZOS)
            image.paste(visual,(345,115))
        draw.rectangle((46,464,1160,625),fill=(15,20,31))
        draw.text((65,480),"PLAYSTATION 2 SU TV 4K",font=font(48),fill="white")
        draw.text((65,552),"GUIDA ZAZOOMTEK",font=font(30),fill=(255,105,121))
    else:
        draw.rounded_rectangle((55,105,1140,558),radius=25,outline=(112,133,160),width=3)
        draw.text((88,150),"COMMUNITY ZAZOOMTEK",font=font(43),fill=(255,105,121))
        draw.text((88,276),"AVETE GIA PRENOTATO",font=font(57),fill="white")
        draw.text((88,365),"GT6?",font=font(90),fill="white")
    output=root/"assets"/"discover"/name
    output.parent.mkdir(parents=True,exist_ok=True)
    image.save(output,format="WEBP",quality=88,method=6)
    with Image.open(output) as check:
        assert check.size==SIZE
    return ORIGIN+"/assets/discover/"+name

def inject(page,url):
    source=page.read_text(encoding="utf-8")
    m=re.search(r"</head\s*>",source,re.I)
    if not m: raise RuntimeError("Missing closing head: "+page.name)
    head,tail=source[:m.start()],source[m.start():]
    canonical=f'<link rel="canonical" href="{ORIGIN}/{page.name}">'
    if canonical not in head: raise RuntimeError("Canonical mismatch: "+page.name)
    old=re.findall(r'<meta\b[^>]*property=["\\\']og:image["\\\'][^>]*>',head,re.I)
    new=f'<meta property="og:image" content="{escape(url,quote=True)}">'
    if len(old)>1: raise RuntimeError("Multiple OG images: "+page.name)
    if old: head=head.replace(old[0],new,1)
    else: head=head+"\n"+new
    if "twitter:image" not in head:
        head=head+'\n<meta name="twitter:image" content="'+escape(url,quote=True)+'">'
    else:
        head=re.sub(r'<meta\b[^>]*name=["\\\']twitter:image["\\\'][^>]*>',
                    '<meta name="twitter:image" content="'+escape(url,quote=True)+'">',head,count=1,flags=re.I)
    # Preserve all rendered article markup and original images.
    revised=head+tail
    assert revised.endswith(tail)
    if source!=revised: page.write_text(revised,encoding="utf-8")

def main():
    root=Path(".").resolve()
    for filename,(name,title,kind) in PAGES.items():
        image=graphic(root,name,title,kind)
        inject(root/filename,image)
        print("Discover preview verified:",filename,image,SIZE)

if __name__=="__main__":main()
