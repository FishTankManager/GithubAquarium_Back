from apps.items.models import FishSpecies
from apps.aquatics.models import Aquarium,ContributionFish , Fishtank
from .sprite import render_fish_group
from .utils import strip_outer_svg , extract_svg_size

def render_aquarium_svg(user,width=512, height=512):
    aquarium = Aquarium.objects.get(user=user)

    if aquarium.background and aquarium.background.background.background_image:
        bg_url = aquarium.background.background.background_image.url
    else:
        bg_url = ""  
    #width, height = extract_svg_size(bg_svg)
    #bg_inner = strip_outer_svg(bg_svg)
    width = 512
    height = 512
    fishes = ContributionFish.objects.filter(
        aquarium=aquarium,
        is_visible_in_aquarium=True
    ).select_related("fish_species", "contributor__repository")

    fish_groups = [
        render_fish_group(cf, width, height, mode="aquarium")
        for cf in fishes
    ]

    return f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">

      <image href="{bg_url}" width="{width}" height="{height}" />
      <g id="fish-container">
        {''.join(fish_groups)}
      </g>
    </svg>
    """


def render_fishtank_svg(repository):
    fishtank = Fishtank.objects.get(repository=repository)

 
    setting = fishtank.settings.select_related("background__background").first()
    if setting and setting.background and setting.background.background.background_image:
        bg_url = setting.background.background.background_image.url
    else:
        bg_url = ""
 
    #width, height = extract_svg_size(bg_svg)
    #bg_inner = strip_outer_svg(bg_svg)
    width = 512
    height = 512
    fishes = ContributionFish.objects.filter(
        contributor__repository=repository,
        is_visible_in_fishtank=True
    ).select_related("fish_species", "contributor__user")

    fish_groups = [
        render_fish_group(cf, width, height, mode="fishtank")
        for cf in fishes
    ]

    return f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <image href="{bg_url}" width="{width}" height="{height}" preserveAspectRatio="none" />
      <g id="fish-container">{''.join(fish_groups)}</g>
    </svg>
    """