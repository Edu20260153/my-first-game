import pygame
from obstacles import Meteor
from enemies import *
from boss import *

class StageManager:
    def __init__(self):
        self.play_time = 0
        self.current_stage = 1
        self.warning_timer = 0
        self.meteor_timer = 0
        self.pirate_timer = 0
        self.bomber_timer = 0
        self.scout_timer = 0
        self.support_timer = 0
        self.current_chapter = 1
        self.choice = True

    def update(self, dt, player_obj, meteors_group, pirates_group, bombers_group, scouts_group, supports_group, boss_group, game_manager):
        keys = pygame.key.get_pressed()
        time_multiplier = 1
        
        if keys[pygame.K_KP3]:
            time_multiplier = 10 ** 3 
        elif keys[pygame.K_KP2]:
            time_multiplier = 10 ** 2
        elif keys[pygame.K_KP1]:
            time_multiplier = 10 ** 1
        elif keys[pygame.K_KP4]:
            self.play_time = 0
        elif keys[pygame.K_KP5]:
            self.play_time = 210000
        elif keys[pygame.K_KP6]:
            self.play_time = 410000
        elif keys[pygame.K_KP7]:
            player_obj.hp, player_obj.max_hp = 1000, 1000
        elif keys[pygame.K_KP8]:
            player_obj.damage += 10

        if game_manager.state in ["PLAYING", "WARNING", "BOSS_BATTLE", "GAME_CLEAR_CHOICE"]:
            if len(boss_group) == 0 and game_manager.state != "WARNING": 
                self.play_time += dt * time_multiplier
            self.current_stage = (self.play_time // 20000) + 1 

            if self.current_stage >= 30 and self.choice:
                if len(boss_group) == 0:
                    game_manager.state = "GAME_CLEAR_CHOICE"
                    self.choice = False
                    # 중요: 보스를 안 잡았지만 잡은 걸로 처리해야 다음 루프에서 에러가 안 납니다.
                    game_manager.boss_cleared_stages.append(30)
            
            # ★ 보스 경고 및 소환
            if self.current_stage % 10 == 0 and self.current_stage not in game_manager.boss_cleared_stages and len(boss_group) == 0:
                if game_manager.state == "PLAYING": 
                    game_manager.state = "WARNING"
                    self.warning_timer = 3000
                elif game_manager.state == "WARNING":
                    self.warning_timer -= dt*100
                    if self.warning_timer <= 0: 
                        game_manager.state = "BOSS_BATTLE" 
                        # ★ 보스 객체를 그룹에 추가!
                        if self.current_stage == 10:
                            boss_group.add(Chapter1Boss())
                        if self.current_stage == 20:
                            boss_group.add(Chapter2Boss(player_obj, self.current_stage))
                        if self.current_stage == 30:
                            #boss_group.add(Chapter3Boss())
                            pass

            if len(boss_group) == 0 and game_manager.state != "WARNING":
                self.meteor_timer += dt
                if self.meteor_timer >= max(400, 1000 - (self.current_stage * 100)):
                    self.meteor_timer = 0
                    if len(meteors_group) < 30:
                        meteors_group.add(Meteor(self.current_stage))
                
                if self.current_stage >= 2:
                    self.pirate_timer += dt
                    if self.pirate_timer >= max(1500, 5000 - (self.current_stage * 400)):
                        self.pirate_timer = 0
                        if len(pirates_group) < 5 + (self.current_stage // 5): 
                            pirates_group.add(Pirate(player_obj, self.current_stage))

                if self.current_stage >= 10:
                    self.bomber_timer += dt
                    if self.bomber_timer >= max(1, 6000 - ((self.current_stage - 11) * 200)):
                        self.bomber_timer = 0
                        if len(bombers_group) < 1 + (self.current_stage // 5): 
                            bombers_group.add(Bomber(player_obj, self.current_stage))

                if self.current_stage >= 17:
                    self.scout_timer += dt
                    if self.scout_timer >= max(1, 6000 - ((self.current_stage - 11) * 200)):
                        self.scout_timer = 0
                        if len(scouts_group) < 1 + (self.current_stage // 24): 
                            scouts_group.add(Scout(player_obj, self.current_stage))

                if self.current_stage >= 24:
                    self.support_timer += dt
                    if self.support_timer >= max(1, 6000 - ((self.current_stage - 11) * 200)):
                        self.support_timer = 0
                        if len(supports_group) < 2: 
                            supports_group.add(Support(player_obj, self.current_stage))