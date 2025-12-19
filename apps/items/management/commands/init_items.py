import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from apps.items.models import FishSpecies, Background, Item

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'fixtures 폴더를 기반으로 FishSpecies, Background, 그리고 상점 Item을 초기화합니다.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== 데이터 초기화 시작 ==='))

        # 1. 경로 설정
        base_fixtures_path = settings.BASE_DIR / 'fixtures'
        templates_path = base_fixtures_path / 'templates'
        backgrounds_path = base_fixtures_path / 'backgrounds'

        # 2. FishSpecies 초기화 (SVG Templates)
        if templates_path.exists():
            self.stdout.write('1. FishSpecies 생성 중...')
            for svg_file in templates_path.glob('*.svg'):
                filename = svg_file.stem  # 예: ShrimpWich_1
                
                try:
                    if '_' in filename:
                        group_code, maturity_str = filename.rsplit('_', 1)
                        maturity = int(maturity_str)
                    else:
                        group_code = filename
                        maturity = 1

                    with open(svg_file, 'r', encoding='utf-8') as f:
                        svg_content = f.read()

                    # 진화 단계별 요구 커밋 수 (테스트를 위해 낮게 설정)
                    req_commits = (maturity - 1) * 50 
                    
                    FishSpecies.objects.update_or_create(
                        group_code=group_code,
                        maturity=maturity,
                        defaults={
                            'name': f"{group_code} Lv.{maturity}",
                            'required_commits': req_commits,
                            'rarity': FishSpecies.Rarity.COMMON,
                            'svg_template': svg_content
                        }
                    )
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   - {filename} 처리 실패: {e}"))
            self.stdout.write(self.style.SUCCESS('   - FishSpecies 완료'))
        else:
            self.stdout.write(self.style.WARNING('   - templates 폴더가 없어 FishSpecies 스킵'))


        # 3. Background 및 관련 Shop Item 초기화
        if backgrounds_path.exists():
            self.stdout.write('2. Background 및 배경 상품 생성 중...')
            for img_file in backgrounds_path.glob('*'):
                if img_file.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    raw_name = img_file.stem
                    # 파일명에서 코드 추출 (예: deep-sea_bg -> DEEP_SEA)
                    clean_name = raw_name.split('_')[0]
                    code = clean_name.upper().replace('-', '_')

                    try:
                        with open(img_file, 'rb') as f:
                            # 3-1. 배경 생성
                            bg_obj, created = Background.objects.update_or_create(
                                code=code,
                                defaults={
                                    'name': clean_name.replace('-', ' ').title(),
                                    'background_image': File(f, name=img_file.name)
                                }
                            )

                        # 3-2. 해당 배경을 상점 아이템(해금권)으로 등록
                        Item.objects.update_or_create(
                            code=f"BG_{code}",
                            defaults={
                                'name': f"{bg_obj.name} 배경 해금권",
                                'description': f"'{bg_obj.name}' 배경을 내 수족관에 적용할 수 있습니다.",
                                'item_type': Item.ItemType.BG_UNLOCK,
                                'target_background': bg_obj,
                                'price': 100, # 배경 가격
                                'is_active': True
                            }
                        )
                        self.stdout.write(f"   - 배경 및 상품 등록: {code}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"   - {raw_name} 처리 실패: {e}"))
            self.stdout.write(self.style.SUCCESS('   - Background & Items 완료'))
        else:
            self.stdout.write(self.style.WARNING('   - backgrounds 폴더가 없어 Background 스킵'))


        # 4. 소모품 아이템 초기화 (리롤권)
        self.stdout.write('3. 소모품 상품 생성 중...')
        Item.objects.update_or_create(
            code="TICKET_REROLL",
            defaults={
                'name': "물고기 리롤권",
                'description': "물고기의 종류(패밀리)를 랜덤하게 변경합니다. 등급과 성장 단계는 유지될 수 있습니다.",
                'item_type': Item.ItemType.REROLL_TICKET,
                'price': 50,
                'is_active': True
            }
        )
        self.stdout.write(self.style.SUCCESS('   - 리롤권 상품 등록 완료'))

        self.stdout.write(self.style.SUCCESS('=== 모든 데이터 초기화 완료 ==='))