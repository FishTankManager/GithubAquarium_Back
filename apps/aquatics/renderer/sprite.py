# apps/aquatics/renderer/sprite.py
import random
from .utils import strip_outer_svg

def apply_sprite_id(svg_template: str, fish_id: int) -> str:
    """
    species.svg_template 안의 *{id} 플레이스홀더를
    개별 물고기 id(예: 3, 7, 12)로 치환한다.
    """
    if not svg_template:
        return ""
    return svg_template.replace("*{id}", str(fish_id))


def render_fish_group(cf, width, height,mode):
    species = cf.fish_species
    fish_id = cf.id
    raw_svg = species.svg_template
    templated_svg=apply_sprite_id(raw_svg, fish_id)
    inner = strip_outer_svg(templated_svg)


    # === 레이블 내용 ===
    if mode == "aquarium":
        label_text = cf.contributor.repository.name
    else:  # fishtank
        label_text = cf.contributor.user.username

    # === 랜덤 요소 생성 ===
    start_x = random.uniform(width * 0.1, width * 0.9)
    start_y = random.uniform(height * 0.2, height * 0.8)
    amplitude_x = random.uniform(width * 0.25, width * 0.45)  # x 왕복폭
    amplitude_y = random.uniform(height * 0.05, height * 0.12) # y 파동
    #speed = random.uniform(0.6, 1.6)   # 느린 물고기 / 빠른 물고기
    #phase = random.uniform(0, 6.28)
    duration = random.uniform(8, 18)   # 전체 이동 주기

    # === 이동 keyframes ===
    keyframes = f"""
    @keyframes move-{fish_id} {{
        0% {{
            transform: translate({start_x}px, {start_y}px);
        }}
        25% {{
            transform: translate({start_x + amplitude_x}px, {start_y + amplitude_y}px);
        }}
        50% {{
            transform: translate({start_x}px, {start_y - amplitude_y}px) scale(-1,1);
        }}
        75% {{
            transform: translate({start_x - amplitude_x}px, {start_y + amplitude_y}px) scale(-1,1);
        }}
        100% {{
            transform: translate({start_x}px, {start_y}px);
        }}
    }}
    """

    # === flip reverse keyframes ===
    reverse_keyframes = f"""
    @keyframes keep-label-upright-{fish_id} {{
        0%,25% {{
            transform: scale(1,1);
        }}
        50%,75% {{
            transform: scale(-1,1); /* 물고기가 뒤집힐 때 라벨도 같이 뒤집혀서 정방향 유지 */
        }}
        100% {{
            transform: scale(1,1);
        }}
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
                animation: keep-label-upright-{fish_id} {duration:.1f}s ease-in-out infinite;
                transform-origin: center;
            }}
            #fish-{fish_id} .label text {{
                font-size: 12px;
                fill: white;
                paint-order: stroke;
                stroke: rgba(0, 0, 0, 0.7);
                stroke-width: 2px;
            }}
            #fish-{fish_id} .label rect {{
                fill: rgba(0, 0, 0, 0.5);
                rx: 3px;
                ry: 3px;
            }}
        </style>

        <g class="motion">
            <g class="sprite">
                {inner}
            </g>
            
            <g class="label" transform="translate(0, 24)">
                <rect x="-40" y="-14" width="80" height="18" />
                <text text-anchor="middle" dominant-baseline="central">
                    {label_text}
                </text>
            </g>
        </g>
    </g>
    """