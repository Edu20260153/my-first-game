import pygame
import math
import random
from settings import *
from sprite import Base64_Data
from asset_loader import SpriteFactory
from weapons import Bullet, Missile, ObjectPool, Bomb, BindBullet
from effects import create_explosion

class Pirate(pygame.sprite.Sprite):
    def __init__(self, player_obj, diff_level):
        super().__init__()
        p = Base64_Data["pirate"]
        pirate_base = p["b64"]["PIRATE_BASE_B64"]
        pirate_engine = p["b64"]["PIRATE_ENGINE_B64"]

        self.size = p["size"]
        
        raw_base = SpriteFactory().get_frames(pirate_base["b64"], cols=pirate_base["cols"], rows=pirate_base["rows"])
        raw_engine = SpriteFactory().get_frames(pirate_engine["b64"], cols=pirate_engine["cols"], rows=pirate_engine["rows"])
        
        def enhance_color(img, intensity=120):
            base_img = pygame.transform.scale(img, self.size).convert_alpha()
            
            # 2. 자기 자신을 복사하여 오버레이 생성
            overlay = base_img.copy()
            overlay.set_alpha(intensity) # 0~255 사이 값. 클수록 색이 쨍해지고 밝아집니다.
            
            base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            
            return base_img

        self.base_frames = [enhance_color(img) for img in raw_base]
        self.engine_frames = [enhance_color(img) for img in raw_engine]
        
        self.image = self.base_frames[0]
        
        # 정밀한 충돌 판정 세팅 (중심 기준 72x80)
        self.radius = p["radius"]
        self.hitbox = pygame.Rect(*p["hitbox"])
        
        angle = random.uniform(0, math.pi * 2)
        dist = max(MAP_WIDTH, MAP_HEIGHT) 
        self.pos = pygame.math.Vector2(player_obj.pos.x + math.cos(angle)*dist, player_obj.pos.y + math.sin(angle)*dist)
        self.rect = self.image.get_rect(center=self.pos)
        self.hitbox.center = self.pos
        
        self.offset_dist, self.offset_angle, self.vel = random.uniform(250, 400), random.uniform(0, 360), pygame.math.Vector2(0, 0)
        self.hp = 5 + (diff_level * 2)
        self.last_attack_time, self.attack_delay = pygame.time.get_ticks(), max(800, random.randint(1500, 2500) - (diff_level * 150))
        self.bullet_speed, self.current_angle = 8 + (diff_level * 0.5), 0

        self.enemy_bullet_pool = ObjectPool(Bullet, initial_size=150, owner_class_name="Pirate")
        self.missile_pool = ObjectPool(Missile, initial_size=50)

        self.state = "ALIVE"
        self.anim_idx_base = 0
        self.anim_idx_engine = 0
        self.last_anim_update = pygame.time.get_ticks()
        self.anim_speed = 60 

    def take_damage(self, amount, player_obj, particle_group):
        if self.state == "ALIVE":
            self.hp -= amount
            player_obj.trigger_vampire(particle_group)
            if self.hp <= 0:
                self.state = "EXPLODING"
                self.anim_idx_base = 1 
                self.last_anim_update = pygame.time.get_ticks()
                
                self.radius = 0
                self.hitbox = pygame.Rect(0, 0, 0, 0)
                return True
        return False

    def update(self, cam_pos, player_obj, enemy_proj, current_stage):
        now = pygame.time.get_ticks()
        
        # 충돌 판정이 존재할 때만 위치 동기화
        if self.hitbox.width > 0:
            self.hitbox.center = self.pos
        
        if self.state == "ALIVE":
            target_pos = player_obj.pos + pygame.math.Vector2(self.offset_dist, 0).rotate(self.offset_angle)
            direction = target_pos - self.pos
            if direction.length() > 5: self.vel = self.vel.lerp(direction.normalize() * min(5, direction.length() * 0.05), 0.05)
            else: self.vel *= 0.8
            self.pos += self.vel
            
            self.pos.x = max(self.radius, min(MAP_WIDTH - self.radius, self.pos.x))
            self.pos.y = max(self.radius, min(MAP_HEIGHT - self.radius, self.pos.y))
            
            face_dir = player_obj.pos - self.pos
            if face_dir.length() > 0:
                target_angle = math.degrees(math.atan2(-face_dir.x, -face_dir.y))
                angle_diff = (target_angle - self.current_angle + 180) % 360 - 180
                self.current_angle += 4 if angle_diff > 0 else -4 if abs(angle_diff) > 4 else angle_diff

            if now - self.last_attack_time > self.attack_delay:
                self.last_attack_time = now
                if random.random() < min(0.7, 0.4 + (player_obj.level * 0.05)): 
                    enemy_proj.add(self.missile_pool.get(self.pos, self, player_obj.level))
                else:
                    shoot_dir = pygame.math.Vector2(0, -1).rotate(-self.current_angle)
                    enemy_proj.add(self.enemy_bullet_pool.get(self.pos, shoot_dir, 1, self, speed=self.bullet_speed))
            
            if now - self.last_anim_update > self.anim_speed:
                self.last_anim_update = now
                self.anim_idx_engine = (self.anim_idx_engine + 1) % len(self.engine_frames)

            temp_surf = pygame.Surface(self.size, pygame.SRCALPHA)
            temp_surf.blit(self.engine_frames[self.anim_idx_engine], (0, 0))
            temp_surf.blit(self.base_frames[0], (0, 0))
            
            self.image = pygame.transform.rotate(temp_surf, self.current_angle)
            self.rect = self.image.get_rect(center=self.pos - cam_pos)

        elif self.state == "EXPLODING":
            self.pos += self.vel * 0.5 
            
            if now - self.last_anim_update > self.anim_speed:
                self.last_anim_update = now
                self.anim_idx_base += 1
                
                if self.anim_idx_base >= len(self.base_frames):
                    self.kill()
                    return
            
            self.image = pygame.transform.rotate(self.base_frames[self.anim_idx_base], self.current_angle)
            self.rect = self.image.get_rect(center=self.pos - cam_pos)

class Bomber(pygame.sprite.Sprite):
    _cached_base_frames = []
    _cached_combined_frames = []

    def __init__(self, player_obj, diff_level):
        super().__init__()
        p = Base64_Data["bomber"]
        self.size = p["size"]
        
        # 1. 클래스 캐시가 비어있을 때 (최초 1회 스폰 시)만 무거운 그래픽 작업을 수행
        if not Bomber._cached_combined_frames:
            bomber_base = p["b64"]["BOMBER_BASE_B64"]
            bomber_engine = p["b64"]["BOMBER_ENGINE_B64"]

            raw_base = SpriteFactory().get_frames(bomber_base["b64"], cols=bomber_base["cols"], rows=bomber_base["rows"])
            raw_engine = SpriteFactory().get_frames(bomber_engine["b64"], cols=bomber_engine["cols"], rows=bomber_engine["rows"])
            
            def enhance_color(img, intensity=160):
                base_img = pygame.transform.scale(img, self.size).convert_alpha()
                overlay = base_img.copy()
                overlay.set_alpha(intensity) 
                base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                return base_img

            # 기본 베이스 프레임 굽기 및 저장 (폭발 애니메이션 때 쓰임)
            Bomber._cached_base_frames.extend([enhance_color(img) for img in raw_base])
            engine_frames = [enhance_color(img) for img in raw_engine]
            
            # 엔진과 몸통 합친 프레임 굽기 및 저장
            for engine_img in engine_frames:
                temp_surf = pygame.Surface(self.size, pygame.SRCALPHA)
                temp_surf.blit(engine_img, (0, 0))
                temp_surf.blit(Bomber._cached_base_frames[0], (0, 0)) # 몸통은 0번 고정
                Bomber._cached_combined_frames.append(temp_surf)
                
        # 2. 이후 생성되는 폭탄병은 위 과정 다 패스하고 쏙 빼다 쓰기만 함
        self.base_frames = Bomber._cached_base_frames
        self.combined_frames = Bomber._cached_combined_frames
        
        self.image = self.combined_frames[0]
        
        self.radius = p["radius"]
        self.hitbox = pygame.Rect(*p.get("hitbox", (0, 0, self.radius*2, self.radius*2))) 
        
        # --- (이 아래 스폰, 궤도, 공격 딜레이 등 설정은 기존과 100% 동일) ---
        spawn_angle = random.uniform(0, math.pi * 2)
        dist = max(MAP_WIDTH, MAP_HEIGHT) 
        self.pos = pygame.math.Vector2(player_obj.pos.x + math.cos(spawn_angle)*dist, player_obj.pos.y + math.sin(spawn_angle)*dist)
        self.rect = self.image.get_rect(center=self.pos)
        self.hitbox.center = self.pos
        
        self.orbit_angle = random.uniform(0, 360) 
        self.orbit_dist = random.uniform(250, 400) 
        self.orbit_speed = random.uniform(0.5, 1.2) 
        
        self.vel = pygame.math.Vector2(0, 0)
        self.current_angle = 0 
        
        self.hp = 10 + (diff_level * 2)
        self.speed = 2.5 
        
        self.last_attack_time = pygame.time.get_ticks()
        self.attack_delay = max(1000, 2500 - (diff_level * 150))
        
        self.last_bomb_time = pygame.time.get_ticks()
        self.bomb_delay = max(3000, 6000 - (diff_level * 200))
        
        # 💡 방금 전 폭탄(Bomb) 코드를 최적화했기 때문에, 여기서 Pool을 생성해도 폭탄 생성 랙이 걸리지 않습니다!
        self.enemy_bullet_pool = ObjectPool(Bullet, initial_size=50, owner_class_name="Bomber")
        self.bomb_pool = ObjectPool(Bomb, initial_size=10, owner_class_name="Bomber")
        
        self.state = "ALIVE"
        self.anim_idx_base = 0
        self.anim_idx_engine = 0
        self.last_anim_update = pygame.time.get_ticks()
        self.anim_speed = 60

    def take_damage(self, amount, player_obj, particle_group):
        if self.state == "ALIVE":
            self.hp -= amount
            if self.hp <= 0:
                self.state = "EXPLODING"
                self.anim_idx_base = 1
                self.last_anim_update = pygame.time.get_ticks()
                self.radius = 0
                self.hitbox = pygame.Rect(0, 0, 0, 0)
                return True
        return False

    def update(self, cam_pos, player_obj, enemy_proj, bomb_group):
        now = pygame.time.get_ticks()
        
        if self.hitbox.width > 0:
            self.hitbox.center = self.pos

        if self.state == "ALIVE":
            self.orbit_angle = (self.orbit_angle + self.orbit_speed) % 360
            rad = math.radians(self.orbit_angle)
            target_pos = player_obj.pos + pygame.math.Vector2(math.cos(rad) * self.orbit_dist, math.sin(rad) * self.orbit_dist)
            
            direction = target_pos - self.pos
            if direction.length() > 0:
                self.vel = self.vel.lerp(direction.normalize() * min(self.speed, direction.length() * 0.05), 0.05)
            else:
                self.vel *= 0.8
            self.pos += self.vel
            
            self.pos.x = max(self.radius, min(MAP_WIDTH - self.radius, self.pos.x))
            self.pos.y = max(self.radius, min(MAP_HEIGHT - self.radius, self.pos.y))

            if self.vel.length() > 0.1:
                target_angle = math.degrees(math.atan2(-self.vel.x, -self.vel.y))
                angle_diff = (target_angle - self.current_angle + 180) % 360 - 180
                self.current_angle += 4 if angle_diff > 0 else -4 if abs(angle_diff) > 4 else angle_diff

            if now - self.last_attack_time > self.attack_delay:
                self.last_attack_time = now
                shoot_dir = pygame.math.Vector2(0, -1).rotate(-self.current_angle)
                enemy_proj.add(self.enemy_bullet_pool.get(self.pos, shoot_dir, 1, self, speed=6))

            if now - self.last_bomb_time > self.bomb_delay:
                self.last_bomb_time = now
                bomb = self.bomb_pool.get(start_pos=self.pos, target_pos=player_obj.pos, damage=2)
                bomb_group.add(bomb)

            if now - self.last_anim_update > self.anim_speed:
                self.last_anim_update = now
                self.anim_idx_engine = (self.anim_idx_engine + 1) % len(self.combined_frames)

            self.image = pygame.transform.rotate(self.combined_frames[self.anim_idx_engine], self.current_angle)
            self.rect = self.image.get_rect(center=self.pos - cam_pos)

        elif self.state == "EXPLODING":
            self.pos += self.vel * 0.5 
            
            if now - self.last_anim_update > self.anim_speed:
                self.last_anim_update = now
                self.anim_idx_base += 1
                
                if self.anim_idx_base >= len(self.base_frames):
                    bomb = self.bomb_pool.get(start_pos=self.pos, target_pos=self.pos, damage=2)
                    bomb_group.add(bomb)
                    self.kill()
                    return
            
            self.image = pygame.transform.rotate(self.base_frames[self.anim_idx_base], self.current_angle)
            self.rect = self.image.get_rect(center=self.pos - cam_pos)

class Scout(pygame.sprite.Sprite):
    _cached_base_frames = []
    _cached_combined_frames = []

    def __init__(self, player_obj, diff_level):
        super().__init__()
        p = Base64_Data["scout"]
        self.size = p["size"]
        
        if not Scout._cached_combined_frames:
            scout_base = p["b64"]["SCOUT_BASE_B64"]
            scout_engine = p["b64"]["SCOUT_ENGINE_B64"]

            raw_base = SpriteFactory().get_frames(scout_base["b64"], cols=scout_base["cols"], rows=scout_base["rows"])
            raw_engine = SpriteFactory().get_frames(scout_engine["b64"], cols=scout_engine["cols"], rows=scout_engine["rows"])
            
            def enhance_color(img, intensity=160):
                base_img = pygame.transform.scale(img, self.size).convert_alpha()
                overlay = base_img.copy()
                overlay.set_alpha(intensity) 
                base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                return base_img

            Scout._cached_base_frames.extend([enhance_color(img) for img in raw_base])
            engine_frames = [enhance_color(img) for img in raw_engine]
            
            for engine_img in engine_frames:
                temp_surf = pygame.Surface(self.size, pygame.SRCALPHA)
                temp_surf.blit(engine_img, (0, 0))
                temp_surf.blit(Scout._cached_base_frames[0], (0, 0)) 
                Scout._cached_combined_frames.append(temp_surf)
                
        self.base_frames = Scout._cached_base_frames
        self.combined_frames = Scout._cached_combined_frames
        self.image = self.combined_frames[0]

        self.radius = p["radius"]
        self.hitbox = pygame.Rect(*p["hitbox"])
        
        # --- 2. 스폰 및 이동 로직 ---
        spawn_angle = random.uniform(0, math.pi * 2)

        dist = max(MAP_WIDTH, MAP_HEIGHT) 
        self.pos = pygame.math.Vector2(player_obj.pos.x + math.cos(spawn_angle)*dist, player_obj.pos.y + math.sin(spawn_angle)*dist)

        self.rect = self.image.get_rect(center=self.pos)
        self.hitbox.center = self.pos
        
        self.target_pos = self.get_random_target()
        self.speed = 3.0
        self.vel = pygame.math.Vector2(0, 0)
        self.current_angle = 0 
        self.hp = 15 + (diff_level * 3)
        self.state = "ALIVE"
        
        # --- 3. 기술 및 애니메이션 변수 ---
        self.protected_enemies = []
        self.last_bind_time = pygame.time.get_ticks()
        self.bind_delay = 2000 
        self.bind_bullet_pool = ObjectPool(BindBullet, initial_size=20, owner_class_name="Scout")
        
        self.anim_idx_engine = 0
        self.anim_idx_base = 0  # 폭발 애니메이션용 인덱스
        self.last_anim_update = pygame.time.get_ticks()
        self.anim_speed = 60 

    def get_random_target(self):
        return pygame.math.Vector2(random.uniform(self.radius, MAP_WIDTH - self.radius),
                                   random.uniform(self.radius, MAP_HEIGHT - self.radius))

    def take_damage(self, amount, player_obj, particle_group):
        if self.state == "ALIVE":
            self.hp -= amount
            if self.hp <= 0:
                self.hp = 0
                self.state = "EXPLODING"
                # 죽기 시작할 때 즉시 무적 해제 (선 제거 포함)
                self.release_protected_enemies()
                self.radius = 0
                self.hitbox = pygame.Rect(0, 0, 0, 0)
                return True
        return False

    def release_protected_enemies(self):
        for enemy in self.protected_enemies:
            if hasattr(enemy, 'is_protected'):
                enemy.is_protected = False
        self.protected_enemies.clear()

    def kill(self):
        self.release_protected_enemies()
        super().kill()

    def update(self, cam_pos, player_obj, enemy_proj, enemy_groups_list):
        now = pygame.time.get_ticks()
        
        # 🌟 물리적 히트박스는 맵의 '절대 좌표'를 따라감
        if self.hitbox.width > 0:
            self.hitbox.center = self.pos

        if self.state == "ALIVE":
            # 1. 이동 및 회전
            direction = self.target_pos - self.pos
            if direction.length() > 10:
                self.vel = self.vel.lerp(direction.normalize() * self.speed, 0.05)
            else:
                self.target_pos = self.get_random_target()
                
            self.pos += self.vel
            
            # 🌟 맵 밖 가출 방지 로직 (맵 경계 내부로 가두기)
            self.pos.x = max(self.radius, min(MAP_WIDTH - self.radius, self.pos.x))
            self.pos.y = max(self.radius, min(MAP_HEIGHT - self.radius, self.pos.y))
            
            if self.vel.length() > 0.1:
                target_angle = math.degrees(math.atan2(-self.vel.x, -self.vel.y))
                angle_diff = (target_angle - self.current_angle + 180) % 360 - 180
                self.current_angle += 4 if angle_diff > 0 else -4 if abs(angle_diff) > 4 else angle_diff

            # 2. 팀 보호 (무적 대상 수집)
            self.protected_enemies = [e for e in self.protected_enemies if getattr(e, 'state', '') == "ALIVE"]
            if len(self.protected_enemies) < 3:
                valid_targets = []
                for group in enemy_groups_list:
                    for e in group:
                        if (e != self and getattr(e, 'state', '') == "ALIVE" and 
                            e.__class__.__name__ not in ["Scout", "Meteor"] and 
                            not getattr(e, 'is_protected', False)):
                            valid_targets.append(e)
                if valid_targets:
                    new_target = random.choice(valid_targets)
                    new_target.is_protected = True
                    self.protected_enemies.append(new_target)

            # 3. 속박 공격 (정규화 적용)
            if now - self.last_bind_time > self.bind_delay:
                self.last_bind_time = now
                shoot_dir = player_obj.pos - self.pos
                if shoot_dir.length() > 0:
                    shoot_dir = shoot_dir.normalize()
                    enemy_proj.add(self.bind_bullet_pool.get(self.pos, shoot_dir, 1, self))

            # 4. 애니메이션 및 화면 동기화
            if now - self.last_anim_update > self.anim_speed:
                self.last_anim_update = now
                self.anim_idx_engine = (self.anim_idx_engine + 1) % len(self.combined_frames)

            # 🌟 시각적 이미지는 '카메라 좌표'를 기준으로 계산
            self.image = pygame.transform.rotate(self.combined_frames[self.anim_idx_engine], self.current_angle)
            self.rect = self.image.get_rect(center=self.pos - cam_pos)

        elif self.state == "EXPLODING":
            # 5. 파괴 애니메이션 재생
            if now - self.last_anim_update > self.anim_speed:
                self.last_anim_update = now
                self.anim_idx_base += 1
                if self.anim_idx_base >= len(self.base_frames):
                    self.kill() 
                    return

            if self.anim_idx_base < len(self.base_frames):
                self.image = pygame.transform.rotate(self.base_frames[self.anim_idx_base], self.current_angle)
                self.rect = self.image.get_rect(center=self.pos - cam_pos)

    def draw_lines(self, screen, cam_pos):
        if self.state == "ALIVE":
            start_pos = self.pos - cam_pos
            for e in self.protected_enemies:
                if getattr(e, 'state', '') == "ALIVE":
                    end_pos = e.pos - cam_pos
                    pygame.draw.line(screen, (0, 150, 255), start_pos, end_pos, 2)

class Turret(pygame.sprite.Sprite):
    _cached_frames = []

    def __init__(self, pos, diff_level):
        super().__init__()
        # [가정] Base64_Data["turret"]에 데이터가 있다고 가정
        p = Base64_Data["turret"]
        self.size = p["size"]
        
        if not Turret._cached_frames:
            turret_base = p["b64"]["TURRET_BASE_B64"]
            # 1cols 짜리 기본 스프라이트 시트
            raw_base = SpriteFactory().get_frames(turret_base["b64"], cols=turret_base["cols"], rows=turret_base["rows"])
            
            def enhance_color(img, intensity=120):
                base_img = pygame.transform.scale(img, self.size).convert_alpha()
                overlay = base_img.copy()
                overlay.set_alpha(intensity)
                base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                return base_img
                
            Turret._cached_frames.extend([enhance_color(img) for img in raw_base])
            
        self.frames = Turret._cached_frames
        self.image = self.frames[0]
        
        # 🌟 물리적 위치 및 히트박스 고정 (포탑은 이동하지 않음)
        self.pos = pygame.math.Vector2(pos)
        self.radius = p["radius"]
        self.hitbox = pygame.Rect(*p["hitbox"])
        self.hitbox.center = self.pos
        self.rect = self.image.get_rect(center=self.pos)
        
        self.max_hp = 10 + (diff_level * 3)
        self.hp = self.max_hp
        self.state = "ALIVE"
        
        # 공격 관련 (공속이 빠르고 사거리가 존재)
        self.attack_range = 600
        self.attack_delay = max(200, 400 - (diff_level * 20)) # 난이도에 따라 공속 증가
        self.last_attack_time = pygame.time.get_ticks()
        self.bullet_speed = 10 + (diff_level * 0.5)
        
        # 총알 풀 (기존 총알 재사용)
        self.bullet_pool = ObjectPool(Bullet, initial_size=50, owner_class_name="Turret")
        
        self.current_angle = 0

    def take_damage(self, amount, player_obj, particle_group):
        if self.state == "ALIVE":
            self.hp -= amount
            if self.hp <= 0:
                self.hp = 0
                self.state = "DEAD" # 폭발 프레임이 없으므로 바로 DEAD 처리
                self.radius = 0
                self.hitbox = pygame.Rect(0, 0, 0, 0)
                self.kill() # 즉시 삭제
                return True
        return False

    def update(self, cam_pos, player_obj, enemy_proj, *args):
        # 포탑은 이동하지 않으므로 히트박스 업데이트 생략 가능
        if self.state == "ALIVE":
            now = pygame.time.get_ticks()
            
            # 플레이어와의 거리 및 방향 계산
            direction = player_obj.pos - self.pos
            dist = direction.length()
            
            if dist > 0:
                # 플레이어 쪽으로 포신 회전
                target_angle = math.degrees(math.atan2(-direction.x, -direction.y))
                self.current_angle = target_angle
                
                # 사거리 내에 들어오면 빠른 속도로 난사
                if dist <= self.attack_range and now - self.last_attack_time > self.attack_delay:
                    self.last_attack_time = now
                    shoot_dir = direction.normalize()
                    # 데미지 1로 설정하여 발사
                    enemy_proj.add(self.bullet_pool.get(self.pos, shoot_dir, 1, self, speed=self.bullet_speed))
            
            # 카메라 기준 렌더링 동기화
            self.image = pygame.transform.rotate(self.frames[0], self.current_angle)
            self.rect = self.image.get_rect(center=self.pos - cam_pos)

class Support(pygame.sprite.Sprite):
    _cached_base_frames = []
    _cached_combined_frames = []

    def __init__(self, player_obj, diff_level):
        super().__init__()
        p = Base64_Data["support"]
        self.size = p["size"]
        
        # --- 1. 최적화된 프레임 캐싱 (Scout와 동일한 방식) ---
        if not Support._cached_combined_frames:
            support_base = p["b64"]["SUPPORT_BASE_B64"]
            support_engine = p["b64"]["SUPPORT_ENGINE_B64"]

            raw_base = SpriteFactory().get_frames(support_base["b64"], cols=support_base["cols"], rows=support_base["rows"])
            raw_engine = SpriteFactory().get_frames(support_engine["b64"], cols=support_engine["cols"], rows=support_engine["rows"])
            
            def enhance_color(img, intensity=160):
                base_img = pygame.transform.scale(img, self.size).convert_alpha()
                overlay = base_img.copy()
                overlay.set_alpha(intensity) 
                base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                return base_img

            Support._cached_base_frames.extend([enhance_color(img) for img in raw_base])
            engine_frames = [enhance_color(img) for img in raw_engine]
            
            for engine_img in engine_frames:
                temp_surf = pygame.Surface(self.size, pygame.SRCALPHA)
                temp_surf.blit(engine_img, (0, 0))
                temp_surf.blit(Support._cached_base_frames[0], (0, 0)) 
                Support._cached_combined_frames.append(temp_surf)
                
        self.base_frames = Support._cached_base_frames
        self.combined_frames = Support._cached_combined_frames
        self.image = self.combined_frames[0]

        self.radius = p["radius"]
        self.hitbox = pygame.Rect(*p["hitbox"])
        
        # --- 2. 스폰 및 이동 로직 ---
        spawn_angle = random.uniform(0, math.pi * 2)
        dist = 1000 # 화면 밖 적당한 거리에서 스폰
        self.pos = pygame.math.Vector2(player_obj.pos.x + math.cos(spawn_angle)*dist, player_obj.pos.y + math.sin(spawn_angle)*dist)

        self.rect = self.image.get_rect(center=self.pos)
        self.hitbox.center = self.pos
        
        self.speed = 3.5
        self.vel = pygame.math.Vector2(0, 0)
        self.current_angle = 0 
        self.hp = 20 + (diff_level * 4)
        self.state = "ALIVE"
        self.diff_level = diff_level
        
        # --- 3. 공성(설치) 패턴 및 회복 변수 ---
        self.active_turrets = []
        self.support_action = "MOVING" # "MOVING" (이동 중) / "DEPLOYING" (설치 중)
        self.target_pos = self.get_distant_target(player_obj)
        
        self.deploy_delay = 3000 # 3초 대기
        self.deploy_timer_start = 0
        
        self.last_heal_time = pygame.time.get_ticks()
        self.heal_cooldown = 1000 # 1초마다 회복
        self.heal_amount = 2      # 초당 회복량
        
        self.anim_idx_engine = 0
        self.anim_idx_base = 0  # 폭발 애니메이션용 인덱스
        self.last_anim_update = pygame.time.get_ticks()
        self.anim_speed = 60 

    def get_distant_target(self, player_obj):
        angle = random.uniform(0, math.pi * 2)
        distance = random.uniform(600, 800)
        target = player_obj.pos + pygame.math.Vector2(distance, 0).rotate_rad(angle)
        
        target.x = max(self.radius, min(MAP_WIDTH - self.radius, target.x))
        target.y = max(self.radius, min(MAP_HEIGHT - self.radius, target.y))
        
        return target

    def take_damage(self, amount, player_obj, particle_group):
        if self.state == "ALIVE":
            self.hp -= amount
            if self.hp <= 0:
                self.hp = 0
                self.state = "EXPLODING"
                self.active_turrets.clear() # 죽으면 포탑과의 회복선 연결 해제
                self.radius = 0
                self.hitbox = pygame.Rect(0, 0, 0, 0)
                return True
        return False

    def update(self, cam_pos, player_obj, enemy_proj, turrets_group):
        now = pygame.time.get_ticks()
        
        if self.hitbox.width > 0:
            self.hitbox.center = self.pos

        if self.state == "ALIVE":
            self.active_turrets = [t for t in self.active_turrets if t.state == "ALIVE"]
            
            if self.support_action == "MOVING":
                direction = self.target_pos - self.pos
                if direction.length() > 10:
                    self.vel = self.vel.lerp(direction.normalize() * self.speed, 0.05)
                else:
                    self.vel = pygame.math.Vector2(0, 0)
                    self.support_action = "DEPLOYING"
                    self.deploy_timer_start = now
            
            elif self.support_action == "DEPLOYING":
                # 설치 중에는 완전히 정지
                self.vel = self.vel.lerp(pygame.math.Vector2(0, 0), 0.1)
                
                # 3초 경과 시 포탑 생성 및 다음 목적지로 이동
                if now - self.deploy_timer_start >= self.deploy_delay:
                    new_turret = Turret(self.pos, self.diff_level)
                    turrets_group.add(new_turret)
                    self.active_turrets.append(new_turret)
                    
                    self.target_pos = self.get_distant_target(player_obj)
                    self.support_action = "MOVING"

            self.pos += self.vel
            
            self.pos.x = max(self.radius, min(MAP_WIDTH - self.radius, self.pos.x))
            self.pos.y = max(self.radius, min(MAP_HEIGHT - self.radius, self.pos.y))
            
            target_angle = self.current_angle

            if self.vel.length() > 0.1:
                target_angle = math.degrees(math.atan2(-self.vel.x, -self.vel.y))
            elif self.support_action == "DEPLOYING":
                face_dir = player_obj.pos - self.pos
                if face_dir.length() > 0:
                    target_angle = math.degrees(math.atan2(-face_dir.x, -face_dir.y))

            angle_diff = (target_angle - self.current_angle + 180) % 360 - 180
            self.current_angle += 4 if angle_diff > 0 else -4 if abs(angle_diff) > 4 else angle_diff

            if now - self.last_heal_time > self.heal_cooldown:
                self.last_heal_time = now
                for t in self.active_turrets:
                    t.hp = min(t.max_hp, t.hp + self.heal_amount)

            # 5. 애니메이션 및 화면 동기화
            if now - self.last_anim_update > self.anim_speed:
                self.last_anim_update = now
                self.anim_idx_engine = (self.anim_idx_engine + 1) % len(self.combined_frames)

            self.image = pygame.transform.rotate(self.combined_frames[self.anim_idx_engine], self.current_angle)
            self.rect = self.image.get_rect(center=self.pos - cam_pos)

        elif self.state == "EXPLODING":
            # 6. 파괴 애니메이션 재생
            if now - self.last_anim_update > self.anim_speed:
                self.last_anim_update = now
                self.anim_idx_base += 1
                if self.anim_idx_base >= len(self.base_frames):
                    self.kill() 
                    return

            if self.anim_idx_base < len(self.base_frames):
                self.image = pygame.transform.rotate(self.base_frames[self.anim_idx_base], self.current_angle)
                self.rect = self.image.get_rect(center=self.pos - cam_pos)

    def draw_heal_lines(self, screen, cam_pos):
        # Support가 살아있고, 관리 중인 포탑이 있다면 초록색 선을 그림
        if self.state == "ALIVE":
            start_pos = self.pos - cam_pos
            for t in self.active_turrets:
                if getattr(t, 'state', '') == "ALIVE":
                    end_pos = t.pos - cam_pos
                    pygame.draw.line(screen, (0, 255, 0), start_pos, end_pos, 2)