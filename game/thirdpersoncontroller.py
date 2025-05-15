import threading
import time
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    print("Библиотека keyboard не установлена. Используем стандартный ввод ursina.")
    print("Для установки: pip install keyboard")
    KEYBOARD_AVAILABLE = False

from ursina import *


class FirstPersonController(Entity):
    def __init__(self, **kwargs):
        self.cursor = Entity(parent=camera.ui, model='quad', color=color.pink, scale=.008, rotation_z=45)
        super().__init__()
        self.speed = 5
        self.acceleration = 150  # Ускорение при движении
        self.friction = 80      # Трение на земле
        self.air_friction = 5   # Трение в воздухе
        self.max_speed = 15     # Максимальная скорость ходьбы
        self.velocity = Vec3(0, 0, 0)  # Текущая скорость в виде вектора
        
        # Параметры для bhop
        self.bhop_window = 0.2  # Увеличено временное окно для bhop (в секундах)
        self.bhop_boost = 1.5    # Множитель скорости при успешном bhop
        self.landing_time = 0    # Время последнего приземления
        self.bhop_active = False # Флаг активного bhop
        self.consecutive_bhops = 0  # Счетчик последовательных успешных bhop
        self.max_bhop_boost = 2.0  # Максимальный множитель скорости от bhop
        self.air_control = 0.33   # Коэффициент контроля в воздухе (1/3 от нормального)
        
        # Добавляем переменную для отслеживания нажатия пробела через keyboard
        self.should_jump = False
        self.last_jump_time = 0
        
        self.height = 2
        self.camera_pivot = Entity(parent=self, y=self.height)

        camera.parent = self.camera_pivot
        camera.position = (0,0,0)
        camera.rotation = (0,0,0)
        camera.fov = 90
        mouse.locked = True
        self.mouse_sensitivity = Vec2(40, 40)

        # Физика прыжка
        self.gravity_value = 20      # Значение гравитации для реалистичной параболы
        self.jump_height = 1.2       # Высота прыжка в юнитах
        self.jump_duration = 0.5     # Желаемая длительность прыжка в секундах (время до пика)
        
        # Вычисляем начальную скорость прыжка из формулы: v_0 = sqrt(2 * g * h)
        self.jump_initial_velocity = sqrt(2 * self.gravity_value * self.jump_height)
        
        self.grounded = False
        self.jumping = False
        self.air_time = 0

        self.traverse_target = scene
        self.ignore_list = [self, ]
        self.on_destroy = self.on_disable

        for key, value in kwargs.items():
            setattr(self, key ,value)

        # make sure we don't fall through the ground if we start inside it
        if self.gravity_value:
            ray = raycast(self.world_position+(0,self.height,0), self.down, traverse_target=self.traverse_target, ignore=self.ignore_list)
            if ray.hit:
                self.y = ray.world_point.y
        
        # Настраиваем обработчики клавиш с использованием библиотеки keyboard только для пробела
        if KEYBOARD_AVAILABLE:
            self._setup_keyboard_space()
            
    def _setup_keyboard_space(self):
        """Настраиваем только обработчик клавиши пробела через keyboard"""
        if not KEYBOARD_AVAILABLE:
            return
        
        # Простой обработчик нажатия пробела - устанавливает флаг
        keyboard.on_press_key('space', lambda _: self._mark_jump())
    
    def _mark_jump(self):
        """Отмечаем необходимость прыжка - будет обработан в update"""
        # Избегаем дребезга - минимум 100мс между прыжками
        if time.time() - self.last_jump_time > 0.1:
            self.should_jump = True
            self.last_jump_time = time.time()                

    def update(self):
        self.rotation_y += mouse.velocity[0] * self.mouse_sensitivity[1]

        self.camera_pivot.rotation_x -= mouse.velocity[1] * self.mouse_sensitivity[0]
        self.camera_pivot.rotation_x= clamp(self.camera_pivot.rotation_x, -90, 90)

        # Направление движения через обычный held_keys Ursina
        direction_input = Vec3(
            self.forward * (held_keys['w'] - held_keys['s'])
            + self.right * (held_keys['d'] - held_keys['a'])
        )
            
        # Нормализуем только если длина не равна нулю
        self.direction = direction_input.normalized() if direction_input.length() > 0 else direction_input
        
        # Проверяем, нужно ли выполнить прыжок, отмеченный библиотекой keyboard
        if self.should_jump and self.grounded:
            # Если мы находимся в окне для bhop после приземления
            if time.time() - self.landing_time < self.bhop_window:
                self.bhop_active = True
                self.consecutive_bhops += 1
                print(f"BHOP! Множитель скорости: x{min(self.bhop_boost + (self.consecutive_bhops * 0.1), self.max_bhop_boost):.1f}")
            
            # Выполняем прыжок
            self.jump()
            self.should_jump = False

        # Проверка на столкновения 
        feet_ray = raycast(self.position+Vec3(0,0.5,0), self.direction, traverse_target=self.traverse_target, ignore=self.ignore_list, distance=.5, debug=False)
        head_ray = raycast(self.position+Vec3(0,self.height-.1,0), self.direction, traverse_target=self.traverse_target, ignore=self.ignore_list, distance=.5, debug=False)
        
        # Обновление времени для bhop
        if self.grounded and time.time() - self.landing_time > self.bhop_window:
            self.bhop_active = False
            self.consecutive_bhops = 0
            
        # Применение ускорения к скорости
        if not feet_ray.hit and not head_ray.hit:
            # Ускорение в направлении движения
            if self.direction.length() > 0:
                # Базовое ускорение
                acceleration_multiplier = self.acceleration
                
                # В воздухе меньшее ускорение от нажатия клавиш
                if not self.grounded and not self.bhop_active:
                    acceleration_multiplier = self.acceleration * self.air_control
                
                # Применяем ускорение
                self.velocity += self.direction * acceleration_multiplier * time.dt
            
            # Применяем трение
            if self.velocity.length() > 0:
                # Выбираем силу трения в зависимости от того, на земле мы или в воздухе
                friction_strength = self.friction if self.grounded else self.air_friction
                
                # Направление противоположное текущей скорости для трения
                friction_dir = -self.velocity.normalized()
                friction_force = friction_dir * friction_strength * time.dt
                
                # Применяем трение только если это не приведет к изменению направления скорости
                if self.velocity.length() > friction_force.length():
                    self.velocity += friction_force
                else:
                    # Если трение сильнее текущей скорости, останавливаемся
                    self.velocity = Vec3(0,0,0)
            
            # Ограничиваем максимальную горизонтальную скорость
            horizontal_velocity = Vec3(self.velocity.x, 0, self.velocity.z)
            if horizontal_velocity.length() > self.max_speed:
                horizontal_velocity = horizontal_velocity.normalized() * self.max_speed
                self.velocity.x = horizontal_velocity.x
                self.velocity.z = horizontal_velocity.z
                
            # Проверка на столкновения по каждой из осей
            move_amount = self.velocity * time.dt

            if raycast(self.position+Vec3(-.0,1,0), Vec3(1,0,0), distance=.5, traverse_target=self.traverse_target, ignore=self.ignore_list).hit:
                move_amount.x = min(move_amount.x, 0)
                self.velocity.x = 0
            if raycast(self.position+Vec3(-.0,1,0), Vec3(-1,0,0), distance=.5, traverse_target=self.traverse_target, ignore=self.ignore_list).hit:
                move_amount.x = max(move_amount.x, 0)
                self.velocity.x = 0
            if raycast(self.position+Vec3(-.0,1,0), Vec3(0,0,1), distance=.5, traverse_target=self.traverse_target, ignore=self.ignore_list).hit:
                move_amount.z = min(move_amount.z, 0)
                self.velocity.z = 0
            if raycast(self.position+Vec3(-.0,1,0), Vec3(0,0,-1), distance=.5, traverse_target=self.traverse_target, ignore=self.ignore_list).hit:
                move_amount.z = max(move_amount.z, 0)
                self.velocity.z = 0
                
            self.position += move_amount

        # Гравитация и проверка на земле
        if self.gravity_value:
            # Проверка на приземление
            ray = raycast(self.world_position+(0,self.height,0), self.down, traverse_target=self.traverse_target, ignore=self.ignore_list)

            if ray.distance <= self.height+.1:
                if not self.grounded:
                    self.land()
                self.grounded = True
                # Сбрасываем вертикальную скорость при приземлении
                self.velocity.y = 0
                # Корректируем позицию, если не стена и не слишком высоко
                if ray.world_normal.y > .7 and ray.world_point.y - self.world_y < .5: # walk up slope
                    self.y = ray.world_point[1]
                return
            else:
                self.grounded = False

            # Применяем гравитацию для параболической траектории прыжка
            self.velocity.y -= self.gravity_value * time.dt
            self.y += self.velocity.y * time.dt
            
            self.air_time += time.dt

    def input(self, key):
        # Обрабатываем нажатие пробела напрямую (резервный метод, если keyboard не работает)
        if not KEYBOARD_AVAILABLE and key == 'space':
            # Если мы находимся в окне для bhop после приземления
            if self.grounded and time.time() - self.landing_time < self.bhop_window:
                self.bhop_active = True
                self.consecutive_bhops += 1
                print(f"BHOP! Множитель скорости: x{min(self.bhop_boost + (self.consecutive_bhops * 0.1), self.max_bhop_boost):.1f}")
            self.jump()

    def jump(self):
        if not self.grounded:
            return

        self.grounded = False
        
        # Устанавливаем начальную скорость прыжка для параболической траектории
        self.velocity.y = self.jump_initial_velocity
        
        # Получаем текущую горизонтальную скорость
        horizontal_vel = Vec3(self.velocity.x, 0, self.velocity.z)
        
        # Направление движения игрока (горизонтальное)
        horizontal_dir = Vec3(self.direction.x, 0, self.direction.z).normalized()
        
        # Если нажаты клавиши движения, даем дополнительный импульс в этом направлении 
        # или усиливаем текущий импульс
        if horizontal_dir.length() > 0:
            # Если bhop активен, получаем более сильный импульс
            if self.bhop_active:
                current_boost = min(self.bhop_boost + (self.consecutive_bhops * 0.1), self.max_bhop_boost)
                # Увеличиваем существующую горизонтальную скорость (или на bhop бонус)
                boost_multiplier = current_boost
            else:
                # Обычный прыжок - увеличиваем скорость в 1.5 раза
                boost_multiplier = 1.5
            
            # Если текущая скорость в нужном направлении, усиливаем её
            if horizontal_vel.length() > 0:
                # Вычисляем угол между текущей скоростью и направлением движения
                same_direction = horizontal_vel.normalized().dot(horizontal_dir) > 0.7
                
                if same_direction:
                    # Если движемся примерно в том же направлении, усиливаем текущую скорость
                    boosted_vel = horizontal_vel * boost_multiplier
                    if boosted_vel.length() > self.max_speed * boost_multiplier:
                        boosted_vel = boosted_vel.normalized() * self.max_speed * boost_multiplier
                else:
                    # Если движемся в другом направлении, задаем новый импульс
                    boosted_vel = horizontal_dir * self.max_speed * boost_multiplier
            else:
                # Если скорость была нулевой, задаем новый импульс
                boosted_vel = horizontal_dir * self.max_speed * boost_multiplier
            
            # Применяем новую горизонтальную скорость
            self.velocity.x = boosted_vel.x
            self.velocity.z = boosted_vel.z

    def start_fall(self):
        self.jumping = False

    def land(self):
        # print('land')
        self.air_time = 0
        self.grounded = True
        self.landing_time = time.time()  # Запоминаем время приземления для bhop

    def on_enable(self):
        mouse.locked = True
        self.cursor.enabled = True
        # restore parent and position/rotation from before disablem in case you moved the camera in the meantime.
        if hasattr(self, 'camera_pivot') and hasattr(self, '_original_camera_transform'):
            camera.parent = self.camera_pivot
            camera.transform = self._original_camera_transform

    def on_disable(self):
        mouse.locked = False
        self.cursor.enabled = False
        self._original_camera_transform = camera.transform  # store original position and rotation
        camera.world_parent = scene
        
    def __del__(self):
        # Удаляем все хуки клавиш при уничтожении объекта
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.unhook_all()
            except:
                pass


if __name__ == '__main__':
    from ursina.prefabs.first_person_controller import FirstPersonController
    window.vsync = False
    app = Ursina()
    # Sky(color=color.gray)
    ground = Entity(model='plane', scale=(100,1,100), color=color.yellow.tint(-.2), texture='white_cube', texture_scale=(100,100), collider='box')
    e = Entity(model='cube', scale=(1,5,10), x=2, y=.01, rotation_y=45, collider='box', texture='white_cube')
    e.texture_scale = (e.scale_z, e.scale_y)
    e = Entity(model='cube', scale=(1,5,10), x=-2, y=.01, collider='box', texture='white_cube')
    e.texture_scale = (e.scale_z, e.scale_y)

    player = FirstPersonController(y=2, origin_y=-.5)
    player.gun = None


    gun = Button(parent=scene, model='cube', color=color.blue, origin_y=-.5, position=(3,0,3), collider='box', scale=(.2,.2,1))
    def get_gun():
        gun.parent = camera
        gun.position = Vec3(.5,0,.5)
        player.gun = gun
    gun.on_click = get_gun

    gun_2 = duplicate(gun, z=7, x=8)
    slope = Entity(model='cube', collider='box', position=(0,0,8), scale=6, rotation=(45,0,0), texture='brick', texture_scale=(8,8))
    slope = Entity(model='cube', collider='box', position=(5,0,10), scale=6, rotation=(80,0,0), texture='brick', texture_scale=(8,8))
    # hill = Entity(model='sphere', position=(20,-10,10), scale=(25,25,25), collider='sphere', color=color.green)
    # hill = Entity(model='sphere', position=(20,-0,10), scale=(25,25,25), collider='mesh', color=color.green)
    # from ursina.shaders import basic_lighting_shader
    # for e in scene.entities:
    #     e.shader = basic_lighting_shader

    hookshot_target = Button(parent=scene, model='cube', color=color.brown, position=(4,5,5))
    hookshot_target.on_click = Func(player.animate_position, hookshot_target.position, duration=.5, curve=curve.linear)

    def input(key):
        if key == 'left mouse down' and player.gun:
            gun.blink(color.orange)
            bullet = Entity(parent=gun, model='cube', scale=.1, color=color.black)
            bullet.world_parent = scene
            bullet.animate_position(bullet.position+(bullet.forward*50), curve=curve.linear, duration=1)
            destroy(bullet, delay=1)

    # player.add_script(NoclipMode())
    app.run() 