import pygame
import ctypes

# 해상도 상수 데이터를 가져오기 위해 최소한의 디스플레이 초기화 수행
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

pygame.display.init()

info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
MAP_WIDTH, MAP_HEIGHT = WIDTH * 2, HEIGHT * 2

# 색상
BLACK, GREEN, WHITE = (0, 0, 0), (0, 255, 0), (255, 255, 255)
RED, CYAN, YELLOW = (255, 50, 50), (0, 255, 255), (255, 255, 0)
PURPLE, ORANGE, BLUE = (150, 0, 255), (255, 165, 0), (50, 100, 255)

# 업그레이드 옵션
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