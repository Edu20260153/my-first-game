import pygame
import math
import random
from settings import *
from sprite import Base64_Data
from asset_loader import SpriteFactory, sounds
from weapons import Bullet, ObjectPool
from effects import create_explosion

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        p = Base64_Data["player"]
        player_base = p["b64"]["PLAYER_BASE_B64"]
        player_engine = p["b64"]["PLAYER_ENGINE_B64"]
        player_BARRIER_B64 = p["b64"]["PLAYER_BARRIER_B64"]

        self.size = p["size"]
        
        raw_base = SpriteFactory().get_frames(player_base["b64"], cols=player_base["cols"], rows=player_base["rows"])
        raw_engine = SpriteFactory().get_frames(player_engine["b64"], cols=player_engine["cols"], rows=player_engine["rows"])
        raw_barrier = SpriteFactory().get_frames(player_BARRIER_B64["b64"], cols=player_BARRIER_B64["cols"], rows=player_BARRIER_B64["rows"])
        
        # [수정 2] 스프라이트를 더 밝게 만드는 헬퍼 함수
        def enhance_color(img, intensity=120):
            base_img = pygame.transform.scale(img, self.size).convert_alpha()
            overlay = base_img.copy()
            overlay.set_alpha(intensity)
            base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            return base_img

        self.base_frames = [enhance_color(img) for img in raw_base]
        self.engine_frames = [enhance_color(img) for img in raw_engine]
        self.barrier_frames = [enhance_color(img) for img in raw_barrier]
        
        self.image = self.base_frames[0]
        self.rect = self.image.get_rect()
        self.pos = pygame.math.Vector2(MAP_WIDTH//2, MAP_HEIGHT//2) 
        
        # [수정 4] 이미지 크기와 별개로, 충돌 판정 반경을 24로 설정
        self.radius = p["radius"]
        self.hitbox = pygame.Rect(*p["hitbox"])
        
        self.anim_idx_base = 0
        self.anim_idx_engine = 0
        self.anim_idx_barrier = 0
        self.last_anim_update = pygame.time.get_ticks()
        self.anim_speed = p["anim_speed"]
        
        self.vel = pygame.math.Vector2(0, 0)
        self.accel_power, self.friction = 0.6, 0.92
        self.current_angle, self.target_angle, self.rotation_speed = 0, 0, 15
        self.max_hp, self.hp, self.damage, self.bullet_count, self.shoot_delay = 10, 10, 1, 1, 250
        self.level, self.exp, self.max_exp = 1, 0, 10
        self.is_invincible, self.last_hit_time, self.last_shoot_time = False, 0, 0
        self.dash_power, self.dash_cooldown, self.last_dash_time, self.is_dashing = 20, 1500, 0, False
        self.afterimages = []
        
        self.laser_level = 0
        self.laser_cooldown, self.laser_duration, self.laser_timer, self.laser_active = 3000, 500, 0, False
        self.laser_damage_tick = 0
        self.lasers_hit = set()
        self.laser_angle = 0.0
        self.laser_rot_speed = 4.0

        self.vampire_level, self.invincible_timer = 0, 0
        self.stun_end_time = 0
        self.player_bullet_pool = ObjectPool(Bullet, initial_size=150, owner_class_name="Player")
        
        self.is_dead = False 
        self.is_destroyed = False 

        self.is_hacked = False
        self.hack_end_time = 0
        
        # 기본 이동 키 매핑 (상, 하, 좌, 우)
        self.default_move_keys = {
            'up': pygame.K_w,
            'down': pygame.K_s,
            'left': pygame.K_a,
            'right': pygame.K_d
        }
        
        # 기본 발사 키 매핑 (상, 하, 좌, 우)
        self.default_shoot_keys = {
            'up': pygame.K_UP,
            'down': pygame.K_DOWN,
            'left': pygame.K_LEFT,
            'right': pygame.K_RIGHT
        }
        
        # 현재 활성화된 키 매핑 (해킹 시 이 값이 변경됨)
        self.current_move_keys = self.default_move_keys.copy()
        self.current_shoot_keys = self.default_shoot_keys.copy()

    def gain_exp(self, base_amount, diff_level):
        self.exp += base_amount + diff_level
        if self.exp >= self.max_exp:
            self.exp -= self.max_exp
            self.level += 1
            self.max_exp = int(10 + (self.level ** 1.8) * 5)
            return True
        return False

    def take_damage(self, amount):
        if not self.is_invincible and not self.is_dead:
            self.hp -= amount
            self.is_invincible, self.last_hit_time, self.invincible_timer = True, pygame.time.get_ticks(), 1000
            
            if self.hp <= 0:
                self.hp = 0
                self.is_dead = True
                self.anim_idx_base = 0 

                self.radius = 0
                self.hitbox = pygame.Rect(0, 0, 0, 0)
            return True
        return False

    def trigger_vampire(self, particle_group):
        if self.vampire_level > 0 and random.random() < (self.vampire_level * 0.01):
            heal_amt = 1 + (self.vampire_level // 2)
            if self.hp < self.max_hp:
                self.hp = min(self.max_hp, self.hp + heal_amt)
                create_explosion(self.pos, GREEN, 3, particle_group) 

    def update(self, cam_pos, bullet_group):
        now = pygame.time.get_ticks()
        if self.is_dead:
            if not self.is_destroyed:
                if now - self.last_anim_update > self.anim_speed:
                    self.last_anim_update = now
                    if self.anim_idx_base < len(self.base_frames) - 1:
                        self.anim_idx_base += 1
                    else:
                        self.is_destroyed = True 
                
                self.image = pygame.transform.rotate(self.base_frames[self.anim_idx_base], self.current_angle)
                self.rect = self.image.get_rect(center=self.pos - cam_pos)
            return

        keys = pygame.key.get_pressed()
        
        # 🌟 해킹 상태 확인 및 해제
        if self.is_hacked and now > self.hack_end_time:
            self.restore_hack()

        # 🌟 스턴 상태 확인 플래그
        is_stunned = now < self.stun_end_time
        
        # =================================================================
        # 스턴 상태가 아닐 때만 이동, 대시, 공격, 회전 로직 실행
        # =================================================================
        if not is_stunned:
            accel = pygame.math.Vector2(0, 0)
            
            # [수정] 하드코딩된 키 대신 current_move_keys 딕셔너리 사용
            if keys[self.current_move_keys['up']]:    accel.y -= 1
            if keys[self.current_move_keys['down']]:  accel.y += 1
            if keys[self.current_move_keys['left']]:  accel.x -= 1
            if keys[self.current_move_keys['right']]: accel.x += 1
            
            if accel.length() > 0: self.vel += accel.normalize() * self.accel_power


            if keys[pygame.K_LSHIFT] and now - self.last_dash_time > self.dash_cooldown and self.vel.length() > 0:
                self.vel = self.vel.normalize() * self.dash_power
                self.last_dash_time, self.is_dashing, self.is_invincible = now, True, True
                self.last_hit_time, self.invincible_timer = now, 200
                if "dash" in sounds and sounds["dash"]: sounds["dash"].play()

            shoot_dir = pygame.math.Vector2(0, 0)
            
            # [수정] 하드코딩된 키 대신 current_shoot_keys 딕셔너리 사용
            if keys[self.current_shoot_keys['up']]:    shoot_dir.y -= 1
            if keys[self.current_shoot_keys['down']]:  shoot_dir.y += 1
            if keys[self.current_shoot_keys['left']]:  shoot_dir.x -= 1
            if keys[self.current_shoot_keys['right']]: shoot_dir.x += 1

            if shoot_dir.length() > 0:
                shoot_dir = shoot_dir.normalize()
                self.target_angle = math.degrees(math.atan2(-shoot_dir.x, -shoot_dir.y))
                if now - self.last_shoot_time > self.shoot_delay:
                    for i in range(self.bullet_count):
                        offset = (i - (self.bullet_count - 1) / 2) * 15
                        bullet_group.add(self.player_bullet_pool.get(self.pos, shoot_dir.rotate(offset), self.damage, self))
                    self.last_shoot_time = now
                    if "shoot" in sounds and sounds["shoot"]: sounds["shoot"].play()

            if self.laser_level > 0:
                if not self.laser_active and now - self.laser_timer > self.laser_cooldown:
                    self.laser_active, self.laser_timer, self.laser_damage_tick = True, now, now
                    self.lasers_hit.clear()
                elif self.laser_active:
                    if now - self.laser_timer > self.laser_duration:
                        self.laser_active, self.laser_timer = False, now
                    else:
                        if now - self.laser_damage_tick > 100:
                            self.lasers_hit.clear()
                            self.laser_damage_tick = now

            # 1. 플레이어 본체 회전 로직 (빠르게 회전)
            angle_diff = (self.target_angle - self.current_angle + 180) % 360 - 180
            if abs(angle_diff) > self.rotation_speed: 
                self.current_angle += self.rotation_speed if angle_diff > 0 else -self.rotation_speed
            else: 
                self.current_angle = self.target_angle

            # 2. 레이저 독립 회전 로직
            laser_angle_diff = (self.target_angle - self.laser_angle + 180) % 360 - 180
            if abs(laser_angle_diff) > self.laser_rot_speed:
                self.laser_angle += self.laser_rot_speed if laser_angle_diff > 0 else -self.laser_rot_speed
            else:
                self.laser_angle = self.target_angle

        self.vel *= self.friction
        self.pos += self.vel
        
        self.pos.x = max(15, min(MAP_WIDTH - 15, self.pos.x))
        self.pos.y = max(15, min(MAP_HEIGHT - 15, self.pos.y))

        self.hitbox.center = self.pos

        if self.is_dashing: self.afterimages.append([pygame.math.Vector2(self.pos), self.current_angle, 150])
        for img in self.afterimages[:]:
            img[2] -= 15
            if img[2] <= 0: self.afterimages.remove(img)

        if self.is_dashing and now - self.last_dash_time > 200: self.is_dashing = False
        if self.is_invincible and now - self.last_hit_time > self.invincible_timer: self.is_invincible = False

        if now - self.last_anim_update > self.anim_speed:
            self.last_anim_update = now
            self.anim_idx_engine = (self.anim_idx_engine + 1) % len(self.engine_frames)
            self.anim_idx_barrier = (self.anim_idx_barrier + 1) % len(self.barrier_frames)

        temp_surf = pygame.Surface(self.size, pygame.SRCALPHA)
        
        # 🌟 스턴 중이 아닐 때만 엔진 불꽃 표시 (선택사항, 스턴 중엔 엔진 꺼짐)
        if self.vel.length() > 0.1 and not is_stunned:
            temp_surf.blit(self.engine_frames[self.anim_idx_engine], (0, 0))
            
        temp_surf.blit(self.base_frames[0], (0, 0))
        
        if self.is_invincible or self.is_dashing:
            temp_surf.blit(self.barrier_frames[self.anim_idx_barrier], (0, 0))

        self.image = pygame.transform.rotate(temp_surf, self.current_angle)
        self.rect = self.image.get_rect(center=self.pos - cam_pos)

    def draw_afterimages(self, surface, cam_pos):
        for pos, angle, alpha in self.afterimages:
            barrier_img = self.barrier_frames[self.anim_idx_barrier].copy()
            barrier_img.fill((*CYAN, alpha), special_flags=pygame.BLEND_RGBA_MULT)
            rotated_img = pygame.transform.rotate(barrier_img, angle)
            surface.blit(rotated_img, rotated_img.get_rect(center=pos - cam_pos))

    def apply_hack(self, duration=5000):
        """보스가 이 메서드를 호출하여 플레이어를 해킹합니다."""
        now = pygame.time.get_ticks()
        self.is_hacked = True
        self.hack_end_time = now + duration

        # 1. 모든 키를 하나의 리스트로 모읍니다 (이동 키 4개 + 발사 키 4개 = 총 8개)
        all_keys = list(self.default_move_keys.values()) + list(self.default_shoot_keys.values())
        
        # 2. 키 리스트를 무작위로 섞습니다.
        import random
        random.shuffle(all_keys)

        # 3. 섞인 키를 다시 이동과 발사에 무작위로 배정합니다.
        self.current_move_keys = {
            'up': all_keys[0],
            'down': all_keys[1],
            'left': all_keys[2],
            'right': all_keys[3]
        }
        
        self.current_shoot_keys = {
            'up': all_keys[4],
            'down': all_keys[5],
            'left': all_keys[6],
            'right': all_keys[7]
        }
        
        # (선택) 해킹당했을 때 시스템 에러 소리를 재생해도 좋습니다.
        # if "error" in sounds: sounds["error"].play()

    def restore_hack(self):
        """해킹 시간이 끝나면 원래 키로 복구합니다."""
        self.is_hacked = False
        self.current_move_keys = self.default_move_keys.copy()
        self.current_shoot_keys = self.default_shoot_keys.copy()