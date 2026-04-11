import pygame
import math
import random
import base64
import io

# 1. 초기화 및 설정
pygame.init()
pygame.mixer.init() # 사운드 믹서 초기화

info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Space Isaac: Sound & Ultimate Boss")

MAP_WIDTH = WIDTH * 2
MAP_HEIGHT = HEIGHT * 2
camera_pos = pygame.math.Vector2(0, 0) 
clock = pygame.time.Clock()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎵 사운드 설정 (경로를 한곳에서 관리)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOUND_PATHS = {
    "bgm": "bgm.mp3",       # 배경음악 파일 이름
    "shoot": "shoot.wav",   # 플레이어 총 발사음
    "dash": "dash.wav"      # 플레이어 대시음
}

sounds = {}
try:
    pygame.mixer.music.load(SOUND_PATHS["bgm"])
    pygame.mixer.music.set_volume(0.4)
    pygame.mixer.music.play(-1) # 무한 반복 재생
except Exception as e:
    print(f"BGM 로드 실패 (파일이 없어도 게임은 실행됩니다): {e}")

try: sounds["shoot"] = pygame.mixer.Sound(SOUND_PATHS["shoot"]); sounds["shoot"].set_volume(0.3)
except: sounds["shoot"] = None
try: sounds["dash"] = pygame.mixer.Sound(SOUND_PATHS["dash"]); sounds["dash"].set_volume(0.5)
except: sounds["dash"] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎨 챕터별 배경 Base64 데이터 변수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BG_CHAPTER1_B64 = ""  # 여기에 1챕터(지구) 애니메이션 Base64 복사

try:
    font = pygame.font.SysFont("malgungothic", 20, True)
    mid_font = pygame.font.SysFont("malgungothic", 30, True)
    large_font = pygame.font.SysFont("malgungothic", 70, True)
except:
    font = pygame.font.SysFont("arial", 20, True)
    mid_font = pygame.font.SysFont("arial", 30, True)
    large_font = pygame.font.SysFont("arial", 70, True)

BLACK, GREEN, WHITE = (0, 0, 0), (0, 255, 0), (255, 255, 255)
RED, CYAN, YELLOW = (255, 50, 50), (0, 255, 255), (255, 255, 0)
PURPLE, ORANGE, BLUE = (150, 0, 255), (255, 165, 0), (50, 100, 255)


class Base64SpriteSheet:
    def __init__(self, b64_string, cols, rows):
        self.frames = []
        try:
            sheet_bytes = base64.b64decode(b64_string)
            sheet = pygame.image.load(io.BytesIO(sheet_bytes)).convert_alpha()
            frame_w = sheet.get_width() // cols
            frame_h = sheet.get_height() // rows
            target_size = (int(frame_w * 1.5), int(frame_h * 1.5))

            for i in range(cols * rows):
                row, col = divmod(i, cols)
                rect = pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h)
                image = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
                image.blit(sheet, (0, 0), rect)
                
                image = pygame.transform.scale(image, target_size)
                tint_surface = pygame.Surface(target_size, pygame.SRCALPHA)
                tint_surface.fill((100, 150, 150))
                image.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                self.frames.append(image)
        except:
            surf = pygame.Surface((100, 100))
            surf.fill((15, 15, 25))
            self.frames.append(surf)

    def get_frames(self):
        return self.frames

class TwinklingStars:
    def __init__(self, num_stars):
        self.stars = []
        for _ in range(num_stars):
            x, y = random.randint(0, WIDTH), random.randint(0, HEIGHT)
            base_size = random.uniform(0.5, 2.5)
            twinkle_speed = random.uniform(0.02, 0.08)
            parallax = random.uniform(0.05, 0.4) 
            color = random.choice([(255, 255, 255), (255, 255, 100), (100, 100, 255)])
            self.stars.append({'pos': pygame.math.Vector2(x, y), 'base_size': base_size, 'twinkle_speed': twinkle_speed, 'color': color, 'current_twinkle': 0, 'parallax': parallax})

    def update_and_draw(self, surface, cam_pos):
        for star in self.stars:
            star['current_twinkle'] += star['twinkle_speed']
            brightness = math.sin(star['current_twinkle']) * 0.5 + 0.5 
            size = star['base_size'] * (1 + brightness * 0.5)
            color = tuple(int(c * brightness) for c in star['color'])
            parallax_x = (star['pos'].x - cam_pos.x * star['parallax']) % WIDTH
            parallax_y = (star['pos'].y - cam_pos.y * star['parallax']) % HEIGHT
            pygame.draw.circle(surface, color, (int(parallax_x), int(parallax_y)), size)

class AnimatedBackground:
    def __init__(self):
        self.frames_ch1 = Base64SpriteSheet(BG_CHAPTER1_B64, cols=50, rows=5).get_frames()
        self.current_frames = self.frames_ch1
        self.frame_index = 0
        self.animation_speed = 60 
        self.last_update = pygame.time.get_ticks()
        self.stars_effect = TwinklingStars(int(WIDTH * HEIGHT / 3000))

    def update_and_draw(self, surface, current_stage, cam_pos):
        self.current_frames = self.frames_ch1
        now = pygame.time.get_ticks()
        if now - self.last_update > self.animation_speed:
            self.last_update = now
            self.frame_index = (self.frame_index + 1) % len(self.current_frames)

        self.stars_effect.update_and_draw(surface, cam_pos)

        bg_offset_x = -cam_pos.x * 0.1
        bg_offset_y = -cam_pos.y * 0.1
        
        current_image = self.current_frames[self.frame_index]
        image_rect = current_image.get_rect(center=(WIDTH // 2 + bg_offset_x, HEIGHT // 2 + bg_offset_y))
        surface.blit(current_image, image_rect)

UPGRADE_OPTIONS = [
    {"name": "저격수 총열", "desc": "피해량 +5, 연사속도 15% 느려짐", "effects": [{"type": "damage", "value": 5}, {"type": "fire_rate", "value": 1.15}]},
    {"name": "중장갑 테두리", "desc": "최대 체력 +2, 피해량 +1", "effects": [{"type": "max_hp", "value": 2}, {"type": "damage", "value": 1}]},
    {"name": "기관총 개조", "desc": "연사속도 20% 빨라짐, 피해량 -1", "effects": [{"type": "fire_rate", "value": 0.8}, {"type": "damage", "value": -1}]},
    {"name": "산탄총", "desc": "발사체 +1, 연사속도 10% 느려짐", "effects": [{"type": "bullet_count", "value": 1}, {"type": "fire_rate", "value": 1.1}]},
    {"name": "올라운더", "desc": "체력 +1, 피해량 +1, 연사 5% 단축", "effects": [{"type": "max_hp", "value": 1}, {"type": "damage", "value": 1}, {"type": "fire_rate", "value": 0.95}]},
    {"name": "궤도 레이저", "desc": "주기적으로 관통 레이저 발사", "effects": [{"type": "laser", "value": 1}]},
    {"name": "흡혈 모듈", "desc": "타격시 1% 확률로 체력 회복", "effects": [{"type": "vampire", "value": 1}]},
    {"name": "핵", "desc": "최대 체력 +200, 연사속도 200% 빨라짐", "effects": [{"type": "max_hp", "value": 200}, {"type": "fire_rate", "value": 0.6}]},
]

def create_explosion(pos, color, count=10):
    for _ in range(count): particles.add(Particle(pos, color))

def check_line_collision(start_pos, dir_vec, target_pos, target_radius, thickness=30):
    vec_to_target = target_pos - start_pos
    projection = vec_to_target.dot(dir_vec)
    if projection > 0:
        closest_point = start_pos + dir_vec * projection
        if target_pos.distance_to(closest_point) < (thickness/2) + target_radius:
            return True
    return False

def handle_exp(amount, stage):
    global game_state, current_choices
    if player.gain_exp(amount, stage):
        current_choices = random.sample(UPGRADE_OPTIONS, 3)
        game_state = "LEVEL_UP"

def trigger_vampire():
    if player.vampire_level > 0 and random.random() < (player.vampire_level * 0.01):
        heal_amt = 1 + (player.vampire_level // 2)
        if player.hp < player.max_hp:
            player.hp = min(player.max_hp, player.hp + heal_amt)
            create_explosion(player.pos, GREEN, 3) 

class Particle(pygame.sprite.Sprite):
    def __init__(self, pos, color, speed_range=(1, 4), lifetime=30):
        super().__init__()
        self.size = random.randint(2, 5)
        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (self.size//2, self.size//2), self.size//2)
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)
        angle = random.uniform(0, math.pi * 2)
        self.vel = pygame.math.Vector2(math.cos(angle), math.sin(angle)) * random.uniform(*speed_range)
        self.lifetime = random.randint(lifetime - 10, lifetime + 10)
        self.start_life = self.lifetime

    def update(self, *args):
        cam_pos = args[0]
        self.pos += self.vel
        self.rect.center = self.pos - cam_pos 
        self.lifetime -= 1
        if self.lifetime <= 0: self.kill()
        else: self.image.set_alpha(max(0, int(255 * (self.lifetime / self.start_life))))

class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos, direction, damage, owner, color=YELLOW, speed=12):
        super().__init__()
        self.image = pygame.Surface((10, 10), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (5, 5), 5)
        self.pos = pygame.math.Vector2(pos)
        self.rect = self.image.get_rect(center=self.pos)
        self.radius = 5 
        self.vel = direction * speed
        self.damage = damage
        self.owner = owner

    def update(self, *args):
        cam_pos = args[0]
        self.pos += self.vel
        self.rect.center = self.pos - cam_pos
        if not (-200 <= self.pos.x <= MAP_WIDTH + 200 and -200 <= self.pos.y <= MAP_HEIGHT + 200): 
            self.kill()

class Missile(pygame.sprite.Sprite):
    def __init__(self, pos, owner, diff_level):
        super().__init__()
        self.original_image = pygame.Surface((16, 8), pygame.SRCALPHA)
        pygame.draw.polygon(self.original_image, ORANGE, [(0, 2), (12, 2), (16, 4), (12, 6), (0, 6)])
        self.image = self.original_image
        self.radius, self.pos = 4, pygame.math.Vector2(pos)
        self.rect = self.image.get_rect(center=self.pos)
        self.current_angle = owner.current_angle if hasattr(owner, 'current_angle') else 0
        self.speed = 6 + (diff_level * 0.4)
        self.rotation_speed = 1.0 + (diff_level * 0.05)
        self.damage, self.spawn_time, self.lifetime = 1, pygame.time.get_ticks(), 5000

    def update(self, *args):
        cam_pos, player_obj = args[0], args[1]
        now = pygame.time.get_ticks()
        if now - self.spawn_time > self.lifetime: self.kill(); return
        
        direction = player_obj.pos - self.pos
        if direction.length() > 0:
            target_angle = math.degrees(math.atan2(-direction.y, direction.x))
            angle_diff = (target_angle - self.current_angle + 180) % 360 - 180
            if abs(angle_diff) > self.rotation_speed: self.current_angle += self.rotation_speed if angle_diff > 0 else -self.rotation_speed
            else: self.current_angle = target_angle
        rad = math.radians(self.current_angle)
        self.vel = pygame.math.Vector2(math.cos(rad), -math.sin(rad)) * self.speed
        self.pos += self.vel
        self.image = pygame.transform.rotate(self.original_image, self.current_angle)
        self.rect = self.image.get_rect(center=self.pos - cam_pos)

class Meteor(pygame.sprite.Sprite):
    def __init__(self, diff_level):
        super().__init__()
        self.size = random.randint(30, 60)
        self.original_image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.polygon(self.original_image, (100, 100, 100), [(self.size//2, 0), (self.size, self.size//3), (self.size*0.8, self.size), (self.size//4, self.size), (0, self.size//2)])
        self.image, self.radius = self.original_image.copy(), self.size * 0.35
        
        side = random.choice(['top', 'bottom', 'left', 'right'])
        if side == 'top': self.pos = pygame.math.Vector2(random.randint(0, MAP_WIDTH), 10)
        elif side == 'bottom': self.pos = pygame.math.Vector2(random.randint(0, MAP_WIDTH), MAP_HEIGHT - 10)
        elif side == 'left': self.pos = pygame.math.Vector2(10, random.randint(0, MAP_HEIGHT))
        else: self.pos = pygame.math.Vector2(MAP_WIDTH - 10, random.randint(0, MAP_HEIGHT))
        
        self.rect = self.image.get_rect(center=self.pos)
        target = pygame.math.Vector2(MAP_WIDTH//2 + random.randint(-200, 200), MAP_HEIGHT//2 + random.randint(-200, 200))
        self.vel = (target - self.pos).normalize() * (random.uniform(2, 4) + diff_level * 0.2)
        self.hp, self.angle, self.rotation_speed = 3 + diff_level, 0, random.uniform(-4, 4)

    def take_damage(self, amount):
        self.hp -= amount
        trigger_vampire()
        if self.hp <= 0: self.kill(); return True
        return False

    def update(self, *args):
        cam_pos = args[0]
        self.pos += self.vel; self.angle = (self.angle + self.rotation_speed) % 360
        
        if self.pos.x <= self.radius or self.pos.x >= MAP_WIDTH - self.radius:
            self.vel.x *= -1
            self.pos.x = max(self.radius, min(MAP_WIDTH - self.radius, self.pos.x))
        if self.pos.y <= self.radius or self.pos.y >= MAP_HEIGHT - self.radius:
            self.vel.y *= -1
            self.pos.y = max(self.radius, min(MAP_HEIGHT - self.radius, self.pos.y))

        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect = self.image.get_rect(center=self.pos - cam_pos)

class Pirate(pygame.sprite.Sprite):
    def __init__(self, player_obj, diff_level):
        super().__init__()
        self.original_image = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.polygon(self.original_image, PURPLE, [(20, 0), (0, 40), (20, 30), (40, 40)])
        self.image, self.radius = self.original_image, 15
        
        angle = random.uniform(0, math.pi * 2)
        dist = max(WIDTH, HEIGHT) 
        self.pos = pygame.math.Vector2(player_obj.pos.x + math.cos(angle)*dist, player_obj.pos.y + math.sin(angle)*dist)
        
        self.rect = self.image.get_rect(center=self.pos)
        self.offset_dist, self.offset_angle, self.vel = random.uniform(250, 400), random.uniform(0, 360), pygame.math.Vector2(0, 0)
        self.hp = 5 + (diff_level * 2)
        self.last_attack_time, self.attack_delay = pygame.time.get_ticks(), max(800, random.randint(1500, 2500) - (diff_level * 150))
        self.bullet_speed, self.current_angle = 8 + (diff_level * 0.5), 0

    def take_damage(self, amount):
        self.hp -= amount
        trigger_vampire()
        if self.hp <= 0: self.kill(); return True
        return False

    def update(self, *args):
        cam_pos, player_obj, enemy_proj = args[0], args[1], args[2]
        now = pygame.time.get_ticks()
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
            if random.random() < min(0.7, 0.4 + (player_obj.level * 0.05)): enemy_proj.add(Missile(self.pos, self, player_obj.level))
            else:
                shoot_dir = pygame.math.Vector2(0, -1).rotate(-self.current_angle)
                enemy_proj.add(Bullet(self.pos, shoot_dir, 1, self, color=RED, speed=self.bullet_speed))
        
        self.image = pygame.transform.rotate(self.original_image, self.current_angle)
        self.rect = self.image.get_rect(center=self.pos - cam_pos)

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.size = (30, 30)
        self.original_image = pygame.Surface(self.size, pygame.SRCALPHA)
        pygame.draw.polygon(self.original_image, GREEN, [(15, 0), (0, 30), (30, 30)])
        self.image, self.radius = self.original_image, 12 
        self.pos = pygame.math.Vector2(MAP_WIDTH//2, MAP_HEIGHT//2) 
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
        self.vampire_level, self.invincible_timer = 0, 0

    def gain_exp(self, base_amount, diff_level):
        self.exp += base_amount + diff_level
        if self.exp >= self.max_exp:
            self.exp -= self.max_exp
            self.level += 1
            self.max_exp = int(10 + (self.level ** 1.8) * 5)
            return True
        return False

    def take_damage(self, amount):
        if not self.is_invincible:
            self.hp -= amount
            self.is_invincible, self.last_hit_time, self.invincible_timer = True, pygame.time.get_ticks(), 1000
            return True
        return False

    def update(self, *args):
        cam_pos, bullet_group = args[0], args[1]
        now = pygame.time.get_ticks()
        keys = pygame.key.get_pressed()
        
        accel = pygame.math.Vector2(0, 0)
        if keys[pygame.K_w]: accel.y -= 1
        if keys[pygame.K_s]: accel.y += 1
        if keys[pygame.K_a]: accel.x -= 1
        if keys[pygame.K_d]: accel.x += 1
        if accel.length() > 0: self.vel += accel.normalize() * self.accel_power

        if keys[pygame.K_LSHIFT] and now - self.last_dash_time > self.dash_cooldown and self.vel.length() > 0:
            self.vel = self.vel.normalize() * self.dash_power
            self.last_dash_time, self.is_dashing, self.is_invincible = now, True, True
            self.last_hit_time, self.invincible_timer = now, 200
            # [신규] 대시 사운드 재생
            if sounds["dash"]: sounds["dash"].play()

        shoot_dir = pygame.math.Vector2(0, 0)
        if keys[pygame.K_UP]:    shoot_dir.y -= 1
        if keys[pygame.K_DOWN]:  shoot_dir.y += 1
        if keys[pygame.K_LEFT]:  shoot_dir.x -= 1
        if keys[pygame.K_RIGHT]: shoot_dir.x += 1

        if shoot_dir.length() > 0:
            shoot_dir = shoot_dir.normalize()
            self.target_angle = math.degrees(math.atan2(-shoot_dir.x, -shoot_dir.y))
            if now - self.last_shoot_time > self.shoot_delay:
                for i in range(self.bullet_count):
                    offset = (i - (self.bullet_count - 1) / 2) * 15
                    bullet_group.add(Bullet(self.pos, shoot_dir.rotate(offset), self.damage, self, color=CYAN))
                self.last_shoot_time = now
                # [신규] 사격 사운드 재생
                if sounds["shoot"]: sounds["shoot"].play()

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

        self.vel *= self.friction
        self.pos += self.vel
        
        self.pos.x = max(15, min(MAP_WIDTH - 15, self.pos.x))
        self.pos.y = max(15, min(MAP_HEIGHT - 15, self.pos.y))

        if self.is_dashing: self.afterimages.append([pygame.math.Vector2(self.pos), self.current_angle, 150])
        for img in self.afterimages[:]:
            img[2] -= 15
            if img[2] <= 0: self.afterimages.remove(img)

        if self.is_dashing and now - self.last_dash_time > 200: self.is_dashing = False
        if self.is_invincible and now - self.last_hit_time > self.invincible_timer: self.is_invincible = False

        angle_diff = (self.target_angle - self.current_angle + 180) % 360 - 180
        if abs(angle_diff) > self.rotation_speed: self.current_angle += self.rotation_speed if angle_diff > 0 else -self.rotation_speed
        else: self.current_angle = self.target_angle

        temp_surf = pygame.Surface(self.size, pygame.SRCALPHA)
        if self.is_invincible:
            stealth_color = (0, 100, 100) if self.is_dashing else (0, 100, 0)
            pygame.draw.polygon(temp_surf, stealth_color, [(15, 0), (0, 30), (30, 30)])
        else:
            pygame.draw.polygon(temp_surf, GREEN, [(15, 0), (0, 30), (30, 30)])
            
        self.image = pygame.transform.rotate(temp_surf, self.current_angle)
        self.rect = self.image.get_rect(center=self.pos - cam_pos)

    def draw_afterimages(self, surface, cam_pos):
        for pos, angle, alpha in self.afterimages:
            temp_surf = pygame.Surface(self.size, pygame.SRCALPHA)
            pygame.draw.polygon(temp_surf, (*CYAN, alpha), [(15, 0), (0, 30), (30, 30)])
            rotated_img = pygame.transform.rotate(temp_surf, angle)
            surface.blit(rotated_img, rotated_img.get_rect(center=pos - cam_pos))

# --- [수정됨] 대폭 강화된 별 보스 ---
class StarBoss(pygame.sprite.Sprite):
    def __init__(self, diff_level):
        super().__init__()
        self.outer_radius, self.inner_radius = 120, 50
        self.size = self.outer_radius * 2 + 60 
        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        self.pos = pygame.math.Vector2(MAP_WIDTH//2, 100) 
        self.rect = self.image.get_rect(center=self.pos)
        self.radius = 70 
        self.max_hp = 20000
        self.hp = self.max_hp
        self.angle = 0
        
        self.state = "SPAWNING"
        self.pattern_timer, self.action_timer, self.dash_count = 0, 0, 0
        self.target_pos = pygame.math.Vector2(MAP_WIDTH//2, MAP_HEIGHT//2)
        
        # 레이저 정보: (시작점, 끝점, 방향, 두께, 대미지)
        self.active_lasers = [] 
        self.phase2_triggered, self.shield_active = False, False
        self.summoned_pirates = []
        self.afterimages = [] 
        self.locked_target = pygame.math.Vector2(0, 0)
        self.blast_dir = pygame.math.Vector2(0, 1)
        self.desp_angle = 0
        self.visible = True

    def get_star_polygon(self):
        points = []
        center = self.size // 2
        for i in range(10):
            r = self.outer_radius if i % 2 == 0 else self.inner_radius
            rad = math.radians(i * 36 + self.angle)
            points.append((center + math.cos(rad)*r, center + math.sin(rad)*r))
        return points

    def get_world_vertices(self, all_points=False):
        points = []
        for i in range(10):
            if all_points or i % 2 == 0: 
                r = self.outer_radius if i % 2 == 0 else self.inner_radius
                rad = math.radians(i * 36 + self.angle)
                points.append(self.pos + pygame.math.Vector2(math.cos(rad), math.sin(rad)) * r)
        return points

    def take_damage(self, amount):
        if self.state in ["SPAWNING", "SHIELD_PREP", "SHIELD_ACTIVE", "DASH_HIDE"]: return False
        self.hp -= amount
        trigger_vampire()
        if self.hp <= 0: self.kill(); return True
        return False

    def update(self, *args):
        cam_pos, player_obj, enemy_proj, pirates_group, current_stage = args[0], args[1], args[2], args[3], args[4]
        dt = clock.get_time()
        self.pattern_timer -= dt
        self.action_timer -= dt
        self.active_lasers.clear()
        
        old_pos = pygame.math.Vector2(self.pos) # [신규] 상시 잔상을 위한 이전 위치 저장

        for img in self.afterimages[:]:
            img[2] -= 8 
            if img[2] <= 0: self.afterimages.remove(img)

        # 1페이즈 -> 2페이즈
        if self.hp <= self.max_hp * 0.5 and not self.phase2_triggered and self.state != "SPAWNING" and self.hp > self.max_hp * 0.1:
            self.phase2_triggered = True
            self.state = "SHIELD_PREP"
            self.target_pos = pygame.math.Vector2(MAP_WIDTH//2, MAP_HEIGHT//2)

        # 발악 (10% 이하)
        if self.hp > 0 and self.hp <= self.max_hp * 0.1 and self.state not in ["DESPERATION_PREP", "DESPERATION_BLAST"]:
            self.state, self.pattern_timer = "DESPERATION_PREP", 3000
            self.blast_dir = (player_obj.pos - self.pos).normalize()
            self.desp_angle = math.degrees(math.atan2(-self.blast_dir.y, self.blast_dir.x))

        if self.state == "SPAWNING":
            self.angle += 2
            direction = self.target_pos - self.pos
            if direction.length() > 5: self.pos += direction.normalize() * 2
            else: self.state, self.pattern_timer = "IDLE", 1000

        elif self.state == "SHIELD_PREP":
            self.angle += 5
            direction = self.target_pos - self.pos
            if direction.length() > 5: self.pos += direction.normalize() * 4
            else:
                self.state, self.shield_active = "SHIELD_ACTIVE", True
                self.summoned_pirates.clear()
                for _ in range(5):
                    new_pirate = Pirate(player_obj, current_stage + 2) 
                    pirates_group.add(new_pirate)
                    self.summoned_pirates.append(new_pirate)

        elif self.state == "SHIELD_ACTIVE":
            self.angle += 1
            alive_count = sum(1 for p in self.summoned_pirates if p.alive())
            if alive_count == 0: 
                self.shield_active = False
                self.state, self.pattern_timer = "IDLE", 1000
            else:
                heal_amount = self.max_hp * 0.02 * (dt / 1000)
                self.hp = min(self.max_hp, self.hp + heal_amount)

        elif self.state == "IDLE":
            self.angle += 1
            if self.pattern_timer <= 0: self.choose_pattern()

        elif self.state == "RUSH_PREP":
            self.angle += 3
            direction = self.target_pos - self.pos
            if direction.length() > 5: self.pos += direction.normalize() * 4
            else: self.state, self.pattern_timer, self.action_timer = "RUSH", 4000, 0
                
        elif self.state == "RUSH":
            self.angle += 8
            if self.action_timer <= 0:
                self.action_timer = 40
                for vertex in self.get_world_vertices(all_points=True):
                    dir_vec = (vertex - self.pos).normalize()
                    enemy_proj.add(Bullet(vertex, dir_vec, 1, self, color=RED, speed=7))
            if self.pattern_timer <= 0: self.state, self.pattern_timer = "IDLE", 1500

        elif self.state == "LASER_PREP":
            self.angle += 3
            direction = self.target_pos - self.pos
            if direction.length() > 5: self.pos += direction.normalize() * 4
            else: self.state, self.pattern_timer = "LASER", 5000
                
        elif self.state == "LASER":
            self.angle += 1.5
            for vertex in self.get_world_vertices():
                dir_vec = (vertex - self.pos).normalize()
                self.active_lasers.append((vertex, vertex + dir_vec * 4000, dir_vec, 30, 1))
            if self.pattern_timer <= 0: self.state, self.pattern_timer = "IDLE", 1500

        # [신규] 돌진 개편 (가두리 왕복 8번)
        elif self.state == "DASH_HIDE":
            self.visible = False
            edge = random.choice([(random.randint(0, MAP_WIDTH), 0), (random.randint(0, MAP_WIDTH), MAP_HEIGHT),
                                  (0, random.randint(0, MAP_HEIGHT)), (MAP_WIDTH, random.randint(0, MAP_HEIGHT))])
            self.pos = pygame.math.Vector2(edge)
            self.state, self.pattern_timer = "DASH_WARN", 500
            
        elif self.state == "DASH_WARN":
            self.visible = True
            self.angle += 20
            self.blast_dir = (player_obj.pos - self.pos).normalize()
            if self.pattern_timer <= 0:
                self.state = "DASHING"

        elif self.state == "DASHING":
            self.angle += 25
            self.pos += self.blast_dir * 50 # 엄청나게 빠른 속도
            
            # 돌진 중 노란 총알 무작위 난사
            if random.random() < 0.2: 
                shoot_dir = self.blast_dir.rotate(random.uniform(-40, 40))
                enemy_proj.add(Bullet(self.pos, shoot_dir, 1, self, color=YELLOW, speed=8))
                
            # 화면 끝(반대편)에 닿으면 즉시 다음 돌진 준비
            if self.pos.x <= 0 or self.pos.x >= MAP_WIDTH or self.pos.y <= 0 or self.pos.y >= MAP_HEIGHT:
                self.pos.x = max(0, min(MAP_WIDTH, self.pos.x))
                self.pos.y = max(0, min(MAP_HEIGHT, self.pos.y))
                self.dash_count += 1
                
                if self.dash_count >= 8:
                    self.state, self.pattern_timer = "IDLE", 2000
                else:
                    # 도착한 그 자리에서 바로 다시 경고 후 돌진
                    self.state, self.pattern_timer = "DASH_WARN", 400

        elif self.state == "BLACKHOLE_PREP":
            self.angle += 5
            direction = pygame.math.Vector2(MAP_WIDTH//2, MAP_HEIGHT//2) - self.pos
            if direction.length() > 15: self.pos += direction.normalize() * 15
            else: self.state, self.pattern_timer = "BLACKHOLE_PULL", 5000

        elif self.state == "BLACKHOLE_PULL":
            self.angle += 10
            pull_dir = self.pos - player_obj.pos
            if pull_dir.length() > 20: player_obj.pos += pull_dir.normalize() * 1.5
            
            if self.action_timer <= 0:
                self.action_timer = 100
                edge_x = random.choice([-100, MAP_WIDTH+100]) if random.random() > 0.5 else random.randint(0, MAP_WIDTH)
                edge_y = random.choice([-100, MAP_HEIGHT+100]) if edge_x not in [-100, MAP_WIDTH+100] else random.randint(0, MAP_HEIGHT)
                b_dir = (self.pos - pygame.math.Vector2(edge_x, edge_y)).normalize()
                enemy_proj.add(Bullet((edge_x, edge_y), b_dir, 1, self, color=YELLOW, speed=5))
                
            if self.pattern_timer <= 0:
                self.state, self.pattern_timer = "BLACKHOLE_AIM", 1200
                self.locked_target = pygame.math.Vector2(player_obj.pos)
                self.blast_dir = (self.locked_target - self.pos).normalize()

        elif self.state == "BLACKHOLE_AIM":
            self.angle += 25 
            if self.pattern_timer <= 0: self.state, self.pattern_timer = "BLACKHOLE_FIRE", 1000

        elif self.state == "BLACKHOLE_FIRE":
            self.angle += 35
            self.active_lasers.append((self.pos, self.pos + self.blast_dir * 4000, self.blast_dir, 120, 1))
            if self.pattern_timer <= 0: self.state, self.pattern_timer = "IDLE", 2000

        # [신규] 발악 개편
        elif self.state == "DESPERATION_PREP":
            self.angle += 25
            if self.pattern_timer <= 0: self.state, self.pattern_timer = "DESPERATION_BLAST", 10000

        elif self.state == "DESPERATION_BLAST":
            self.angle += 50
            # 플레이어 방향으로 전보다 더 빠르게 회전 (1.0도)
            target_angle = math.degrees(math.atan2(-(player_obj.pos.y - self.pos.y), player_obj.pos.x - self.pos.x))
            angle_diff = (target_angle - self.desp_angle + 180) % 360 - 180
            rot_speed = 1.0
            if abs(angle_diff) > rot_speed: self.desp_angle += rot_speed if angle_diff > 0 else -rot_speed
            else: self.desp_angle = target_angle
            
            rad = math.radians(self.desp_angle)
            self.blast_dir = pygame.math.Vector2(math.cos(rad), -math.sin(rad))
            
            # 두께 400, 대미지 2의 무시무시한 레이저
            self.active_lasers.append((self.pos, self.pos + self.blast_dir * 5000, self.blast_dir, 400, 2))
            
            # 발사하는 동안 초당 1%씩 자신의 피를 깎음
            self.hp -= self.max_hp * 0.01 * (dt / 1000)
            if self.hp <= 0:
                self.kill() # 자멸

        # 맵 외곽 제한 (돌진 중일 때는 밖으로 나갈 수 있게 예외처리)
        if self.state != "DASHING":
            self.pos.x = max(self.radius, min(MAP_WIDTH - self.radius, self.pos.x))
            self.pos.y = max(self.radius, min(MAP_HEIGHT - self.radius, self.pos.y))

        # [신규] 상시 이동 잔상 추가 (위치가 1 픽셀이라도 변했다면 잔상 생성)
        if (self.pos - old_pos).length() > 1.0 and self.visible:
            self.afterimages.append([pygame.math.Vector2(self.pos), self.angle, 100])

        self.image.fill(pygame.SRCALPHA)
        if self.visible:
            color = GREEN if self.shield_active else ((255, 100, 100) if self.state in ["DESPERATION_PREP", "DESPERATION_BLAST"] else ORANGE)
            pygame.draw.circle(self.image, (*color, 80), (self.size//2, self.size//2), self.outer_radius + 20)
            if self.shield_active: pygame.draw.circle(self.image, (*GREEN, 100), (self.size//2, self.size//2), self.outer_radius + 25, 8)
            pygame.draw.polygon(self.image, color, self.get_star_polygon())
        
        self.rect = self.image.get_rect(center=self.pos - cam_pos)

    def choose_pattern(self):
        pattern = random.choice(["RUSH", "LASER", "DASH", "BLACKHOLE"])
        if pattern == "RUSH":
            self.state, self.target_pos = "RUSH_PREP", pygame.math.Vector2(MAP_WIDTH//2, MAP_HEIGHT//2)
        elif pattern == "LASER":
            self.state, self.target_pos = "LASER_PREP", pygame.math.Vector2(MAP_WIDTH//2, MAP_HEIGHT//2)
        elif pattern == "DASH":
            self.state, self.dash_count = "DASH_HIDE", 0
        elif pattern == "BLACKHOLE":
            self.state = "BLACKHOLE_PREP"

    def draw_effects(self, surface, cam_pos):
        for pos, angle, alpha in self.afterimages:
            temp_surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            points = []
            c = self.size // 2
            for i in range(10):
                r = self.outer_radius if i % 2 == 0 else self.inner_radius
                rad_ang = math.radians(i * 36 + angle)
                points.append((c + math.cos(rad_ang)*r, c + math.sin(rad_ang)*r))
            pygame.draw.polygon(temp_surf, (*ORANGE, alpha), points)
            surface.blit(temp_surf, temp_surf.get_rect(center=pos - cam_pos))

        if self.state in ["DASH_WARN", "BLACKHOLE_AIM", "DESPERATION_PREP"]:
            if self.visible:
                pygame.draw.line(surface, (150, 0, 0), self.pos - cam_pos, self.pos + self.blast_dir * 4000 - cam_pos, 15)
            
        for start_pos, end_pos, _, thickness, _ in self.active_lasers:
            pygame.draw.line(surface, RED, start_pos - cam_pos, end_pos - cam_pos, thickness)
            pygame.draw.line(surface, WHITE, start_pos - cam_pos, end_pos - cam_pos, thickness // 3)

    # [수정됨] 피격 시 대미지를 반환하도록 변경 (0이면 안맞음)
    def check_laser_collision(self, player_obj):
        for start_pos, _, dir_vec, thickness, damage in self.active_lasers:
            if check_line_collision(start_pos, dir_vec, player_obj.pos, player_obj.radius, thickness): 
                return damage
        return 0

# --- 메인 실행 준비 ---
player = Player()
player_bullets, enemy_projectiles = pygame.sprite.Group(), pygame.sprite.Group()
meteors, pirates, particles = pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group()
boss_group = pygame.sprite.GroupSingle()

background_manager = AnimatedBackground()

running, game_state = True, "PLAYING"
play_time, current_stage = 0, 1 
boss_cleared_stages, current_choices = [], []
warning_timer, meteor_timer, pirate_timer = 0, 0, 0

# --- 게임 루프 ---
while running:
    dt = clock.tick(60)
    
    target_camera = player.pos - pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)
    camera_pos = camera_pos.lerp(target_camera, 0.1) 
    camera_pos.x = max(0, min(camera_pos.x, MAP_WIDTH - WIDTH))
    camera_pos.y = max(0, min(camera_pos.y, MAP_HEIGHT - HEIGHT))

    screen.fill(BLACK)
    background_manager.update_and_draw(screen, current_stage, camera_pos)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: running = False
        
        elif game_state == "LEVEL_UP" and event.type == pygame.KEYDOWN:
            idx = -1
            if event.key == pygame.K_1: idx = 0
            elif event.key == pygame.K_2: idx = 1
            elif event.key == pygame.K_3: idx = 2
            
            if 0 <= idx < len(current_choices):
                for effect in current_choices[idx]["effects"]:
                    if effect["type"] == "damage": player.damage = max(1, player.damage + effect["value"])
                    elif effect["type"] == "max_hp": player.max_hp += effect["value"]; player.hp += effect["value"]
                    elif effect["type"] == "fire_rate": player.shoot_delay = int(player.shoot_delay * effect["value"])
                    elif effect["type"] == "bullet_count": player.bullet_count += effect["value"]
                    elif effect["type"] == "vampire": player.vampire_level += effect["value"]
                    elif effect["type"] == "laser":
                        player.laser_level += 1
                        if player.laser_level > 1:
                            player.laser_cooldown = max(800, player.laser_cooldown - 300)
                            player.laser_duration += 150
                game_state = "PLAYING"
                player.hp = min(player.max_hp, player.hp + int(player.max_hp * 0.4))

    if game_state in ["PLAYING", "WARNING", "BOSS_BATTLE"]:
        if len(boss_group) == 0 and game_state != "WARNING": play_time += dt
        current_stage = (play_time // 20000) + 1 
        
        if current_stage % 10 == 0 and current_stage not in boss_cleared_stages and len(boss_group) == 0:
            if game_state == "PLAYING": game_state, warning_timer = "WARNING", 3000
            elif game_state == "WARNING":
                warning_timer -= dt
                if warning_timer <= 0: boss_group.add(StarBoss(current_stage)); game_state = "BOSS_BATTLE"

        if len(boss_group) == 0 and game_state != "WARNING":
            meteor_timer += dt
            if meteor_timer >= max(400, 1000 - (current_stage * 100)):
                meteor_timer = 0
                if len(meteors) < 25 + (current_stage * 2): meteors.add(Meteor(current_stage))
            if current_stage >= 2:
                pirate_timer += dt
                if pirate_timer >= max(1500, 5000 - (current_stage * 400)):
                    pirate_timer = 0
                    if len(pirates) < 5 + (current_stage // 2): pirates.add(Pirate(player, current_stage))

        player.update(camera_pos, player_bullets)
        player_bullets.update(camera_pos)
        enemy_projectiles.update(camera_pos, player)
        meteors.update(camera_pos)
        pirates.update(camera_pos, player, enemy_projectiles, current_stage)
        boss_group.update(camera_pos, player, enemy_projectiles, pirates, current_stage)
        particles.update(camera_pos)

        player_laser_lines = []
        if player.laser_active:
            base_dir = pygame.math.Vector2(0, -1).rotate(-player.current_angle)
            for i in range(player.laser_level):
                offset_angle = (i - (player.laser_level - 1) / 2) * 15
                dir_vec = base_dir.rotate(offset_angle)
                player_laser_lines.append((player.pos, player.pos + dir_vec * 1500, dir_vec))
                
            for start_pos, end_pos, dir_vec in player_laser_lines:
                for m in meteors:
                    if m not in player.lasers_hit and check_line_collision(start_pos, dir_vec, m.pos, m.radius, 30):
                        player.lasers_hit.add(m)
                        create_explosion(m.pos, YELLOW, 5)
                        if m.take_damage(player.damage): create_explosion(m.pos, (150, 150, 150), 15); handle_exp(2, current_stage)
                for p in pirates:
                    if p not in player.lasers_hit and check_line_collision(start_pos, dir_vec, p.pos, p.radius, 30):
                        player.lasers_hit.add(p)
                        create_explosion(p.pos, PURPLE, 5)
                        if p.take_damage(player.damage): create_explosion(p.pos, PURPLE, 20); handle_exp(5, current_stage)
                if boss_group.sprite and boss_group.sprite not in player.lasers_hit:
                    if check_line_collision(start_pos, dir_vec, boss_group.sprite.pos, boss_group.sprite.radius, 30):
                        player.lasers_hit.add(boss_group.sprite)
                        create_explosion(boss_group.sprite.pos, ORANGE, 5)
                        if boss_group.sprite.take_damage(player.damage):
                            create_explosion(boss_group.sprite.pos, ORANGE, 150); boss_cleared_stages.append(current_stage)
                            game_state = "PLAYING"; handle_exp(50, current_stage)

        for bullet in player_bullets:
            for hit in pygame.sprite.spritecollide(bullet, meteors, False, pygame.sprite.collide_circle):
                bullet.kill(); create_explosion(bullet.pos, YELLOW, 5)
                if hit.take_damage(bullet.damage): create_explosion(hit.pos, (150, 150, 150), 15); handle_exp(2, current_stage)
            for hit in pygame.sprite.spritecollide(bullet, pirates, False, pygame.sprite.collide_circle):
                bullet.kill(); create_explosion(bullet.pos, YELLOW, 5)
                if hit.take_damage(bullet.damage): create_explosion(hit.pos, PURPLE, 20); handle_exp(5, current_stage)
            if boss_group.sprite and pygame.sprite.collide_circle(bullet, boss_group.sprite):
                bullet.kill(); create_explosion(bullet.pos, ORANGE, 8)
                if boss_group.sprite.take_damage(bullet.damage):
                    create_explosion(boss_group.sprite.pos, ORANGE, 150); boss_cleared_stages.append(current_stage)
                    game_state = "PLAYING"; handle_exp(50, current_stage)

        if not player.is_invincible:
            hit = False
            dmg_to_take = 1
            
            # [수정됨] 보스 레이저 피격 (발악일 경우 2대미지 반영)
            if boss_group.sprite:
                laser_dmg = boss_group.sprite.check_laser_collision(player)
                if laser_dmg > 0:
                    hit = True
                    dmg_to_take = laser_dmg

            if pygame.sprite.spritecollide(player, enemy_projectiles, True, pygame.sprite.collide_circle): hit = True
            elif pygame.sprite.spritecollide(player, meteors, True, pygame.sprite.collide_circle): hit = True
            elif pygame.sprite.spritecollide(player, pirates, False, pygame.sprite.collide_circle): hit = True
            elif boss_group.sprite and pygame.sprite.collide_circle(player, boss_group.sprite): hit = True
            
            if hit:
                if player.take_damage(dmg_to_take): create_explosion(player.pos, GREEN, 20)
                if player.hp <= 0: game_state = "GAME_OVER"

    # --- 렌더링 ---
    pygame.draw.rect(screen, (50, 50, 80), (-camera_pos.x, -camera_pos.y, MAP_WIDTH, MAP_HEIGHT), 5)

    if player.laser_active:
        for start_pos, end_pos, _ in player_laser_lines:
            pygame.draw.line(screen, BLUE, start_pos - camera_pos, end_pos - camera_pos, 10 + player.laser_level * 2)
            pygame.draw.line(screen, WHITE, start_pos - camera_pos, end_pos - camera_pos, 4)

    if boss_group.sprite: boss_group.sprite.draw_effects(screen, camera_pos)

    particles.draw(screen); player_bullets.draw(screen); enemy_projectiles.draw(screen)
    meteors.draw(screen); pirates.draw(screen); boss_group.draw(screen)
    
    if game_state != "GAME_OVER":
        player.draw_afterimages(screen, camera_pos)
        screen.blit(player.image, player.rect)
    
    pygame.draw.rect(screen, (80, 0, 0), (20, 20, 200, 20))
    pygame.draw.rect(screen, RED, (20, 20, int(200 * max(0, player.hp / player.max_hp)), 20))
    pygame.draw.rect(screen, WHITE, (20, 20, 200, 20), 2)
    screen.blit(font.render(f"HP: {player.hp} / {player.max_hp}", True, WHITE), (230, 18))

    pygame.draw.rect(screen, (50, 50, 50), (20, 50, 200, 20))
    pygame.draw.rect(screen, YELLOW, (20, 50, int(200 * (player.exp / player.max_exp)), 20))
    pygame.draw.rect(screen, WHITE, (20, 50, 200, 20), 2)
    screen.blit(font.render(f"LV: {player.level} ({player.exp}/{player.max_exp})", True, WHITE), (230, 48))
    
    time_text = mid_font.render(f"Time: {play_time//60000:02d}:{(play_time//1000)%60:02d}  |  Stage(Diff): {current_stage}", True, CYAN)
    screen.blit(time_text, time_text.get_rect(center=(WIDTH//2, HEIGHT - 30)))
    
    if boss_group.sprite:
        boss, bar_width = boss_group.sprite, 600
        pygame.draw.rect(screen, (50, 0, 0), (WIDTH//2 - bar_width//2, 20, bar_width, 25))
        pygame.draw.rect(screen, RED, (WIDTH//2 - bar_width//2, 20, int(bar_width * (max(0, boss.hp) / boss.max_hp)), 25))
        pygame.draw.rect(screen, WHITE, (WIDTH//2 - bar_width//2, 20, bar_width, 25), 2)
        boss_txt = font.render(f"STAR BOSS [{(max(0, boss.hp) / boss.max_hp)*100:.1f}%]", True, WHITE)
        screen.blit(boss_txt, boss_txt.get_rect(center=(WIDTH//2, 32)))

    if game_state == "WARNING":
        if (play_time // 200) % 2 == 0:
            warn = large_font.render("WARNING: BOSS APPROACHING", True, RED)
            screen.blit(warn, warn.get_rect(center=(WIDTH//2, HEIGHT//2)))
            
    elif game_state == "LEVEL_UP":
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180)); screen.blit(overlay, (0, 0))
        lv_msg = large_font.render("레벨 업!", True, CYAN)
        screen.blit(lv_msg, lv_msg.get_rect(center=(WIDTH//2, HEIGHT//3 - 50)))
        
        for idx, choice in enumerate(current_choices):
            box = pygame.Rect(WIDTH//2 - 250, HEIGHT//2 - 50 + (idx * 90), 500, 70)
            pygame.draw.rect(screen, (50, 50, 50), box, border_radius=10)
            pygame.draw.rect(screen, WHITE, box, 2, border_radius=10)
            screen.blit(mid_font.render(f"{idx + 1}. {choice['name']}", True, WHITE), (box.x + 20, box.y + 10))
            screen.blit(font.render(choice['desc'], True, GREEN), (box.x + 20, box.y + 45))

    elif game_state == "GAME_OVER":
        msg = large_font.render("게임 오버", True, RED)
        screen.blit(msg, msg.get_rect(center=(WIDTH//2, HEIGHT//2)))
        tip_msg = font.render("Press ESC to Exit", True, WHITE)
        screen.blit(tip_msg, tip_msg.get_rect(center=(WIDTH//2, HEIGHT//2 + 50)))
    
    pygame.display.flip()

pygame.quit()