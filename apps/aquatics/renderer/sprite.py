import random
from .utils import strip_outer_svg

def render_fish_group(cf, width, height):
    species = cf.fish_species
    raw_svg = species.svg_template
    inner = strip_outer_svg(raw_svg)
    fish_id = cf.id

    # === 랜덤 요소 생성 ===
    start_x = random.uniform(width * 0.1, width * 0.9)
    start_y = random.uniform(height * 0.2, height * 0.8)
    amplitude_x = random.uniform(width * 0.25, width * 0.45)  # x 왕복폭
    amplitude_y = random.uniform(height * 0.05, height * 0.12) # y 파동
    speed = random.uniform(0.6, 1.6)   # 느린 물고기 / 빠른 물고기
    phase = random.uniform(0, 6.28)
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

    return f"""
    <g id="fish-{fish_id}" class="fish species-{species.id}">
        <style>
            {keyframes}

            #fish-{fish_id} {{
                animation: move-{fish_id} {duration}s ease-in-out infinite;
                transform-origin: center;
            }}
        </style>

        {inner}
    </g>
    """
