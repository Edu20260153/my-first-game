import pygame
import math
import random

# 1. 초기화 및 설정
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Isaac: Laser & Boss Update")
clock = pygame.time.Clock()

try:
    font = pygame.font.SysFont("malgungothic", 20, True)
    mid_font = pygame.font.SysFont("malgungothic", 30, True)
    large_font = pygame.font.SysFont("malgungothic", 70, True)
except:
    font = pygame.font.SysFont("arial", 20, True)
    mid_font = pygame.font.SysFont("arial", 30, True)
    large_font = pygame.font.SysFont("arial", 70, True)

# 색상
BLACK, GREEN, WHITE = (0, 0, 0), (0, 255, 0), (255, 255, 255)
RED, CYAN, YELLOW = (255, 50, 50), (0, 255, 255), (255, 255, 0)
PURPLE, ORANGE, BLUE = (150, 0, 255), (255, 165, 0), (50, 100, 255)

# --- 1. 업그레이드 선택지 (레이저 추가) ---
UPGRADE_OPTIONS = [
    {"name": "저격수 총열", "desc": "피해량 +5, 연사속도 15% 느려짐", "effects": [{"type": "damage", "value": 5}, {"type": "fire_rate", "value": 1.15}]},
    {"name": "중장갑 테두리", "desc": "최대 체력 +2, 피해량 +1", "effects": [{"type": "max_hp", "value": 2}, {"type": "damage", "value": 1}]},
    {"name": "기관총 개조", "desc": "연사속도 20% 빨라짐, 피해량 -1", "effects": [{"type": "fire_rate", "value": 0.8}, {"type": "damage", "value": -1}]},
    {"name": "산탄총", "desc": "발사체 +1, 연사속도 10% 느려짐", "effects": [{"type": "bullet_count", "value": 1}, {"type": "fire_rate", "value": 1.1}]},
    {"name": "올라운더", "desc": "체력 +1, 피해량 +1, 연사 5% 단축", "effects": [{"type": "max_hp", "value": 1}, {"type": "damage", "value": 1}, {"type": "fire_rate", "value": 0.95}]},
    {"name": "궤도 레이저", "desc": "주기적으로 관통 레이저 발사 (중복시 강화)", "effects": [{"type": "laser", "value": 1}]},
    {"name": "핵", "desc": "최대 체력 +200, 연사속도 200% 빨라짐", "effects": [{"type": "max_hp", "value": 200}, {"type": "fire_rate", "value": 0.6}]},
]

# --- 2. 헬퍼 함수 및 파티클 ---
def create_explosion(pos, color, count=10):
    for _ in range(count): particles.add(Particle(pos, color))

def check_line_collision(start_pos, dir_vec, target_pos, target_radius):
    vec_to_target = target_pos - start_pos
    projection = vec_to_target.dot(dir_vec)
    if projection > 0:
        closest_point = start_pos + dir_vec * projection
        if target_pos.distance_to(closest_point) < 15 + target_radius:
            return True
    return False

def handle_exp(amount, stage):
    global game_state, current_choices
    if player.gain_exp(amount, stage):
        current_choices = random.sample(UPGRADE_OPTIONS, 3)
        game_state = "LEVEL_UP"

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
        self.pos += self.vel
        self.rect.center = self.pos
        self.lifetime -= 1
        if self.lifetime <= 0: self.kill()
        else: self.image.set_alpha(max(0, int(255 * (self.lifetime / self.start_life))))

class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos, direction, damage, owner, color=YELLOW, speed=12):
        super().__init__()
        self.image = pygame.Surface((10, 10), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (5, 5), 5)
        self.rect = self.image.get_rect(center=pos)
        self.radius = 5 
        self.pos = pygame.math.Vector2(pos)
        self.vel = direction * speed
        self.damage = damage
        self.owner = owner

    def update(self, *args):
        self.pos += self.vel
        self.rect.center = self.pos
        if not screen.get_rect().inflate(100, 100).collidepoint(self.pos): self.kill()

class Missile(pygame.sprite.Sprite):
    def __init__(self, pos, owner, diff_level):
        super().__init__()
        self.original_image = pygame.Surface((16, 8), pygame.SRCALPHA)
        pygame.draw.polygon(self.original_image, ORANGE, [(0, 2), (12, 2), (16, 4), (12, 6), (0, 6)])
        self.image = self.original_image
        self.rect = self.image.get_rect(center=pos)
        self.radius, self.pos = 4, pygame.math.Vector2(pos)
        self.current_angle = owner.current_angle if hasattr(owner, 'current_angle') else 0
        self.speed = 6 + (diff_level * 0.4)
        self.rotation_speed = 1.0 + (diff_level * 0.05)
        self.damage, self.spawn_time, self.lifetime = 1, pygame.time.get_ticks(), 5000

    def update(self, player):
        now = pygame.time.get_ticks()
        if now - self.spawn_time > self.lifetime:
            self.kill(); return
        direction = player.pos - self.pos
        if direction.length() > 0:
            target_angle = math.degrees(math.atan2(-direction.y, direction.x))
            angle_diff = (target_angle - self.current_angle + 180) % 360 - 180
            if abs(angle_diff) > self.rotation_speed: self.current_angle += self.rotation_speed if angle_diff > 0 else -self.rotation_speed
            else: self.current_angle = target_angle
        rad = math.radians(self.current_angle)
        self.vel = pygame.math.Vector2(math.cos(rad), -math.sin(rad)) * self.speed
        self.pos += self.vel
        self.image = pygame.transform.rotate(self.original_image, self.current_angle)
        self.rect = self.image.get_rect(center=self.pos)

# --- 3. 환경 및 적 앤티티 ---
class Meteor(pygame.sprite.Sprite):
    def __init__(self, diff_level):
        super().__init__()
        self.size = random.randint(30, 60)
        self.original_image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.polygon(self.original_image, (100, 100, 100), [(self.size//2, 0), (self.size, self.size//3), (self.size*0.8, self.size), (self.size//4, self.size), (0, self.size//2)])
        self.image, self.radius = self.original_image.copy(), self.size * 0.35
        side = random.choice(['top', 'bottom', 'left', 'right'])
        if side == 'top': self.pos = pygame.math.Vector2(random.randint(0, WIDTH), -50)
        elif side == 'bottom': self.pos = pygame.math.Vector2(random.randint(0, WIDTH), HEIGHT + 50)
        elif side == 'left': self.pos = pygame.math.Vector2(-50, random.randint(0, HEIGHT))
        else: self.pos = pygame.math.Vector2(WIDTH + 50, random.randint(0, HEIGHT))
        self.rect = self.image.get_rect(center=self.pos)
        target = pygame.math.Vector2(WIDTH//2 + random.randint(-100, 100), HEIGHT//2 + random.randint(-100, 100))
        self.vel = (target - self.pos).normalize() * (random.uniform(2, 4) + diff_level * 0.2)
        self.hp, self.angle, self.rotation_speed = 3 + diff_level, 0, random.uniform(-4, 4)

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0: self.kill(); return True
        return False

    def update(self, *args):
        self.pos += self.vel; self.angle = (self.angle + self.rotation_speed) % 360
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect = self.image.get_rect(center=self.pos)
        if self.pos.length_squared() > (WIDTH**2 + HEIGHT**2) * 2: self.kill()

class Pirate(pygame.sprite.Sprite):
    def __init__(self, player, diff_level):
        super().__init__()
        self.original_image = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.polygon(self.original_image, PURPLE, [(20, 0), (0, 40), (20, 30), (40, 40)])
        self.image, self.radius = self.original_image, 15
        angle = random.uniform(0, math.pi * 2)
        dist = max(WIDTH, HEIGHT)
        self.pos = pygame.math.Vector2(WIDTH//2 + math.cos(angle)*dist, HEIGHT//2 + math.sin(angle)*dist)
        self.rect = self.image.get_rect(center=self.pos)
        self.offset_dist, self.offset_angle, self.vel = random.uniform(250, 400), random.uniform(0, 360), pygame.math.Vector2(0, 0)
        self.hp = 5 + (diff_level * 2)
        self.last_attack_time, self.attack_delay = pygame.time.get_ticks(), max(800, random.randint(1500, 2500) - (diff_level * 150))
        self.bullet_speed, self.current_angle = 8 + (diff_level * 0.5), 0

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0: self.kill(); return True
        return False

    def update(self, player, enemy_projectiles, diff_level):
        now = pygame.time.get_ticks()
        target_pos = player.pos + pygame.math.Vector2(self.offset_dist, 0).rotate(self.offset_angle)
        direction = target_pos - self.pos
        if direction.length() > 5: self.vel = self.vel.lerp(direction.normalize() * min(5, direction.length() * 0.05), 0.05)
        else: self.vel *= 0.8
        self.pos += self.vel
        
        face_dir = player.pos - self.pos
        if face_dir.length() > 0:
            target_angle = math.degrees(math.atan2(-face_dir.x, -face_dir.y))
            angle_diff = (target_angle - self.current_angle + 180) % 360 - 180
            self.current_angle += 4 if angle_diff > 0 else -4 if abs(angle_diff) > 4 else angle_diff

        if now - self.last_attack_time > self.attack_delay:
            self.last_attack_time = now
            if random.random() < min(0.7, 0.4 + (diff_level * 0.05)): enemy_projectiles.add(Missile(self.pos, self, diff_level))
            else:
                shoot_dir = pygame.math.Vector2(0, -1).rotate(-self.current_angle)
                enemy_projectiles.add(Bullet(self.pos, shoot_dir, 1, self, color=RED, speed=self.bullet_speed))
        self.image = pygame.transform.rotate(self.original_image, self.current_angle)
        self.rect = self.image.get_rect(center=self.pos)

# --- 4. 플레이어 클래스 ---
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.size = (30, 30)
        self.original_image = pygame.Surface(self.size, pygame.SRCALPHA)
        pygame.draw.polygon(self.original_image, GREEN, [(15, 0), (0, 30), (30, 30)])
        self.image, self.radius = self.original_image, 12 
        self.pos, self.vel = pygame.math.Vector2(WIDTH//2, HEIGHT//2), pygame.math.Vector2(0, 0)
        self.accel_power, self.friction = 0.6, 0.92
        self.current_angle, self.target_angle, self.rotation_speed = 0, 0, 15
        self.max_hp, self.hp, self.damage, self.bullet_count, self.shoot_delay = 10, 10, 1, 1, 250
        self.level, self.exp, self.max_exp = 1, 0, 10
        self.is_invincible, self.last_hit_time, self.last_shoot_time = False, 0, 0
        self.dash_power, self.dash_cooldown, self.last_dash_time, self.is_dashing = 20, 1500, 0, False
        self.afterimages = []
        
        # 레이저 스킬 변수
        self.laser_level = 0
        self.laser_cooldown = 3000
        self.laser_duration = 500
        self.laser_timer = 0
        self.laser_active = False
        self.laser_damage_tick = 0
        self.lasers_hit = set()

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
            self.is_invincible, self.last_hit_time = True, pygame.time.get_ticks()
            return True
        return False

    def update(self, bullet_group):
        now = pygame.time.get_ticks()
        keys = pygame.key.get_pressed()
        
        # 이동 처리
        accel = pygame.math.Vector2(0, 0)
        if keys[pygame.K_w]: accel.y -= 1
        if keys[pygame.K_s]: accel.y += 1
        if keys[pygame.K_a]: accel.x -= 1
        if keys[pygame.K_d]: accel.x += 1
        if accel.length() > 0: self.vel += accel.normalize() * self.accel_power

        if keys[pygame.K_LSHIFT] and now - self.last_dash_time > self.dash_cooldown and self.vel.length() > 0:
            self.vel = self.vel.normalize() * self.dash_power
            self.last_dash_time, self.is_dashing, self.is_invincible, self.last_hit_time = now, True, True, now

        # 사격 처리
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

        # 레이저 발사 제어 로직
        if self.laser_level > 0:
            if not self.laser_active and now - self.laser_timer > self.laser_cooldown:
                self.laser_active, self.laser_timer, self.laser_damage_tick = True, now, now
                self.lasers_hit.clear()
            elif self.laser_active:
                if now - self.laser_timer > self.laser_duration:
                    self.laser_active, self.laser_timer = False, now
                else:
                    if now - self.laser_damage_tick > 100: # 0.1초마다 타격 판정 초기화 (지속 딜)
                        self.lasers_hit.clear()
                        self.laser_damage_tick = now

        self.vel *= self.friction
        self.pos += self.vel
        self.pos.x = max(15, min(WIDTH - 15, self.pos.x))
        self.pos.y = max(15, min(HEIGHT - 15, self.pos.y))

        # 애니메이션 및 각도 처리
        if self.is_dashing: self.afterimages.append([pygame.math.Vector2(self.pos), self.current_angle, 150])
        for img in self.afterimages[:]:
            img[2] -= 15
            if img[2] <= 0: self.afterimages.remove(img)

        if self.is_dashing and now - self.last_dash_time > 200: self.is_dashing = False
        if self.is_invincible and now - self.last_hit_time > 1000: self.is_invincible = False

        angle_diff = (self.target_angle - self.current_angle + 180) % 360 - 180
        if abs(angle_diff) > self.rotation_speed: self.current_angle += self.rotation_speed if angle_diff > 0 else -self.rotation_speed
        else: self.current_angle = self.target_angle

        if self.is_invincible and (now // 100) % 2 == 0: self.image = pygame.Surface(self.size, pygame.SRCALPHA)
        else:
            temp_surf = pygame.Surface(self.size, pygame.SRCALPHA)
            pygame.draw.polygon(temp_surf, CYAN if self.is_dashing else GREEN, [(15, 0), (0, 30), (30, 30)])
            self.image = pygame.transform.rotate(temp_surf, self.current_angle)
        self.rect = self.image.get_rect(center=self.pos)

    def draw_afterimages(self, surface):
        for pos, angle, alpha in self.afterimages:
            temp_surf = pygame.Surface(self.size, pygame.SRCALPHA)
            pygame.draw.polygon(temp_surf, (*CYAN, alpha), [(15, 0), (0, 30), (30, 30)])
            rotated_img = pygame.transform.rotate(temp_surf, angle)
            surface.blit(rotated_img, rotated_img.get_rect(center=pos))

# --- 5. 보스 클래스 ---
class StarBoss(pygame.sprite.Sprite):
    def __init__(self, diff_level):
        super().__init__()
        self.outer_radius, self.inner_radius = 80, 35
        self.size = self.outer_radius * 2
        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(WIDTH//2, -100))
        self.pos = pygame.math.Vector2(WIDTH//2, -100)
        self.radius = 50 
        self.max_hp = 15000
        self.hp = self.max_hp
        self.angle = 0
        
        self.state = "SPAWNING"
        self.pattern_timer, self.action_timer, self.dash_count = 0, 0, 0
        self.target_pos = pygame.math.Vector2(WIDTH//2, HEIGHT//2)
        self.active_lasers = [] 

    def get_star_polygon(self):
        points = []
        for i in range(10):
            r = self.outer_radius if i % 2 == 0 else self.inner_radius
            rad = math.radians(i * 36 + self.angle)
            points.append((self.outer_radius + math.cos(rad)*r, self.outer_radius + math.sin(rad)*r))
        return points

    def get_world_vertices(self, all_points=False):
        points = []
        for i in range(10):
            if all_points or i % 2 == 0: # all_points가 참이면 10개 모든 꼭지점 반환
                r = self.outer_radius if i % 2 == 0 else self.inner_radius
                rad = math.radians(i * 36 + self.angle)
                points.append(self.pos + pygame.math.Vector2(math.cos(rad), math.sin(rad)) * r)
        return points

    def take_damage(self, amount):
        if self.state == "SPAWNING": return False
        self.hp -= amount
        if self.hp <= 0: self.kill(); return True
        return False

    def update(self, player, enemy_projectiles):
        dt = clock.get_time()
        self.pattern_timer -= dt
        self.action_timer -= dt
        self.active_lasers.clear()

        if self.hp > 0 and self.hp <= self.max_hp * 0.1 and self.state != "DESPERATION":
            self.state, self.pattern_timer = "DESPERATION", 999999
            self.target_pos = pygame.math.Vector2(WIDTH//2, HEIGHT//2)

        if self.state == "SPAWNING":
            self.angle += 2
            direction = self.target_pos - self.pos
            if direction.length() > 5: self.pos += direction.normalize() * 2
            else: self.state, self.pattern_timer = "IDLE", 1000

        elif self.state == "IDLE":
            self.angle += 1
            if self.pattern_timer <= 0: self.choose_pattern()

        # [수정됨] 중앙 복귀 준비 상태 (러쉬 / 레이저 공통)
        elif self.state in ["RUSH_PREP", "LASER_PREP"]:
            self.angle += 3
            direction = self.target_pos - self.pos
            if direction.length() > 5:
                self.pos += direction.normalize() * 4
            else:
                if self.state == "RUSH_PREP": self.state, self.pattern_timer, self.action_timer = "RUSH", 4000, 0
                else: self.state, self.pattern_timer = "LASER", 5000

        elif self.state == "RUSH":
            self.angle += 8
            if self.action_timer <= 0:
                self.action_timer = 200 # [수정됨] 간격 단축 (300 -> 200)
                # [수정됨] 10개 모든 꼭지점에서 발사하여 탄막 수 증가, 속도는 5로 감속
                for vertex in self.get_world_vertices(all_points=True):
                    dir_vec = (vertex - self.pos).normalize()
                    enemy_projectiles.add(Bullet(vertex, dir_vec, 1, self, color=RED, speed=5))
            if self.pattern_timer <= 0: self.state, self.pattern_timer = "IDLE", 1500

        elif self.state == "LASER":
            self.angle += 1.5
            for vertex in self.get_world_vertices():
                dir_vec = (vertex - self.pos).normalize()
                self.active_lasers.append((vertex, vertex + dir_vec * 1500, dir_vec))
            if self.pattern_timer <= 0: self.state, self.pattern_timer = "IDLE", 1500

        elif self.state == "DASH_PREP":
            self.angle += 5
            direction = self.target_pos - self.pos
            if direction.length() > 10: self.pos += direction.normalize() * 5
            else:
                self.state, self.action_timer = "DASHING", 800
                self.target_pos = player.pos + (player.pos - self.pos).normalize() * 200

        elif self.state == "DASHING":
            self.angle += 15
            direction = self.target_pos - self.pos
            if direction.length() > 10 and self.action_timer > 0:
                self.pos += direction.normalize() * 18
            else:
                self.dash_count += 1
                if self.dash_count >= 3:
                    self.state, self.pattern_timer = "IDLE", 2000
                    self.target_pos = pygame.math.Vector2(WIDTH//2, HEIGHT//2)
                else:
                    self.state = "DASH_PREP"
                    edge = random.choice([(random.randint(0, WIDTH), 50), (random.randint(0, WIDTH), HEIGHT-50),
                                          (50, random.randint(0, HEIGHT)), (WIDTH-50, random.randint(0, HEIGHT))])
                    self.target_pos = pygame.math.Vector2(edge)

        elif self.state == "DESPERATION":
            self.angle += 3
            direction = pygame.math.Vector2(WIDTH//2, HEIGHT//2) - self.pos
            if direction.length() > 5: self.pos += direction.normalize() * 3
            for vertex in self.get_world_vertices():
                dir_vec = (vertex - self.pos).normalize()
                self.active_lasers.append((vertex, vertex + dir_vec * 1500, dir_vec))
            if self.action_timer <= 0:
                self.action_timer = 200
                enemy_projectiles.add(Bullet(self.pos, pygame.math.Vector2(1, 0).rotate(random.uniform(0, 360)), 1, self, color=PURPLE, speed=10))

        self.image.fill(pygame.SRCALPHA)
        pygame.draw.polygon(self.image, (255, 100, 100) if self.state == "DESPERATION" else ORANGE, self.get_star_polygon())
        self.rect = self.image.get_rect(center=self.pos)

    def choose_pattern(self):
        pattern = random.choice(["RUSH", "LASER", "DASH"])
        if pattern == "RUSH":
            self.state = "RUSH_PREP"
            self.target_pos = pygame.math.Vector2(WIDTH//2, HEIGHT//2)
        elif pattern == "LASER":
            self.state = "LASER_PREP"
            self.target_pos = pygame.math.Vector2(WIDTH//2, HEIGHT//2)
        elif pattern == "DASH":
            self.state, self.dash_count = "DASH_PREP", 0
            self.target_pos = pygame.math.Vector2(random.randint(100, WIDTH-100), 100)

    def draw_lasers(self, surface):
        for start_pos, end_pos, _ in self.active_lasers:
            pygame.draw.line(surface, RED, start_pos, end_pos, 15)
            pygame.draw.line(surface, WHITE, start_pos, end_pos, 5)

    def check_laser_collision(self, player):
        for start_pos, _, dir_vec in self.active_lasers:
            if check_line_collision(start_pos, dir_vec, player.pos, player.radius): return True
        return False

# --- 메인 실행 ---
player = Player()
player_bullets, enemy_projectiles = pygame.sprite.Group(), pygame.sprite.Group()
meteors, pirates, particles = pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group()
boss_group = pygame.sprite.GroupSingle()

running, game_state = True, "PLAYING"
play_time, current_stage = 0, 5
boss_cleared_stages, current_choices = [], []
warning_timer, meteor_timer, pirate_timer = 0, 0, 0

while running:
    dt = clock.tick(60)
    screen.fill(BLACK)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
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
                    elif effect["type"] == "laser":
                        player.laser_level += 1
                        if player.laser_level > 1:
                            player.laser_cooldown = max(800, player.laser_cooldown - 300)
                            player.laser_duration += 150
                game_state = "PLAYING"

    if game_state in ["PLAYING", "WARNING", "BOSS_BATTLE"]:
        play_time += dt
        current_stage = (play_time // 20000) + 1 
        
        if current_stage % 10 == 0 and current_stage not in boss_cleared_stages and len(boss_group) == 0:
            if game_state == "PLAYING":
                game_state, warning_timer = "WARNING", 3000
            elif game_state == "WARNING":
                warning_timer -= dt
                if warning_timer <= 0: boss_group.add(StarBoss(current_stage)); game_state = "BOSS_BATTLE"

        if len(boss_group) == 0 and game_state != "WARNING":
            meteor_timer += dt
            if meteor_timer >= max(400, 1000 - (current_stage * 100)):
                meteor_timer = 0
                if len(meteors) < 15 + (current_stage * 2): meteors.add(Meteor(current_stage))
            if current_stage >= 2:
                pirate_timer += dt
                if pirate_timer >= max(1500, 5000 - (current_stage * 400)):
                    pirate_timer = 0
                    if len(pirates) < 3 + (current_stage // 2): pirates.add(Pirate(player, current_stage))

        player.update(player_bullets)
        player_bullets.update()
        enemy_projectiles.update(player)
        meteors.update(); pirates.update(player, enemy_projectiles, current_stage)
        boss_group.update(player, enemy_projectiles); particles.update()

        # [신규] 플레이어 레이저 위치 계산 및 충돌 판정
        player_laser_lines = []
        if player.laser_active:
            base_dir = pygame.math.Vector2(0, -1).rotate(-player.current_angle)
            for i in range(player.laser_level):
                offset_angle = (i - (player.laser_level - 1) / 2) * 15
                dir_vec = base_dir.rotate(offset_angle)
                player_laser_lines.append((player.pos, player.pos + dir_vec * 1500, dir_vec))
                
            for start_pos, end_pos, dir_vec in player_laser_lines:
                for m in meteors:
                    if m not in player.lasers_hit and check_line_collision(start_pos, dir_vec, m.pos, m.radius):
                        player.lasers_hit.add(m)
                        create_explosion(m.pos, YELLOW, 5)
                        if m.take_damage(player.damage): create_explosion(m.pos, (150, 150, 150), 15); handle_exp(2, current_stage)
                for p in pirates:
                    if p not in player.lasers_hit and check_line_collision(start_pos, dir_vec, p.pos, p.radius):
                        player.lasers_hit.add(p)
                        create_explosion(p.pos, PURPLE, 5)
                        if p.take_damage(player.damage): create_explosion(p.pos, PURPLE, 20); handle_exp(5, current_stage)
                if boss_group.sprite and boss_group.sprite not in player.lasers_hit:
                    if check_line_collision(start_pos, dir_vec, boss_group.sprite.pos, boss_group.sprite.radius):
                        player.lasers_hit.add(boss_group.sprite)
                        create_explosion(boss_group.sprite.pos, ORANGE, 5)
                        if boss_group.sprite.take_damage(player.damage):
                            create_explosion(boss_group.sprite.pos, ORANGE, 100); boss_cleared_stages.append(current_stage)
                            game_state = "PLAYING"; handle_exp(50, current_stage)

        # 일반 총알 충돌
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
                    create_explosion(boss_group.sprite.pos, ORANGE, 100); boss_cleared_stages.append(current_stage)
                    game_state = "PLAYING"; handle_exp(50, current_stage)

        if not player.is_invincible:
            hit = False
            if pygame.sprite.spritecollide(player, enemy_projectiles, True, pygame.sprite.collide_circle): hit = True
            elif pygame.sprite.spritecollide(player, meteors, True, pygame.sprite.collide_circle): hit = True
            elif pygame.sprite.spritecollide(player, pirates, False, pygame.sprite.collide_circle): hit = True
            elif boss_group.sprite and pygame.sprite.collide_circle(player, boss_group.sprite): hit = True
            elif boss_group.sprite and boss_group.sprite.check_laser_collision(player): hit = True
            if hit:
                if player.take_damage(1): create_explosion(player.pos, GREEN, 20)
                if player.hp <= 0: game_state = "GAME_OVER"

    # --- 그리기 ---
    # 1. 플레이어 레이저 (이펙트를 바닥에 깔기 위함)
    if player.laser_active:
        for start_pos, end_pos, _ in player_laser_lines:
            pygame.draw.line(screen, BLUE, start_pos, end_pos, 10 + player.laser_level * 2)
            pygame.draw.line(screen, WHITE, start_pos, end_pos, 4)

    # 2. 보스 레이저
    if boss_group.sprite: boss_group.sprite.draw_lasers(screen)

    particles.draw(screen); player_bullets.draw(screen); enemy_projectiles.draw(screen)
    meteors.draw(screen); pirates.draw(screen); boss_group.draw(screen)
    
    if game_state != "GAME_OVER":
        player.draw_afterimages(screen)
        screen.blit(player.image, player.rect)
    
    # UI 영역
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
        boss, bar_width = boss_group.sprite, 400
        pygame.draw.rect(screen, (50, 0, 0), (WIDTH//2 - bar_width//2, 20, bar_width, 25))
        pygame.draw.rect(screen, RED, (WIDTH//2 - bar_width//2, 20, int(bar_width * (max(0, boss.hp) / boss.max_hp)), 25))
        pygame.draw.rect(screen, WHITE, (WIDTH//2 - bar_width//2, 20, bar_width, 25), 2)
        boss_txt = font.render(f"STAR BOSS [{(max(0, boss.hp) / boss.max_hp)*100:.1f}%]", True, WHITE)
        screen.blit(boss_txt, boss_txt.get_rect(center=(WIDTH//2, 32)))

    # 오버레이 UI
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
    
    pygame.display.flip()

pygame.quit()