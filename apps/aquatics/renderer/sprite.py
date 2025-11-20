from .utils import strip_outer_svg , safe_attr

def render_fish_group(cf):
    """
    ContributionFish 인스턴스를 받아서,
    <g id="fish-{id}"> ... species svg ... </g> 형태로 만들어 줌.
    애니메이션은 프론트에서~
    """
    species = cf.species
    raw_svg = species.svg_template
    inner = strip_outer_svg(raw_svg)
    fish_id = cf.id   

    # 위치는 프론트에서 transform 걸 거면 여기선 0,0 기준으로 두고,
    # 그냥 id와 class만 설정해줘도 됨.
    return f"""
    <g id="fish-{fish_id}" 
       class="fish species-{species.id}"
       data-fish-id="{fish_id}"
       data-species-id="{species.id}">
       {inner}
    </g>
    """
