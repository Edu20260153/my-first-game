import pygame
from settings import YELLOW, PURPLE, ORANGE, GREEN
from effects import create_explosion

def check_line_collision(start_pos, dir_vec, target_pos, target_radius, thickness=30):
    vec_to_target = target_pos - start_pos
    projection = vec_to_target.dot(dir_vec)
    if projection > 0:
        closest_point = start_pos + dir_vec * projection
        if target_pos.distance_to(closest_point) < (thickness/2) + target_radius:
            return True
    return False

def handle_collisions(player, player_bullets, enemy_projectiles, meteors, pirates, bombers, bombs, scouts, supports, turrets, boss_group, nuke_group, boss_enemy_group, particles, game_manager, current_stage):
    player_laser_lines = []
    
    # ---------------------------------------------------------
    # 1. 플레이어 공격 -> 적 충돌 판정 (레이저 & 총알)
    # ---------------------------------------------------------
    if player.laser_active:
        base_dir = pygame.math.Vector2(0, -1).rotate(-player.laser_angle)
        for i in range(player.laser_level):
            offset_angle = (i - (player.laser_level - 1) / 2) * 15
            dir_vec = base_dir.rotate(offset_angle)
            player_laser_lines.append((player.pos, player.pos + dir_vec * 1500, dir_vec))
            
        for start_pos, end_pos, dir_vec in player_laser_lines:
            # 적 그룹을 리스트로 묶어서 순회 (Scout 추가)
            for group_idx, enemy_list in enumerate([meteors, pirates, bombers, scouts, supports, turrets, boss_enemy_group]):
                for e in enemy_list:
                    # 🌟 무적(is_protected) 상태면 타격 무시
                    if getattr(e, 'is_protected', False):
                        continue
                        
                    if e not in player.lasers_hit and check_line_collision(start_pos, dir_vec, e.pos, e.radius, 30):
                        player.lasers_hit.add(e)
                        # 색상 및 경험치 설정
                        color = YELLOW if group_idx == 0 else PURPLE if group_idx == 1 else (255, 100, 100) if group_idx == 2 else (0, 150, 255)
                        exp_val = 2 if group_idx == 0 else 5 if group_idx == 1 else 8 if group_idx == 2 else 6
                        
                        create_explosion(e.pos, color, 5, particles)
                        if e.take_damage(player.damage, player, particles): 
                            create_explosion(e.pos, color, 20 if group_idx != 0 else 15, particles)
                            game_manager.handle_exp(player, exp_val, current_stage)

            # 보스 레이저 판정
            if boss_group.sprite and boss_group.sprite not in player.lasers_hit:
                if check_line_collision(start_pos, dir_vec, boss_group.sprite.pos, boss_group.sprite.radius, 30):
                    player.lasers_hit.add(boss_group.sprite)
                    create_explosion(boss_group.sprite.pos, ORANGE, 5, particles)
                    if boss_group.sprite.take_damage(player.damage, player, particles):
                        create_explosion(boss_group.sprite.pos, ORANGE, 150, particles)
                        game_manager.boss_cleared_stages.append(current_stage)
                        game_manager.state = "PLAYING"
                        game_manager.handle_exp(player, 50, current_stage)

    # 총알 판정
    for bullet in player_bullets:
        for group_idx, enemy_list in enumerate([meteors, pirates, bombers, scouts, supports, turrets, boss_enemy_group]):
            for hit in pygame.sprite.spritecollide(bullet, enemy_list, False, pygame.sprite.collide_circle):
                if getattr(hit, 'is_protected', False):
                    continue
                    
                bullet.kill()
                color = YELLOW if group_idx == 0 else PURPLE if group_idx == 1 else (255, 100, 100) if group_idx == 2 else (0, 150, 255)
                exp_val = 2 if group_idx == 0 else 5 if group_idx == 1 else 8 if group_idx == 2 else 6
                
                create_explosion(bullet.pos, YELLOW, 5, particles)
                if hit.take_damage(bullet.damage, player, particles): 
                    create_explosion(hit.pos, color, 20 if group_idx != 0 else 15, particles)
                    game_manager.handle_exp(player, exp_val, current_stage)
                    
        # 보스 총알 판정
        if boss_group.sprite and not getattr(boss_group.sprite, 'is_stealth', False):
            if pygame.sprite.collide_circle(bullet, boss_group.sprite):
                bullet.kill()
                create_explosion(bullet.pos, ORANGE, 8, particles)
                if boss_group.sprite.take_damage(bullet.damage, player, particles):
                    create_explosion(boss_group.sprite.pos, ORANGE, 150, particles)
                    game_manager.boss_cleared_stages.append(current_stage)
                    game_manager.state = "PLAYING"
                    game_manager.handle_exp(player, 50, current_stage)

    # ---------------------------------------------------------
    # 2. 적 -> 플레이어 충돌 판정
    # ---------------------------------------------------------
    if not player.is_invincible:
        hit = False
        dmg_to_take = 0
        
        if boss_group.sprite:
            if hasattr(boss_group.sprite, 'check_laser_collision'):
                laser_dmg = boss_group.sprite.check_laser_collision(player)
                if laser_dmg > 0:
                    hit = True
                    dmg_to_take += laser_dmg

        # 🌟 적 투사체(enemy_projectiles) 개별 처리 방식으로 변경
        # 속박 총알의 특수 효과와 투사체별 개별 데미지를 적용하기 위해 True(자동삭제) 옵션을 끄고 수동으로 처리합니다.
        hit_projectiles = pygame.sprite.spritecollide(player, enemy_projectiles, False, pygame.sprite.collide_circle)
        for proj in hit_projectiles:
            hit = True
            # 투사체 객체에 데미지가 설정되어 있다면 그 값을, 아니면 기본값 1 적용
            dmg_to_take += getattr(proj, 'damage', 1) 
            
            # 속박(BindBullet) 확인 및 플레이어 스턴 적용
            if getattr(proj, 'is_bind', False):
                player.stun_end_time = pygame.time.get_ticks() + proj.stun_duration
                
            # 일반 kill 대신 deactivate가 있다면 풀로 반환
            if hasattr(proj, 'deactivate'):
                proj.deactivate()
            else:
                proj.kill()

        for bomb in bombs:
            # 폭발 중이고, 아직 플레이어에게 데미지를 주지 않았다면
            if bomb.state == "EXPLODING" and not bomb.has_damaged:
                dist = (bomb.pos - player.pos).length()
                # 폭발 반경 안에 플레이어가 들어왔는지 확인
                if dist <= bomb.exp_radius + player.radius:
                    hit = True
                    dmg_to_take += getattr(bomb, 'damage', 2) # 폭탄 데미지 적용
                    bomb.has_damaged = True # 중복 타격 방지 플래그 On!

        for nuk in nuke_group:
            if nuk.state == "EXPLODING" and not nuk.has_damaged:
                dist = (nuk.pos - player.pos).length()
                # 폭발 반경 안에 플레이어가 들어왔는지 확인
                if dist <= nuk.exp_radius + player.radius:
                    hit = True
                    dmg_to_take += getattr(nuk, 'damage', 2) # 폭탄 데미지 적용
                    nuk.has_damaged = True # 중복 타격 방지 플래그 On!

        # 운석 충돌 (자동 삭제 유지)
        if pygame.sprite.spritecollide(player, meteors, True, pygame.sprite.collide_circle): 
            hit = True
            dmg_to_take += 1
            
        # 적 몸통 박치기 (Scout 추가)
        if (pygame.sprite.spritecollide(player, pirates, False, pygame.sprite.collide_circle) or 
            pygame.sprite.spritecollide(player, bombers, False, pygame.sprite.collide_circle) or 
            pygame.sprite.spritecollide(player, scouts, False, pygame.sprite.collide_circle) or 
            pygame.sprite.spritecollide(player, turrets, False, pygame.sprite.collide_circle) or 
            pygame.sprite.spritecollide(player, supports, False, pygame.sprite.collide_circle) or 
            pygame.sprite.spritecollide(player, boss_enemy_group, False, pygame.sprite.collide_circle)):
            hit = True
            dmg_to_take += 1
            
        if boss_group.sprite and pygame.sprite.collide_circle(player, boss_group.sprite): 
            hit = True
            dmg_to_take += 1
        
        # 최종 데미지 적용
        if hit and dmg_to_take > 0:
            if player.take_damage(dmg_to_take): 
                create_explosion(player.pos, GREEN, 20, particles)
            if player.is_destroyed: 
                game_manager.state = "GAME_OVER"

    return player_laser_lines