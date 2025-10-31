#비즈니스 로직 자동화
#특정이벤트 발생 시 코드 자동 실행
#ex 유저 가입 시 어항 자동생성

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.manager.models import Aquarium, FishTank
from apps.repositories.models import Repository, Contributor

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_aquarium_and_tanks(sender, instance, created, **kwargs):
    if not created:
        return

    Aquarium.objects.get_or_create(owner=instance)

    if not instance.github_username:
        return

    user_contribs = Contributor.objects.filter(github_username=instance.github_username)
    repo_ids = user_contribs.values_list("repository_id", flat=True).distinct()

    for repo_id in repo_ids:
        repo = Repository.objects.get(id=repo_id)
        FishTank.objects.get_or_create(
            owner=instance,
            repository=repo,
            defaults={"contributor_count": repo.contributors.count()},
        )
