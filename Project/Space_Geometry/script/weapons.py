import pygame
import math
from settings import *
from sprite import Base64_Data
from asset_loader import SpriteFactory, SOUND_PATHS

class ObjectPool:
    def __init__(self, class_type, initial_size=100, **kwargs):
        self.class_type = class_type
        self.kwargs = kwargs # 객체 생성 시 필요한 추가 정보 (예: owner_class_name)
        # 게임 시작 시 객체를 미리 생성해 리스트(창고)에 보관
        self.pool = [self.class_type(self, **self.kwargs) for _ in range(initial_size)]

    def get(self, *args, **reset_kwargs):
        if self.pool:
            obj = self.pool.pop()
        else:
            obj = self.class_type(self, **self.kwargs)
        
        # 꺼낸 객체의 상태를 리셋(초기화)
        obj.reset(*args, **reset_kwargs)
        return obj

    def return_to_pool(self, obj):
        self.pool.append(obj)

# [공통 헬퍼 함수] 스프라이트를 쨍하게 만들어줌
def enhance_color(img, size, intensity=150):
    base_img = pygame.transform.scale(img, size).convert_alpha()
    overlay = base_img.copy()
    overlay.set_alpha(intensity)
    base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return base_img

class Bullet(pygame.sprite.Sprite):
    def __init__(self, pool, owner_class_name="Player"):
        super().__init__()
        self.pool = pool
        
        # 창고를 만들 때 한 번만 이미지를 로딩해 둡니다.
        if owner_class_name == "Player":
            config = Base64_Data["PLAYER_BULLET_B64"]
        else: # Pirate 등 적군 총알
            config = Base64_Data["PIRATE_BULLET_B64"]
            
        self.size = config["size"]
        raw_frames = SpriteFactory().get_frames(config["b64"], cols=config["cols"], rows=config["rows"])
        self.bright_image = enhance_color(raw_frames[0], self.size, intensity=160)
        
        self.radius = config["radius"]
        self.hitbox_size = config["hitbox_size"]
        self.hitbox = pygame.Rect(0, 0, *self.hitbox_size)

    def reset(self, pos, direction, damage, owner, speed=12):
        # 쏠 때마다 위치, 방향, 데미지 등을 새롭게 세팅합니다.
        angle = math.degrees(math.atan2(-direction.x, -direction.y)) + 90
        self.image = pygame.transform.rotate(self.bright_image, angle)
        
        self.pos = pygame.math.Vector2(pos)
        self.rect = self.image.get_rect(center=self.pos)
        
        self.hitbox.center = self.pos
        self.vel = direction * speed
        self.damage = damage
        self.owner = owner

    def update(self, cam_pos, *args):
        self.pos += self.vel
        self.rect.center = self.pos - cam_pos
        self.hitbox.center = self.pos 
        
        # 화면 밖을 벗어나면 삭제 대신 풀(창고)로 반납
        if not (-200 <= self.pos.x <= MAP_WIDTH + 200 and -200 <= self.pos.y <= MAP_HEIGHT + 200): 
            self.deactivate()

    def deactivate(self):
        self.kill()
        self.pool.return_to_pool(self)

class BindBullet(pygame.sprite.Sprite):
    def __init__(self, pool, owner_class_name="Scout"):
        super().__init__()
        self.pool = pool
        
        # 스프라이트는 일단 기존 적 총알과 같은 것을 사용한다고 하셨으므로 그대로 가져옵니다.
        config = Base64_Data["SCOUT_BULLET_B464"]
            
        self.size = config["size"]
        raw_frames = SpriteFactory().get_frames(config["b64"], cols=config["cols"], rows=config["rows"])
        
        # (참고) 만약 나중에 속박 총알만 색을 노랗게 바꾸고 싶다면 enhance_color 파라미터를 조절하시면 됩니다.
        self.bright_image = enhance_color(raw_frames[0], self.size, intensity=160)
        
        self.radius = config["radius"]
        self.hitbox_size = config["hitbox_size"]
        self.hitbox = pygame.Rect(0, 0, *self.hitbox_size)
        
        # 🌟 핵심: 일반 총알과 구분하기 위한 특수 속성 추가
        self.is_bind = True 
        self.stun_duration = 1000 # 1초(1000ms) 속박

    def reset(self, pos, direction, damage, owner, speed=7): 
        # 일반 총알(12)보다 피하기 쉽게 속도를 7로 살짝 낮췄습니다. 원하시면 수정 가능합니다.
        angle = math.degrees(math.atan2(-direction.x, -direction.y)) + 90
        self.image = pygame.transform.rotate(self.bright_image, angle)
        
        self.pos = pygame.math.Vector2(pos)
        self.rect = self.image.get_rect(center=self.pos)
        
        self.hitbox.center = self.pos
        self.vel = direction * speed
        self.damage = damage
        self.owner = owner

    def update(self, cam_pos, *args):
        self.pos += self.vel
        self.rect.center = self.pos - cam_pos
        self.hitbox.center = self.pos 
        
        # 화면 밖을 벗어나면 삭제 대신 풀(창고)로 반납 (기존과 완벽 동일)
        if not (-200 <= self.pos.x <= MAP_WIDTH + 200 and -200 <= self.pos.y <= MAP_HEIGHT + 200): 
            self.deactivate()

    def deactivate(self):
        self.kill()
        self.pool.return_to_pool(self)


class Missile(pygame.sprite.Sprite):
    def __init__(self, pool):
        super().__init__()
        self.pool = pool
        config = Base64_Data["MISSILE_B64"]
        self.size = config["size"]
        
        raw_frames = SpriteFactory().get_frames(config["b64"], cols=config["cols"], rows=config["rows"])
        self.frames = [enhance_color(img, self.size, intensity=160) for img in raw_frames]
        
        self.anim_speed = 80
        self.hitbox_size = config["hitbox_size"]
        self.hitbox = pygame.Rect(0, 0, *self.hitbox_size)
        self.lifetime = 5000

    def reset(self, pos, owner, diff_level):
        self.pos = pygame.math.Vector2(pos)
        self.hitbox.center = self.pos
        
        self.current_angle = owner.current_angle if hasattr(owner, 'current_angle') else 0
        self.image = pygame.transform.rotate(self.frames[0], self.current_angle)
        self.rect = self.image.get_rect(center=self.pos)
        
        self.speed = 6 + (diff_level * 0.4)
        self.rotation_speed = 0.5 # + (diff_level * 0.05)
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

    def deactivate(self):
        self.kill()
        self.pool.return_to_pool(self)

class Bomb(pygame.sprite.Sprite):
    _cached_bomb_frames = []
    _cached_exp_frames = []

    def __init__(self, pool, **kwargs):
        super().__init__()
        self.pool = pool
        
        # 1. 캐시가 비어있을 때 (게임 켜지고 최초 1회)만 굽습니다.
        if not Bomb._cached_bomb_frames:
            b_data = Base64_Data["bomb"]["B64"]
            
            bomb_b64 = b_data["bomb_b64"]
            bomb_cols, bomb_rows = bomb_b64.get("cols", 40), bomb_b64.get("rows", 25)
            bomb_size = bomb_b64.get("size", (64, 64))
            bomb_indices = bomb_b64.get("indices", [0, 1, 2, 3]) 
            
            raw_bomb = SpriteFactory().get_frames(bomb_b64["b64"], cols=bomb_cols, rows=bomb_rows)
            
            def enhance_color(img, target_size, intensity=160):
                base_img = pygame.transform.scale(img, target_size).convert_alpha()
                overlay = base_img.copy()
                overlay.set_alpha(intensity) 
                base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                return base_img

            # 구워진 프레임을 클래스 변수 리스트에 채워 넣습니다.
            Bomb._cached_bomb_frames.extend([enhance_color(raw_bomb[i], bomb_size) for i in bomb_indices])
            
            exp_b64 = b_data["explosion"]
            exp_cols, exp_rows = exp_b64.get("cols", 12), exp_b64.get("rows", 9)
            base_exp_size = exp_b64.get("size", (150, 150))
            
            visual_scale = 2.8 
            visual_exp_size = (int(base_exp_size[0] * visual_scale), int(base_exp_size[1] * visual_scale))
            
            exp_indices = exp_b64.get("indices", [0,1,2,3,4,5,6,7,8,9,11]) 
            raw_exp = SpriteFactory().get_frames(exp_b64["b64"], cols=exp_cols, rows=exp_rows)
            
            # 그 무거운 420x420 폭발 프레임도 딱 한 번만 굽습니다!
            Bomb._cached_exp_frames.extend([enhance_color(raw_exp[i], visual_exp_size, intensity=180) for i in exp_indices])
            
        # 2. 이후 생성되는 모든 폭탄은 이미 구워진 이미지만 쏙 빼다 씁니다.
        self.bomb_frames = Bomb._cached_bomb_frames
        self.exp_frames = Bomb._cached_exp_frames
        
        b_data = Base64_Data["bomb"]["B64"]
        exp_b64 = b_data["explosion"]
        self.exp_radius = exp_b64.get("hitbox", (150, 150))[0] // 2
        
        self.anim_speed = 100
        self.fuse_time = 2000

    def reset(self, start_pos, target_pos, damage=2, speed=5, **kwargs):
        # 2. 풀에서 꺼낼 때마다 상태 초기화
        self.pos = pygame.math.Vector2(start_pos)
        self.target_pos = pygame.math.Vector2(target_pos)
        self.damage = damage
        
        # 🛠️ [수정됨] 매개변수로 받은 speed를 인스턴스 변수로 저장!
        self.speed = speed 
        
        self.state = "MOVING"
        self.anim_idx = 0
        now = pygame.time.get_ticks()
        self.last_anim_update = now
        self.timer_start = now
        self.has_damaged = False
        
        self.image = self.bomb_frames[0]
        self.rect = self.image.get_rect(center=self.pos)

    def update(self, cam_pos, player_obj, particle_group=None, **kwargs):
        now = pygame.time.get_ticks()
        
        if self.state == "MOVING":
            direction = self.target_pos - self.pos
            # 🛠️ [수정됨] 하드코딩된 '5' 대신 'self.speed'를 사용하도록 변경!
            if direction.length() > self.speed:
                self.pos += direction.normalize() * self.speed
            else:
                self.pos = pygame.math.Vector2(self.target_pos)
                self.state = "PLANTED"
                self.timer_start = now # 도착 시점부터 퓨즈 카운트 시작
                
            if now - self.last_anim_update > self.anim_speed:
                self.last_anim_update = now
                self.anim_idx = (self.anim_idx + 1) % len(self.bomb_frames)
            self.image = self.bomb_frames[self.anim_idx]
            self.rect = self.image.get_rect(center=self.pos - cam_pos)
            
        elif self.state == "PLANTED":
            if now - self.last_anim_update > self.anim_speed:
                self.last_anim_update = now
                self.anim_idx = (self.anim_idx + 1) % len(self.bomb_frames)
            self.image = self.bomb_frames[self.anim_idx]
            self.rect = self.image.get_rect(center=self.pos - cam_pos)
            
            # 퓨즈 타임 아웃 시 폭발
            if now - self.timer_start > self.fuse_time:
                self.state = "EXPLODING"
                self.anim_idx = 0
                self.last_anim_update = now
                
        elif self.state == "EXPLODING":
            # 폭발 시 데미지 1회만 적용
            if now - self.last_anim_update > 60:
                self.last_anim_update = now
                self.anim_idx += 1
                
                # 폭발 애니메이션이 끝나면 풀로 반환
                if self.anim_idx >= len(self.exp_frames):
                    self.deactivate()
                    return
                    
            self.image = self.exp_frames[self.anim_idx]
            self.rect = self.image.get_rect(center=self.pos - cam_pos)

    def draw(self, screen, cam_pos):
        screen_pos = self.pos - cam_pos
        
        # 🛠️ [추가됨] 목표 지점의 화면 좌표 계산 (착탄 지점 표시용)
        target_screen_pos = self.target_pos - cam_pos 
        
        if self.state == "MOVING":
            # 날아가는 중일 때도 목표 지점에 얇은 빨간색 범위 선을 미리 그려줌
            pygame.draw.circle(screen, (139, 0, 0), target_screen_pos, int(self.exp_radius), 1)
            screen.blit(self.image, self.rect)
            
        elif self.state == "PLANTED":
            screen.blit(self.image, self.rect)
            
            # 다급해지는 점멸 효과 (PLANTED 상태일 때만)
            elapsed = pygame.time.get_ticks() - self.timer_start
            progress = min(1.0, elapsed / self.fuse_time)
            
            blink_interval = max(50, 500 - int(progress * 450))
            
            # 기본 범위 라인은 계속 보이게 유지
            pygame.draw.circle(screen, (139, 0, 0), screen_pos, int(self.exp_radius), 1)
            
            # 점멸하는 붉은 원
            if (elapsed % blink_interval) < (blink_interval // 2):
                pygame.draw.circle(screen, (255, 0, 0), screen_pos, int(self.exp_radius), max(1, int(3 * progress)))
                
        elif self.state == "EXPLODING":
            screen.blit(self.image, self.rect)

    def deactivate(self):
        # 3. 미사일 클래스처럼 리스트 배제(kill) 및 풀로 반환
        self.kill()
        if hasattr(self, 'pool') and self.pool:
            self.pool.return_to_pool(self)

def render_glowing_laser(surface, start_pos, end_pos, color, level):
    """
    거대 Surface 생성과 rotate 연산을 제거하여 최적화된 다이렉트 레이저 드로잉
    """
    diff = end_pos - start_pos
    length = diff.length()
    if length == 0:
        return
        
    thickness = int(10 + level * 2)
    
    # 전달받은 색상에서 RGB 값만 추출
    c_r, c_g, c_b = color[:3]
    
    # 투명도(Alpha)를 쓰는 대신, 색상을 어둡게 만들어 빛 번짐을 흉내냅니다.
    outer_color = (c_r // 3, c_g // 3, c_b // 3)
    mid_color = (int(c_r * 0.8), int(c_g * 0.8), int(c_b * 0.8))
    core_color = (255, 255, 255)

    # 1. 캔버스 생성/회전 없이 시작점과 끝점을 연결하는 선을 화면에 '직접' 그립니다.
    pygame.draw.line(surface, outer_color, start_pos, end_pos, thickness * 2)
    pygame.draw.line(surface, mid_color, start_pos, end_pos, thickness)
    pygame.draw.line(surface, core_color, start_pos, end_pos, max(2, thickness // 3))

    # 2. 총구(시작 부분) 이펙트도 화면에 직접 그립니다.
    # int()로 감싸주어 좌표나 반지름에 소수점이 들어가 에러가 나는 것을 방지합니다.
    start_pos_int = (int(start_pos.x), int(start_pos.y))
    pygame.draw.circle(surface, mid_color, start_pos_int, int(thickness * 1.5))
    pygame.draw.circle(surface, core_color, start_pos_int, int(thickness // 1.5))