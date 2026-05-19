import pygame
from settings import WIDTH, HEIGHT, MAP_WIDTH, MAP_HEIGHT, RED, WHITE, YELLOW, CYAN, GREEN
from asset_loader import font, mid_font, large_font

class UIManager:
    def draw_ui(self, screen, player, game_manager, stage_manager, boss_group):
        # 1. 체력 바
        pygame.draw.rect(screen, (80, 0, 0), (20, 20, 200, 20))
        pygame.draw.rect(screen, RED, (20, 20, int(200 * max(0, player.hp / player.max_hp)), 20))
        pygame.draw.rect(screen, WHITE, (20, 20, 200, 20), 2)
        screen.blit(font.render(f"HP: {player.hp} / {player.max_hp}", True, WHITE), (230, 18))

        # 2. 경험치 바
        pygame.draw.rect(screen, (50, 50, 50), (20, 50, 200, 20))
        pygame.draw.rect(screen, YELLOW, (20, 50, int(200 * (player.exp / player.max_exp)), 20))
        pygame.draw.rect(screen, WHITE, (20, 50, 200, 20), 2)
        screen.blit(font.render(f"LV: {player.level} ({player.exp}/{player.max_exp})", True, WHITE), (230, 48))
        
        # 3. 시간 및 스테이지
        time_text = mid_font.render(f"Time: {stage_manager.play_time//60000:02d}:{(stage_manager.play_time//1000)%60:02d}  |  Stage(Diff): {stage_manager.current_stage}", True, CYAN)
        screen.blit(time_text, time_text.get_rect(center=(WIDTH//2, HEIGHT - 30)))
        
        # 4. 보스 체력 바
        if boss_group.sprite:
            boss, bar_width = boss_group.sprite, 600
            pygame.draw.rect(screen, (50, 0, 0), (WIDTH//2 - bar_width//2, 20, bar_width, 25))
            pygame.draw.rect(screen, RED, (WIDTH//2 - bar_width//2, 20, int(bar_width * (max(0, boss.hp) / boss.max_hp)), 25))
            pygame.draw.rect(screen, WHITE, (WIDTH//2 - bar_width//2, 20, bar_width, 25), 2)
            boss_txt = font.render(f"STAR BOSS [{(max(0, boss.hp) / boss.max_hp)*100:.1f}%]", True, WHITE)
            screen.blit(boss_txt, boss_txt.get_rect(center=(WIDTH//2, 32)))

        # 5. 상태별 오버레이 화면
        if game_manager.state == "WARNING":
            if (stage_manager.play_time // 200) % 2 == 0:
                warn = large_font.render("WARNING: BOSS APPROACHING", True, RED)
                screen.blit(warn, warn.get_rect(center=(WIDTH//2, HEIGHT//2)))
                
        elif game_manager.state == "LEVEL_UP":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180)); screen.blit(overlay, (0, 0))
            lv_msg = large_font.render("레벨 업!", True, CYAN)
            screen.blit(lv_msg, lv_msg.get_rect(center=(WIDTH//2, HEIGHT//3 - 50)))
            
            for idx, choice in enumerate(game_manager.current_choices):
                box = pygame.Rect(WIDTH//2 - 250, HEIGHT//2 - 50 + (idx * 90), 500, 70)
                pygame.draw.rect(screen, (50, 50, 50), box, border_radius=10)
                pygame.draw.rect(screen, WHITE, box, 2, border_radius=10)
                screen.blit(mid_font.render(f"{idx + 1}. {choice['name']}", True, WHITE), (box.x + 20, box.y + 10))
                screen.blit(font.render(choice['desc'], True, GREEN), (box.x + 20, box.y + 45))

        elif game_manager.state == "GAME_OVER":
            msg = large_font.render("게임 오버", True, RED)
            screen.blit(msg, msg.get_rect(center=(WIDTH//2, HEIGHT//2)))
            tip_msg = font.render("Press ESC to Exit", True, WHITE)
            screen.blit(tip_msg, tip_msg.get_rect(center=(WIDTH//2, HEIGHT//2 + 50)))