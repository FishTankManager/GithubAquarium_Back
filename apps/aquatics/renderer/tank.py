from apps.items.models import FishSpecies
from apps.aquatics.models import Aquarium,ContributionFish , Fishtank
from .sprite import render_fish_group
from .utils import strip_outer_svg , extract_svg_size

def render_aquarium_svg(user,width=512, height=512):
    aquarium = Aquarium.objects.get(user=user)

    if aquarium.background:
      bg_svg = aquarium.background.background.svg_template
    else:
      bg_svg = '<svg width="512" height="512"></svg>'

    width, height = extract_svg_size(bg_svg)
    bg_inner = strip_outer_svg(bg_svg)

    fishes = ContributionFish.objects.filter(
        aquarium=aquarium,
        is_visible=True
    ).select_related("fish_species", "contributor__repository")

    fish_groups = [
        render_fish_group(cf, width, height, mode="aquarium")
        for cf in fishes
    ]

    return f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">

      <g id="background">
        {bg_inner}
      </g>
      <g id="fish-container">
        {''.join(fish_groups)}
      </g>
    </svg>
    """


def render_fishtank_svg(repository):
    fishtank = Fishtank.objects.get(repository=repository)

 
    setting = fishtank.settings.select_related("background__background").first()
    if setting and setting.background:
        bg_svg = setting.background.background.svg_template
    else:
        bg_svg = '<svg width="512" height="512"><rect width="100%" height="100%" fill="#001f3f"/></svg>'

 
    width, height = extract_svg_size(bg_svg)
    bg_inner = strip_outer_svg(bg_svg)

    fishes = ContributionFish.objects.filter(
        contributor__repository=repository,
        is_visible=True
    ).select_related("fish_species", "contributor__user")

    fish_groups = [
        render_fish_group(cf, width, height, mode="fishtank")
        for cf in fishes
    ]

    return f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <g id="background">{bg_inner}</g>
      <g id="fish-container">{''.join(fish_groups)}</g>
    </svg>
    """