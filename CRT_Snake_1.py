import pygame
import pygame.gfxdraw
import random
import math
import sys

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
GAME_WIDTH = 640
GAME_HEIGHT = 480
GRID_SIZE = 20
GRID_WIDTH = GAME_WIDTH // GRID_SIZE
GRID_HEIGHT = GAME_HEIGHT // GRID_SIZE

# Colors (CRT-style green phosphor)
BLACK = (0, 0, 0)
GREEN_BRIGHT = (0, 255, 100)
GREEN_DIM = (0, 180, 60)
GREEN_DARK = (0, 80, 30)
SCANLINE_COLOR = (0, 40, 15, 60)

class Vector3D:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
    
    def rotate_y(self, angle):
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        new_x = self.x * cos_a + self.z * sin_a
        new_z = -self.x * sin_a + self.z * cos_a
        return Vector3D(new_x, self.y, new_z)
    
    def project(self, distance=300, screen_x=0, screen_y=0):
        # Simple perspective projection
        if self.z == 0:
            self.z = 0.1  # Avoid division by zero
        factor = distance / (distance + self.z)
        x = int(self.x * factor + screen_x)
        y = int(self.y * factor + screen_y)
        return (x, y, factor)  # Return depth factor for z-sorting

class Shape3D:
    def __init__(self, vertices, faces, position, size=1.0):
        self.vertices = [Vector3D(v[0] * size, v[1] * size, v[2] * size) for v in vertices]
        self.faces = faces
        self.position = position
        self.rotation = 0
        self.size = size
    
    def update(self, rotation_speed=0.02):
        self.rotation += rotation_speed
    
    def get_projected_vertices(self):
        projected = []
        for vertex in self.vertices:
            # Rotate around Y-axis
            rotated = vertex.rotate_y(self.rotation)
            # Project to 2D
            x, y, depth = rotated.project(300, self.position[0], self.position[1])
            projected.append((x, y, depth))
        return projected
    
    def draw(self, surface, color):
        projected_vertices = self.get_projected_vertices()
        
        # Calculate face depths for z-sorting
        face_depths = []
        for face in self.faces:
            avg_depth = sum(projected_vertices[i][2] for i in face) / len(face)
            face_depths.append((avg_depth, face))
        
        # Sort faces by depth (back to front)
        face_depths.sort(key=lambda x: x[0])
        
        # Draw faces
        for depth, face in face_depths:
            if len(face) >= 3:  # Only draw if we have at least 3 vertices
                points = []
                all_visible = True
                
                for vertex_idx in face:
                    if vertex_idx < len(projected_vertices):
                        x, y, z_factor = projected_vertices[vertex_idx]
                        # Check if point is on screen
                        if 0 <= x <= WINDOW_WIDTH and 0 <= y <= WINDOW_HEIGHT:
                            points.append((x, y))
                        else:
                            all_visible = False
                            break
                
                if len(points) >= 3 and all_visible:
                    # Adjust color based on depth for simple lighting
                    light_factor = max(0.3, min(1.0, depth))
                    lit_color = (
                        int(color[0] * light_factor),
                        int(color[1] * light_factor),
                        int(color[2] * light_factor)
                    )
                    
                    try:
                        pygame.draw.polygon(surface, lit_color, points)
                        pygame.draw.polygon(surface, GREEN_BRIGHT, points, 1)  # Wireframe
                    except:
                        pass  # Skip if polygon is invalid

class CRTEffect:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.scanline_y_pos = 0
        self.scanline_speed = 2.5  # Slightly slower for better visibility
        self.scanline_thickness = 12  # Thicker scanline
        self.phosphor_decay = {}
        
    def apply_scanlines(self, surface):
        # Create scanline overlay
        scanline_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Static horizontal scanlines (subtle background lines like original)
        for i in range(0, self.height, 4):
            alpha = 30 if i % 8 == 0 else 15
            scanline_color = (20, 20, 20, alpha)
            pygame.draw.line(scanline_surface, scanline_color, 
                           (0, i), (self.width, i), 1)
        
        # Moving scanline effect (based on original but with snake game's smoothness)
        # Update scanline position
        self.scanline_y_pos = (self.scanline_y_pos + self.scanline_speed) % (self.height + 20)
        
        # Draw the moving bright scanline with multiple layers for smooth effect
        for thickness in range(self.scanline_thickness):
            y_pos = (self.scanline_y_pos + thickness) % self.height
            
            # Core scanline - dark green tint instead of white/gray
            core_color = (10, 50, 20, 60)  # Dark green with reduced opacity
            pygame.draw.line(scanline_surface, core_color,
                           (0, y_pos), (self.width, y_pos), 1)
        
        # Add subtle glow above and below the main scanline (dark green theme)
        main_y = int(self.scanline_y_pos) % self.height
        for i in range(-4, 5):  # Glow range
            if 0 <= main_y + i < self.height:
                distance = abs(i)
                if distance == 1:
                    # Close glow - dark green
                    glow_color = (8, 35, 15, 35)
                    pygame.draw.line(scanline_surface, glow_color,
                                   (0, main_y + i), (self.width, main_y + i), 1)
                elif distance == 2:
                    # Medium glow - darker green
                    glow_color = (5, 25, 10, 25)
                    pygame.draw.line(scanline_surface, glow_color,
                                   (0, main_y + i), (self.width, main_y + i), 1)
                elif distance == 3:
                    # Outer glow - very dark green
                    glow_color = (3, 15, 8, 15)
                    pygame.draw.line(scanline_surface, glow_color,
                                   (0, main_y + i), (self.width, main_y + i), 1)
                elif distance == 4:
                    # Far outer glow - barely visible dark green
                    glow_color = (2, 10, 5, 10)
                    pygame.draw.line(scanline_surface, glow_color,
                                   (0, main_y + i), (self.width, main_y + i), 1)
        
        # Blit scanlines to main surface
        surface.blit(scanline_surface, (0, 0))
        
    def apply_phosphor_glow(self, surface, snake_segments, food_pos):
        # Create glow effect around bright pixels
        glow_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Glow around snake
        for segment in snake_segments:
            x, y = segment[0] * GRID_SIZE, segment[1] * GRID_SIZE
            # Offset for centering in window
            x += (WINDOW_WIDTH - GAME_WIDTH) // 2
            y += (WINDOW_HEIGHT - GAME_HEIGHT) // 2
            
            # Create glow circles
            for radius in range(15, 5, -2):
                alpha = max(10, 40 - radius * 2)
                color = (*GREEN_DARK[:3], alpha)
                try:
                    pygame.gfxdraw.filled_circle(glow_surface, x + GRID_SIZE//2, 
                                               y + GRID_SIZE//2, radius, color)
                except:
                    pass
        
        # Glow around food
        if food_pos:
            x, y = food_pos[0] * GRID_SIZE, food_pos[1] * GRID_SIZE
            x += (WINDOW_WIDTH - GAME_WIDTH) // 2
            y += (WINDOW_HEIGHT - GAME_HEIGHT) // 2
            
            for radius in range(20, 8, -2):
                alpha = max(15, 60 - radius * 2)
                color = (*GREEN_BRIGHT[:3], alpha)
                try:
                    pygame.gfxdraw.filled_circle(glow_surface, x + GRID_SIZE//2, 
                                               y + GRID_SIZE//2, radius, color)
                except:
                    pass
        
        surface.blit(glow_surface, (0, 0), special_flags=pygame.BLEND_ADD)

    def apply_scanline_glow(self, surface, snake_segments, food_pos):
        # Create enhanced glow when scanline passes over game elements
        scanline_y = int(self.scanline_y_pos) % self.height
        scanline_range = 15  # How close elements need to be to scanline for glow effect
        
        glow_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Check snake segments for scanline interaction
        for segment in snake_segments:
            x, y = segment[0] * GRID_SIZE, segment[1] * GRID_SIZE
            # Offset for centering in window
            x += (WINDOW_WIDTH - GAME_WIDTH) // 2
            y += (WINDOW_HEIGHT - GAME_HEIGHT) // 2
            
            # Check if this segment is near the scanline
            distance_to_scanline = abs(y + GRID_SIZE//2 - scanline_y)
            if distance_to_scanline < scanline_range:
                # Create intense glow when scanline passes over
                intensity = 1.0 - (distance_to_scanline / scanline_range)
                glow_strength = int(80 * intensity)  # Max glow strength
                
                # Multiple glow circles for intense effect
                for radius in range(25, 8, -3):
                    alpha = max(15, glow_strength - radius)
                    color = (0, int(255 * intensity), int(100 * intensity), alpha)
                    try:
                        pygame.gfxdraw.filled_circle(glow_surface, x + GRID_SIZE//2, 
                                                   y + GRID_SIZE//2, radius, color)
                    except:
                        pass
        
        # Check food for scanline interaction
        if food_pos:
            x, y = food_pos[0] * GRID_SIZE, food_pos[1] * GRID_SIZE
            x += (WINDOW_WIDTH - GAME_WIDTH) // 2
            y += (WINDOW_HEIGHT - GAME_HEIGHT) // 2
            
            distance_to_scanline = abs(y + GRID_SIZE//2 - scanline_y)
            if distance_to_scanline < scanline_range:
                intensity = 1.0 - (distance_to_scanline / scanline_range)
                glow_strength = int(100 * intensity)  # Food glows even brighter
                
                # Pulsing effect for food when scanline hits
                pulse = math.sin(pygame.time.get_ticks() * 0.01) * 0.3 + 0.7
                
                for radius in range(30, 10, -3):
                    alpha = max(20, int((glow_strength - radius) * pulse))
                    color = (0, int(255 * intensity * pulse), int(150 * intensity * pulse), alpha)
                    try:
                        pygame.gfxdraw.filled_circle(glow_surface, x + GRID_SIZE//2, 
                                                   y + GRID_SIZE//2, radius, color)
                    except:
                        pass
        
        surface.blit(glow_surface, (0, 0), special_flags=pygame.BLEND_ADD)

class SnakeGame:
    def __init__(self):
        self.snake = [(GRID_WIDTH//2, GRID_HEIGHT//2)]
        self.direction = (1, 0)
        self.food = self.spawn_food()
        self.score = 0
        self.game_over = False
        
    def spawn_food(self):
        while True:
            food = (random.randint(0, GRID_WIDTH-1), random.randint(0, GRID_HEIGHT-1))
            if food not in self.snake:
                return food
    
    def move(self):
        if self.game_over:
            return
            
        head = self.snake[0]
        new_head = (head[0] + self.direction[0], head[1] + self.direction[1])
        
        # Check boundaries
        if (new_head[0] < 0 or new_head[0] >= GRID_WIDTH or 
            new_head[1] < 0 or new_head[1] >= GRID_HEIGHT or
            new_head in self.snake):
            self.game_over = True
            return
        
        self.snake.insert(0, new_head)
        
        # Check food collision
        if new_head == self.food:
            self.score += 10
            self.food = self.spawn_food()
        else:
            self.snake.pop()
    
    def change_direction(self, new_direction):
        if (new_direction[0] * -1, new_direction[1] * -1) != self.direction:
            self.direction = new_direction
    
    def reset(self):
        self.snake = [(GRID_WIDTH//2, GRID_HEIGHT//2)]
        self.direction = (1, 0)
        self.food = self.spawn_food()
        self.score = 0
        self.game_over = False

def create_cube():
    # Cube vertices
    vertices = [
        (-1, -1,  1), ( 1, -1,  1), ( 1,  1,  1), (-1,  1,  1),  # Front face
        (-1, -1, -1), (-1,  1, -1), ( 1,  1, -1), ( 1, -1, -1)   # Back face
    ]
    
    # Cube faces (indices of vertices)
    faces = [
        [0, 1, 2, 3],  # Front
        [4, 5, 6, 7],  # Back
        [0, 4, 7, 1],  # Bottom
        [2, 6, 5, 3],  # Top
        [0, 3, 5, 4],  # Left
        [1, 7, 6, 2]   # Right
    ]
    
    return vertices, faces

def create_pyramid():
    # Pyramid vertices
    vertices = [
        ( 0,  1,  0),   # Top
        (-1, -1,  1),   # Front left
        ( 1, -1,  1),   # Front right
        ( 1, -1, -1),   # Back right
        (-1, -1, -1)    # Back left
    ]
    
    # Pyramid faces
    faces = [
        [0, 1, 2],  # Front face
        [0, 2, 3],  # Right face
        [0, 3, 4],  # Back face
        [0, 4, 1],  # Left face
        [1, 4, 3, 2]  # Base
    ]
    
    return vertices, faces

def create_tetrahedron():
    # Tetrahedron vertices
    vertices = [
        ( 0,  1,  0),   # Top
        (-1, -1,  1),   # Front left
        ( 1, -1,  1),   # Front right
        ( 0, -1, -1)    # Back
    ]
    
    # Tetrahedron faces
    faces = [
        [0, 1, 2],  # Front face
        [0, 2, 3],  # Right face
        [0, 3, 1],  # Left face
        [1, 3, 2]   # Base
    ]
    
    return vertices, faces

def main():
    # Set up display
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("CRT Snake Game - Pure Pygame 3D")
    clock = pygame.time.Clock()
    
    # Initialize game components
    game = SnakeGame()
    crt_effect = CRTEffect(WINDOW_WIDTH, WINDOW_HEIGHT)
    
    # Use a more retro-style font (monospace, smaller, pixelated feel)
    try:
        # Try to use a monospace font first
        font = pygame.font.SysFont('courier', 24, bold=True)
    except:
        # Fallback to default but make it smaller and bold
        font = pygame.font.Font(None, 28)
        font.set_bold(True)
    
    # Create 3D shapes for corners
    cube_verts, cube_faces = create_cube()
    pyramid_verts, pyramid_faces = create_pyramid()
    tetra_verts, tetra_faces = create_tetrahedron()
    
    # Position shapes in corners (outside game area)
    shapes = [
        Shape3D(cube_verts, cube_faces, (120, 120), 30),           # Top left
        Shape3D(pyramid_verts, pyramid_faces, (WINDOW_WIDTH-120, 120), 25),  # Top right
        Shape3D(tetra_verts, tetra_faces, (120, WINDOW_HEIGHT-120), 35),     # Bottom left
        Shape3D(cube_verts, cube_faces, (WINDOW_WIDTH-120, WINDOW_HEIGHT-120), 28)  # Bottom right
    ]
    
    running = True
    move_timer = 0
    MOVE_DELAY = 150  # milliseconds
    
    while running:
        dt = clock.tick(60)
        move_timer += dt
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    game.change_direction((0, -1))
                elif event.key == pygame.K_DOWN:
                    game.change_direction((0, 1))
                elif event.key == pygame.K_LEFT:
                    game.change_direction((-1, 0))
                elif event.key == pygame.K_RIGHT:
                    game.change_direction((1, 0))
                elif event.key == pygame.K_SPACE and game.game_over:
                    game.reset()
        
        # Move snake
        if move_timer >= MOVE_DELAY:
            game.move()
            move_timer = 0
        
        # Clear screen
        screen.fill(BLACK)
        
        # Update and draw 3D shapes
        for i, shape in enumerate(shapes):
            shape.update(0.02 + i * 0.005)  # Different rotation speeds
            color = GREEN_DIM if i % 2 == 0 else GREEN_DARK
            shape.draw(screen, color)
        
        # Calculate game area offset (center the game)
        game_x = (WINDOW_WIDTH - GAME_WIDTH) // 2
        game_y = (WINDOW_HEIGHT - GAME_HEIGHT) // 2
        
        # Draw game border
        pygame.draw.rect(screen, GREEN_DIM, 
                        (game_x - 2, game_y - 2, GAME_WIDTH + 4, GAME_HEIGHT + 4), 2)
        
        # Draw snake
        for i, segment in enumerate(game.snake):
            x = game_x + segment[0] * GRID_SIZE
            y = game_y + segment[1] * GRID_SIZE
            color = GREEN_BRIGHT if i == 0 else GREEN_DIM  # Head brighter
            pygame.draw.rect(screen, color, (x, y, GRID_SIZE-1, GRID_SIZE-1))
        
        # Draw food
        food_x = game_x + game.food[0] * GRID_SIZE
        food_y = game_y + game.food[1] * GRID_SIZE
        pygame.draw.rect(screen, GREEN_BRIGHT, 
                        (food_x, food_y, GRID_SIZE-1, GRID_SIZE-1))
        
        # Draw score
        score_text = font.render(f"SCORE: {game.score}", True, GREEN_BRIGHT)
        screen.blit(score_text, (20, 20))
        
        # Draw game over message
        if game.game_over:
            game_over_text = font.render("GAME OVER - PRESS SPACE TO RESTART", True, GREEN_BRIGHT)
            text_rect = game_over_text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2))
            screen.blit(game_over_text, text_rect)
        
        # Apply CRT effects
        crt_effect.apply_phosphor_glow(screen, game.snake, game.food)
        crt_effect.apply_scanline_glow(screen, game.snake, game.food)  # New scanline interaction
        crt_effect.apply_scanlines(screen)
        
        pygame.display.flip()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()