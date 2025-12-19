# apps/aquatics/renderers.py
import random
import re
import logging
from django.conf import settings
from django.db.models import Q
from apps.aquatics.models import Aquarium, ContributionFish, Fishtank

logger = logging.getLogger(__name__)

# --- Utilities ---

FONT_FAMILY = 'Menlo'

def _strip_outer_svg(svg_text: str) -> str:
    """
    가장 바깥쪽 <svg> 태그를 제거하고 내부 요소만 반환합니다.
    """
    if not svg_text:
        return ""
    start = svg_text.find(">") + 1
    end = svg_text.rfind("</svg>")
    if start <= 0 or end == -1:
        return svg_text.strip()
    return svg_text[start:end].strip()


def _apply_sprite_id(svg_template: str, fish_id: int) -> str:
    """
    SVG 내부의 ID 중복을 방지하기 위해 *{id} 플레이스홀더를 치환합니다.
    """
    if not svg_template:
        return ""
    return svg_template.replace("*{id}", str(fish_id))


def _get_absolute_url(relative_path: str) -> str:
    """
    상대 경로(예: /media/bg.png)를 입력받아
    settings.SITE_DOMAIN을 결합한 절대 경로를 반환합니다.
    Github Readme 등 외부에서 이미지가 깨지지 않도록 하기 위함입니다.
    """
    if not relative_path:
        return ""
    if relative_path.startswith('http'):
        return relative_path
    
    # settings.py에 SITE_DOMAIN이 정의되어 있어야 함 (기본값 localhost)
    domain = getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000')
    
    # 경로가 /로 시작하지 않으면 붙여줌
    if not relative_path.startswith('/'):
        relative_path = f'/{relative_path}'
        
    return f"{domain}{relative_path}"

def _escape_text(s: str) -> str:
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

def _bg_url_from_ownbackground(own_bg) -> str:
    if not own_bg:
        return ""
    try:
        bg = getattr(own_bg, "background", None)
        if bg and getattr(bg, "background_image", None):
            return _get_absolute_url(bg.background_image.url)
    except Exception:
        pass
    return ""


def _parse_viewbox(svg_text: str):
    m = re.search(r'viewBox\s*=\s*"([^"]+)"', svg_text, re.I)
    if not m:
        return (0.0, 0.0, 50.0, 50.0)
    parts = [float(x) for x in m.group(1).split()]
    if len(parts) != 4:
        return (0.0, 0.0, 50.0, 50.0)
    return tuple(parts)  # minx, miny, w, h

def _find_anchor_xy(svg_text: str, anchor_id: str):
    """
    circle: cx/cy
    rect: x/y (+ width/height center)
    fallback: None
    """
    if not svg_text or not anchor_id:
        return None

    # id="...anchor_id..."
    # 1) circle
    m = re.search(
        rf'<circle[^>]*\bid\s*=\s*"{re.escape(anchor_id)}"[^>]*>',
        svg_text, re.I
    )
    if m:
        tag = m.group(0)
        cx = re.search(r'\bcx\s*=\s*"([^"]+)"', tag, re.I)
        cy = re.search(r'\bcy\s*=\s*"([^"]+)"', tag, re.I)
        if cx and cy:
            return (float(cx.group(1)), float(cy.group(1)))

    # 2) rect
    m = re.search(
        rf'<rect[^>]*\bid\s*=\s*"{re.escape(anchor_id)}"[^>]*>',
        svg_text, re.I
    )
    if m:
        tag = m.group(0)
        x = re.search(r'\bx\s*=\s*"([^"]+)"', tag, re.I)
        y = re.search(r'\by\s*=\s*"([^"]+)"', tag, re.I)
        w = re.search(r'\bwidth\s*=\s*"([^"]+)"', tag, re.I)
        h = re.search(r'\bheight\s*=\s*"([^"]+)"', tag, re.I)
        if x and y:
            xx = float(x.group(1))
            yy = float(y.group(1))
            if w and h:
                return (xx + float(w.group(1))/2.0, yy + float(h.group(1))/2.0)
            return (xx, yy)

    return None

# --- Sprite Renderer ---
def _clamp(v, a, b):
    return max(a, min(b, v))

def render_fish_group(cf, tank_w, tank_h, mode, persona_width_percent=4, padding=8):
    species = cf.fish_species
    fish_id = cf.id

    raw_svg = getattr(species, "svg_template", "") or ""
    templated_svg = _apply_sprite_id(raw_svg, fish_id)
    inner = _strip_outer_svg(templated_svg)

    # ---- label text ----
    if mode == "aquarium":
        top_label = _escape_text(getattr(cf.contributor.repository, "name", ""))
        bottom_label = _escape_text(f"{getattr(cf.contributor, 'commit_count', 0)} commits")
    else:
        top_label = _escape_text(getattr(cf.contributor.user, "username", ""))
        bottom_label = _escape_text(f"{getattr(cf.contributor, 'commit_count', 0)} commits")

    # ---- viewBox ----
    vb_minx, vb_miny, vb_w, vb_h = _parse_viewbox(templated_svg)

    # 프론트: baseW = tankW * (percent/100), spriteW = baseW*2
    baseW = tank_w * (persona_width_percent / 100.0)
    spriteW = baseW * 6.0
    scale = spriteW / max(1e-6, vb_w)
    spriteH = vb_h * scale

    # 탱크 안에서만 움직이도록 (패딩 + 스프라이트 크기 고려)
    minX = padding
    maxX = max(padding, tank_w - padding - spriteW)
    minY = padding
    maxY = max(padding, tank_h - padding - spriteH*(0.7))

    # ---- movement points (밖으로 안 나가게!) ----
    x0 = random.uniform(minX, maxX)
    y0 = random.uniform(minY, maxY)
    x1 = random.uniform(minX, maxX)
    y1 = random.uniform(minY, maxY)

    # 살짝만 위아래 흔들 (프론트처럼 과하지 않게)
    wiggle = min(spriteH * 0.10, 10.0)
    y0a = _clamp(y0 + random.uniform(-wiggle, wiggle), minY, maxY)
    y1a = _clamp(y1 + random.uniform(-wiggle, wiggle), minY, maxY)

    duration = random.uniform(10, 20)

    # ---- anchors in template coord -> pixel coord (프론트 로직 이식) ----
    top_anchor_id = f"{fish_id}-anchor-label-top"
    bottom_anchor_id = f"{fish_id}-anchor-label-bottom"
    center_anchor_id = f"{fish_id}-anchor-center"

    top_xy = (
        _find_anchor_xy(templated_svg, top_anchor_id)
        or _find_anchor_xy(templated_svg, center_anchor_id)
        or (vb_minx + vb_w / 2.0, vb_miny)
    )
    bot_xy = (
        _find_anchor_xy(templated_svg, bottom_anchor_id)
        or (vb_minx + vb_w / 2.0, vb_miny + vb_h)
    )

    # (ax-minX)*scale 로 픽셀화
    top_px = (top_xy[0] - vb_minx) * scale
    top_py = (top_xy[1] - vb_miny) * scale
    bot_px = (bot_xy[0] - vb_minx) * scale
    bot_py = (bot_xy[1] - vb_miny) * scale

    # ---- font size: 프론트 기반 (top 조금 더 큼/굵게) ----
    baseSize = max(10.0, baseW * 0.22)
    topFont = baseSize * 1.1
    botFont = baseSize * 0.85

    # ---- keyframes: p0 -> p1 -> p0 (linear 대신 ease-in-out는 유지 가능) ----
    move_kf = f"""
    @keyframes move-{fish_id} {{
      0%   {{ transform: translate({x0}px, {y0a}px); }}
      50%  {{ transform: translate({x1}px, {y1a}px); }}
      100% {{ transform: translate({x0}px, {y0a}px); }}
    }}
    """

    # flip은 50%에서 딱 반전만 (빙글빙글 X)
    flip_kf = f"""
    @keyframes flip-{fish_id} {{
      0%, 49.999% {{ transform: scale(1); }}
      50%, 100%   {{ transform: scaleX(-1); }}
    }}
    """

    return f"""
    <g id="fish-{fish_id}">
      <style>
        {move_kf}
        {flip_kf}

        /* 이동 담당 */
        #fish-{fish_id} .mover {{
          animation: move-{fish_id} {duration}s ease-in-out infinite;
          will-change: transform;
        }}

        /* 반전 담당: SVG에서는 transform-box/transform-origin이 중요 */
        #fish-{fish_id} .flipper {{
          animation: flip-{fish_id} {duration}s step-end infinite;
          transform-origin: center;
          transform-box: fill-box;
          will-change: transform;
        }}

        /* 라벨 */
        #fish-{fish_id} .label-top {{
          font-family: {FONT_FAMILY};
          font-size: {topFont}px;
          font-weight: 900;
          fill: #000;
          paint-order: none;
        }}
        #fish-{fish_id} .label-bottom {{
          font-family: {FONT_FAMILY};
          font-size: {botFont}px;
          font-weight: 900;
          fill: #000;
          paint-order: none;
        }}
      </style>

      <g class="mover">
        <!-- flipper 안에는 스프라이트만: 라벨은 절대 뒤집히지 않게 바깥 -->
        <g class="flipper">
          <!-- viewBox를 유지한 채 픽셀 스케일로 렌더 -->
          <g transform="scale({scale})">
            {inner}
          </g>
        </g>

        <!-- 라벨은 "스프라이트 픽셀 좌표"에 붙임 -->
        <text class="label-top"
              x="{top_px}"
              y="{top_py +64}"
              text-anchor="middle"
              dominant-baseline="ideographic">{top_label}</text>

        <text class="label-bottom"
              x="{bot_px}"
              y="{bot_py-46}"
              text-anchor="middle"
              dominant-baseline="hanging">{bottom_label}</text>
      </g>
    </g>
    """


# --- Main Renderers ---

def render_aquarium_svg(user, width=700, height=400):
    """
    유저의 개인 아쿠아리움 SVG 렌더링
    - user 기준으로 Aquarium을 추측하지 않음
    - ContributionFish에 실제로 연결된 aquarium을 기준으로 렌더
    """
    fishes = (
        ContributionFish.objects
        .filter(
            contributor__user=user,  
            is_visible_in_aquarium=True,
        )
        .select_related(
            "aquarium",
            "fish_species",
            "contributor__repository",
            "contributor__user",
        )
    )

    if not fishes.exists():
        logger.warning(f"[render_aquarium_svg] user={user.id} has no visible fish")
        # 그래도 SVG는 반환
        return f"""
        <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
            <rect width="100%" height="100%" fill="#001a33"/>
            <text x="20" y="40" fill="#aaa">No fish in aquarium</text>
        </svg>
        """

    aquarium, _ = Aquarium.objects.get_or_create(user=user)

    logger.warning(
        f"[render_aquarium_svg] user={user.id} aquarium_id={aquarium.id} fish_count={fishes.count()}"
    )

    bg_url = ""
    if (
        aquarium.background
        and aquarium.background.background
        and aquarium.background.background.background_image
    ):
        bg_url = _get_absolute_url(
            aquarium.background.background.background_image.url
        )

    fish_groups = [
        render_fish_group(
            cf,
            tank_w=width,
            tank_h=height,
            mode="aquarium",
            persona_width_percent=4,  # 프론트 기본값 맞춤
            padding=8,               # 프론트 기본값 맞춤
        )
        for cf in fishes
    ]

    return f"""
    <svg xmlns="http://www.w3.org/2000/svg"
         width="{width}"
         height="{height}"
         viewBox="0 0 {width} {height}">
        <defs>
            <clipPath id="tank-clip">
                <rect width="{width}" height="{height}" rx="20" ry="20"/>
            </clipPath>
        </defs>

        <rect width="{width}" height="{height}" fill="#b8e6fe" rx="20" ry="20"/>

        <g clip-path="url(#tank-clip)">
            {f'<image href="{bg_url}" width="{width}" height="{height}" preserveAspectRatio="xMidYMid slice" />' if bg_url else ''}
            <g id="fish-container">
                {''.join(fish_groups)}
            </g>
        </g>
    </svg>
    """

def render_fishtank_svg(repository, user, width=700, height=400):
    """
    레포지토리 공용 피시탱크를 특정 유저의 배경 설정에 맞춰 렌더링합니다.
    """
    try:
        # 해당 유저의 피시탱크 설정 조회
        fishtank = Fishtank.objects.select_related('background__background').get(
            repository=repository, 
            user=user
        )
        bg_url = ""
        if fishtank.background and fishtank.background.background.background_image:
            raw_url = fishtank.background.background.background_image.url
            bg_url = _get_absolute_url(raw_url)

    except Fishtank.DoesNotExist:
        bg_url = ""

    # 물고기들은 해당 레포지토리의 모든 기여자들 것을 가져옴
    fishes = ContributionFish.objects.filter(
        contributor__repository=repository,
        is_visible_in_fishtank=True
    ).select_related("fish_species", "contributor__user")

    fish_groups = [
        render_fish_group(
            cf,
            tank_w=width,
            tank_h=height,
            mode="fishtank",
            persona_width_percent=4,  # 프론트 기본값 맞춤
            padding=8,               # 프론트 기본값 맞춤
        )
        for cf in fishes
    ]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
        <rect width="{width}" height="{height}" fill="#b8e6fe" rx="15" ry="15" />
        {f'<image href="{bg_url}" width="{width}" height="{height}" preserveAspectRatio="xMidYMid slice" />' if bg_url else ''}
        <g id="fish-container">
            {''.join(fish_groups)}
        </g>
    </svg>"""



