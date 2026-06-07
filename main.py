# main.py - Game Utama dengan finish RANDOM!

import pygame
import sys
import random
from settings import *
from map import get_grid
from player import Player
from ghost import Ghost
from search import bfs_path
from sprite_utils import load_sprite
import os

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()  # ← TAMBAHKAN INI
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("ESCAPE THE GHOST - ULTIMATE EDITION")
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 32)
        
        # Load suara (opsional, kalo file gak ada gak error)
        self.load_sounds()
        
        # Load sprite pintu
        self.door_sprite = load_sprite("door.png", (80, 255, 120), "rect", "🚪")
        
        # Game state
        self.reset_game()

    def load_sounds(self):
        """Load sound effects (kalau file gak ada, di-skip)"""
        try:
            self.teleport_sound = pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "teleport.mp3"))
            self.hit_sound = pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "hit.mp3"))
            pygame.mixer.music.load(os.path.join(SOUNDS_DIR, "bg_music.mp3"))
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play(-1)  # loop forever
        except:
            print("Sound files not found — playing without sound")
            self.teleport_sound = None
            self.hit_sound = None
    
    def reset_game(self):
        """Reset game dengan spawn RANDOM"""
        self.grid, self.exit_pos = get_grid()
        
        # Cari semua sel kosong
        empty_cells = []
        for i in range(GRID_HEIGHT):
            for j in range(GRID_WIDTH):
                if self.grid[i][j] == 0:
                    empty_cells.append((i, j))
        
        # Player spawn random (tapi reachable ke exit)
        random.shuffle(empty_cells)
        start_pos = None
        for pos in empty_cells:
            if bfs_path(self.grid, pos, self.exit_pos):
                start_pos = pos
                break
        
        if start_pos:
            self.player = Player(start_pos[0], start_pos[1])
        else:
            self.player = Player(0, 0)  # fallback
        
        # Ghost spawn random (jauh dari player)
        best_ghost_pos = None
        max_dist = -1
        for pos in empty_cells:
            if pos != self.player.get_position() and pos != self.exit_pos:
                dist = abs(pos[0] - self.player.x) + abs(pos[1] - self.player.y)
                if dist > max_dist:
                    max_dist = dist
                    best_ghost_pos = pos
        
        if best_ghost_pos:
            self.ghost = Ghost(best_ghost_pos[0], best_ghost_pos[1])
        else:
            self.ghost = Ghost(GRID_HEIGHT-2, GRID_WIDTH-2)
        
        self.game_over = False
        self.win = False
        self.auto_path = []
        self.auto_index = 0
        self.flash_alpha = 0
        self.start_time = pygame.time.get_ticks()
        
        # Timer teleport
        self.last_ghost_teleport = pygame.time.get_ticks()
        self.last_door_teleport = pygame.time.get_ticks()
    
    def draw_grid(self):
        """Gambar grid dengan dinding JELAS (pake X)"""
        for row in range(GRID_HEIGHT):
            for col in range(GRID_WIDTH):
                x = col * CELL_SIZE
                y = row * CELL_SIZE
                
                if self.grid[row][col] == 1:
                    # DINDING: gelap + tanda X
                    pygame.draw.rect(self.screen, DARK_GRAY, (x, y, CELL_SIZE, CELL_SIZE))
                    pygame.draw.rect(self.screen, BLACK, (x, y, CELL_SIZE, CELL_SIZE), 2)
                    # Tanda X
                    pygame.draw.line(self.screen, BLACK, (x + 8, y + 8), (x + CELL_SIZE - 8, y + CELL_SIZE - 8), 3)
                    pygame.draw.line(self.screen, BLACK, (x + CELL_SIZE - 8, y + 8), (x + 8, y + CELL_SIZE - 8), 3)
                else:
                    # JALAN: warna gradasi
                    color = (45, 45, 65) if (row + col) % 2 == 0 else (55, 55, 75)
                    pygame.draw.rect(self.screen, color, (x, y, CELL_SIZE, CELL_SIZE))
                    pygame.draw.rect(self.screen, LIGHT_GRAY, (x, y, CELL_SIZE, CELL_SIZE), 1)
    
    def draw_entities(self):
        """Gambar player, hantu, dan pintu pake SPRITE"""
        # Pintu
        exit_x = self.exit_pos[1] * CELL_SIZE
        exit_y = self.exit_pos[0] * CELL_SIZE
        
        # Efek glow pintu
        glow_surf = pygame.Surface((CELL_SIZE+10, CELL_SIZE+10), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (0, 255, 0, 50), (CELL_SIZE//2+5, CELL_SIZE//2+5), CELL_SIZE//2)
        self.screen.blit(glow_surf, (exit_x-5, exit_y-5))
        
        # Gambar sprite pintu
        self.screen.blit(self.door_sprite, (exit_x + 5, exit_y + 5))
        
        # Player
        px = self.player.y * CELL_SIZE
        py = self.player.x * CELL_SIZE
        
        # Efek glow player
        glow = pygame.Surface((CELL_SIZE+10, CELL_SIZE+10), pygame.SRCALPHA)
        pygame.draw.circle(glow, (80, 150, 255, 80), (CELL_SIZE//2+5, CELL_SIZE//2+5), CELL_SIZE//2)
        self.screen.blit(glow, (px-5, py-5))
        
        # Gambar sprite player
        self.screen.blit(self.player.get_sprite(), (px + 5, py + 5))
        
        # Hantu
        gx = self.ghost.y * CELL_SIZE
        gy = self.ghost.x * CELL_SIZE
        
        # Efek glow hantu
        glow = pygame.Surface((CELL_SIZE+10, CELL_SIZE+10), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 80, 80, 80), (CELL_SIZE//2+5, CELL_SIZE//2+5), CELL_SIZE//2)
        self.screen.blit(glow, (gx-5, gy-5))
        
        # Gambar sprite hantu
        self.screen.blit(self.ghost.get_sprite(), (gx + 5, gy + 5))
    
    def draw_ui(self):
        y_offset = GRID_HEIGHT * CELL_SIZE
        
        # HP bar
        hp_display = "❤️" * self.player.hp + "🖤" * (3 - self.player.hp)
        hp_surface = self.font_big.render(hp_display, True, RED)
        self.screen.blit(hp_surface, (10, y_offset + 10))
        
        # Timer
        elapsed = (pygame.time.get_ticks() - self.start_time) // 1000
        timer_text = self.font_small.render(f"⏱️ {elapsed}s", True, WHITE)
        self.screen.blit(timer_text, (SCREEN_WIDTH - 80, y_offset + 15))
        
        # Indikator teleport countdown
        now = pygame.time.get_ticks()
        time_to_ghost_teleport = 3000 - (now - self.last_ghost_teleport)
        time_to_door_teleport = 5000 - (now - self.last_door_teleport)

        # Ghost teleport timer
        ghost_text = self.font_small.render(f"👻 Teleport: {max(0, time_to_ghost_teleport//1000)}s", True, (200, 100, 100))
        self.screen.blit(ghost_text, (SCREEN_WIDTH - 180, y_offset + 45))

        # Door teleport timer
        door_text = self.font_small.render(f"🚪 Teleport: {max(0, time_to_door_teleport//1000)}s", True, (100, 200, 100))
        self.screen.blit(door_text, (SCREEN_WIDTH - 180, y_offset + 70))
        
        # Peringatan ghost dekat
        dist = abs(self.player.x - self.ghost.x) + abs(self.player.y - self.ghost.y)
        if dist <= 3 and not self.game_over and not self.win:
            warning = self.font_small.render("⚠️ GHOST NEAR! ⚠️", True, RED)
            self.screen.blit(warning, (SCREEN_WIDTH//2 - 80, y_offset + 50))
            
            beat = (pygame.time.get_ticks() // 200) % 2
            if beat:
                warning_big = self.font_big.render("⚠️⚠️⚠️", True, RED)
                self.screen.blit(warning_big, (SCREEN_WIDTH//2 - 60, y_offset + 20))
        
        # Help text
        if not self.game_over and not self.win:
            help_text = self.font_small.render("←↑↓→: Move | SPACE: Auto-Solve | R: New Maze", True, LIGHT_GRAY)
            self.screen.blit(help_text, (10, y_offset + 85))
        
        # Game Over screen
        if self.game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(180)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0,0))
            go_text = self.font_big.render("💀 GAME OVER 💀", True, RED)
            self.screen.blit(go_text, (SCREEN_WIDTH//2 - 120, SCREEN_HEIGHT//2))
            restart_text = self.font_small.render("Press R for New Maze", True, WHITE)
            self.screen.blit(restart_text, (SCREEN_WIDTH//2 - 90, SCREEN_HEIGHT//2 + 50))
        
        # Win screen
        if self.win:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(180)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0,0))
            win_text = self.font_big.render("🎉 YOU ESCAPED! 🎉", True, GREEN)
            self.screen.blit(win_text, (SCREEN_WIDTH//2 - 130, SCREEN_HEIGHT//2))
            restart_text = self.font_small.render("Press R for New Maze", True, WHITE)
            self.screen.blit(restart_text, (SCREEN_WIDTH//2 - 90, SCREEN_HEIGHT//2 + 50))
    
    def draw_flash_effect(self):
        if self.flash_alpha > 0:
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            flash.set_alpha(self.flash_alpha)
            flash.fill(RED)
            self.screen.blit(flash, (0,0))
            self.flash_alpha -= 15
    
    def check_collisions(self):
        if self.player.get_position() == self.ghost.get_position():
            if self.player.take_damage():
                self.flash_alpha = 120
                if hasattr(self, 'hit_sound') and self.hit_sound:
                    self.hit_sound.play()
                # Knockback
                dx = self.player.x - self.ghost.x
                dy = self.player.y - self.ghost.y
                if dx != 0:
                    self.player.move(dx, 0, self.grid)
                if dy != 0:
                    self.player.move(0, dy, self.grid)
        
        if self.player.get_position() == self.exit_pos:
            self.win = True
        
        if not self.player.is_alive():
            self.game_over = True
            
    def teleport_ghost(self):
        """Teleport ghost ke posisi random"""
        empty_cells = []
        for i in range(GRID_HEIGHT):
            for j in range(GRID_WIDTH):
                if self.grid[i][j] == 0 and (i, j) != self.player.get_position():
                    empty_cells.append((i, j))
        
        if empty_cells:
            new_pos = random.choice(empty_cells)
            self.ghost.x, self.ghost.y = new_pos
            self.flash_alpha = 80
            if hasattr(self, 'teleport_sound') and self.teleport_sound:
                self.teleport_sound.play()

    def teleport_door(self):
        """Teleport pintu keluar ke posisi random yang reachable"""
        empty_cells = []
        for i in range(GRID_HEIGHT):
            for j in range(GRID_WIDTH):
                if self.grid[i][j] == 0 and (i, j) != (0, 0):
                    if bfs_path(self.grid, self.player.get_position(), (i, j)):
                        empty_cells.append((i, j))
        
        if empty_cells:
            new_exit = random.choice(empty_cells)
            self.exit_pos = new_exit
            self.flash_alpha = 100
            if hasattr(self, 'teleport_sound') and self.teleport_sound:
                self.teleport_sound.play()
    
    def auto_solve(self):
        start = self.player.get_position()
        goal = self.exit_pos
        path = bfs_path(self.grid, start, goal)
        if path:
            self.auto_path = path[1:]
            self.auto_index = 0
    
    def update_auto_move(self):
        if self.auto_index < len(self.auto_path):
            next_pos = self.auto_path[self.auto_index]
            dx = next_pos[0] - self.player.x
            dy = next_pos[1] - self.player.y
            self.player.move(dx, dy, self.grid)
            self.auto_index += 1
        else:
            self.auto_path = []
    
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    pygame.quit()
                    sys.exit()
                
                if event.type == pygame.KEYDOWN:
                    if not self.game_over and not self.win:
                        if event.key == pygame.K_UP:
                            self.player.move(-1, 0, self.grid)
                        elif event.key == pygame.K_DOWN:
                            self.player.move(1, 0, self.grid)
                        elif event.key == pygame.K_LEFT:
                            self.player.move(0, -1, self.grid)
                        elif event.key == pygame.K_RIGHT:
                            self.player.move(0, 1, self.grid)
                        elif event.key == pygame.K_SPACE:
                            self.auto_solve()
                    
                    if event.key == pygame.K_r:
                        self.reset_game()
            
            if not self.game_over and not self.win:
                # Timer untuk ghost teleport (setiap 3 detik = 3000 ms)
                now = pygame.time.get_ticks()
                if now - self.last_ghost_teleport > 3000:
                    self.teleport_ghost()
                    self.last_ghost_teleport = now
    
                # Timer untuk door teleport (setiap 5 detik = 5000 ms)
                if now - self.last_door_teleport > 5000:
                    self.teleport_door()
                    self.last_door_teleport = now
    
                self.ghost.move_towards(self.player.x, self.player.y, self.grid)
                self.update_auto_move()
                self.player.update()
                self.check_collisions()
            
            self.screen.fill(BLACK)
            self.draw_grid()
            self.draw_entities()
            self.draw_ui()
            self.draw_flash_effect()
            
            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()