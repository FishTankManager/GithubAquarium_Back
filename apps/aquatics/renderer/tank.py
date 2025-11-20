# apps/aquarium/renderer/tank.py
from apps.items.models import FishSpecies
from apps.aquatics.models import Aquarium,ContributionFish 
from .sprite import render_fish_group
from .utils import strip_outer_svg 

def render_aquarium_svg(user,width=512, height=512):
    aquarium = Aquarium.objects.select_related("background").get(user=user)
    bg_svg= aquarium.background.svg_template
    bg_inner = strip_outer_svg(bg_svg)

    fishes = ContributionFish.objects.filter(
        user=user,
        is_visible=True
    ).select_related("species")

    fish_groups = [render_fish_group(cf) for cf in fishes]

    return f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">

      <g id="background">
        {bg_inner}
      </g>

      <g id="fish-container">
        {''.join(fish_groups)}
      </g>

    </svg>
    """
