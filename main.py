import pymem
import pymem.process
import win32gui
import win32con
import threading
import subprocess
import time
import os
import imgui
from imgui.integrations.glfw import GlfwRenderer
import glfw
import OpenGL.GL as gl
import requests
from PIL import ImageGrab

# Grab the entire screen
screen = ImageGrab.grab()

# Get the screen size
screen_width, screen_height = screen.size

# Set the CMD window title
pid = os.getpid()
os.system('title mint-ex')

gui_script = 'gui.py'

command = f'start cmd /k "python {gui_script} {pid}"'

# Run the command
subprocess.run(command, shell=True)

# Initialize global variables
WINDOW_WIDTH = screen_width  # Initial value, can be any default value
WINDOW_HEIGHT = screen_height  # Initial value, can be any default value

def update_screen():
    global WINDOW_WIDTH, WINDOW_HEIGHT, window  # Declare that we are using global variables
    
    while True:
        screen = ImageGrab.grab()
        screen_width2, screen_height2 = screen.size
        
        # Update global variables
        WINDOW_WIDTH = screen_width2
        WINDOW_HEIGHT = screen_height2
        
        print(f"Res: {WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        time.sleep(2)  # Adjust sleep duration as needed

# Create and start the thread
screenupdate = threading.Thread(target=update_screen)
screenupdate.daemon = True  # This allows the thread to exit when the main program exits
screenupdate.start()

colordef = (0, 0, 0, 1)
enemycolordef = (1, 1, 1, 1)
fillcolordef = (1, 1, 1, 0.15)
headdotcolordef = (1, 0, 0, 1)


esp_rendering = 1  # 0 - Disable ESP, 1 - Enable ESP
esp_mode = 1  # 0 - Enemies only, 1 - Enemies and teammates
line_rendering = 0  # 0 - Do not draw lines, 1 - Draw lines
hp_bar_rendering = 1  # 0 - Do not draw HP bar, 1 - Draw HP bar
head_hitbox_rendering = 0  # 0 - Do not draw head hitbox, 1 - Draw head hitbox

offsets = requests.get('https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json').json()
client_dll = requests.get('https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json').json()

dwEntityList = offsets['client.dll']['dwEntityList']
dwLocalPlayerPawn = offsets['client.dll']['dwLocalPlayerPawn']
dwViewMatrix = offsets['client.dll']['dwViewMatrix']

m_iTeamNum = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iTeamNum']
m_lifeState = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_lifeState']
m_pGameSceneNode = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_pGameSceneNode']

m_modelState = client_dll['client.dll']['classes']['CSkeletonInstance']['fields']['m_modelState']

m_hPlayerPawn = client_dll['client.dll']['classes']['CCSPlayerController']['fields']['m_hPlayerPawn']

m_iHealth = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iHealth']

print("Waiting for the launch of cs2.exe")

while True:
    time.sleep(1)
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        break
    except:
        pass

time.sleep(1)
print("Starting Scripts!")
os.system("cls")

pm = pymem.Pymem("cs2.exe")
client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll

def w2s(mtx, posx, posy, posz, width, height):
    screenW = (mtx[12] * posx) + (mtx[13] * posy) + (mtx[14] * posz) + mtx[15]

    if screenW > 0.001:
        screenX = (mtx[0] * posx) + (mtx[1] * posy) + (mtx[2] * posz) + mtx[3]
        screenY = (mtx[4] * posx) + (mtx[5] * posy) + (mtx[6] * posz) + mtx[7]

        camX = width / 2
        camY = height / 2

        x = camX + (camX * screenX / screenW)//1
        y = camY - (camY * screenY / screenW)//1

        return [x, y]

    return [-999, -999]

def esp(draw_list):
    global entity_team
    global local_player_team
    if esp_rendering == 0:
        return
    
    view_matrix = []
    for i in range(16):
        temp_mat_val = pm.read_float(client + dwViewMatrix + i * 4)
        view_matrix.append(temp_mat_val)

    local_player_pawn_addr = pm.read_longlong(client + dwLocalPlayerPawn)

    try:
        local_player_team = pm.read_int(local_player_pawn_addr + m_iTeamNum)
    except:
        return

    center_x = WINDOW_WIDTH / 2
    center_y = WINDOW_HEIGHT * 0.75  # Center horizontally and below center vertically

    for i in range(64):
        entity = pm.read_longlong(client + dwEntityList)

        if not entity:
            continue

        list_entry = pm.read_longlong(entity + ((8 * (i & 0x7FFF) >> 9) + 16))

        if not list_entry:
            continue

        entity_controller = pm.read_longlong(list_entry + (120) * (i & 0x1FF))

        if not entity_controller:
            continue

        entity_controller_pawn = pm.read_longlong(entity_controller + m_hPlayerPawn)

        if not entity_controller_pawn:
            continue

        list_entry = pm.read_longlong(entity + (0x8 * ((entity_controller_pawn & 0x7FFF) >> 9) + 16))

        if not list_entry:
            continue

        entity_pawn_addr = pm.read_longlong(list_entry + (120) * (entity_controller_pawn & 0x1FF))

        if not entity_pawn_addr or entity_pawn_addr == local_player_pawn_addr:
            continue
        
        entity_alive = pm.read_int(entity_pawn_addr + m_lifeState)

        if entity_alive != 256:
            continue
        entity_team = pm.read_int(entity_pawn_addr + m_iTeamNum)

        if entity_team == local_player_team and esp_mode == 0:
            continue
        
        color = imgui.get_color_u32_rgba(colordef[0],colordef[1],colordef[2],colordef[3]) if entity_team == local_player_team else imgui.get_color_u32_rgba(enemycolordef[0],enemycolordef[1],enemycolordef[2],enemycolordef[3])
        fillcolor = imgui.get_color_u32_rgba(fillcolordef[0],fillcolordef[1],fillcolordef[2],fillcolordef[3])

        game_scene = pm.read_longlong(entity_pawn_addr + m_pGameSceneNode)
        bone_matrix = pm.read_longlong(game_scene + m_modelState + 0x80)

        try:
            headX = pm.read_float(bone_matrix + 6 * 0x20)
            headY = pm.read_float(bone_matrix + 6 * 0x20 + 0x4)
            headZ = pm.read_float(bone_matrix + 6 * 0x20 + 0x8) + 8

            head_pos = w2s(view_matrix, headX, headY, headZ, WINDOW_WIDTH, WINDOW_HEIGHT)

            if line_rendering == 1:
                # Draw line from the bottom left of the enemy's bounding box
                legZ = pm.read_float(bone_matrix + 28 * 0x20 + 0x8)
                leg_pos = w2s(view_matrix, headX, headY, legZ, WINDOW_WIDTH, WINDOW_HEIGHT)

                bottom_left_x = head_pos[0] - (head_pos[0] - leg_pos[0]) // 2
                bottom_y = leg_pos[1]

                draw_list.add_line(bottom_left_x, bottom_y, center_x, center_y, color, 2.0)




            # Drawing the bounding box
            legZ = pm.read_float(bone_matrix + 28 * 0x20 + 0x8)
            leg_pos = w2s(view_matrix, headX, headY, legZ, WINDOW_WIDTH, WINDOW_HEIGHT)

            deltaZ = abs(head_pos[1] - leg_pos[1])
            leftX = head_pos[0] - deltaZ // 3
            rightX = head_pos[0] + deltaZ // 3

            draw_list.add_rect_filled(leftX, leg_pos[1], rightX, head_pos[1], fillcolor)
            # Draw the bounding box
            draw_list.add_line(leftX, leg_pos[1], rightX, leg_pos[1], color, 2.0)
            draw_list.add_line(leftX, leg_pos[1], leftX, head_pos[1], color, 2.0)
            draw_list.add_line(rightX, leg_pos[1], rightX, head_pos[1], color, 2.0)
            draw_list.add_line(leftX, head_pos[1], rightX, head_pos[1], color, 2.0)

            if hp_bar_rendering == 1:
                # Get HP of the entity
                entity_hp = pm.read_int(entity_pawn_addr + m_iHealth)
                max_hp = 100
                hp_percentage = min(1.0, max(0.0, entity_hp / max_hp))
                bottom_left_x = head_pos[0] - (head_pos[0] - leg_pos[0]) // 2
                bottom_y = leg_pos[1]

                # Draw HP bar
                hp_bar_width = deltaZ // 1.5  # Width of HP bar
                hp_bar_height = 4  # Height of HP bar
                hp_bar_x_left = head_pos[0] - hp_bar_width / 2
                hp_bar_y_top = leg_pos[1] - deltaZ / 1008  # Made closer
                hp_bar_y_bottom = hp_bar_y_top - hp_bar_height

                # Draw the background of the HP bar
                draw_list.add_rect_filled(hp_bar_x_left, hp_bar_y_bottom, hp_bar_x_left + hp_bar_width, hp_bar_y_top, imgui.get_color_u32_rgba(0, 0, 0, 0.7))

                # Draw the HP bar
                draw_list.add_rect_filled(hp_bar_x_left, hp_bar_y_bottom, hp_bar_x_left + (hp_bar_width * hp_percentage), hp_bar_y_top, imgui.get_color_u32_rgba(0, 1, 0, 1))

                if head_hitbox_rendering == 1:
                    # Draw head hitbox
                    head_hitbox_size = (rightX - leftX) / 7  # One fifth of the bounding box width
                    head_hitbox_radius = head_hitbox_size * 2 ** 0.5 / 2  # Diameter is equal to the diagonal
                    head_hitbox_x = leftX + 2.5 * head_hitbox_size  # Centered horizontally
                    head_hitbox_y = head_pos[1] + deltaZ / 8  # Adjust this value to lower the head hitbox position
                    draw_list.add_circle_filled(head_hitbox_x, head_hitbox_y, head_hitbox_radius, imgui.get_color_u32_rgba(headdotcolordef[0],headdotcolordef[1],headdotcolordef[2],headdotcolordef[3]))


        except:
            return
def main():
    global esp_mode
    global line_rendering
    global esp_rendering
    global hp_bar_rendering
    global head_hitbox_rendering

    if not glfw.init():
        print("Could not initialize OpenGL context")
        exit(1)
    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, glfw.TRUE)
    window = glfw.create_window(WINDOW_WIDTH, WINDOW_HEIGHT, "overlay", None, None)

    hwnd = glfw.get_win32_window(window)

    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME)
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

    ex_style = win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, -2, -2, 0, 0,
                          win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)

    glfw.make_context_current(window)

    imgui.create_context()
    impl = GlfwRenderer(window)

    # Avoid state changes outside the main loop
    gl.glClearColor(0, 0, 0, 0)

    while not glfw.window_should_close(window):
        glfw.poll_events()
        impl.process_inputs()

        imgui.new_frame()

        imgui.set_next_window_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        imgui.set_next_window_position(0, 0)

        imgui.begin("overlay", flags=imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_SCROLLBAR | imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_BACKGROUND)
        draw_list = imgui.get_window_draw_list()

        # Make sure esp is optimized
        esp(draw_list)

        imgui.end()
        imgui.end_frame()

        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        imgui.render()
        impl.render(imgui.get_draw_data())

        glfw.swap_buffers(window)

    impl.shutdown()
    glfw.terminate()

if __name__ == '__main__':
    main()
