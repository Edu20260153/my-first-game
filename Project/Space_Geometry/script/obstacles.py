import pygame
import random
import math
from settings import *
from sprite import Base64_Data
from asset_loader import SpriteFactory
from effects import create_explosion

class Meteor(pygame.sprite.Sprite):
    def __init__(self, diff_level):
        super().__init__()
        m = Base64_Data["meteor"]
        meteor_b64 = m["b64"]["METEOR_B64"]

        self.size = m["size"]

        def enhance_color(img, intensity=120):
            base_img = pygame.transform.scale(img, self.size).convert_alpha()
            
            # 2. 자기 자신을 복사하여 오버레이 생성
            overlay = base_img.copy()
            overlay.set_alpha(intensity) # 0~255 사이 값. 클수록 색이 쨍해지고 밝아집니다.
            
            base_img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            
            return base_img
        
        raw_frames = SpriteFactory().get_frames(meteor_b64["b64"], cols=meteor_b64["cols"], rows=meteor_b64["rows"])
        self.frames = [enhance_color(img, intensity=60) for img in raw_frames]
        
        self.image = self.frames[0] 
        self.rect = self.image.get_rect()
        
        self.radius = m["radius"]
        self.hitbox = pygame.Rect(*m["hitbox"])
        
        side = random.choice(['top', 'bottom', 'left', 'right'])
        if side == 'top': self.pos = pygame.math.Vector2(random.randint(0, MAP_WIDTH), 10)
        elif side == 'bottom': self.pos = pygame.math.Vector2(random.randint(0, MAP_WIDTH), MAP_HEIGHT - 10)
        elif side == 'left': self.pos = pygame.math.Vector2(10, random.randint(0, MAP_HEIGHT))
        else: self.pos = pygame.math.Vector2(MAP_WIDTH - 10, random.randint(0, MAP_HEIGHT))
        
        target = pygame.math.Vector2(MAP_WIDTH//2 + random.randint(-200, 200), MAP_HEIGHT//2 + random.randint(-200, 200))
        self.vel = (target - self.pos).normalize() * (random.uniform(2, 4) + diff_level * 0.2)
        
        self.hp = 3 + diff_level
        self.angle = 0
        self.rotation_speed = random.uniform(-4, 4)
        
        self.state = "ALIVE"
        self.anim_index = 0
        self.last_anim_update = pygame.time.get_ticks()
        self.anim_speed = m["anim_speed"]

    def take_damage(self, amount, player_obj, particle_group):
        if self.state == "ALIVE":
            self.hp -= amount
            player_obj.trigger_vampire(particle_group)
            
            if self.hp <= 0:
                self.state = "EXPLODING"
                self.anim_index = 1 
                self.last_anim_update = pygame.time.get_ticks()

                self.radius = 0
                self.hitbox = pygame.Rect(0, 0, 0, 0)
                return True 
        return False

    def update(self, cam_pos):
        # [수정 4] hitbox 중심 위치 동기화
        self.hitbox.center = self.pos

        if self.state == "ALIVE":
            self.pos += self.vel
            self.angle = (self.angle + self.rotation_speed) % 360
            
            if self.pos.x <= self.radius or self.pos.x >= MAP_WIDTH - self.radius:
                self.vel.x *= -1
                self.pos.x = max(self.radius, min(MAP_WIDTH - self.radius, self.pos.x))
            if self.pos.y <= self.radius or self.pos.y >= MAP_HEIGHT - self.radius:
                self.vel.y *= -1
                self.pos.y = max(self.radius, min(MAP_HEIGHT - self.radius, self.pos.y))

            self.image = pygame.transform.rotate(self.frames[0], self.angle)
            self.rect = self.image.get_rect(center=self.pos - cam_pos)
            
        elif self.state == "EXPLODING":
            self.pos += self.vel * 0.5 
            
            now = pygame.time.get_ticks()
            if now - self.last_anim_update > self.anim_speed:
                self.last_anim_update = now
                self.anim_index += 1
                
                if self.anim_index >= len(self.frames):
                    self.kill()
                    return
            
            self.image = pygame.transform.rotate(self.frames[self.anim_index], self.angle)
            self.rect = self.image.get_rect(center=self.pos - cam_pos)