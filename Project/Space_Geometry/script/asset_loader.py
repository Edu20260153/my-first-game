import pygame
import base64
import io
from sprite import *

# 시스템 초기화
pygame.init()
pygame.mixer.init()

# 폰트 설정
try:
    font = pygame.font.SysFont("malgungothic", 20, True)
    mid_font = pygame.font.SysFont("malgungothic", 30, True)
    large_font = pygame.font.SysFont("malgungothic", 70, True)
except:
    font = pygame.font.SysFont("arial", 20, True)
    mid_font = pygame.font.SysFont("arial", 30, True)
    large_font = pygame.font.SysFont("arial", 70, True)

# 사운드 설정
SOUND_PATHS = {
    "bgm": "../asset/sound/bgm.mp3",
}
sounds = {}

try:
    pygame.mixer.music.load(SOUND_PATHS["bgm"])
    pygame.mixer.music.set_volume(0.4)
    pygame.mixer.music.play(-1)
except Exception as e:
    print(f"BGM 로드 실패: {e}")

try: 
    sounds["shoot"] = pygame.mixer.Sound(SOUND_PATHS["shoot"])
    sounds["shoot"].set_volume(0.3)
except: 
    sounds["shoot"] = None

try: 
    sounds["dash"] = pygame.mixer.Sound(SOUND_PATHS["dash"])
    sounds["dash"].set_volume(0.5)
except: 
    sounds["dash"] = None

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
                
                # 기본 틴트 효과 (필요 시 수정)
                tint_surface = pygame.Surface(target_size, pygame.SRCALPHA)
                tint_surface.fill((100, 150, 150))
                image.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                self.frames.append(image)
        except:
            surf = pygame.Surface((100, 100))
            surf.fill((15, 15, 25))
            self.frames.append(surf)

class SpriteFactory:
    _instance = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SpriteFactory, cls).__new__(cls)
        return cls._instance

    def get_frames(self, b64_string, cols=1, rows=1):
        cache_key = (hash(b64_string), cols, rows)
        if cache_key not in self._cache:
            sheet = Base64SpriteSheet(b64_string, cols, rows)
            self._cache[cache_key] = sheet.frames
        return self._cache[cache_key]