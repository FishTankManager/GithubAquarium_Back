# apps/aquatics/renderers.py
import random
import re
import logging
from django.conf import settings
from apps.aquatics.models import Aquarium, ContributionFish, Fishtank

logger = logging.getLogger(__name__)

# --- Utilities ---

def _extract_svg_size(svg_text: str):
    """
    SVG 템플릿에서 width, height를 추출하거나 기본값(512)을 반환합니다.
    """
    if not svg_text:
        return (512, 512)

    width_match = re.search(r'width="([\d\.]+)"', svg_text)
    height_match = re.search(r'height="([\d\.]+)"', svg_text)

    if width_match and height_match:
        return (float(width_match.group(1)), float(height_match.group(1)))

    viewbox_match = re.search(r'viewBox="[^"]*?(\d+\.?\d*)\s+(\d+\.?\d*)"', svg_text)
    if viewbox_match:
        return (float(viewbox_match.group(1)), float(viewbox_match.group(2)))

    return (512, 512)


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


# --- Sprite Renderer ---

def render_fish_group(cf, width, height, mode):
    """
    개별 물고기와 그에 따른 CSS 애니메이션을 생성합니다.
    """
    species = cf.fish_species
    fish_id = cf.id
    raw_svg = species.svg_template
    templated_svg = _apply_sprite_id(raw_svg, fish_id)
    inner = _strip_outer_svg(templated_svg)

    # 레이블 텍스트 결정
    if mode == "aquarium":
        # 개인 아쿠아리움에서는 출처 레포지토리 이름 표시
        label_text = cf.contributor.repository.name
    else:
        # 레포 피시탱크에서는 기여자 유저네임 표시
        label_text = cf.contributor.user.username

    # 랜덤 이동 변수
    start_x = random.uniform(width * 0.1, width * 0.8)
    start_y = random.uniform(height * 0.2, height * 0.7)
    amplitude_x = random.uniform(width * 0.2, width * 0.4)
    amplitude_y = random.uniform(height * 0.05, height * 0.1)
    duration = random.uniform(10, 20)

    # 이동 애니메이션 (50% 시점에서 방향 전환 scale(-1, 1))
    keyframes = f"""
    @keyframes move-{fish_id} {{
        0% {{ transform: translate({start_x}px, {start_y}px); }}
        25% {{ transform: translate({start_x + amplitude_x}px, {start_y + amplitude_y}px); }}
        50% {{ transform: translate({start_x}px, {start_y - amplitude_y}px) scale(-1, 1); }}
        75% {{ transform: translate({start_x - amplitude_x}px, {start_y + amplitude_y}px) scale(-1, 1); }}
        100% {{ transform: translate({start_x}px, {start_y}px); }}
    }}
    """

    # 라벨 역회전 애니메이션 (물고기가 뒤집힐 때 글자는 정방향 유지)
    reverse_keyframes = f"""
    @keyframes keep-label-upright-{fish_id} {{
        0%, 25%, 100% {{ transform: scale(1, 1); }}
        50%, 75% {{ transform: scale(-1, 1); }}
    }}
    """

    return f"""
    <g id="fish-{fish_id}">
        <style>
            {keyframes}
            {reverse_keyframes}
            #fish-{fish_id} .motion {{
                animation: move-{fish_id} {duration}s ease-in-out infinite;
                transform-origin: center;
            }}
            #fish-{fish_id} .label {{
                animation: keep-label-upright-{fish_id} {duration}s ease-in-out infinite;
                transform-origin: center;
            }}
            #fish-{fish_id} .label text {{
                font-family: sans-serif;
                font-size: 11px;
                fill: white;
                paint-order: stroke;
                stroke: rgba(0, 0, 0, 0.8);
                stroke-width: 2px;
            }}
            #fish-{fish_id} .label rect {{
                fill: rgba(0, 0, 0, 0.4);
                rx: 4px;
            }}
        </style>

        <g class="motion">
            <g class="sprite">
                {inner}
            </g>
            <g class="label" transform="translate(0, 30)">
                <rect x="-35" y="-12" width="70" height="16" />
                <text text-anchor="middle" dominant-baseline="central">{label_text}</text>
            </g>
        </g>
    </g>
    """


# --- Main Renderers ---

def render_aquarium_svg(user, width=512, height=512):
    """
    유저의 개인 아쿠아리움 전체를 SVG로 렌더링합니다.
    """
    try:
        aquarium = Aquarium.objects.select_related('background__background').get(user=user)
    except Aquarium.DoesNotExist:
        return ""

    bg_url = ""
    if aquarium.background and aquarium.background.background.background_image:
        raw_url = aquarium.background.background.background_image.url
        bg_url = _get_absolute_url(raw_url)

    fishes = ContributionFish.objects.filter(
        aquarium=aquarium,
        is_visible_in_aquarium=True
    ).select_related("fish_species", "contributor__repository")

    fish_groups = [render_fish_group(cf, width, height, mode="aquarium") for cf in fishes]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
        <defs>
            <clipPath id="tank-clip">
                <rect width="{width}" height="{height}" rx="20" ry="20" />
            </clipPath>
        </defs>
        <rect width="{width}" height="{height}" fill="#001a33" rx="20" ry="20" />
        <g clip-path="url(#tank-clip)">
            {f'<image href="{bg_url}" width="{width}" height="{height}" preserveAspectRatio="xMidYMid slice" />' if bg_url else ''}
            <g id="fish-container">
                {''.join(fish_groups)}
            </g>
        </g>
    </svg>"""


def render_fishtank_svg(repository, user, width=512, height=512):
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

    fish_groups = [render_fish_group(cf, width, height, mode="fishtank") for cf in fishes]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
        <rect width="{width}" height="{height}" fill="#050505" rx="15" ry="15" />
        {f'<image href="{bg_url}" width="{width}" height="{height}" preserveAspectRatio="xMidYMid slice" />' if bg_url else ''}
        <g id="fish-container">
            {''.join(fish_groups)}
        </g>
    </svg>"""