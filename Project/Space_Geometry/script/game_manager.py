import random
from settings import UPGRADE_OPTIONS

class GameManager:
    def __init__(self):
        self.state = "PLAYING"
        self.current_choices = []
        self.boss_cleared_stages = []

    def handle_exp(self, player_obj, amount, current_stage):
        # 플레이어가 경험치를 얻어 레벨업(True 반환)하면 선택지를 뽑고 상태 전환
        if player_obj.gain_exp(amount, current_stage):
            self.current_choices = random.sample(UPGRADE_OPTIONS, 3)
            self.state = "LEVEL_UP"

    def apply_upgrade(self, player_obj, idx):
        if 0 <= idx < len(self.current_choices):
            for effect in self.current_choices[idx]["effects"]:
                if effect["type"] == "damage": 
                    player_obj.damage = max(1, player_obj.damage + effect["value"])
                elif effect["type"] == "max_hp": 
                    player_obj.max_hp += effect["value"]
                    player_obj.hp += effect["value"]
                elif effect["type"] == "fire_rate": 
                    player_obj.shoot_delay = int(player_obj.shoot_delay * effect["value"])
                elif effect["type"] == "bullet_count": 
                    player_obj.bullet_count += effect["value"]
                elif effect["type"] == "vampire": 
                    player_obj.vampire_level += effect["value"]
                elif effect["type"] == "laser":
                    player_obj.laser_level += 1
                    if player_obj.laser_level > 1:
                        player_obj.laser_cooldown = max(800, player_obj.laser_cooldown - 300)
                        player_obj.laser_duration += 150
            
            self.state = "PLAYING"
            player_obj.hp = min(player_obj.max_hp, player_obj.hp + int(player_obj.max_hp * 0.4))