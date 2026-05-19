import pygame
import math
import random
from settings import *
from asset_loader import SpriteFactory, Base64_Data
from weapons import *
from effects import create_explosion
from enemies import *

# 보스 전용 미사일
class BossMissile(pygame.sprite.Sprite):
    def __init__(self, pool):
        super().__init__()
        self.pool = pool
        config = Base64_Data["MISSILE_B64"]
        self.size = (int(config["size"][0] * 1.5), int(config["size"][1] * 1.5))
        
        raw_frames = SpriteFactory().get_frames(config["b64"], cols=config["cols"], rows=config["rows"])
        
        def local_enhance_color(img):
            base_img = pygame.transform.scale(img, self.size).convert_alpha()
            overlay = base_img.copy()
            overlay.fill((255, 100, 100), special_flags=pygame.BLEND_RGBA_MULT)
            overlay.set_alpha(180) 
            base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            return base_img

        self.frames = [local_enhance_color(img) for img in raw_frames]
        self.anim_speed = 60 
        self.hitbox_size = config["hitbox_size"]
        self.hitbox = pygame.Rect(0, 0, *self.hitbox_size)
        self.lifetime = 4000 

    def reset(self, pos, current_angle, player_level):
        self.pos = pygame.math.Vector2(pos)
        self.hitbox.center = self.pos
        
        self.current_angle = current_angle
        self.image = pygame.transform.rotate(self.frames[0], self.current_angle)
        self.rect = self.image.get_rect(center=self.pos)
        
        self.speed = 12 + (player_level * 0.4) 
        self.rotation_speed = 0.7 + (player_level * 0.03) 
        self.damage = 1
        
        self.spawn_time = pygame.time.get_ticks()
        self.anim_idx = 0
        self.last_anim_update = self.spawn_time

    def update(self, cam_pos, player_obj):
        now = pygame.time.get_ticks()
        if now - self.spawn_time > self.lifetime:
            self.deactivate()
            return
        
        if now - self.last_anim_update > self.anim_speed:
            self.last_anim_update = now
            self.anim_idx = (self.anim_idx + 1) % len(self.frames)
        
        direction = player_obj.pos - self.pos
        if direction.length() > 0:
            target_angle = math.degrees(math.atan2(-direction.y, direction.x))
            angle_diff = (target_angle - self.current_angle + 180) % 360 - 180
            if abs(angle_diff) > self.rotation_speed: 
                self.current_angle += self.rotation_speed if angle_diff > 0 else -self.rotation_speed
            else: 
                self.current_angle = target_angle
                
        rad = math.radians(self.current_angle)
        self.vel = pygame.math.Vector2(math.cos(rad), -math.sin(rad)) * self.speed
        self.pos += self.vel
        
        self.image = pygame.transform.rotate(self.frames[self.anim_idx], self.current_angle - 90)
        self.rect = self.image.get_rect(center=self.pos - cam_pos)
        self.hitbox.center = self.pos

        if not (-500 <= self.pos.x <= MAP_WIDTH + 500 and -500 <= self.pos.y <= MAP_HEIGHT + 500): 
            self.deactivate()

    def deactivate(self):
        self.kill()
        self.pool.return_to_pool(self)

class Chapter1Boss(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        b_data = Base64_Data["C1_BOSS_B64"]
        b64_dict = b_data.get("b64", b_data.get("B64"))
        
        boss_base = b64_dict["C1_BOSS_BASE"]
        boss_engine = b64_dict["C1_BOSS_ENGINE"]
        boss_shield = b64_dict["C1_BOSS_SHIELD"]
        
        self.size = b_data["size"]
        self.radius = b_data["radius"]
        self.hitbox = pygame.Rect(*b_data["hitbox"])
        self.anim_speed = b_data["anim_speed"]
        
        sf = SpriteFactory()
        raw_base = sf.get_frames(boss_base["b64"], cols=boss_base.get("cols", 5), rows=boss_base.get("rows", 1))
        raw_engine = sf.get_frames(boss_engine["b64"], cols=boss_engine.get("cols", 4), rows=1)
        raw_shield = sf.get_frames(boss_shield["b64"], cols=boss_shield.get("cols", 4), rows=1)
        
        # ★ 누락됐던 크기 변환 및 밝기 향상 함수 부활!
        def enhance_color(img, intensity=120):
            base_img = pygame.transform.scale(img, self.size).convert_alpha()
            overlay = base_img.copy()
            overlay.set_alpha(intensity) 
            base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            return base_img

        self.base_frames = [enhance_color(img) for img in raw_base]
        self.engine_frames = [enhance_color(img) for img in raw_engine]
        self.shield_frames = [enhance_color(img) for img in raw_shield]
        
        self.pos = pygame.math.Vector2(MAP_WIDTH // 2, -300)
        self.target_pos = pygame.math.Vector2(MAP_WIDTH // 2, MAP_HEIGHT // 2)
        self.max_hp = 1200
        self.hp = self.max_hp
        self.current_angle = 90
        self.target_angle = 90
        
        self.state = "SPAWN"
        self.pattern = None
        self.pattern_timer = pygame.time.get_ticks()

        self.boss_missile_pool = ObjectPool(BossMissile, initial_size=100)
        self.boss_bullet_pool = ObjectPool(Bullet, initial_size=200, owner_class_name="Boss")
        
        self.anim_idx_base = 0
        self.anim_idx_engine = 0
        self.anim_idx_shield = 0
        self.last_anim_update = pygame.time.get_ticks()
        
        self.barrage_tick = 0
        self.shield_active = False
        self.shield_angle = 0 
        self.laser_active = False
        self.laser_start = None
        self.laser_dir = None
        self.summon_tick = 0

    def take_damage(self, amount, player_obj, particle_group):
        if self.state in ["SPAWN", "EXPLODING"]: return False
        if self.state == "DESPERATION": amount *= 0.5
            
        self.hp -= amount
        player_obj.trigger_vampire(particle_group)
        
        if self.hp <= 0:
            self.hp = 0
            self.state = "EXPLODING"
            self.anim_idx_base = 1
            return True
        if self.hp <= self.max_hp * 0.1 and self.state != "DESPERATION":
            self.state = "DESPERATION"
            self.target_pos = pygame.math.Vector2(MAP_WIDTH // 2, MAP_HEIGHT // 2)
            self.shield_active = True

            self.laser_active = False 
            self.shield_active = False
            self.pattern = None
        return False

    def update(self, cam_pos, player_obj, enemy_proj_group, pirates_group, current_stage, clock):
        now = pygame.time.get_ticks()
        
        # 1. 이동 및 회전
        if self.state != "EXPLODING":
            if self.state == "DESPERATION":
                self.pos = self.pos.lerp(pygame.math.Vector2(MAP_WIDTH//2, MAP_HEIGHT//2), 0.05)
                self.shield_active = True
            else:
                if self.pos.distance_to(self.target_pos) < 20:
                    if self.state == "SPAWN": 
                        self.state = "IDLE"
                    elif self.state == "IDLE":
                        offset = pygame.math.Vector2(random.randint(-500, 500), random.randint(-500, 500))
                        self.target_pos = player_obj.pos + offset
                        
                        margin = self.size[0] // 2
                        
                        self.target_pos.x = max(margin, min(MAP_WIDTH - margin, self.target_pos.x))
                        self.target_pos.y = max(margin, min(MAP_HEIGHT - margin, self.target_pos.y))
                        
                self.pos = self.pos.lerp(self.target_pos, 0.02)

            margin = self.size[0] // 2 
            
            if self.pos.x < margin:
                self.pos.x = margin
            elif self.pos.x > MAP_WIDTH - margin:
                self.pos.x = MAP_WIDTH - margin
                
            if self.pos.y < margin:
                self.pos.y = margin
            elif self.pos.y > MAP_HEIGHT - margin:
                self.pos.y = MAP_HEIGHT - margin

            self.hitbox.center = self.pos
            
            face_dir = player_obj.pos - self.pos
            if face_dir.length() > 0:
                self.target_angle = math.degrees(math.atan2(-face_dir.x, -face_dir.y))
            angle_diff = (self.target_angle - self.current_angle + 180) % 360 - 180
            self.current_angle += 2 if angle_diff > 0 else -2 if abs(angle_diff) > 2 else angle_diff

        # 2. 패턴 제어
        if self.state == "IDLE":
            if now - self.pattern_timer > 2500:
                self.pattern_timer = now
                patterns = ["BARRAGE", "SUMMON"]
                if self.hp < self.max_hp * 0.6: patterns.append("SHIELD_LASER")
                if self.hp < self.max_hp * 0.5: patterns.append("MISSILE")
                self.pattern = random.choice(patterns)
                self.state = "PATTERN"

        elif self.state == "PATTERN":
            if self.pattern == "BARRAGE":
                if now - self.barrage_tick > 80: 
                    self.barrage_tick = now
                    perp_dir = pygame.math.Vector2(1, 0).rotate(-self.current_angle)
                    offset = perp_dir * random.uniform(-self.hitbox.width/2, self.hitbox.width/2)
                    shoot_dir = pygame.math.Vector2(0, -1).rotate(-self.current_angle)
                    enemy_proj_group.add(self.boss_bullet_pool.get(self.pos + offset, shoot_dir, 1, self, speed=14))
                if now - self.pattern_timer > 3000: self.state = "IDLE"

            elif self.pattern == "MISSILE":
                if now - self.barrage_tick > 100:
                    self.barrage_tick = now
                    random_angle = random.uniform(0, 360) 
                    enemy_proj_group.add(self.boss_missile_pool.get(self.pos, random_angle, player_obj.level))
                if now - self.pattern_timer > 2000: self.state = "IDLE"

            elif self.pattern == "SUMMON":
                p = Pirate(player_obj, current_stage)
                p.pos = pygame.math.Vector2(self.pos); pirates_group.add(p)
                self.state = "IDLE"

            elif self.pattern == "SHIELD_LASER":
                if not self.shield_active and not self.laser_active:
                    face_dir = player_obj.pos - self.pos
                    if face_dir.length() > 0:
                        self.shield_angle = math.degrees(math.atan2(-face_dir.x, -face_dir.y))
                
                self.shield_active = True
                
                if face_dir.length() > 0:
                    target_angle = math.degrees(math.atan2(-face_dir.x, -face_dir.y))
                    angle_diff = (target_angle - self.shield_angle + 180) % 360 - 180
                    
                    track_speed = 0.5 # 쉴드의 일정한 회전 속도 (필요시 조절)
                    if abs(angle_diff) > track_speed:
                        self.shield_angle += track_speed if angle_diff > 0 else -track_speed
                    else:
                        self.shield_angle += angle_diff

                # 레이저 방향도 오직 쉴드의 각도(shield_angle)에만 맞춰서 발사
                self.laser_dir = pygame.math.Vector2(0, -1).rotate(-self.shield_angle)
                self.laser_start = self.pos + self.laser_dir * ((self.size[0] / 2) + 20)
                
                if now - self.pattern_timer > 1500: 
                    self.laser_active = True
                    if now - self.pattern_timer > 4500:
                        self.shield_active = False
                        self.laser_active = False
                        self.state = "IDLE"

        elif self.state == "DESPERATION":
            self.shield_angle += 2
            if now - self.barrage_tick > 1000:
                self.barrage_tick = now
                for i in range(4):
                    enemy_proj_group.add(self.boss_missile_pool.get(self.pos, self.shield_angle + (i*90), player_obj.level))
            if now - self.summon_tick > 4000:
                self.summon_tick = now
                p = Pirate(player_obj, current_stage); p.pos = pygame.math.Vector2(self.pos); pirates_group.add(p)

        # 3. 애니메이션 및 이미지 생성
        if now - self.last_anim_update > self.anim_speed:
            self.last_anim_update = now
            if self.state == "EXPLODING":
                self.anim_idx_base += 1
                if self.anim_idx_base >= len(self.base_frames): self.kill()
            else:
                self.anim_idx_engine = (self.anim_idx_engine + 1) % len(self.engine_frames)
                self.anim_idx_shield = (self.anim_idx_shield + 1) % len(self.shield_frames)

        # 쉴드가 밖으로 밀려나도 잘리지 않도록 그리기 캔버스(temp_surf)를 2.5배 넉넉하게 만듭니다.
        canvas_size = (int(self.size[0] * 2.5), int(self.size[1] * 2.5))
        temp_surf = pygame.Surface(canvas_size, pygame.SRCALPHA)
        center_x, center_y = canvas_size[0] // 2, canvas_size[1] // 2

        # 1. 보스 본체 그리기 (current_angle로 독립 회전)
        boss_img = pygame.Surface(self.size, pygame.SRCALPHA)
        if self.state != "EXPLODING":
            boss_img.blit(self.engine_frames[self.anim_idx_engine], (0, 0))
        if len(self.base_frames) > 0:
            self.anim_idx_base = self.anim_idx_base % len(self.base_frames)
            boss_img.blit(self.base_frames[self.anim_idx_base], (0, 0))
        
        r_boss = pygame.transform.rotate(boss_img, self.current_angle)
        temp_surf.blit(r_boss, r_boss.get_rect(center=(center_x, center_y)))
        
        # 2. 쉴드 그리기 (shield_angle로 독립 회전)
        if self.shield_active:
            shield_img = self.shield_frames[self.anim_idx_shield]
            distance = self.size[0] / 2 # 보스와 쉴드 사이의 궤도 거리
            
            if self.state == "DESPERATION":
                for i in range(4): 
                    angle = self.shield_angle + (i*90)
                    r_shield = pygame.transform.rotate(shield_img, angle)
                    offset = pygame.math.Vector2(0, -1).rotate(-angle) * distance
                    r_rect = r_shield.get_rect(center=(center_x + offset.x, center_y + offset.y))
                    temp_surf.blit(r_shield, r_rect)
            else:
                r_shield = pygame.transform.rotate(shield_img, self.shield_angle)
                offset = pygame.math.Vector2(0, -1).rotate(-self.shield_angle) * distance
                r_rect = r_shield.get_rect(center=(center_x + offset.x, center_y + offset.y))
                temp_surf.blit(r_shield, r_rect)

        # 도화지를 통째로 회전시키지 않고 그대로 image로 사용합니다.
        self.image = temp_surf
        self.rect = self.image.get_rect(center=self.pos - cam_pos)

    def draw_effects(self, surface, cam_pos):
        from weapons import render_glowing_laser
        if self.laser_active and self.laser_start and self.laser_dir:
            start_screen = self.laser_start - cam_pos
            end_screen = start_screen + self.laser_dir * 2000
            render_glowing_laser(surface, start_screen, end_screen, (255, 30, 30), 5)

    def check_laser_collision(self, player_obj):
        if self.laser_active and self.laser_start and self.laser_dir:
            vec_to_player = player_obj.pos - self.laser_start
            projection = vec_to_player.dot(self.laser_dir)
            if projection > 0:
                closest_point = self.laser_start + self.laser_dir * projection
                if player_obj.pos.distance_to(closest_point) < 30 + player_obj.radius:
                    return 2
        return 0

class HomingNuke(pygame.sprite.Sprite):
    _cached_nuke_frames = []
    _cached_exp_frames = []

    def __init__(self, start_pos, player_obj):
        super().__init__()
        self.player = player_obj
        self.pos = pygame.math.Vector2(start_pos)
        
        # --- 1. 클래스 캐시 굽기 (최초 1회) ---
        if not HomingNuke._cached_nuke_frames:
            missile_b64 = Base64_Data["MISSILE_B64"]
            m_cols, m_rows = missile_b64.get("cols", 40), missile_b64.get("rows", 25)
            missile_indices = [0, 1, 2]
            
            base_m_size = missile_b64.get("size", (32, 32))
            self.nuke_size = (base_m_size[0] * 4, base_m_size[1] * 4) 
            raw_missile = SpriteFactory().get_frames(missile_b64["b64"], cols=m_cols, rows=m_rows)
            
            b_data = Base64_Data["bomb"]["B64"]
            exp_b64 = b_data["explosion"]
            exp_cols, exp_rows = exp_b64.get("cols", 12), exp_b64.get("rows", 9)
            exp_indices = exp_b64.get("indices", [0,1,2,3,4,5,6,7,8,9,11])
            
            base_exp_size = exp_b64.get("size", (150, 150))
            visual_scale = 5.0 
            visual_exp_size = (int(base_exp_size[0] * visual_scale), int(base_exp_size[1] * visual_scale))
            raw_exp = SpriteFactory().get_frames(exp_b64["b64"], cols=exp_cols, rows=exp_rows)

            def enhance_color(img, target_size, intensity=160, tint=None):
                base_img = pygame.transform.scale(img, target_size).convert_alpha()
                if tint:
                    s = pygame.Surface(target_size, pygame.SRCALPHA)
                    s.fill((*tint, 255))
                    base_img.blit(s, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                
                overlay = base_img.copy()
                overlay.set_alpha(intensity) 
                base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                return base_img

            HomingNuke._cached_nuke_frames.extend([
                enhance_color(raw_missile[i], self.nuke_size, tint=(255, 50, 0)) for i in missile_indices
            ])
            HomingNuke._cached_exp_frames.extend([
                enhance_color(raw_exp[i], visual_exp_size, intensity=180) for i in exp_indices
            ])
            
        self.nuke_frames = HomingNuke._cached_nuke_frames
        self.exp_frames = HomingNuke._cached_exp_frames
        
        exp_b64 = Base64_Data["bomb"]["B64"]["explosion"]
        base_hitbox = exp_b64.get("hitbox", (150, 150))[0] // 2
        self.exp_radius = int(base_hitbox * 2.5) 
        
        self.speed = 1.5           
        self.rotation_speed = 0.5  
        self.damage = 5            
        
        self.state = "CHASING" 
        self.current_angle = 0
        self.anim_idx = 0
        self.has_damaged = False
        
        now = pygame.time.get_ticks()
        self.last_anim_update = now

        self.spawn_time = now
        self.lifetime = 9999999
        self.life_time = 9999999
        
        self.nuke_timer_start = now
        self.nuke_fuse_time = 8000

        self.image = self.nuke_frames[0]
        self.rect = self.image.get_rect(center=self.pos)

    def update(self, cam_pos, player_obj=None, **kwargs):
        target_player = player_obj if player_obj else self.player
        now = pygame.time.get_ticks()
        
        if self.state == "CHASING":
            direction = target_player.pos - self.pos
            if direction.length() > 0:
                target_angle = math.degrees(math.atan2(-direction.y, direction.x))
                angle_diff = (target_angle - self.current_angle + 180) % 360 - 180
                
                if abs(angle_diff) > self.rotation_speed:
                    self.current_angle += self.rotation_speed if angle_diff > 0 else -self.rotation_speed
                else:
                    self.current_angle = target_angle
                    
            rad = math.radians(self.current_angle)
            self.vel = pygame.math.Vector2(math.cos(rad), -math.sin(rad)) * self.speed
            self.pos += self.vel
            
            if now - self.last_anim_update > 80:
                self.last_anim_update = now
                self.anim_idx = (self.anim_idx + 1) % len(self.nuke_frames)
                
            self.image = pygame.transform.rotate(self.nuke_frames[self.anim_idx], self.current_angle - 90)
            self.rect = self.image.get_rect(center=self.pos - cam_pos)
            
            # ★ 내부 타이머(nuke_fuse_time)로 기폭 조건 확인
            dist_to_player = self.pos.distance_to(target_player.pos)
            hit_condition = dist_to_player < (20 + 30) 
            time_condition = (now - self.nuke_timer_start > self.nuke_fuse_time)
            
            if hit_condition or time_condition:
                self.state = "EXPLODING" 
                self.last_anim_update = now
                self.anim_idx = 0
                
                # 가짜 수명을 폭발 시간 내내 유지하도록 갱신해줌
                self.spawn_time = now 
                
                self.image = self.exp_frames[0]
                self.rect = self.image.get_rect(center=self.pos - cam_pos)
                
        elif self.state == "EXPLODING":
            if not self.has_damaged:
                dist = self.pos.distance_to(target_player.pos)
                if dist < self.exp_radius + 20: 
                    if hasattr(target_player, 'take_damage'):
                        target_player.take_damage(self.damage)
                self.has_damaged = True
                
            if now - self.last_anim_update > 60:
                self.last_anim_update = now
                self.anim_idx += 1
                
                if self.anim_idx >= len(self.exp_frames):
                    self.kill()
                    return
                    
            self.image = self.exp_frames[self.anim_idx]
            self.rect = self.image.get_rect(center=self.pos - cam_pos)

    def draw(self, screen, cam_pos):
        screen_pos = self.pos - cam_pos
        
        if self.state == "CHASING":
            # ★ 내부 타이머 기준 점멸 효과 적용
            elapsed = pygame.time.get_ticks() - self.nuke_timer_start
            progress = min(1.0, elapsed / self.nuke_fuse_time) 
            
            blink_interval = max(50, 500 - int(progress * 450))
            
            pygame.draw.circle(screen, (139, 0, 0), screen_pos, int(self.exp_radius), 1)
            
            if (elapsed % blink_interval) < (blink_interval // 2):
                thickness = max(1, int(5 * progress)) 
                pygame.draw.circle(screen, (255, 0, 0), screen_pos, int(self.exp_radius), thickness)
                
                danger_surf = pygame.Surface((self.exp_radius * 2, self.exp_radius * 2), pygame.SRCALPHA)
                alpha = int(80 * progress) 
                pygame.draw.circle(danger_surf, (255, 0, 0, alpha), (self.exp_radius, self.exp_radius), self.exp_radius)
                screen.blit(danger_surf, screen_pos - pygame.math.Vector2(self.exp_radius, self.exp_radius))

            screen.blit(self.image, self.rect)
                
        elif self.state == "EXPLODING":
            screen.blit(self.image, self.rect)
class Chapter2Boss(pygame.sprite.Sprite):
    _cached_base_frames = []
    _cached_engine_frames = []
    _cached_shield_frames = []

    def __init__(self, player_obj, diff_level):
        super().__init__()
        self.diff_level = diff_level
        
        b_data = Base64_Data["C2_BOSS_B64"]  
        b64_dict = b_data.get("b64", b_data.get("B64"))
        
        boss_base = b64_dict["C2_BOSS_BASE"]
        boss_engine = b64_dict["C2_BOSS_ENGINE"]
        boss_shield = b64_dict["C2_BOSS_SHIELD"]
        
        self.size = b_data["size"]
        self.radius = b_data["radius"]
        self.hitbox = pygame.Rect(*b_data["hitbox"])
        self.anim_speed = b_data.get("anim_speed", 60)
        
        if not Chapter2Boss._cached_base_frames:
            sf = SpriteFactory()
            raw_base = sf.get_frames(boss_base["b64"], cols=boss_base.get("cols", 5), rows=boss_base.get("rows", 1))
            raw_engine = sf.get_frames(boss_engine["b64"], cols=boss_engine.get("cols", 4), rows=boss_engine.get("rows", 1))
            raw_shield = sf.get_frames(boss_shield["b64"], cols=boss_shield.get("cols", 4), rows=boss_shield.get("rows", 1))
            
            def enhance_color(img, intensity=120):
                base_img = pygame.transform.scale(img, self.size).convert_alpha()
                overlay = base_img.copy()
                overlay.set_alpha(intensity) 
                base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                return base_img

            Chapter2Boss._cached_base_frames.extend([enhance_color(img) for img in raw_base])
            Chapter2Boss._cached_engine_frames.extend([enhance_color(img) for img in raw_engine])
            Chapter2Boss._cached_shield_frames.extend([enhance_color(img) for img in raw_shield])
            
        self.base_frames = Chapter2Boss._cached_base_frames
        self.engine_frames = Chapter2Boss._cached_engine_frames
        self.shield_frames = Chapter2Boss._cached_shield_frames

        self.boss_bullet_pool = ObjectPool(Bullet, initial_size=300, owner_class_name="Boss")
        self.boss_bomb_pool = ObjectPool(Bomb, initial_size=50, owner_class_name="Boss")

        self.pos = pygame.math.Vector2(MAP_WIDTH // 2, -300)
        self.vel = pygame.math.Vector2(0, 0)
        self.speed = 3.5 
        
        self.orbit_angle = random.uniform(0, 360) 
        self.orbit_dist = random.uniform(500, 650) 
        self.orbit_speed = random.uniform(0.5, 0.8) 
        
        self.max_hp = 5000 + (diff_level * 1000)
        self.hp = self.max_hp
        self.current_angle = 0
        self.target_angle = 0
        
        self.state = "SPAWN"
        self.is_shielded = False
        self.is_desperation_done = False
        self.shockwave_hit = False # 충격파 데미지 1회 판정용
        
        self.last_skill_time = pygame.time.get_ticks()
        self.skill_cooldown = 4000
        self.current_skill = None
        
        self.anim_idx_base = 0
        self.anim_idx_engine = 0
        self.anim_idx_shield = 0
        self.last_anim_update = pygame.time.get_ticks()
        
        self.skills_config = {
            "SPRAY": {"min_hp": 1.0, "weight": 25},
            "DASH":  {"min_hp": 0.8, "weight": 20},
            "BOMB":  {"min_hp": 1.0, "weight": 20},
            "LASER": {"min_hp": 0.4, "weight": 20},
            "NUKE":  {"min_hp": 0.6, "weight": 15} 
        }

    def execute_teleport(self, target_pos, callback_state, callback_phase):
        self.state = "TELEPORTING"
        self.teleport_target = pygame.math.Vector2(target_pos)
        self.teleport_timer = pygame.time.get_ticks()
        self.teleport_phase = "WARNING"
        self.teleport_callback_state = callback_state
        self.teleport_callback_phase = callback_phase
        self.shockwave_hit = False # 텔레포트마다 데미지 플래그 초기화

    def take_damage(self, amount, player_obj, particle_group):
        if self.state in ["SPAWN", "DEAD"]: return False
        
        actual_damage = amount * 0.5 if self.is_shielded else amount
        self.hp -= actual_damage
        player_obj.trigger_vampire(particle_group)
        
        if self.hp <= self.max_hp * 0.1 and not self.is_desperation_done and self.state != "DESPERATION_SEQ":
            if not getattr(self, 'is_desp_started', False):
                self.is_desp_started = True
                self.state = "DESPERATION_SEQ"
                self.desp_count = 0  
                self.desp_phase = "TELEPORT_EDGE"
                
        if self.hp <= 0:
            self.hp = 0
            self.state = "DEAD"
            self.anim_idx_base = 1
            return True
        return False

    def start_random_skill(self, player_obj, nuke_group):
        hp_ratio = self.hp / self.max_hp
        available = [name for name, conf in self.skills_config.items() if hp_ratio <= conf["min_hp"]]
        weights = [self.skills_config[name]["weight"] for name in available]
        
        if available:
            chosen_skill = random.choices(available, weights=weights, k=1)[0]
            
            if chosen_skill == "LASER":
                self.execute_teleport((MAP_WIDTH // 2, MAP_HEIGHT // 2), "CASTING_SKILL", "LASER_PHASE_A")
            elif chosen_skill == "NUKE":
                self.state = "CASTING_SKILL"
                self.current_skill = "NUKE"
                self.skill_timer = pygame.time.get_ticks()
                nuke_group.add(HomingNuke(self.pos, player_obj))
            else:
                self.state = "CASTING_SKILL"
                self.current_skill = chosen_skill
                self.skill_timer = pygame.time.get_ticks()
                
                if self.current_skill == "SPRAY":
                    self.spray_count = 0  
                elif self.current_skill == "DASH":
                    self.dash_phase = "WARNING"
                    dir_vec = player_obj.pos - self.pos
                    self.dash_dir = dir_vec.normalize() if dir_vec.length() > 0 else pygame.math.Vector2(0, -1)
                    self.target_angle = math.degrees(math.atan2(-self.dash_dir.x, -self.dash_dir.y))
                    self.dash_start_pos = self.pos.copy()
                    self.spawned_mobs = 0
                elif self.current_skill == "BOMB":
                    self.bombs_thrown = 0

    def update(self, cam_pos, player_obj, enemy_proj_group, bomb_group, nuke_group, mob_groups, current_stage, clock):
        now = pygame.time.get_ticks()
        
        if self.state != "DEAD":
            
            # ==========================================
            # 💡 서브 스킬: 순간이동 로직 (원형 충격파 적용)
            # ==========================================
            if self.state == "TELEPORTING":
                self.vel *= 0
                if self.teleport_phase == "WARNING":
                    if now - self.teleport_timer > 400: 
                        self.pos = self.teleport_target.copy()
                        self.teleport_phase = "SHOCKWAVE"
                        self.shockwave_timer = now
                        
                elif self.teleport_phase == "SHOCKWAVE":
                    elapsed = now - self.shockwave_timer
                    
                    # 충격파 데미지 판정: 반지름이 커졌다 작아지는 흐름에 맞춰 계산
                    scale = math.sin((elapsed / 500) * math.pi)
                    max_radius = self.size[1] // 2 + 50
                    current_radius = max_radius * scale
                    
                    if self.pos.distance_to(player_obj.pos) < current_radius:
                        if hasattr(player_obj, 'take_damage') and not self.shockwave_hit:
                            player_obj.take_damage(2) 
                            self.shockwave_hit = True
                            
                    if elapsed > 500: 
                        self.state = self.teleport_callback_state
                        
                        if self.teleport_callback_state == "CASTING_SKILL":
                            self.current_skill = "LASER"
                            self.laser_phase = "PHASE_A"
                            self.skill_timer = now
                            self.laser_bullet_tick = 0
                            self.scatter_tick = 0
                            
                            # ★ 레이저(블랙홀) 시작 시 강제로 위를 보도록(0도) 설정
                            self.current_angle = 0
                            self.target_angle = 0
                            
                        elif self.teleport_callback_state == "DESPERATION_SEQ":
                            self.desp_phase = self.teleport_callback_phase
                            self.skill_timer = now

            # ==========================================
            # 💡 페이즈 2: 발악 패턴 로직 (생략 - 기존과 동일하게 유지)
            # ==========================================
            elif self.state == "DESPERATION_SEQ":
                if self.desp_phase == "TELEPORT_EDGE":
                    edge_x = random.choice([200, MAP_WIDTH - 200])
                    edge_y = random.choice([200, MAP_HEIGHT - 200])
                    # 텔레포트 스킬 실행 후, 끝나면 DASH_START로 돌아오게 예약
                    self.execute_teleport((edge_x, edge_y), "DESPERATION_SEQ", "DASH_START")
                    
                elif self.desp_phase == "DASH_START":
                    # 💡 여기가 핵심! 기존 돌진 스킬로 상태를 넘겨버립니다.
                    self.state = "CASTING_SKILL"
                    self.current_skill = "DASH"
                    self.skill_timer = now
                    self.dash_phase = "WARNING"
                    self.dash_start_pos = self.pos.copy()
                    self.spawned_mobs = 0
                    
                    self.is_desp_dashing = True # 발악 중인 대시라는 '꼬리표' 달기
                    if not hasattr(self, 'desp_count'): self.desp_count = 0
                    
                    dir_vec = player_obj.pos - self.pos
                    self.dash_dir = dir_vec.normalize() if dir_vec.length() > 0 else pygame.math.Vector2(0, 1)
                    self.target_angle = math.degrees(math.atan2(-self.dash_dir.x, -self.dash_dir.y))
                    
                elif self.desp_phase == "TELEPORT_CENTER":
                    # 중앙 텔레포트 후 쉴드 켜기로 예약
                    self.execute_teleport((MAP_WIDTH // 2, MAP_HEIGHT // 2), "DESPERATION_SEQ", "SHIELD_ON")
                    
                elif self.desp_phase == "SHIELD_ON":
                    self.is_shielded = True
                    self.is_desperation_done = True
                    self.state = "MOVING"
                    self.last_skill_time = now

            # ==========================================
            # 💡 일반 순항 & 진입
            # ==========================================
            elif not (self.state == "CASTING_SKILL" and self.current_skill in ["DASH", "LASER"]):
                self.orbit_angle = (self.orbit_angle + self.orbit_speed) % 360
                rad = math.radians(self.orbit_angle)
                target_pos = player_obj.pos + pygame.math.Vector2(math.cos(rad) * self.orbit_dist, math.sin(rad) * self.orbit_dist)
                
                direction = target_pos - self.pos
                if direction.length() > 0:
                    self.vel = self.vel.lerp(direction.normalize() * min(self.speed, direction.length() * 0.05), 0.05)
                else:
                    self.vel *= 0.8
                self.pos += self.vel
                
                if self.vel.length() > 0.1:
                    self.target_angle = math.degrees(math.atan2(-self.vel.x, -self.vel.y))

            if self.state == "SPAWN":
                if self.pos.distance_to(player_obj.pos) < self.orbit_dist + 150:
                    self.state = "MOVING"
                    self.last_skill_time = now

            if self.state == "MOVING" and now - self.last_skill_time > self.skill_cooldown:
                self.start_random_skill(player_obj, nuke_group)
                    
            # ==========================================
            # 💡 액티브 스킬 로직
            # ==========================================
            elif self.state == "CASTING_SKILL":
                if self.current_skill == "SPRAY":
                    # 예: 100ms 마다 총알 1발씩 발사 (간격은 원하는 대로 조절)
                    if now - self.skill_timer > 100: 
                        self.skill_timer = now
                        self.spray_count += 1
                        
                        # 플레이어 방향을 향해 부채꼴(-30도 ~ +30도)로 난사
                        dir_vec = player_obj.pos - self.pos
                        if dir_vec.length() > 0:
                            base_angle = math.degrees(math.atan2(-dir_vec.x, -dir_vec.y))
                        else:
                            base_angle = self.current_angle
                            
                        # 약간의 랜덤 각도를 더해서 흩뿌리기
                        spread_angle = base_angle + random.uniform(-30, 30)
                        rad = math.radians(spread_angle)
                        
                        # 삼각함수로 다시 방향 벡터 생성 (Pygame 좌표계 맞춤)
                        spray_dir = pygame.math.Vector2(-math.sin(rad), -math.cos(rad))
                        
                        # 총알 스폰 (속도는 10~15 사이 랜덤)
                        rand_speed = random.uniform(10, 15)
                        bullet = self.boss_bullet_pool.get(self.pos, spray_dir, 1, self, speed=rand_speed)
                        enemy_proj_group.add(bullet)
                        
                        # ★ 여기가 제일 중요합니다! 목표치(예: 20발)를 다 쐈으면 스킬 강제 종료!
                        if self.spray_count >= 20: 
                            self.state = "MOVING"
                            self.last_skill_time = now

                elif self.current_skill == "DASH":
                    if self.dash_phase == "WARNING":
                        self.vel *= 0.8 
                        self.pos += self.vel
                        if now - self.skill_timer > 1000:
                            self.dash_phase = "DASHING"
                    elif self.dash_phase == "DASHING":
                        self.vel = self.dash_dir * 35.0 
                        self.pos += self.vel
                        
                        dist_traveled = (self.pos - self.dash_start_pos).length()
                        expected_mobs = min(4, int(dist_traveled / 400))
                        
                        while self.spawned_mobs < expected_mobs:
                            self.spawned_mobs += 1
                            MobClass = random.choice([Pirate, Bomber])
                            new_mob = MobClass(player_obj, self.diff_level) 
                            new_mob.pos = self.pos.copy() 
                            if MobClass == Pirate: mob_groups["pirates"].add(new_mob)
                            else: mob_groups["bombers"].add(new_mob)
                        
                        margin = self.radius + 100
                        # 벽에 박아서 대시가 끝났을 때
                        if self.pos.x <= margin or self.pos.x >= MAP_WIDTH - margin or \
                           self.pos.y <= margin or self.pos.y >= MAP_HEIGHT - margin:
                            
                            # 🌟 방금 한 대시가 발악 패턴 꼬리표가 붙은 대시였다면?
                            if getattr(self, 'is_desp_dashing', False):
                                self.is_desp_dashing = False
                                self.desp_count += 1
                                self.state = "DESPERATION_SEQ" # 발악 시퀀스로 복귀
                                
                                if self.desp_count < 4:
                                    self.desp_phase = "TELEPORT_EDGE" # 4번 채울 때까지 다시 가장자리로
                                else:
                                    self.desp_phase = "TELEPORT_CENTER" # 다 채웠으면 중앙으로
                            else:
                                # 일반 대시면 평소처럼 대기 상태로 복귀
                                self.state = "MOVING"
                                self.last_skill_time = now
                            
                elif self.current_skill == "BOMB":
                    if now - self.skill_timer > 200:
                        self.skill_timer = now
                        self.bombs_thrown += 1
                        
                        target = player_obj.pos + (player_obj.vel * 30)
                        offset = pygame.math.Vector2(random.uniform(-150, 150), random.uniform(-150, 150))
                        drop_pos = target + offset
                        
                        drop_pos.x = max(50, min(MAP_WIDTH - 50, drop_pos.x))
                        drop_pos.y = max(50, min(MAP_HEIGHT - 50, drop_pos.y))
                        
                        boss_bomb = self.boss_bomb_pool.get(start_pos=self.pos, target_pos=drop_pos, damage=2, speed=15)
                        bomb_group.add(boss_bomb)
                        
                        if self.bombs_thrown >= 8:
                            self.state = "MOVING"
                            self.last_skill_time = now

                elif self.current_skill == "NUKE":
                    if now - self.skill_timer > 1000: 
                        self.state = "MOVING"
                        self.last_skill_time = now

                # ★ 블랙홀 및 거대 레이저 패턴
                elif self.current_skill == "LASER":
                    self.laser_dir = pygame.math.Vector2(0, -1).rotate(-self.current_angle)
                    self.gather_point = self.pos + (self.laser_dir * (self.size[1] // 2))
                    
                    # [공통] PHASE_A와 PHASE_B 동안 거점에 도달한 블랙홀 총알 파기 (잔여 총알 정리)
                    if self.laser_phase in ["PHASE_A", "PHASE_B"]:
                        for bullet in enemy_proj_group.sprites():
                            if getattr(bullet, 'owner', None) == self:
                                if bullet.pos.distance_to(self.gather_point) < 40: 
                                    if hasattr(bullet, 'deactivate'): bullet.deactivate()
                                    else: bullet.kill()

                    if self.laser_phase == "PHASE_A": 
                        self.vel *= 0.9 
                        elapsed = now - self.skill_timer
                        
                        # 총알 스폰 주기 80ms -> 60ms 로 단축 (더 많이 소환)
                        if now - self.laser_bullet_tick > 60:
                            self.laser_bullet_tick = now
                            
                            # 맵의 경계(상/하/좌/우) 중 한 곳을 랜덤으로 선택
                            edge = random.randint(0, 3)
                            margin = 20 # 맵 밖 파기 로직에 걸리지 않도록 맵 안쪽으로 20픽셀 들여서 스폰
                            
                            if edge == 0:   # 위
                                edge_pos = pygame.math.Vector2(random.uniform(margin, MAP_WIDTH - margin), margin)
                            elif edge == 1: # 아래
                                edge_pos = pygame.math.Vector2(random.uniform(margin, MAP_WIDTH - margin), MAP_HEIGHT - margin)
                            elif edge == 2: # 왼쪽
                                edge_pos = pygame.math.Vector2(margin, random.uniform(margin, MAP_HEIGHT - margin))
                            else:           # 오른쪽
                                edge_pos = pygame.math.Vector2(MAP_WIDTH - margin, random.uniform(margin, MAP_HEIGHT - margin))
                            
                            b_dir = (self.gather_point - edge_pos)
                            if b_dir.length() > 0:
                                # 총알마다 속도를 12 ~ 28 사이로 무작위 부여하여 흩뿌려지며 모이는 느낌 강조
                                rand_speed = random.uniform(12, 28)
                                enemy_proj_group.add(self.boss_bullet_pool.get(edge_pos, b_dir.normalize(), 1, self, speed=rand_speed))
                                        
                        if elapsed > 4000: 
                            self.laser_phase = "PHASE_B"
                            self.skill_timer = now
                            
                    elif self.laser_phase == "PHASE_B": 
                        elapsed = now - self.skill_timer
                        
                        # 2초 동안 조준 및 잔여 총알 모으기 (새 총알 생성 안 함)
                        dir_vec = player_obj.pos - self.pos
                        if dir_vec.length() > 0:
                            self.target_angle = math.degrees(math.atan2(-dir_vec.x, -dir_vec.y))
                        
                        if elapsed > 2000: 
                            self.laser_phase = "PHASE_C"
                            self.skill_timer = now
                            
                    elif self.laser_phase == "PHASE_C": 
                        elapsed = now - self.skill_timer
                        
                        dir_vec = player_obj.pos - self.pos
                        if dir_vec.length() > 0:
                            self.target_angle = math.degrees(math.atan2(-dir_vec.x, -dir_vec.y))
                            
                        proj_len = (player_obj.pos - self.pos).dot(self.laser_dir)
                        if proj_len > 0:
                            closest_pt = self.pos + self.laser_dir * proj_len
                            if (player_obj.pos - closest_pt).length() < player_obj.radius + 80: 
                                if hasattr(player_obj, 'take_damage'): player_obj.take_damage(2) 

                        # ★ 레이저 뿜을 때 발사되는 스파크 총알(발사량) 대폭 상향
                        if now - self.scatter_tick > 80:  # 기존 150ms -> 80ms 틱 단축
                            self.scatter_tick = now
                            for _ in range(8):  # 기존 3발 -> 한 틱당 8발씩 폭발적으로 뿜어냄
                                angle = math.radians(random.uniform(0, 360))
                                scatter_dir = pygame.math.Vector2(math.cos(angle), math.sin(angle))
                                # 스파크 총알 속도도 불규칙하게(8~20) 세팅
                                rand_speed = random.uniform(8, 20)
                                enemy_proj_group.add(self.boss_bullet_pool.get(self.gather_point, scatter_dir, 1, self, speed=rand_speed))

                        if elapsed > 2500: 
                            self.state = "MOVING"
                            self.last_skill_time = now

            # ==========================================
            # 💡 회전 및 애니메이션, 렌더링
            # ==========================================
            if self.state != "TELEPORTING":
                margin = self.size[0] // 2 
                self.pos.x = max(margin, min(MAP_WIDTH - margin, self.pos.x))
                self.pos.y = max(margin, min(MAP_HEIGHT - margin, self.pos.y))
                self.hitbox.center = self.pos

                # 레이저 발사 중이거나 조준 중(PHASE_B)일 때도 공통으로 이 회전 로직을 탑니다!
                turn_speed = 5  # 기본 회전 속도
                if self.state == "CASTING_SKILL" and self.current_skill == "LASER":
                    if getattr(self, "laser_phase", "") == "PHASE_A":
                        turn_speed = 0  # 블랙홀 모으는 중에는 제자리 고정
                    else:
                        turn_speed = 0.6  # 조준 및 발사 중에는 아주 느리고 '일정하게' 트래킹

                # 부드러운 회전 적용 (target_angle이 어디든 turn_speed만큼만 회전)
                angle_diff = (self.target_angle - self.current_angle + 180) % 360 - 180
                
                if abs(angle_diff) <= turn_speed:
                    self.current_angle = self.target_angle  # 거의 다 왔으면 딱 맞춤
                else:
                    self.current_angle += turn_speed if angle_diff > 0 else -turn_speed

        if now - self.last_anim_update > self.anim_speed:
            self.last_anim_update = now
            if self.state == "DEAD":
                self.anim_idx_base += 1
                if self.anim_idx_base >= len(self.base_frames):
                    self.kill()
                    return
            else:
                self.anim_idx_engine = (self.anim_idx_engine + 1) % len(self.engine_frames)
                if self.is_shielded:
                    self.anim_idx_shield = (self.anim_idx_shield + 1) % len(self.shield_frames)

        canvas_size = (int(self.size[0] * 2.5), int(self.size[1] * 2.5))
        temp_surf = pygame.Surface(canvas_size, pygame.SRCALPHA)
        center_x, center_y = canvas_size[0] // 2, canvas_size[1] // 2

        boss_img = pygame.Surface(self.size, pygame.SRCALPHA)
        if self.state != "DEAD":
            boss_img.blit(self.engine_frames[self.anim_idx_engine], (0, 0))
        if len(self.base_frames) > 0:
            boss_img.blit(self.base_frames[self.anim_idx_base % len(self.base_frames)], (0, 0))
        
        if self.is_shielded and self.state != "DEAD":
            boss_img.blit(self.shield_frames[self.anim_idx_shield], (0, 0))
        
        r_boss = pygame.transform.rotate(boss_img, self.current_angle)
        temp_surf.blit(r_boss, r_boss.get_rect(center=(center_x, center_y)))
        self.image = temp_surf
        self.rect = self.image.get_rect(center=self.pos - cam_pos)

    def draw_effects(self, screen, cam_pos):
        # 1. 순간이동 & 발악 충격파 (원형 애니메이션으로 변경)
        if self.state == "TELEPORTING":
            if self.teleport_phase == "WARNING":
                rect = pygame.Rect(0, 0, self.size[0], self.size[1])
                rect.center = self.teleport_target - cam_pos
                pygame.draw.rect(screen, (255, 50, 50), rect, 3)
            elif self.teleport_phase == "SHOCKWAVE":
                elapsed = pygame.time.get_ticks() - self.shockwave_timer
                if elapsed < 500:
                    scale = math.sin((elapsed / 500) * math.pi)
                    max_radius = self.size[1] // 2 + 50
                    current_radius = int(max_radius * scale)
                    screen_pos = self.pos - cam_pos
                    
                    pygame.draw.circle(screen, (255, 100, 50, 150), screen_pos, current_radius, max(1, int(15 * scale)))
                    pygame.draw.circle(screen, (255, 200, 100, 100), screen_pos, max(1, current_radius - 10))

        # 2. 일반 돌진 및 발악 돌진 궤적
        if (self.state == "CASTING_SKILL" and self.current_skill == "DASH" and getattr(self, 'dash_phase', '') == "WARNING") or \
           (self.state == "DESPERATION_SEQ" and getattr(self, 'desp_phase', '') == "DASH_WARN"):
            start_screen = self.pos - cam_pos
            safe_dash_dir = getattr(self, 'dash_dir', pygame.math.Vector2(0, 1))
            end_screen = start_screen + (safe_dash_dir * max(MAP_WIDTH, MAP_HEIGHT) * 2)
            pygame.draw.line(screen, (255, 0, 0) if self.state == "DESPERATION_SEQ" else (139, 0, 0), start_screen, end_screen, 100 if self.state == "DESPERATION_SEQ" else int(self.radius * 2))

        # 3. 레이저 & 블랙홀 이펙트 (최적화 레이저 적용)
        if self.state == "CASTING_SKILL" and self.current_skill == "LASER":
            gather_screen_pos = self.gather_point - cam_pos
            
            if self.laser_phase in ["PHASE_A", "PHASE_B"]:
                # 🌟 블랙홀 모으기 연출 (속이 꽉 찬 형태로 천천히 커짐)
                # 전체 모으는 시간: A(4초) + B(2초) = 총 6000ms
                if self.laser_phase == "PHASE_A":
                    elapsed_total = pygame.time.get_ticks() - self.skill_timer
                else:
                    elapsed_total = 4000 + (pygame.time.get_ticks() - self.skill_timer)
                    
                progress = min(1.0, elapsed_total / 6000.0) 
                
                # 최대 반지름 50 정도로 너무 크지 않게 제어 (기본 10에서 시작해 50까지 커짐)
                radius = int(10 + progress * 40) 
                
                bh_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                center_pt = (radius, radius)
                
                # 색상 채우기 (circle 함수의 두께 파라미터를 안 주면 속이 꽉 채워집니다)
                pygame.draw.circle(bh_surf, (100, 0, 255, int(150 + 105 * progress)), center_pt, radius)         # 바깥쪽 보라색 오라
                pygame.draw.circle(bh_surf, (50, 0, 200, 255), center_pt, max(1, int(radius * 0.65)))            # 안쪽 짙은 코어
                pygame.draw.circle(bh_surf, (255, 255, 255, 255), center_pt, max(1, int(radius * 0.35)))         # 새하얀 중심점
                
                screen.blit(bh_surf, bh_surf.get_rect(center=(int(gather_screen_pos.x), int(gather_screen_pos.y))))
                
            elif self.laser_phase == "PHASE_C":
                end_screen = gather_screen_pos + (self.laser_dir * max(MAP_WIDTH, MAP_HEIGHT) * 2)
                
                color = (138, 43, 226) 
                level = 30 
                thickness = int(10 + level * 2)
                
                c_r, c_g, c_b = color
                outer_color = (c_r // 3, c_g // 3, c_b // 3)
                mid_color = (int(c_r * 0.8), int(c_g * 0.8), int(c_b * 0.8))
                core_color = (255, 255, 255)

                pygame.draw.line(screen, outer_color, gather_screen_pos, end_screen, thickness * 2)
                pygame.draw.line(screen, mid_color, gather_screen_pos, end_screen, thickness)
                pygame.draw.line(screen, core_color, gather_screen_pos, end_screen, max(2, thickness // 3))

                start_pos_int = (int(gather_screen_pos.x), int(gather_screen_pos.y))
                pygame.draw.circle(screen, mid_color, start_pos_int, int(thickness * 1.5))
                pygame.draw.circle(screen, core_color, start_pos_int, int(thickness // 1.5))

class CloneSlash(pygame.sprite.Sprite):
    def __init__(self, pos, direction, damage=1, speed=12):
        super().__init__()
        
        # ★ 총알 클래스 구조 차용: Base64_Data에서 스매쉬(참격) 데이터 로드
        # (딕셔너리 키는 실제 스매쉬 데이터 이름으로 맞춰주세요. 예: "SMASH_B64")
        config = Base64_Data.get("SMASH_B64", Base64_Data["PIRATE_BULLET_B64"]) 
        self.size = config["size"]
        raw_frames = SpriteFactory().get_frames(config["b64"], cols=config["cols"], rows=config["rows"])
        
        # 총알처럼 첫 프레임 사용 (원하신다면 HomingNuke처럼 enhance_color를 추가하셔도 됩니다)
        base_img = pygame.transform.scale(raw_frames[0], self.size).convert_alpha()
        
        # 방향에 맞춰 이미지 회전
        angle = math.degrees(math.atan2(-direction.x, -direction.y)) + 90
        self.image = pygame.transform.rotate(base_img, angle)
        
        self.pos = pygame.math.Vector2(pos)
        self.rect = self.image.get_rect(center=self.pos)
        
        # 히트박스 설정
        self.hitbox_size = config.get("hitbox_size", (30, 30))
        self.hitbox = pygame.Rect(0, 0, *self.hitbox_size)
        self.hitbox.center = self.pos
        
        self.vel = direction * speed
        self.damage = damage

    def update(self, cam_pos, *args):
        self.pos += self.vel
        self.rect.center = self.pos - cam_pos
        self.hitbox.center = self.pos 
        
        # 화면 밖을 벗어나면 삭제 (풀을 안 쓴다면 그냥 kill)
        if not (-200 <= self.pos.x <= MAP_WIDTH + 200 and -200 <= self.pos.y <= MAP_HEIGHT + 200): 
            self.kill()

class BossClone(pygame.sprite.Sprite):
    _cached_exp_frames = []

    def __init__(self, start_pos, player_obj, boss_base_image, enemy_proj_group):
        super().__init__()
        self.player = player_obj
        self.pos = pygame.math.Vector2(start_pos)
        self.enemy_proj_group = enemy_proj_group
        
        # --- 1. 폭발 캐시 굽기 (HomingNuke 로직 100% 동일) ---
        if not BossClone._cached_exp_frames:
            b_data = Base64_Data["bomb"]["B64"]
            exp_b64 = b_data["explosion"]
            exp_cols, exp_rows = exp_b64.get("cols", 12), exp_b64.get("rows", 9)
            exp_indices = exp_b64.get("indices", [0,1,2,3,4,5,6,7,8,9,11])
            
            base_exp_size = exp_b64.get("size", (150, 150))
            visual_scale = 5.0 
            visual_exp_size = (int(base_exp_size[0] * visual_scale), int(base_exp_size[1] * visual_scale))
            raw_exp = SpriteFactory().get_frames(exp_b64["b64"], cols=exp_cols, rows=exp_rows)

            def enhance_color(img, target_size, intensity=160, tint=None):
                base_img = pygame.transform.scale(img, target_size).convert_alpha()
                if tint:
                    s = pygame.Surface(target_size, pygame.SRCALPHA)
                    s.fill((*tint, 255))
                    base_img.blit(s, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                overlay = base_img.copy()
                overlay.set_alpha(intensity) 
                base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                return base_img

            BossClone._cached_exp_frames.extend([
                enhance_color(raw_exp[i], visual_exp_size, intensity=180) for i in exp_indices
            ])
            
        self.exp_frames = BossClone._cached_exp_frames
        
        # 폭발 범위 (뉴크와 동일)
        exp_b64 = Base64_Data["bomb"]["B64"]["explosion"]
        base_hitbox = exp_b64.get("hitbox", (150, 150))[0] // 2
        self.exp_radius = int(base_hitbox * 2.5) 
        
        # --- 2. 분신 이미지 세팅 (붉은 색조 덮어씌우기) ---
        # 원본 보스 이미지를 받아와서 투명도 있는 빨간색을 Multiply 블렌딩
        self.base_image = boss_base_image.copy()
        tint_surf = pygame.Surface(self.base_image.get_size(), pygame.SRCALPHA)
        tint_surf.fill((255, 50, 50, 200)) # 빨간색 홀로그램 느낌
        self.base_image.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        self.image = self.base_image
        self.rect = self.image.get_rect(center=self.pos)
        
        # --- 3. 스탯 및 상태 초기화 ---
        self.hp = 50
        self.damage = 5  # 자폭 시 플레이어에게 줄 데미지
        self.rotation_speed = 1.5
        
        self.state = "CHASING" # HomingNuke처럼 상태 분리
        self.current_angle = 0
        self.anim_idx = 0
        self.has_damaged = False
        
        now = pygame.time.get_ticks()
        self.last_anim_update = now
        
        # 분신 전용 참격 타이머
        self.last_slash_time = now
        self.slash_cooldown = 1500

    def update(self, cam_pos, player_obj=None, **kwargs):
        target_player = player_obj if player_obj else self.player
        now = pygame.time.get_ticks()
        
        if self.state == "CHASING":
            # ★ HomingNuke의 일정한 속도 회전 로직 그대로 적용
            direction = target_player.pos - self.pos
            if direction.length() > 0:
                target_angle = math.degrees(math.atan2(-direction.y, direction.x))
                angle_diff = (target_angle - self.current_angle + 180) % 360 - 180
                
                if abs(angle_diff) > self.rotation_speed:
                    self.current_angle += self.rotation_speed if angle_diff > 0 else -self.rotation_speed
                else:
                    self.current_angle = target_angle
                    
            # 렌더링용 이미지 회전
            self.image = pygame.transform.rotate(self.base_image, self.current_angle - 90)
            self.rect = self.image.get_rect(center=self.pos - cam_pos)
            
            # ★ 참격(Slash) 발사
            if now - self.last_slash_time > self.slash_cooldown:
                self.last_slash_time = now
                rad = math.radians(self.current_angle)
                dir_vec = pygame.math.Vector2(math.cos(rad), -math.sin(rad))
                
                slash = CloneSlash(self.pos, dir_vec)
                self.enemy_proj_group.add(slash)
            
            # ★ 자폭 조건: 플레이어와 닿았거나(Hitbox), 체력이 0 이하일 때
            dist_to_player = self.pos.distance_to(target_player.pos)
            if dist_to_player < 50 or self.hp <= 0: # 50은 본체 피격 반경
                self.state = "EXPLODING" 
                self.last_anim_update = now
                self.anim_idx = 0
                self.image = self.exp_frames[0]
                self.rect = self.image.get_rect(center=self.pos - cam_pos)
                
        elif self.state == "EXPLODING":
            # ★ HomingNuke의 폭발 애니메이션 및 1회성 데미지 로직 100% 동일
            if not self.has_damaged:
                dist = self.pos.distance_to(target_player.pos)
                if dist < self.exp_radius + 20: 
                    if hasattr(target_player, 'take_damage'):
                        target_player.take_damage(self.damage)
                self.has_damaged = True
                
            if now - self.last_anim_update > 60:
                self.last_anim_update = now
                self.anim_idx += 1
                
                if self.anim_idx >= len(self.exp_frames):
                    self.kill()
                    return
                    
            self.image = self.exp_frames[self.anim_idx]
            self.rect = self.image.get_rect(center=self.pos - cam_pos)

    def draw(self, screen, cam_pos):
        screen_pos = self.pos - cam_pos
        
        if self.state == "CHASING":
            # ★ 뉴크의 깜빡거림은 빼고, 항시 선명한 경고선 유지
            pygame.draw.circle(screen, (255, 0, 0), screen_pos, int(self.exp_radius), 2)
            
            danger_surf = pygame.Surface((self.exp_radius * 2, self.exp_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(danger_surf, (255, 0, 0, 40), (self.exp_radius, self.exp_radius), self.exp_radius)
            screen.blit(danger_surf, screen_pos - pygame.math.Vector2(self.exp_radius, self.exp_radius))

            screen.blit(self.image, self.rect)
                
        elif self.state == "EXPLODING":
            screen.blit(self.image, self.rect)
            
    def take_damage(self, amount):
        if self.state == "CHASING":
            self.hp -= amount

class SpaceDistortion(pygame.sprite.Sprite):
    def __init__(self, pos, player_obj, duration=6000):
        super().__init__()
        self.pos = pygame.math.Vector2(pos)
        self.player = player_obj
        self.duration = duration # 지속 시간 (기본 6초)
        self.start_time = pygame.time.get_ticks()
        
        # --- 1. 에셋 로드 (기존 총알/뉴크 구조 응용) ---
        # "BLACKHOLE_B64"나 "DISTORTION_B64"가 있다고 가정하고 가져옵니다.
        # 데이터가 없다면 기본 구체 설정을 따릅니다.
        config = Base64_Data.get("DISTORTION_B64", {
            "size": (100, 100),
            "hitbox": (80, 80)
        })
        
        # 만약 스프라이트 시트가 있다면 SpriteFactory로 프레임을 가져올 수 있습니다.
        # 여기서는 구체가 커지고 작아지는 연출을 위해 scale을 실시간으로 조절합니다.
        if "b64" in config:
            raw_frames = SpriteFactory().get_frames(config["b64"], cols=config.get("cols", 1), rows=config.get("rows", 1))
            self.base_image = raw_frames[0]
        else:
            # 에셋이 없을 경우를 대비한 임시 검은 구체 생성
            self.base_image = pygame.Surface(config["size"], pygame.SRCALPHA)
            pygame.draw.circle(self.base_image, (20, 20, 20), (config["size"][0]//2, config["size"][1]//2), config["size"][0]//2)
            pygame.draw.circle(self.base_image, (100, 0, 255), (config["size"][0]//2, config["size"][1]//2), config["size"][0]//2, 2)

        self.image = self.base_image
        self.rect = self.image.get_rect(center=self.pos)
        
        # --- 2. 속성 설정 ---
        self.max_scale = 3.0       # 최대 3배까지 커짐
        self.pull_strength = 0.8   # 플레이어를 끌어당기는 힘의 세기
        self.damage = 1            # 닿았을 때 도트 데미지
        self.has_damaged = False
        self.last_damage_tick = 0

    def update(self, cam_pos, **kwargs):
        now = pygame.time.get_ticks()
        elapsed = now - self.start_time
        
        # 1. 수명 다하면 제거
        if elapsed >= self.duration:
            self.kill()
            return

        # 2. 크기 변화 로직 (균열이 커졌다가 작아지는 연출)
        # 0.0 ~ 1.0 사이의 진행률 계산
        progress = elapsed / self.duration
        
        # Ease Out-In 형태의 크기 조절 (처음과 끝은 작고 중간은 큼)
        # sin 함수를 이용하면 0 -> 1 -> 0으로 부드럽게 변합니다.
        scale_factor = math.sin(progress * math.pi) * self.max_scale
        if scale_factor < 0.1: scale_factor = 0.1 # 최소 크기 유지
        
        new_size = (int(self.base_image.get_width() * scale_factor), 
                    int(self.base_image.get_height() * scale_factor))
        
        self.image = pygame.transform.scale(self.base_image, new_size)
        self.rect = self.image.get_rect(center=self.pos - cam_pos)
        
        # 3. 플레이어 인력(Gravity) 로직
        # 플레이어와 균열 중심 사이의 벡터 계산
        vec_to_center = self.pos - self.player.pos
        dist = vec_to_center.length()
        
        if dist > 1: # 거리가 0이 아닐 때만 작동
            pull_dir = vec_to_center.normalize()
            # 거리에 상관없이 일정하게 당기거나, 가까울수록 더 강하게 설정 가능
            # 여기서는 일정한 힘으로 당기도록 설정
            self.player.pos += pull_dir * self.pull_strength
            
        # 4. 데미지 판정 (현재 구체 크기 안에 플레이어가 들어와 있다면)
        current_radius = (new_size[0] // 2) * 0.8 # 히트박스는 이미지보다 약간 작게
        if dist < current_radius:
            if now - self.last_damage_tick > 500: # 0.5초마다 데미지
                self.player.take_damage(self.damage)
                self.last_damage_tick = now

    def draw(self, screen, cam_pos):
        # 균열 패턴은 특별하니까 바닥에 장판 효과를 추가로 그려줄 수 있습니다.
        screen_pos = self.pos - cam_pos
        
        # 주변에 일렁이는 보라색 오라 (선택 사항)
        aura_radius = self.rect.width // 2 + 20
        aura_surf = pygame.Surface((aura_radius * 2, aura_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(aura_surf, (100, 0, 255, 30), (aura_radius, aura_radius), aura_radius)
        screen.blit(aura_surf, screen_pos - pygame.math.Vector2(aura_radius, aura_radius))
        
        # 메인 이미지 출력
        screen.blit(self.image, self.rect)


class Chapter3Boss(pygame.sprite.Sprite):
    _cached_base_frames = []
    _cached_engine_frames = []
    _cached_shield_frames = []

    def __init__(self):
        super().__init__()
        
        # --- [1] 에셋 로드 및 보정 ---
        b_data = Base64_Data.get("C3_BOSS_B64", {"size": (150, 150), "radius": 60, "hitbox": (0, 0, 100, 100), "anim_speed": 60})
        b64_dict = b_data.get("B64", {"C3_BOSS_BASE": {"b64": "", "cols": 1, "rows": 1}, 
                                      "C3_BOSS_ENGINE": {"b64": "", "cols": 1, "rows": 1},
                                      "C3_BOSS_SHIELD": {"b64": "", "cols": 1, "rows": 1}})
        
        self.size = b_data["size"]
        self.radius = b_data["radius"]
        self.hitbox = pygame.Rect(*b_data["hitbox"])
        self.anim_speed = b_data.get("anim_speed", 60)
        
        if not Chapter3Boss._cached_base_frames:
            sf = SpriteFactory()
            boss_base = b64_dict["C3_BOSS_BASE"]
            boss_engine = b64_dict["C3_BOSS_ENGINE"]
            boss_shield = b64_dict["C3_BOSS_SHIELD"]
            
            try:
                raw_base = sf.get_frames(boss_base["b64"], cols=boss_base.get("cols", 1), rows=boss_base.get("rows", 1))
                raw_engine = sf.get_frames(boss_engine["b64"], cols=boss_engine.get("cols", 1), rows=1)
                raw_shield = sf.get_frames(boss_shield["b64"], cols=boss_shield.get("cols", 1), rows=1)
            except Exception:
                dummy = pygame.Surface(self.size, pygame.SRCALPHA)
                pygame.draw.polygon(dummy, (200, 50, 200), [(self.size[0]//2, 0), (self.size[0], self.size[1]), (self.size[0]//2, self.size[1]*0.8), (0, self.size[1])])
                raw_base, raw_engine, raw_shield = [dummy], [dummy], [pygame.Surface(self.size, pygame.SRCALPHA)]

            def enhance_color(img, intensity=120, tint=None):
                base_img = pygame.transform.scale(img, self.size).convert_alpha()
                if tint:
                    s = pygame.Surface(self.size, pygame.SRCALPHA)
                    s.fill((*tint, 255))
                    base_img.blit(s, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                overlay = base_img.copy()
                overlay.set_alpha(intensity) 
                base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                return base_img

            Chapter3Boss._cached_base_frames.extend([enhance_color(img) for img in raw_base])
            Chapter3Boss._cached_engine_frames.extend([enhance_color(img) for img in raw_engine])
            Chapter3Boss._cached_shield_frames.extend([enhance_color(img, intensity=180, tint=(50, 150, 255)) for img in raw_shield])

        self.base_frames = Chapter3Boss._cached_base_frames
        self.engine_frames = Chapter3Boss._cached_engine_frames
        self.shield_frames = Chapter3Boss._cached_shield_frames

        # 오브젝트 풀
        self.boss_bullet_pool = ObjectPool(Bullet, initial_size=200, owner_class_name="Boss")

        # --- [2] 물리 및 스탯 설정 ---
        self.pos = pygame.math.Vector2(MAP_WIDTH // 2, -300)
        self.target_pos = self.get_random_map_pos()
        self.current_angle = 90
        self.move_speed = 4.0
        self.rotation_speed = 2.0
        
        self.max_hp = 8000
        self.hp = self.max_hp
        
        # 애니메이션
        self.anim_idx_base = 0
        self.anim_idx_engine = 0
        self.anim_idx_shield = 0
        self.last_anim_update = pygame.time.get_ticks()
        self.shield_angle = 0
        self.afterimages = [] # 초광속 이동 잔상

        # --- [3] 상태 및 스킬 관리 ---
        self.state = "SPAWN" 
        self.last_skill_time = pygame.time.get_ticks()
        self.skill_cooldown = 4500
        
        self.active_continuous = None # 현재 작동중인 지속형 스킬
        self.continuous_end_time = 0

        # 스킬 확률 Config (HP% 비례)
        self.skills_config = {
            "HYPER_DASH":  {"min_hp": 1.0, "weight": 20, "type": "instant"},    # 0번
            "BULLET_RAIN": {"min_hp": 1.0, "weight": 20, "type": "continuous"}, # 1번
            "SPACE_DIST":  {"min_hp": 1.0, "weight": 15, "type": "continuous"}, # 2번
            "STEALTH":     {"min_hp": 1.0, "weight": 15, "type": "instant"},    # 3번
            "SHIELD":      {"min_hp": 1.0, "weight": 15, "type": "continuous"}, # 4번
            "GIANT_LASER": {"min_hp": 1.0, "weight": 20, "type": "instant"},    # 5번
            "SOLAR_FLARE": {"min_hp": 0.8, "weight": 10, "type": "continuous"}, # 6번
            "HACKING":     {"min_hp": 0.8, "weight": 10, "type": "continuous"}, # 7번
            "CLONE_BOMB":  {"min_hp": 1.0, "weight": 15, "type": "instant"}     # 8번
        }

        # 스킬 전용 변수들
        self.stealth_active = False
        self.stealth_mobs = []
        self.is_stealth = False  # 무적/투과 판정용
        
        self.shield_active = False
        self.permanent_shield = False
        
        self.pulse_active = False
        self.pulse_start_time = 0
        self.pulse_pos = pygame.math.Vector2(0, 0)
        
        self.desperation_triggered = False
        self.desperation_bosses = []

        self.laser_start = None
        self.laser_dir = None

        self.orbit_dist = 400 # SPAWN 에러 방지용 임시 추가

    # ==========================================
    # 메인 업데이트 루프 (원본 코드와 100% 동일)
    # ==========================================
    def update(self, cam_pos, player_obj, enemy_group, enemy_proj_group, solar_flare_effect=None, particles=None):
        now = pygame.time.get_ticks()
        
        if self.state == "EXPLODING":
            self.update_animation(now)
            self.render_canvas(cam_pos)
            return

        # 1. 상태별 로직 처리
        if self.state == "SPAWN":
            self.pos.y += 2
            if self.pos.distance_to(player_obj.pos) < self.orbit_dist + 150:
                self.state = "MOVING"
                self.last_skill_time = now

        elif self.state in ["MOVING", "DESPERATION"]:
            self.update_movement()
            self.check_skill_trigger(now, player_obj, enemy_group)

        elif self.state == "DASHING": 
            self.update_hyper_dash(now, enemy_group, player_obj)
            
        elif self.state == "LASER":
            self.update_giant_laser(now)

        # 2. 지속형 스킬 및 특수 상태 업데이트
        self.update_continuous_skills(now, enemy_proj_group, player_obj, solar_flare_effect)
        self.update_stealth(now, particles)
        self.update_desperation()

        # 잔상 업데이트
        self.afterimages = [img for img in self.afterimages if now - img["time"] < 300]

        # 3. 애니메이션 및 렌더링
        self.update_animation(now)
        self.render_canvas(cam_pos)
        self.hitbox.center = self.pos

    # ==========================================
    # 이동 (우주선형 물리 이동)
    # ==========================================
    def update_movement(self):
        direction = self.target_pos - self.pos
        if direction.length() < 50:
            self.target_pos = self.get_random_map_pos()
            direction = self.target_pos - self.pos

        if direction.length() > 0:
            target_angle = math.degrees(math.atan2(-direction.y, direction.x))
            angle_diff = (target_angle - self.current_angle + 180) % 360 - 180
            
            if abs(angle_diff) > self.rotation_speed:
                self.current_angle += self.rotation_speed if angle_diff > 0 else -self.rotation_speed
            else:
                self.current_angle = target_angle
                
        rad = math.radians(self.current_angle)
        move_vec = pygame.math.Vector2(math.cos(rad), -math.sin(rad))
        self.pos += move_vec * self.move_speed
        
        margin = self.size[0] // 2 
        self.pos.x = max(margin, min(MAP_WIDTH - margin, self.pos.x))
        self.pos.y = max(margin, min(MAP_HEIGHT - margin, self.pos.y))

    def get_random_map_pos(self):
        return pygame.math.Vector2(random.randint(100, MAP_WIDTH - 100), random.randint(100, MAP_HEIGHT - 100))

    # ==========================================
    # 스킬 트리거
    # ==========================================
    def check_skill_trigger(self, now, player_obj, enemy_group):
        if self.hp <= self.max_hp * 0.2 and not self.desperation_triggered:
            self.execute_skill("DESPERATION", now, player_obj, enemy_group)
            self.last_skill_time = now
            return

        if now - self.last_skill_time > self.skill_cooldown:
            self.last_skill_time = now
            hp_ratio = self.hp / self.max_hp
            
            available = [name for name, conf in self.skills_config.items() if hp_ratio <= conf["min_hp"]]
            
            # 지속형 중복 방지
            if self.active_continuous is not None:
                available = [name for name in available if self.skills_config[name]["type"] != "continuous"]
            
            if available:
                weights = [self.skills_config[name]["weight"] for name in available]
                chosen_skill = random.choices(available, weights=weights, k=1)[0]
                self.execute_skill(chosen_skill, now, player_obj, enemy_group)

    def execute_skill(self, skill_name, now, player_obj, enemy_group):
        conf = self.skills_config.get(skill_name, {})
        
        # 1. 지속형 스킬
        if conf.get("type") == "continuous":
            self.active_continuous = skill_name
            self.continuous_end_time = now + 6000 
            
            if skill_name == "SHIELD":
                self.continuous_end_time = now + 10000
                self.shield_active = True
            elif skill_name == "SPACE_DIST":
                self.space_dist_spawned = False
            elif skill_name == "SOLAR_FLARE":
                self.flare_triggered = False
            elif skill_name == "HACKING":
                self.hack_triggered = False

        # 2. 단발/상태 전환형 스킬
        else:
            if skill_name == "HYPER_DASH":
                self.state = "DASHING"
                self.dash_start_pos = self.pos.copy()
                self.dash_target_pos = self.get_random_map_pos()
                self.dash_start_time = now
                self.dash_callback = "MOVING"
                
            elif skill_name == "STEALTH":
                if not self.stealth_active:
                    self.stealth_active = True
                    self.is_stealth = True
                    self.current_angle = 0
                    
                    self.state = "DASHING"
                    self.dash_start_pos = self.pos.copy()
                    self.dash_target_pos = pygame.math.Vector2(MAP_WIDTH // 2, MAP_HEIGHT // 2)
                    self.dash_start_time = now
                    self.dash_callback = "STEALTH_WAIT"
                    
                    # 10마리 즉시 소환
                    self.stealth_mobs = []
                    for _ in range(10):
                        mob_class = random.choice([Pirate, Bomber]) if 'Pirate' in globals() else None
                        if mob_class:
                            mob = mob_class(player_obj, getattr(self, 'diff_level', 1))
                            mob.pos = self.get_random_map_pos()
                            enemy_group.add(mob)
                            self.stealth_mobs.append(mob)
                    
            elif skill_name == "GIANT_LASER":
                self.state = "LASER"
                self.laser_phase = "CENTERING"
                self.laser_spin_count = 0
                self.dash_start_pos = self.pos.copy()
                self.dash_target_pos = pygame.math.Vector2(MAP_WIDTH // 2, MAP_HEIGHT // 2)
                self.dash_start_time = now
                
            elif skill_name == "CLONE_BOMB":
                if 'BossClone' in globals():
                    clone = BossClone(self.pos, player_obj, self.base_frames[0], enemy_group)
                    enemy_group.add(clone)
                
            elif skill_name == "DESPERATION":
                self.desperation_triggered = True
                self.stealth_active = True
                self.is_stealth = True
                self.state = "DASHING"
                
                self.dash_start_pos = self.pos.copy()
                self.dash_target_pos = pygame.math.Vector2(MAP_WIDTH // 2, MAP_HEIGHT // 2)
                self.dash_start_time = now
                self.dash_callback = "DESPERATION_WAIT"
                
                # 1, 2챕터 보스 소환
                if 'Chapter1Boss' in globals() and 'Chapter2Boss' in globals():
                    boss1 = Chapter1Boss()
                    boss2 = Chapter2Boss(player_obj, getattr(self, 'diff_level', 1))
                    boss1.pos = pygame.math.Vector2(MAP_WIDTH//2 - 300, MAP_HEIGHT//2)
                    boss2.pos = pygame.math.Vector2(MAP_WIDTH//2 + 300, MAP_HEIGHT//2)
                    enemy_group.add(boss1, boss2)
                    self.desperation_bosses.extend([boss1, boss2])

    # ==========================================
    # 개별 스킬 업데이트 세부 구현
    # ==========================================
    def update_continuous_skills(self, now, enemy_proj_group, player_obj, solar_flare_effect=None):
        if not self.active_continuous:
            return
            
        if now > self.continuous_end_time:
            if self.active_continuous == "SHIELD" and not self.permanent_shield:
                self.shield_active = False
            self.active_continuous = None
            return

        if self.active_continuous == "BULLET_RAIN":
            if not hasattr(self, "last_bullet_rain_time"): self.last_bullet_rain_time = 0
            if now - self.last_bullet_rain_time > 80: 
                self.last_bullet_rain_time = now
                spawn_pos = pygame.math.Vector2(random.randint(0, MAP_WIDTH), -50)
                rand_speed = random.uniform(15.0, 25.0)
                enemy_proj_group.add(self.boss_bullet_pool.get(spawn_pos, pygame.math.Vector2(0, 1), 1, self, speed=rand_speed))

        elif self.active_continuous == "SPACE_DIST":
            if not getattr(self, "space_dist_spawned", False):
                if 'SpaceDistortion' in globals():
                    dist = SpaceDistortion(self.get_random_map_pos(), player_obj)
                    enemy_proj_group.add(dist)
                self.space_dist_spawned = True

        elif self.active_continuous == "SOLAR_FLARE":
            if not getattr(self, "flare_triggered", False) and solar_flare_effect:
                solar_flare_effect.trigger(6000)
                self.flare_triggered = True

        elif self.active_continuous == "HACKING":
            if not getattr(self, "hack_triggered", False):
                if hasattr(player_obj, 'apply_hack'):
                    player_obj.apply_hack(6000)
                self.hack_triggered = True

    def update_hyper_dash(self, now, enemy_group, player_obj=None):
        elapsed = now - self.dash_start_time
        duration = 200 # 0.2초 초광속
        
        if elapsed < duration:
            t = elapsed / duration
            self.pos = self.dash_start_pos.lerp(self.dash_target_pos, t)
            # 바라보는 방향 그대로 잔상
            self.afterimages.append({"pos": self.pos.copy(), "angle": self.current_angle, "time": now})
        else:
            self.pos = self.dash_target_pos.copy()
            
            # 콜백 분기
            if getattr(self, "dash_callback", "MOVING") == "MOVING":
                self.state = "MOVING"
                self.target_pos = self.get_random_map_pos()
                
                # 도착 후 확률적 충격파
                if random.random() < 0.6: 
                    self.pulse_active = True
                    self.pulse_start_time = now
                    self.pulse_pos = self.pos.copy()
                    
                    # 충격파 발생 시에만 맵 랜덤 4마리 소환
                    if player_obj:
                        for _ in range(4):
                            mob_class = random.choice([Pirate, Bomber]) if 'Pirate' in globals() else None
                            if mob_class:
                                mob = mob_class(player_obj, getattr(self, 'diff_level', 1))
                                mob.pos = self.get_random_map_pos()
                                enemy_group.add(mob)
            
            elif self.dash_callback == "STEALTH_WAIT":
                self.state = "MOVING" # 메인 루프 호환 유지
                
            elif self.dash_callback == "DESPERATION_WAIT":
                self.state = "MOVING"

    def update_giant_laser(self, now):
        if self.laser_phase == "CENTERING":
            elapsed = now - self.dash_start_time
            if elapsed < 300:
                self.pos = self.dash_start_pos.lerp(self.dash_target_pos, elapsed / 300)
                self.afterimages.append({"pos": self.pos.copy(), "angle": self.current_angle, "time": now})
            else:
                self.pos = self.dash_target_pos.copy()
                self.current_angle = 90 # 0도(위)를 바라보게 세팅
                self.laser_phase = "SPIN"
                self.laser_spin_start = now
                self.laser_base_angle = self.current_angle
                self.laser_spin_dir = random.choice([1, -1])

        elif self.laser_phase == "SPIN":
            elapsed = now - self.laser_spin_start
            spin_duration = 2000 # 한 바퀴 시간
            
            if elapsed <= spin_duration:
                # Ease-In-Out 공식
                t = elapsed / spin_duration
                eased_t = -(math.cos(math.pi * t) - 1) / 2
                self.current_angle = self.laser_base_angle + (360 * self.laser_spin_dir * eased_t)
                
                self.laser_dir = pygame.math.Vector2(0, -1).rotate(-self.current_angle)
                self.laser_start = self.pos + self.laser_dir * (self.size[0] / 2)
                
                # 레이저 회전 중 잔상 기록
                if now % 2 == 0:
                    self.afterimages.append({"pos": self.pos.copy(), "angle": self.current_angle, "time": now})
            else:
                self.laser_start = None 
                self.laser_spin_count += 1
                if self.laser_spin_count >= 3:
                    self.state = "MOVING"
                    self.target_pos = self.get_random_map_pos()
                else:
                    self.laser_phase = "PAUSE"
                    self.laser_pause_start = now

        elif self.laser_phase == "PAUSE":
            if now - self.laser_pause_start > 500:
                self.laser_phase = "SPIN"
                self.laser_spin_start = now
                self.laser_base_angle = self.current_angle
                self.laser_spin_dir = random.choice([1, -1]) 

    def update_stealth(self, now, particles=None):
        if not self.stealth_active: return
        self.current_angle = 90 # 스텔스 중 위쪽 고정
        
        if now % 60 == 0: # 대략 1초에 1번씩 체력 회복
            if self.hp < self.max_hp: self.hp += 1
            if particles and 'HealParticle' in globals():
                particles.add(HealParticle(self.pos.copy()))
        
        self.stealth_mobs = [mob for mob in self.stealth_mobs if mob.alive()]
        if len(self.stealth_mobs) == 0 and not self.desperation_triggered:
            self.stealth_active = False
            self.is_stealth = False
            self.last_skill_time = now

    def update_desperation(self):
        if not self.desperation_triggered: return
        self.current_angle = 90 # 발악 대기 시 위쪽 고정
        
        self.desperation_bosses = [b for b in self.desperation_bosses if b.alive()]
        if len(self.desperation_bosses) == 0 and self.stealth_active:
            self.stealth_active = False
            self.is_stealth = False
            self.permanent_shield = True
            self.shield_active = True
            self.active_continuous = "SHIELD"

    # ==========================================
    # 애니메이션 및 캔버스 렌더링
    # ==========================================
    def update_animation(self, now):
        if now - self.last_anim_update > self.anim_speed:
            self.last_anim_update = now
            if self.state == "EXPLODING":
                self.anim_idx_base += 1
                if self.anim_idx_base >= len(self.base_frames): self.kill()
            else:
                if len(self.engine_frames) > 0:
                    self.anim_idx_engine = (self.anim_idx_engine + 1) % len(self.engine_frames)
                if len(self.shield_frames) > 0:
                    self.anim_idx_shield = (self.anim_idx_shield + 1) % len(self.shield_frames)

    def render_canvas(self, cam_pos):
        canvas_size = (int(self.size[0] * 2.5), int(self.size[1] * 2.5))
        temp_surf = pygame.Surface(canvas_size, pygame.SRCALPHA)
        center_x, center_y = canvas_size[0] // 2, canvas_size[1] // 2

        boss_img = pygame.Surface(self.size, pygame.SRCALPHA)
        if self.state != "EXPLODING" and len(self.engine_frames) > 0:
            boss_img.blit(self.engine_frames[self.anim_idx_engine], (0, 0))
            
        if len(self.base_frames) > 0:
            base_idx = min(self.anim_idx_base, len(self.base_frames)-1)
            boss_img.blit(self.base_frames[base_idx], (0, 0))
            
        # 스텔스 시각 효과 (흐릿하게)
        if getattr(self, 'is_stealth', False):
            boss_img.set_alpha(70)
            
        r_boss = pygame.transform.rotate(boss_img, self.current_angle - 90) 
        temp_surf.blit(r_boss, r_boss.get_rect(center=(center_x, center_y)))

        # 🌟 보호막 그리기 (보스와 같이 돌지 않고 항상 정면 프레임만 루프)
        if self.shield_active and len(self.shield_frames) > 0:
            shield_img = self.shield_frames[self.anim_idx_shield].copy()
            if getattr(self, 'is_stealth', False): shield_img.set_alpha(70)
            temp_surf.blit(shield_img, shield_img.get_rect(center=(center_x, center_y)))
            
        self.image = temp_surf
        self.rect = self.image.get_rect(center=self.pos - cam_pos)

    # ==========================================
    # 데미지 및 외부 이펙트 렌더링
    # ==========================================
    def take_damage(self, amount, player_obj, particle_group):
        if self.state in ["SPAWN", "EXPLODING"]: return False
        if getattr(self, 'is_stealth', False): return False # 🌟 스텔스(무적) 통과 로직
        
        final_damage = amount * 0.5 if self.shield_active else amount
        self.hp -= final_damage
        if hasattr(player_obj, 'trigger_vampire'):
            player_obj.trigger_vampire(particle_group)
        
        if self.hp <= 0:
            self.hp = 0
            self.state = "EXPLODING"
            self.anim_idx_base = 1 
            return True
        return False

    def draw_effects(self, surface, cam_pos):
        now = pygame.time.get_ticks()
        
        # 1. 레이저 & 대쉬 붉은색 잔상 렌더링
        for img_data in self.afterimages:
            time_diff = now - img_data["time"]
            alpha = max(0, 255 - int((time_diff / 300) * 255))
            
            ghost_surf = pygame.Surface(self.size, pygame.SRCALPHA)
            if len(self.base_frames) > 0:
                ghost_surf.blit(self.base_frames[self.anim_idx_base % len(self.base_frames)], (0, 0))
            ghost_surf.fill((255, 50, 50, alpha), special_flags=pygame.BLEND_RGBA_MULT) 
            
            r_ghost = pygame.transform.rotate(ghost_surf, img_data["angle"] - 90)
            screen_pos = img_data["pos"] - cam_pos
            surface.blit(r_ghost, r_ghost.get_rect(center=screen_pos))

        # 2. 충격파 렌더링 (맥박)
        if getattr(self, 'pulse_active', False):
            elapsed = now - self.pulse_start_time
            pulse_duration = 1000 
            if elapsed > pulse_duration:
                self.pulse_active = False
            else:
                progress = elapsed / pulse_duration
                max_radius = max(MAP_WIDTH, MAP_HEIGHT) 
                current_radius = int(max_radius * progress)
                line_thickness = max(1, int(15 * (1 - progress)))
                pygame.draw.circle(surface, (255, 100, 100), self.pulse_pos - cam_pos, current_radius, line_thickness)

        # 3. 거대 레이저 렌더링
        if self.state == "LASER" and getattr(self, 'laser_start', None) and getattr(self, 'laser_dir', None):
            start_screen = self.laser_start - cam_pos
            end_screen = start_screen + self.laser_dir * 3000
            pygame.draw.line(surface, (255, 50, 50), start_screen, end_screen, 40)
            pygame.draw.line(surface, (255, 200, 200), start_screen, end_screen, 15)

    def check_laser_collision(self, player_obj):
        if self.state == "LASER" and getattr(self, 'laser_start', None) and getattr(self, 'laser_dir', None):
            vec_to_player = player_obj.pos - self.laser_start
            projection = vec_to_player.dot(self.laser_dir)
            if projection > 0:
                closest_point = self.laser_start + self.laser_dir * projection
                if player_obj.pos.distance_to(closest_point) < 60 + player_obj.radius:
                    return 5 
        return 0