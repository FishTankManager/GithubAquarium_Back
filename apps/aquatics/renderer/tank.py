# apps/aquarium/renderer/tank.py
from apps.items.models import FishSpecies
from apps.aquatics.models import Aquarium,ContributionFish , Fishtank
from .sprite import render_fish_group
from .utils import strip_outer_svg , extract_svg_size

def render_aquarium_svg(user,width=512, height=512):
    aquarium = Aquarium.objects.select_related("background").get(user=user)
    bg_svg= aquarium.background.svg_template
    width, height = extract_svg_size(bg_svg)
    bg_inner = strip_outer_svg(bg_svg)

    fishes = ContributionFish.objects.filter(
        user=user,
        is_visible=True
    ).select_related("species")

    fish_groups = [render_fish_group(cf, width, height)  for cf in fishes]

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

 
    setting = fishtank.settings.first()
    if setting and setting.background:
        bg_svg = setting.background.background.svg_template
    else:
        bg_svg = '<svg width="512" height="512"></svg>'

 
    width, height = extract_svg_size(bg_svg)
    bg_inner = strip_outer_svg(bg_svg)

    fishes = ContributionFish.objects.filter(
        contributor__repository=repository,
        is_visible=True
    ).select_related("fish_species")

    fish_groups = [
        render_fish_group(cf, width, height)
        for cf in fishes
    ]

    return f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <g id="background">{bg_inner}</g>
      <g id="fish-container">{''.join(fish_groups)}</g>
    </svg>
    """