import pygame
import math
import random # 랜덤 선택을 위해 추가
from sprites import load_sprite

# ── 상수 및 설정 ──────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 800, 600
FPS = 60
SPRITE_SIZE = (150, 150)
# 사용할 수 있는 스프라이트 이름 리스트
SPRITE_NAMES = ["rocket", "adventurer", "stone", "sword"]

COLOR_CIRCLE = (80, 160, 255)
COLOR_AABB   = (255, 80, 80)
COLOR_OBB    = (80, 220, 120)
BG_NORMAL    = (30, 30, 35)

# ── 유틸리티 ──────────────────────────────────────────────────────────────────
def fit_surface(surf, max_w, max_h):
    w, h = surf.get_size()
    scale = min(max_w / w, max_h / h)
    return pygame.transform.scale(surf, (int(w * scale), int(h * scale)))

# ── 게임 오브젝트 클래스 ────────────────────────────────────────────────────────
class GameObject:
    def __init__(self, x, y, sprite_name, is_player=False):
        self.pos = pygame.Vector2(x, y)
        self.is_player = is_player
        self.angle = 0.0
        self.set_sprite(sprite_name)

    def set_sprite(self, name):
        """이미지를 변경하고 충돌 영역을 재계산하는 함수"""
        base = load_sprite(name)
        self.base_img = fit_surface(base, *SPRITE_SIZE)
        self.image = self.base_img
        
        # 실제 콘텐츠 영역 재계산
        br = self.base_img.get_bounding_rect()
        self.bw, self.bh = br.width, br.height
        sw, sh = self.base_img.get_size()
        self.offset = pygame.Vector2(br.centerx - sw / 2, br.centery - sh / 2)
        self.radius = self.bw / 2

    @property
    def content_center(self):
        rotated_offset = self.offset.rotate(self.angle)
        return self.pos + rotated_offset

    def update(self, keys):
        if self.is_player:
            if keys[pygame.K_LEFT]:  self.pos.x -= 5
            if keys[pygame.K_RIGHT]: self.pos.x += 5
            if keys[pygame.K_UP]:    self.pos.y -= 5
            if keys[pygame.K_DOWN]:  self.pos.y += 5
        else:
            rot_speed = 6.0 if keys[pygame.K_z] else 1.5
            self.angle = (self.angle + rot_speed) % 360
        
        self.image = pygame.transform.rotate(self.base_img, -self.angle)

    def get_aabb(self):
        c = self.content_center
        return pygame.Rect(c.x - self.bw/2, c.y - self.bh/2, self.bw, self.bh)

    def get_obb_vertices(self):
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        hw, hh = self.bw / 2, self.bh / 2
        corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        world_corners = []
        c = self.content_center
        for cx, cy in corners:
            rx = cx * cos_a - cy * sin_a
            ry = cx * sin_a + cy * cos_a
            world_corners.append(pygame.Vector2(rx + c.x, ry + c.y))
        return world_corners

    def draw(self, surface):
        rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        surface.blit(self.image, rect)

# ── SAT 충돌 판정 ─────────────────────────────────────────────────────────────
def check_sat(v1, v2):
    def get_axes(verts):
        axes = []
        for i in range(len(verts)):
            edge = verts[(i + 1) % len(verts)] - verts[i]
            if edge.length() > 0:
                axes.append(pygame.Vector2(-edge.y, edge.x).normalize())
        return axes

    axes = get_axes(v1) + get_axes(v2)
    for axis in axes:
        proj1 = [v.dot(axis) for v in v1]
        proj2 = [v.dot(axis) for v in v2]
        if max(proj1) < min(proj2) or max(proj2) < min(proj1):
            return False
    return True

# ── 메인 루프 ──────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Press R to Randomize Sprites!")
    font = pygame.font.SysFont(None, 32)
    clock = pygame.time.Clock()

    player = GameObject(200, 300, "rocket", is_player=True)
    obstacle = GameObject(560, 300, "stone", is_player=False)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # R 키 입력 시 이미지 무작위 변경
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    player.set_sprite(random.choice(SPRITE_NAMES))
                    obstacle.set_sprite(random.choice(SPRITE_NAMES))

        keys = pygame.key.get_pressed()
        player.update(keys)
        obstacle.update(keys)

        # 충돌 판정
        hit_circle = player.content_center.distance_to(obstacle.content_center) < (player.radius + obstacle.radius)
        hit_aabb = player.get_aabb().colliderect(obstacle.get_aabb())
        hit_obb = check_sat(player.get_obb_vertices(), obstacle.get_obb_vertices())

        # 배경색 피드백
        bg_color = BG_NORMAL
        if hit_obb: bg_color = (180, 50, 50)
        elif hit_circle: bg_color = (180, 180, 50)
        screen.fill(bg_color)

        # 그리기
        for obj in [player, obstacle]:
            obj.draw(screen)
            pygame.draw.circle(screen, COLOR_CIRCLE, (int(obj.content_center.x), int(obj.content_center.y)), int(obj.radius), 2)
            pygame.draw.rect(screen, COLOR_AABB, obj.get_aabb(), 2)
            pygame.draw.polygon(screen, COLOR_OBB, obj.get_obb_vertices(), 2)

        # UI
        ui_info = [
            (f"Circle: {'HIT' if hit_circle else 'OFF'}", COLOR_CIRCLE),
            (f"AABB: {'HIT' if hit_aabb else 'OFF'}", COLOR_AABB),
            (f"OBB (SAT): {'HIT' if hit_obb else 'OFF'}", COLOR_OBB),
            ("[R] Random Sprite  [Z] Faster Rotation", (200, 200, 200))
        ]
        for i, (text, color) in enumerate(ui_info):
            txt_surf = font.render(text, True, color)
            screen.blit(txt_surf, (20, 20 + i * 35))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()