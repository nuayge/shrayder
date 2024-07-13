import os
import struct
import subprocess
import sys
from math import cos, pi, sin

from direct.gui.DirectGui import DirectSlider
from direct.showbase.ShowBase import ShowBase

from panda3d.core import (
    CardMaker,
    ClockObject,
    Geom,
    GeomEnums,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    LineSegs,
    Shader,
    Spotlight,
    TextNode,
    Texture,
    load_prc_file_data,
)
from shrayder.helpers import ffmpeg_cmdstring


class H3Shrayder(ShowBase):
    def __init__(
        self,
        data: list[tuple[float, float, float]],
        bounds=(-180, -90, 180, 90),
        z_scaling: float = 1.0,
        colormap: list[tuple[tuple[float, float, float], float]] = [
            ((0, 0, 0), 0),
            ((1, 1, 1), 2),
        ],
        light_pos: tuple[float, float, float] = (-5.0, -5.0, 3),
        cam_pos: tuple[float, float, float] = (-5.0, -5.0, 15),
        edit_mode: bool = False,
        record: bool = False,
        window_size=(1280, 720),
    ):
        load_prc_file_data(
            "",
            f"""
            textures-power-2 none
            gl-coordinate-system default
            gl-version 3 3
            window-title Shrayder Demo
            filled-wireframe-apply-shader true

            # As an optimization, set this to the maximum number of cameras
            # or lights that will be rendering the terrain at any given time.
            stm-max-views 2

            # Further optimize the performance by reducing this to the max
            # number of chunks that will be visible at any given time.
            stm-max-chunk-count 8192
            show-frame-rate-meter 1
            win-size {window_size[0]} {window_size[1]}
            # show-scene-graph-analyzer-meter true
            gl-check-errors #f
        """,
        )
        ShowBase.__init__(self)

        self.record = record
        self.first_frame = False
        self.bounds = bounds
        xmin, ymin, xmax, ymax = bounds
        self.midx = (xmin + xmax) / 2
        self.midy = (ymin + ymax) / 2
        self.ffmpeg = None
        self.z_scaling = z_scaling
        self.colormap = colormap
        self.edit_mode = edit_mode
        self.records = data

        self.num_hexagons = len(self.records)
        self.gc = ClockObject.get_global_clock()
        self.cam_z = cam_pos[2]

        self.angle = 0.0
        self.pitch = 0.0

        self.disable_mouse()

        self.camera_orbit = self.render.attach_new_node("Camera orbit")
        self.camera_pitch = self.camera_orbit.attach_new_node("Camera pitch")
        self.camera.reparent_to(self.camera_pitch)

        # Camera goes wild if not on 0,0 in x,y.
        self.camera.set_pos(0, 0, self.cam_z)
        self.camera.look_at(0, 0, 0)

        # Key events and camera movement task
        self.camera_movement = (0, 0)
        self.accept("escape", self.quit)
        self.accept("arrow_up", self.change_camera_movement, [0, -1])
        self.accept("arrow_up-up", self.change_camera_movement, [0, 1])
        self.accept("arrow_down", self.change_camera_movement, [0, 1])
        self.accept("arrow_down-up", self.change_camera_movement, [0, -1])
        self.accept("arrow_left", self.change_camera_movement, [-0.4, 0])
        self.accept("arrow_left-up", self.change_camera_movement, [0.4, 0])
        self.accept("arrow_right", self.change_camera_movement, [0.4, 0])
        self.accept("arrow_right-up", self.change_camera_movement, [-0.4, 0])
        self.accept("w-repeat", self.zoom_in)
        self.accept("s-repeat", self.zoom_out)
        self.accept("w", self.zoom_in)
        self.accept("s", self.zoom_out)

        self.taskMgr.add(self.move_camera, "Move camera")

        # XYZ texture is the position of our hexagons
        self.create_xyz_texture()
        self.create_colormap_texture()

        dir = os.path.dirname(os.path.abspath(__file__))
        shader = Shader.load(
            Shader.SL_GLSL,
            vertex=os.path.join(dir, "shaders/h3.vert"),
            fragment=os.path.join(dir, "shaders/h3.frag"),
        )

        # make some floor
        # 10% bigger than the bounds
        cm = CardMaker("")
        cm.set_frame(
            (xmin - self.midx) * 1.1,
            (xmax - self.midx) * 1.1,
            (ymin - self.midy) * 1.1,
            (ymax - self.midy) * 1.1,
        )
        floor = self.render.attach_new_node(cm.generate())
        # Color of the floor not working, because my shader is wrong.
        floor.setColor(1.0, 0.1, 0.1, 1)
        floor.set_p(-90)
        floor.set_z(-0.1)
        # floor.set_texture(loader.load_texture('maps/grid.rgb'))
        floor.set_shader(shader)

        # light
        sp = Spotlight("Spot")
        if self.edit_mode:
            sp.show_frustum()
        my_light = self.render.attach_new_node(sp)
        my_light.node().set_shadow_caster(True, 1024, 1024)
        my_light.node().set_color((0.9, 0.9, 0.8, 1.0))
        my_light.node().get_lens().set_fov(90)
        my_light.node().get_lens().set_near_far(0.1, 300)
        self.render.set_light(my_light)
        my_light.set_pos(*light_pos)
        my_light.look_at(0, 0, 0)

        self.render.set_shader_input("shadow_blur", 0.02)

        # make a slider to change the softness
        if self.edit_mode:
            self.shadow_slider = DirectSlider(
                range=(0, 0.5),
                value=0.02,
                scale=0.5,
                pos=(-0.8, 0.0, 0.9),
                command=self.set_softness,
            )

            self.z_scaling_slider = DirectSlider(
                range=(1 / 100000, 1 / 1000),
                value=0.0002,
                scale=0.5,
                pos=(-0.8, 0.0, 0.7),
                command=self.set_z_scaling,
            )

        geom = self.create_hexagon(size=0.018)

        self.hexagon_node = GeomNode("hexagon")
        self.hexagon_node.add_geom(geom)

        self.hexa_np = self.render.attach_new_node(self.hexagon_node)
        self.hexa_np.set_instance_count(self.num_hexagons)
        self.hexa_np.set_shader(shader)
        self.hexa_np.set_shader_input("texbuffer", self.buffer)
        self.hexa_np.set_shader_input("geomtype", 1)
        self.hexa_np.set_shader_input("z_scaling", self.z_scaling)

        self.render.set_shader_input("colormap", self.colorbuffer)
        self.render.set_shader_input("colormap_length", len(self.colormap))
        # floor.set_shader_input("texbuffer", self.buffer)

        floor.set_shader_input("geomtype", -2)
        floor.set_shader_input("z_scaling", self.z_scaling)

        if self.record:
            # Start FFmpeg
            self.ffmpeg = subprocess.Popen(
                ffmpeg_cmdstring("recording", *window_size),
                stdin=subprocess.PIPE,
                bufsize=-1,
                shell=False,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
            # text.setWordwrap(3.0)
            globalClock = ClockObject.get_global_clock()
            globalClock.setMode(ClockObject.MNonRealTime)
            globalClock.setDt(1.0 / float(60))  # 60 fps

            # Add the record task to the task manager
            self.taskMgr.add(self.record_task, "ffmpegTask")

    def zoom_in(
        self,
    ):
        self.cam_z -= 0.5
        # self.camera.set_z(self.cam_z)

    def zoom_out(self, move: bool = True):
        self.cam_z += 0.5
        # self.camera.set_z(self.cam_z)

    def quit(self):
        if self.ffmpeg:
            # Despite closing properly standard input, mp4s are corrupted
            # They open fine in VLC, not in Mac's own video viewer.
            # The play fine in Signal for Desktop but not Signal for Android 🤷
            self.ffmpeg.stdin.close()
        sys.exit()

    def change_camera_movement(self, turn, pitch):
        self.camera_movement = (
            self.camera_movement[0] + turn,
            self.camera_movement[1] + pitch,
        )

    def move_camera(self, task):
        self.camera_orbit.set_h(
            self.camera_orbit,
            self.camera_movement[0] * self.gc.get_dt() * 360.0 / 3.0,
        )
        new_pitch = (
            self.camera_pitch.get_p()
            + self.camera_movement[1] * self.gc.get_dt() * 360.0 / 3.0
        )
        # self.camera_pitch.set_p(min(max(new_pitch, -89), 89))
        self.camera_pitch.set_p(new_pitch)
        self.camera.set_z(self.cam_z)

        return task.cont

    def set_softness(self):
        v = float(self.shadow_slider["value"])
        self.render.set_shader_input("shadow_blur", v)

    def set_z_scaling(self):
        v = float(self.z_scaling_slider["value"])
        self.hexa_np.set_shader_input("z_scaling", v)

    def create_hexagon(self, size=0.01):
        vformat = GeomVertexFormat.getV3n3()
        vdata = GeomVertexData("hexagon", vformat, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, "vertex")
        normal = GeomVertexWriter(vdata, "normal")

        height = size * 1  # Height of the hexagon, adjust as needed

        # Top vertices
        for i in range(6):
            angle = i * (pi / 3)
            x = size * sin(angle)
            y = size * cos(angle)
            vertex.addData3(x, y, height)
            normal.addData3(0, 0, 1)

        # Bottom vertices
        for i in range(6):
            angle = i * (pi / 3)
            x = size * sin(angle)
            y = size * cos(angle)
            vertex.addData3(x, y, 0)
            normal.addData3(0, 0, -1)

        # Side vertices
        for i in range(6):
            angle = i * (pi / 3)
            next_angle = ((i + 1) % 6) * (pi / 3)
            x, y = size * sin(angle), size * cos(angle)
            nx, ny = size * sin(next_angle), size * cos(next_angle)

            vertex.addData3(x, y, height)
            normal.addData3(sin(angle), cos(angle), 0)
            vertex.addData3(x, y, 0)
            normal.addData3(sin(angle), cos(angle), 0)

            vertex.addData3(nx, ny, height)
            normal.addData3(sin(next_angle), cos(next_angle), 0)
            vertex.addData3(nx, ny, 0)
            normal.addData3(sin(next_angle), cos(next_angle), 0)

        prim = GeomTriangles(Geom.UHStatic)

        # Top face
        for i in range(1, 5):
            prim.addVertices(0, i, i + 1)
        prim.addVertices(0, 5, 1)

        # Bottom face
        for i in range(1, 5):
            prim.addVertices(6, i + 7, i + 6)
        prim.addVertices(6, 7, 11)

        # Side faces
        for i in range(6):
            base = 12 + i * 4
            prim.addVertices(base, base + 1, base + 2)
            prim.addVertices(base + 1, base + 3, base + 2)

        geom = Geom(vdata)
        geom.addPrimitive(prim)

        return geom

    def create_xyz_texture(self):
        self.buffer = Texture("texbuffer")
        self.buffer.setup_buffer_texture(
            self.num_hexagons * 12,
            Texture.T_float,
            Texture.F_rgb32,
            GeomEnums.UH_static,
        )
        image = memoryview(self.buffer.modify_ram_image())
        for i, hex in enumerate(self.records):
            off = i * 12
            image[off : off + 12] = struct.pack(
                "fff",
                (hex[0] - self.midx) * 2,
                (hex[1] - self.midy) * 2,
                hex[2],
            )

    def create_colormap_texture(self):
        self.colorbuffer = Texture("colormap")
        self.colorbuffer.setup_buffer_texture(
            len(self.colormap) * 16,
            Texture.T_float,
            Texture.F_rgba32,
            GeomEnums.UH_static,  # Not sure about this
        )
        image = memoryview(self.colorbuffer.modify_ram_image())
        for i, (rgb, cutoff) in enumerate(self.colormap):
            off = i * 16
            image[off : off + 16] = struct.pack("ffff", rgb[0], rgb[1], rgb[2], cutoff)

    def record_task(self, task):
        tex = (
            self.win.getScreenshot()
        )  # Captures the recently rendered image, and returns it as a Texture.
        if tex is None:
            print("WARNING: tex is none!")
            return task.cont
        if self.first_frame:
            # Don't capture first (black) frame.
            self.first_frame = False
            return task.cont
        buf = (
            tex.getRamImage().getData()
        )  # Get the raw BGRA image data from that capture
        self.ffmpeg.stdin.write(buf)  # Pass it to ffmpeg as text buffer
        return task.cont

    def add_text(self, text: str = "OK", x=0, y=0, z: int = 2, rgba=(1, 1, 1, 1)):
        text_box = TextNode(f"{text}-{x}-{y}")
        text_box.setText(text)
        textNodePath = self.render.attach_new_node(text_box)
        textNodePath.setScale(0.3)
        textNodePath.setPos(x, y, z)
        text_box.set_text_color(*rgba)
        textNodePath.setHpr(0, -45, 0)
        textNodePath.setBillboardAxis()

    def add_label(
        self,
        text: str = "",
        x0: int = 0,
        y0: int = 0,
        z0: int = 0,
        x1: int = 0,
        y1: int = 0,
        z1: int = 2,
        line_color=(1, 1, 1, 1),
        text_color=(0, 0, 0, 1),
    ):
        line = LineSegs()
        # Thickness does not work for some reason
        line.set_thickness(10.0)
        line.set_color(*line_color)

        start_point = (x0 - self.midx, y0 - self.midy, z0)
        end_point = (x1 - self.midx, y1 - self.midy, z1)

        # Move to the start point
        line.move_to(*start_point)
        # Draw to the end point
        line.draw_to(*end_point)

        # Create a NodePath from the LineSegs
        line_node = line.create()
        # Attach the NodePath to the render tree
        self.render.attach_new_node(line_node)
        if text:
            self.add_text(text, *end_point, rgba=text_color)
