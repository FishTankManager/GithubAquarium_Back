from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from apps.items.models import FishSpecies, Background

class Command(BaseCommand):
    help = 'fixtures 폴더의 파일명을 기반으로 FishSpecies와 Background를 초기화합니다.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('데이터 초기화를 시작합니다...'))

        # 1. 경로 설정
        base_fixtures_path = settings.BASE_DIR / 'fixtures'
        templates_path = base_fixtures_path / 'templates'
        backgrounds_path = base_fixtures_path / 'backgrounds'

        # 2. FishSpecies 초기화 (SVG Templates)
        if templates_path.exists():
            self.stdout.write('FishSpecies(templates) 처리 중...')
            for svg_file in templates_path.glob('*.svg'):
                filename = svg_file.stem  # 확장자 제외 파일명 (예: ShrimpWich_1)
                
                try:
                    # 파일명 분리 {group_code}_{maturity}
                    if '_' in filename:
                        group_code, maturity_str = filename.rsplit('_', 1)
                        maturity = int(maturity_str)
                    else:
                        group_code = filename
                        maturity = 1

                    with open(svg_file, 'r', encoding='utf-8') as f:
                        svg_content = f.read()

                    # 더미 데이터 설정
                    # maturity에 따른 최소 커밋 수 대략적 배정 (1:0, 2:50, 3:150 ...)
                    req_commits = (maturity - 1) * 100 
                    
                    obj, created = FishSpecies.objects.update_or_create(
                        group_code=group_code,
                        maturity=maturity,
                        defaults={
                            'name': f"{group_code} Lv.{maturity}",
                            'required_commits': req_commits,
                            'rarity': FishSpecies.Rarity.COMMON,
                            'svg_template': svg_content
                        }
                    )
                    status = "생성됨" if created else "업데이트됨"
                    self.stdout.write(f"- {group_code}_{maturity}: {status}")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"- {filename} 처리 실패: {e}"))
        else:
            self.stdout.write(self.style.WARNING('templates 폴더를 찾을 수 없습니다.'))

        # 3. Background 초기화 (Images)
        if backgrounds_path.exists():
            self.stdout.write('Backgrounds 처리 중...')
            for img_file in backgrounds_path.glob('*'):
                if img_file.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    raw_name = img_file.stem
                    clean_name = raw_name.split('_')[0] 
                    
                    code = clean_name.upper().replace('-', '_')

                    with open(img_file, 'rb') as f:
                        # [수정된 부분] File 객체 생성 시 name 인자에 파일명만 전달
                        django_file = File(f, name=img_file.name) 
                        
                        obj, created = Background.objects.update_or_create(
                            code=code,
                            defaults={
                                'name': clean_name.replace('-', ' ').title(),
                                'background_image': django_file
                            }
                        )
                    status = "생성됨" if created else "업데이트됨"
                    self.stdout.write(f"- {clean_name}: {status}")
        else:
            self.stdout.write(self.style.WARNING('backgrounds 폴더를 찾을 수 없습니다.'))

        self.stdout.write(self.style.SUCCESS('모든 데이터 초기화가 완료되었습니다.'))