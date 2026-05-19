import pygame
import sys
import base64
import io
import math
from settings import *
from sprite import Base64_Data

from player import Player
from effects import AnimatedBackground, GLOBAL_PARTICLE_POOL, SolarFlareEffect, EndingCredits
from weapons import render_glowing_laser

from game_manager import GameManager
from stage_manager import StageManager
from collision import handle_collisions
from ui import UIManager

pygame.init()

# ==========================================
# 🌟 1. 폰트 설정 (두껍게 Bold 적용)
# ==========================================
try:
    menu_font = pygame.font.SysFont("malgungothic", 40, bold=True) 
    title_font = pygame.font.SysFont("arial", 100, bold=True) # 타이틀은 영어니 유지해도 됨
    desc_font = pygame.font.SysFont("malgungothic", 22, bold=True) # 크기 26 -> 22로 축소
    popup_title_font = pygame.font.SysFont("malgungothic", 45, bold=True) # 한글 깨짐 방지용 새 폰트
except:
    title_font = pygame.font.SysFont("arial", 100, bold=True)
    menu_font = pygame.font.SysFont("arial", 40, bold=True)
    desc_font = pygame.font.SysFont("arial", 22, bold=True)
    popup_title_font = pygame.font.SysFont("arial", 45, bold=True)

stage_manager = StageManager()
game_credits = EndingCredits(desc_font)

def get_lobby_bg(size):
    """Base64 텍스트를 로드하여 외곽은 어둡고 흐리게, 중앙은 선명하게 처리합니다."""
    # 1. 원본 선명한 이미지 로드
    try:
        if Base64_Data["LOBBY_BG_B64"]:
            image_data = base64.b64decode(Base64_Data["LOBBY_BG_B64"])
            image = pygame.image.load(io.BytesIO(image_data)).convert_alpha()
            sharp_img = pygame.transform.smoothscale(image, size).convert()
        else:
            sharp_img = pygame.Surface(size)
            sharp_img.fill((10, 10, 25))
    except Exception as e:
        print("로비 배경 로드 실패:", e)
        sharp_img = pygame.Surface(size)
        sharp_img.fill((10, 10, 25))

    # 2. 흐릿한(블러) 이미지 생성 (크기를 1/12로 확 줄였다가 다시 늘려서 픽셀을 뭉갬)
    small_size = (size[0] // 12, size[1] // 12)
    small_img = pygame.transform.smoothscale(sharp_img, small_size)
    blur_img = pygame.transform.smoothscale(small_img, size).convert_alpha()

    # 3. 비네팅(어둡게) & 블러 적용을 위한 마스크 생성
    # (연산 속도를 위해 200x200 캔버스에서 수학적으로 그라데이션을 계산 후 화면 크기로 확대)
    mask_size = 200
    mask_surf = pygame.Surface((mask_size, mask_size), pygame.SRCALPHA)
    vignette_surf = pygame.Surface((mask_size, mask_size), pygame.SRCALPHA)
    
    center = mask_size / 2
    max_dist = center * 1.2 # 그라데이션이 시작되는 반경 조절

    for x in range(mask_size):
        for y in range(mask_size):
            dist = math.hypot(x - center, y - center)
            norm = min(1.0, dist / max_dist)
            
            # 외곽으로 갈수록 norm 수치가 1.0에 가까워짐
            # [블러 마스크] 중앙 투명(0), 외곽 불투명(255)
            blur_alpha = int(255 * (norm ** 2.5)) 
            mask_surf.set_at((x, y), (255, 255, 255, blur_alpha))
            
            # [어둠 마스크] 중앙 투명(0), 외곽 짙은 어둠(220)
            dark_alpha = int(220 * (norm ** 2.0))
            vignette_surf.set_at((x, y), (0, 0, 0, dark_alpha))

    # 계산된 200x200 마스크를 실제 화면 크기로 부드럽게 확대
    scaled_mask = pygame.transform.smoothscale(mask_surf, size)
    scaled_vignette = pygame.transform.smoothscale(vignette_surf, size)

    # 4. 블러 이미지에 투명도 마스크 합성 (중앙은 투명해지고 외곽만 흐릿하게 남음)
    blur_img.blit(scaled_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    # 5. 최종 합성: 원본(선명) -> 겉에 블러 씌우기 -> 겉을 어둡게 덮기
    final_bg = sharp_img.copy()
    final_bg.blit(blur_img, (0, 0))
    final_bg.blit(scaled_vignette, (0, 0))

    return final_bg

# ==========================================
# 메인 게임 루프 (변경 없음)
# ==========================================
def run_game():
    screen = pygame.display.get_surface()
    clock = pygame.time.Clock()

    game_manager = GameManager()
    stage_manager = StageManager()
    ui_manager = UIManager()
    background_manager = AnimatedBackground()
    solar_flare = SolarFlareEffect()

    player = Player()
    player_bullets = pygame.sprite.Group()
    enemy_projectiles = pygame.sprite.Group()
    meteors = pygame.sprite.Group()
    pirates = pygame.sprite.Group()
    bombers = pygame.sprite.Group() 
    bombs = pygame.sprite.Group()
    scouts = pygame.sprite.Group()
    supports = pygame.sprite.Group()
    turrets = pygame.sprite.Group()
    boss_group = pygame.sprite.GroupSingle()
    nuke_group = pygame.sprite.Group()
    boss_enemy_group = pygame.sprite.Group()

    camera_pos = pygame.math.Vector2(0, 0)
    running = True

    while running:
        dt = clock.tick(60)
        screen_w, screen_h = screen.get_size()
        
        target_camera = player.pos - pygame.math.Vector2(screen_w // 2, screen_h // 2)
        target_camera.x = max(0, min(target_camera.x, MAP_WIDTH - screen_w))
        target_camera.y = max(0, min(target_camera.y, MAP_HEIGHT - screen_h))
        
        camera_pos = camera_pos.lerp(target_camera, 0.1) 
        camera_pos.x = max(0, min(camera_pos.x, MAP_WIDTH - screen_w))
        camera_pos.y = max(0, min(camera_pos.y, MAP_HEIGHT - screen_h))

        solar_flare.update()
        
        if game_manager.state != "ENDING_CREDITS":
            if solar_flare.is_active:
                screen.fill((255, 255, 255))
            else:
                screen.fill((0, 0, 0))
                background_manager.update_and_draw(screen, camera_pos, stage_manager.current_stage)
        
        # ==========================================
        # 1. 이벤트 처리부 (키보드, 마우스 입력)
        # ==========================================
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False # 로비로 복귀
            
            if game_manager.state == "LEVEL_UP" and event.type == pygame.KEYDOWN:
                idx = -1
                if event.key == pygame.K_1: idx = 0
                elif event.key == pygame.K_2: idx = 1
                elif event.key == pygame.K_3: idx = 2
                if idx != -1:
                    game_manager.apply_upgrade(player, idx)

            if game_manager.state == "GAME_CLEAR_CHOICE" and event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                yes_rect = pygame.Rect(screen_w - 420 + 50, screen_h - 220 + 140, 100, 40)
                no_rect = pygame.Rect(screen_w - 420 + 250, screen_h - 220 + 140, 100, 40)
                
                if yes_rect.collidepoint(mouse_pos):
                    game_manager.state = "PLAYING"
                elif no_rect.collidepoint(mouse_pos):
                    game_manager.state = "ENDING_CREDITS"

        # ==========================================
        # 2. 업데이트 부 (엔딩 아닐 때만 업데이트)
        # ==========================================
        player_laser_lines = []
        if game_manager.state in ["PLAYING", "WARNING", "BOSS_BATTLE"]:
            stage_manager.update(dt, player, meteors, pirates, bombers, scouts, supports, boss_group, game_manager)
            player.update(camera_pos, player_bullets)
            
            # 🚨 [복구됨] 여기서부터 각 엔티티들의 위치와 상태를 갱신합니다!
            player_bullets.update(camera_pos)
            enemy_projectiles.update(camera_pos, player)
            meteors.update(camera_pos)
            pirates.update(camera_pos, player, enemy_projectiles, stage_manager.current_stage)
            bombers.update(camera_pos, player, enemy_projectiles, bombs)
            bombs.update(camera_pos, player, GLOBAL_PARTICLE_POOL)
            scouts.update(camera_pos, player, enemy_projectiles, [pirates, bombers, turrets])
            supports.update(camera_pos, player, enemy_projectiles, turrets)
            turrets.update(camera_pos, player, enemy_projectiles)
            nuke_group.update(camera_pos, player)
            boss_enemy_group.update(camera_pos, player, enemy_projectiles)
            
            # 보스 개별 업데이트
            if boss_group.sprite:
                boss_name = type(boss_group.sprite).__name__
                if boss_name == "Chapter1Boss":
                    boss_group.sprite.update(camera_pos, player, enemy_projectiles, pirates, stage_manager.current_stage, clock)
                elif boss_name == "Chapter2Boss":
                    mob_groups = {"pirates": pirates, "bombers": bombers}
                    boss_group.sprite.update(camera_pos, player, enemy_projectiles, bombs, nuke_group, mob_groups, stage_manager.current_stage, clock)
                elif boss_name == "Chapter3Boss":
                    boss_group.sprite.update(camera_pos, player, boss_enemy_group, enemy_projectiles) 
            
            # 파티클 및 충돌 처리
            GLOBAL_PARTICLE_POOL.update_and_draw(screen, camera_pos) 
            player_laser_lines = handle_collisions(
                player, player_bullets, enemy_projectiles, meteors, pirates, bombers, bombs, scouts, supports, turrets, boss_group, nuke_group, boss_enemy_group,
                GLOBAL_PARTICLE_POOL.active_particles, game_manager, stage_manager.current_stage
            )

        # ==========================================
        # 3. 렌더링 부 (화면 그리기)
        # ==========================================
        if game_manager.state == "ENDING_CREDITS":
            game_credits.update_and_draw(screen) 
            
        else:
            # 기존 인게임 요소 그리기
            if solar_flare.is_active:
                groups_to_draw = [player_bullets, enemy_projectiles, meteors, pirates, bombers, scouts, supports, turrets, boss_group, nuke_group, bombs, boss_enemy_group]
                for group in groups_to_draw:
                    for sprite in group:
                        screen.blit(solar_flare.get_silhouette(sprite.image), sprite.rect)
                if game_manager.state != "GAME_OVER":
                    screen.blit(solar_flare.get_silhouette(player.image), player.rect)
            else:
                if player.laser_active:
                    for start_pos, end_pos, _ in player_laser_lines:
                        render_glowing_laser(screen, start_pos - camera_pos, end_pos - camera_pos, BLUE, player.laser_level)
                if boss_group.sprite: boss_group.sprite.draw_effects(screen, camera_pos)
                
                player_bullets.draw(screen); enemy_projectiles.draw(screen); meteors.draw(screen); pirates.draw(screen)
                boss_group.draw(screen); bombers.draw(screen)
                for scout in scouts: scout.draw_lines(screen, camera_pos); scouts.draw(screen)
                for bomb in bombs: bomb.draw(screen, camera_pos)
                for support in supports: support.draw_heal_lines(screen, camera_pos); supports.draw(screen)
                turrets.draw(screen)
                for nuke in nuke_group: nuke.draw(screen, camera_pos); boss_enemy_group.draw(screen)
                
                if game_manager.state != "GAME_OVER":  # (오타 'ㅁ' 제거)
                    player.draw_afterimages(screen, camera_pos)
                    screen.blit(player.image, player.rect)
                    if pygame.time.get_ticks() < getattr(player, 'stun_end_time', 0):
                        pygame.draw.circle(screen, (255, 255, 0), player.rect.center, player.radius + 15, 3)

            # 일반 UI 그리기
            ui_manager.draw_ui(screen, player, game_manager, stage_manager, boss_group)
            
            if game_manager.state == "GAME_CLEAR_CHOICE":
                draw_clear_choice(screen, desc_font) 

        pygame.display.flip()
    
    return True

# ==========================================
# 로비 화면
# ==========================================
def draw_clear_choice(screen, font):
    # 박스 설정 (우측 하단)
    width, height = 400, 200
    x, y = WIDTH - width - 20, HEIGHT - height - 20
    rect = pygame.Rect(x, y, width, height)
    
    # 배경 박스 (반투명 검정)
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    s.fill((0, 0, 0, 200)) 
    screen.blit(s, (x, y))
    pygame.draw.rect(screen, (255, 255, 255), rect, 2) # 테두리
    
    # 텍스트 출력 (줄바꿈 처리)
    lines = ["당신은 게임을 클리어 하였습니다.", "이후 게임은 반복됩니다.", "계속 하시겠습니까?"]
    for i, line in enumerate(lines):
        text_surf = font.render(line, True, (255, 255, 255))
        screen.blit(text_surf, (x + 20, y + 20 + (i * 30)))
        
    # 버튼 설정
    yes_rect = pygame.Rect(x + 50, y + 140, 100, 40)
    no_rect = pygame.Rect(x + 250, y + 140, 100, 40)
    
    pygame.draw.rect(screen, (0, 150, 0), yes_rect) # 예 (초록)
    pygame.draw.rect(screen, (150, 0, 0), no_rect) # 아니오 (빨강)
    
    screen.blit(font.render("예", True, (255, 255, 255)), (yes_rect.centerx - 10, yes_rect.centery - 10))
    screen.blit(font.render("아니오", True, (255, 255, 255)), (no_rect.centerx - 25, no_rect.centery - 10))
    
    return yes_rect, no_rect

def main_lobby():
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    clock = pygame.time.Clock()
    show_instructions = False
    
    # 스크롤 관련 변수
    scroll_y = 0
    max_scroll = 0

    # 로비 배경 이미지 로드
    bg_surface = get_lobby_bg((WIDTH, HEIGHT))

    # 설명창 내용 정의 (긴 문장은 자동으로 줄바꿈 처리하거나 직접 나눠서 작성)
    instr_texts = [
                "[ 게임 설명 ]",
                "",
                "• 조작: ",
                "     방향키(혹은 WASD)로 이동하고, 마우스로 사격하는 트윈스틱 슈터입니다.",
                "",
                "• 목표: ",
                "     30스테이지까지 무수한 적의 공격에서 생존하여 최종 보스를 처치하세요.",
                "",
                "• 시스템:"
                "     적 파괴 시 붉은 경험치를 얻고, 레벨업을 통해",
                "     무기 개수, 데미지, 체력 등을 다채롭게 업그레이드할 수 있습니다.",
                "• 난이도:",
                "     스테이지가 올라갈수록 강력한 적과 다채로운 보스 패턴이 등장합니다.",
                "",
                "우주의 기하학적 위협 속에서 끝까지 살아남으세요!",
                "",
                "(ESC 혹은 SPACE를 입력하여 닫기)"
    ]

    while True:
        screen.blit(bg_surface, (0, 0))
        mx, my = pygame.mouse.get_pos()

        # [좌측 상단] 타이틀
        title_surf = title_font.render("Space Geometry", True, CYAN)
        screen.blit(title_font.render("Space Geometry", True, BLACK), (85, 85))
        screen.blit(title_surf, (80, 80))

        # [우측 하단] 메뉴 버튼
        button_x = WIDTH - 350
        start_y = HEIGHT // 2 + 50
        play_rect = pygame.Rect(button_x, start_y, 280, 60)
        info_rect = pygame.Rect(button_x, start_y + 90, 280, 60)
        exit_rect = pygame.Rect(button_x, start_y + 180, 280, 60)

        def draw_button(rect, text, is_hover):
            bg_color = CYAN if is_hover else (30, 30, 50, 180)
            text_color = BLACK if is_hover else WHITE
            
            # 버튼 배경
            btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(btn_surf, bg_color, btn_surf.get_rect(), border_radius=10)
            screen.blit(btn_surf, rect.topleft)
            
            if not is_hover: 
                pygame.draw.rect(screen, CYAN, rect, 2, border_radius=10)
            
            # 여기서 menu_font를 사용하여 한글 텍스트 렌더링
            txt_surf = menu_font.render(text, True, text_color)
            screen.blit(txt_surf, txt_surf.get_rect(center=rect.center))

        draw_button(play_rect, "게임 시작", play_rect.collidepoint(mx, my))
        draw_button(info_rect, "게임 설명", info_rect.collidepoint(mx, my))
        draw_button(exit_rect, "종료", exit_rect.collidepoint(mx, my))

        # [설명창 팝업 렌더링]
        if show_instructions:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 220))
            screen.blit(overlay, (0, 0))
            
            popup_w, popup_h = 900, 600
            popup_rect = pygame.Rect(WIDTH//2 - popup_w//2, HEIGHT//2 - popup_h//2, popup_w, popup_h)
            pygame.draw.rect(screen, (20, 20, 35), popup_rect, border_radius=20)
            pygame.draw.rect(screen, CYAN, popup_rect, 3, border_radius=20)

            # 텍스트를 그릴 내부 '뷰포트' 설정 (클리핑 영역)
            padding = 50
            text_area_rect = pygame.Rect(popup_rect.x + padding, popup_rect.y + padding, popup_w - padding*2, popup_h - padding*2)
            
            # 텍스트들을 미리 렌더링하여 전체 높이 계산
            line_height = 40
            total_content_h = len(instr_texts) * line_height
            max_scroll = max(0, total_content_h - text_area_rect.height)

            # 클리핑 서피스 생성 (글자가 팝업창 밖으로 안 나가게 함)
            text_surf = pygame.Surface((text_area_rect.width, text_area_rect.height), pygame.SRCALPHA)
            
            for i, line in enumerate(instr_texts):
                color = CYAN if i == 0 else WHITE
                f = popup_title_font if i == 0 else desc_font
                rendered_line = f.render(line, True, color)
                
                # 스크롤 위치(scroll_y)를 반영하여 그리기
                y_pos = (i * line_height) - scroll_y
                
                # 제목은 중앙, 나머지는 좌측
                if i == 0:
                    text_surf.blit(rendered_line, rendered_line.get_rect(center=(text_area_rect.width // 2, y_pos + 20)))
                else:
                    text_surf.blit(rendered_line, (0, y_pos))

            screen.blit(text_surf, text_area_rect.topleft)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            
            if not show_instructions:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if play_rect.collidepoint(mx, my):
                        if not run_game(): pygame.quit(); sys.exit()
                    elif info_rect.collidepoint(mx, my):
                        show_instructions = True
                        scroll_y = 0 # 열 때마다 스크롤 초기화
                    elif exit_rect.collidepoint(mx, my):
                        pygame.quit(); sys.exit()
            else:
                # 설명창이 켜져 있을 때의 로직
                if event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_SPACE, pygame.K_ESCAPE]:
                        show_instructions = False
                
                # 마우스 휠 스크롤 지원
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4: # 휠 위로
                        scroll_y = max(0, scroll_y - 30)
                    elif event.button == 5: # 휠 아래로
                        scroll_y = min(max_scroll, scroll_y + 30)

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main_lobby()