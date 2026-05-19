import pygame
import math
import random
from settings import *
from asset_loader import SpriteFactory, Base64_Data

# --- 파티클 시스템 ---
class Particle(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.active = False
        self.image = pygame.Surface((1, 1))
        self.rect = self.image.get_rect()
        self.lifetime = 0

    def spawn(self, pos, color, speed_range=(1, 4), lifetime=30):
        self.active = True
        self.size = random.randint(2, 5)
        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (self.size//2, self.size//2), self.size//2)
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)
        angle = random.uniform(0, math.pi * 2)
        self.vel = pygame.math.Vector2(math.cos(angle), math.sin(angle)) * random.uniform(*speed_range)
        self.lifetime = random.randint(lifetime - 10, lifetime + 10)
        self.start_life = self.lifetime

    def update(self, cam_pos):
        if not self.active: return
        self.pos += self.vel
        self.rect.center = self.pos - cam_pos 
        self.lifetime -= 1
        if self.lifetime > 0: 
            self.image.set_alpha(max(0, int(255 * (self.lifetime / self.start_life))))

class ParticlePool:
    def __init__(self, max_particles=1000):
        self.pool = [Particle() for _ in range(max_particles)]
        self.active_particles = pygame.sprite.Group()

    def get_particle(self, pos, color, speed_range=(1, 4), lifetime=30):
        if self.pool:
            p = self.pool.pop()
            p.spawn(pos, color, speed_range, lifetime)
            self.active_particles.add(p)
            return p
        return None

    def return_particle(self, particle):
        particle.active = False
        self.active_particles.remove(particle)
        self.pool.append(particle)

    def update_and_draw(self, surface, cam_pos):
        screen_rect = surface.get_rect().inflate(100, 100)
        for p in list(self.active_particles):
            p.update(cam_pos)
            if p.lifetime <= 0 or not screen_rect.colliderect(p.rect):
                self.return_particle(p)
                continue
            surface.blit(p.image, p.rect)

GLOBAL_PARTICLE_POOL = ParticlePool(max_particles=1000)

def create_explosion(pos, color, amount, particle_group):
    for _ in range(amount):
        p = GLOBAL_PARTICLE_POOL.get_particle(pos, color)
        if p: particle_group.add(p)

# --- 배경 및 별 효과 ---
class TwinklingStars:
    def __init__(self, num_stars):
        self.stars = []
        for _ in range(num_stars):
            x, y = random.randint(0, WIDTH), random.randint(0, HEIGHT)
            self.stars.append({
                'pos': pygame.math.Vector2(x, y),
                'base_size': random.uniform(0.5, 2.5),
                'twinkle_speed': random.uniform(0.02, 0.08),
                'color': random.choice([(255, 255, 255), (255, 255, 100), (100, 100, 255)]),
                'current_twinkle': 0,
                'parallax': random.uniform(0.05, 0.4)
            })

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
        self.current_chapter = 1
        
        # 별 배경 효과 생성
        self.stars_effect = TwinklingStars(int(WIDTH * HEIGHT / 3000))
        
        # 🌟 챕터별로 구워진 프레임과 속도를 저장할 딕셔너리
        self.preloaded_frames = {}
        self.chapter_speeds = {}
        
        # 게임 시작 시 1, 2, 3챕터 배경을 모두 미리 로드하고 보정해둡니다.
        self.preload_all_chapters()
        
        # 초기 세팅 (챕터 1)
        self.frames = self.preloaded_frames.get(1, [])
        self.animation_speed = self.chapter_speeds.get(1, 100)
        self.frame_index = 0
        self.last_update = pygame.time.get_ticks()

    def enhance_color(self, img, target_size, intensity=100): # intensity 수치로 밝기 조절 (0~255)
        """칙칙한 이미지를 밝게 보정해주는 함수"""
        base_img = pygame.transform.smoothscale(img, target_size).convert_alpha()
        overlay = base_img.copy()
        overlay.set_alpha(intensity) 
        base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return base_img

    def preload_all_chapters(self):
        """1, 2, 3 챕터의 배경을 미리 잘라서 메모리에 올려둡니다."""
        for chapter in [1, 2, 3]:
            bg_key = f"BG_CHAPTER{chapter}_B64"
            if bg_key in Base64_Data:
                bg_data = Base64_Data[bg_key]
                raw_frames = SpriteFactory().get_frames(bg_data["b64"], bg_data["cols"], bg_data["rows"])
                
                # Base64_Data에 size가 지정되어 있으면 사용, 없으면 원본 크기 유지
                target_size = bg_data.get("size", raw_frames[0].get_size())
                
                processed_frames = []
                for frame in raw_frames:
                    if chapter == 2:
                        processed_frame = self.enhance_color(frame, target_size, intensity=90)
                    elif chapter == 3:
                        processed_frame = self.enhance_color(frame, target_size, intensity=30)
                    else:
                        # 챕터 1은 크기 조절만 수행
                        processed_frame = pygame.transform.smoothscale(frame, target_size).convert_alpha()
                        
                    processed_frames.append(processed_frame)
                    
                self.preloaded_frames[chapter] = processed_frames
                self.chapter_speeds[chapter] = bg_data.get("speed", 100)

    def change_chapter(self, chapter_num):
        if chapter_num in self.preloaded_frames:
            self.frames = self.preloaded_frames[chapter_num]
            self.animation_speed = self.chapter_speeds[chapter_num]
            self.frame_index = 0

    def update_and_draw(self, surface, cam_pos, current_stage):
        # 10스테이지 단위로 챕터 계산
        target_chapter = ((current_stage - 1) // 10) + 1
        
        # 31스테이지 이상 가더라도 배경은 3챕터 고정
        if target_chapter > 3: 
            target_chapter = 3 
        
        if target_chapter != self.current_chapter:
            self.current_chapter = target_chapter
            self.change_chapter(self.current_chapter)

        now = pygame.time.get_ticks()
        if self.frames and (now - self.last_update > self.animation_speed):
            self.last_update = now
            self.frame_index = (self.frame_index + 1) % len(self.frames)

        # 별 배경 그리기
        self.stars_effect.update_and_draw(surface, cam_pos)
        
        # 행성 이미지 그리기
        if self.frames:
            bg_offset_x = (cam_pos.x + WIDTH // 2 - MAP_WIDTH // 2) * 0.1
            bg_offset_y = (cam_pos.y + HEIGHT // 2 - MAP_HEIGHT // 2) * 0.1

            current_image = self.frames[self.frame_index]
            image_rect = current_image.get_rect(center=((WIDTH // 2) - bg_offset_x, (HEIGHT // 2) - bg_offset_y))
            surface.blit(current_image, image_rect)

class SolarFlareEffect:
    def __init__(self):
        self.is_active = False
        self.start_time = 0
        self.duration = 0

    def trigger(self, duration=6000):
        """보스가 이 스킬을 시전할 때 호출합니다."""
        self.is_active = True
        self.start_time = pygame.time.get_ticks()
        self.duration = duration
        # 시작할 때 화면 전체에 강력한 섬광(순백색)을 번쩍이게 하는 효과를 추가해도 좋습니다.

    def update(self):
        """메인 게임 루프에서 매 프레임 호출하여 지속 시간을 체크합니다."""
        if self.is_active:
            now = pygame.time.get_ticks()
            if now - self.start_time > self.duration:
                self.is_active = False

    def get_silhouette(self, image):
        """
        주어진 이미지를 순흑색 실루엣으로 변환합니다.
        투명도(Alpha)는 그대로 유지하면서 색상만 검은색으로 덮어씌웁니다.
        """
        # 원본 이미지를 복사하여 훼손하지 않음
        silhouette = image.copy()
        
        # (0, 0, 0, 255) 즉, 검은색(불투명)으로 채우되,
        # BLEND_RGBA_MULT를 사용하면 기존 이미지의 알파값(투명도)은 유지되고 색만 검게 변합니다.
        silhouette.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        
        return silhouette
    
class EndingCredits:
    def __init__(self, font):
        self.texts = ["GAME CLEAR!", "","[앤딩 크래딧]", "기획: 박태광", "프로그래밍: 박태광", "디자인: 박태광", "배경 소스: ' Pixel Planet Generator '","https://deep-fold.itch.io/pixel-planet-generator","캐릭터 소스:","https://wenrexa.itch.io/laser2020","https://foozlecc.itch.io/void-fleet-pack-1", "","감사합니다!", "", "PRESS ESC TO EXIT"]
        self.font = font
        self.y = HEIGHT
        self.speed = 1.5

    def update_and_draw(self, screen):
        screen.fill((0, 0, 0)) # 검정 화면
        self.y -= self.speed
        
        for i, line in enumerate(self.texts):
            text_surf = self.font.render(line, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(WIDTH // 2, self.y + (i * 50)))
            screen.blit(text_surf, text_rect)
            
        if self.y + (len(self.texts) * 50) < 0:
            # 크레딧이 다 올라가면 게임 종료 등의 처리
            pass