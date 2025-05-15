import tkinter as tk
from tkinter import Canvas, Button, Label, messagebox
from PIL import Image, ImageDraw, ImageTk
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model, load_model, save_model
from tensorflow.keras.layers import Input, Conv2D, MaxPooling2D, Flatten, Dense
from tensorflow.keras.utils import to_categorical
from sklearn.model_selection import train_test_split
import os
from random import randint as rnd
import logging
import h5py

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_model_compatibility(model_path):
    """Проверяет, можно ли загрузить модель"""
    try:
        with h5py.File(model_path, 'r') as f:
            if 'model_config' not in f.attrs:
                logger.error("Файл не является валидной моделью Keras")
                return False
        return True
    except Exception as e:
        logger.error(f"Ошибка проверки модели: {e}")
        return False

def safe_load_model(model_path):
    """Безопасная загрузка модели с обработкой ошибок"""
    try:
        # Попробуем стандартную загрузку
        model = load_model(model_path)
        logger.info("Модель успешно загружена стандартным способом")
        return model
    except Exception as e:
        logger.warning(f"Стандартная загрузка не удалась: {e}")
        
        try:
            # Попробуем загрузить только архитектуру и веса по отдельности
            with h5py.File(model_path, 'r') as f:
                model_config = f.attrs.get('model_config')
                if model_config is None:
                    raise ValueError("Не найден model_config в файле HDF5")
                
                model = tf.keras.models.model_from_json(model_config.decode('utf-8'))
                model.load_weights(model_path)
                logger.info("Модель загружена через ручную загрузку архитектуры и весов")
                return model
        except Exception as e:
            logger.error(f"Полная ошибка загрузки модели: {e}")
            return None

def generate_and_train_model():
    try:
        if not os.path.exists('assets'):
            os.makedirs('assets')
            messagebox.showwarning("Внимание", "Пожалуйста, добавьте изображения Glock_17.png и Remington_870_shotgun.png в папку assets")
            return None

        try:
            glock = Image.open("assets/Glock_17.png").convert('RGB')
            remington = Image.open("assets/Remington_870_shotgun.png").convert('RGB')
            logger.info("Изображения успешно загружены")
        except FileNotFoundError as e:
            logger.error(f"Ошибка загрузки изображений: {e}")
            messagebox.showerror("Ошибка", f"Не найдены изображения в папке assets: {e}")
            return None

        images = [glock, remington]
        samples = []
        target_size = (128, 128)

        logger.info("Начало генерации тренировочных данных...")
        for i in range(500):
            choice = rnd(0, 1)
            img = images[choice].copy()
            rot = rnd(0, 359)
            
            img = img.rotate(rot, expand=True)
            img = img.resize(target_size)
            
            img_array = np.array(img)
            noise = np.random.randint(0, 50, img_array.shape, dtype=np.uint8)
            img_array = np.clip(img_array + noise, 0, 255)
            
            samples.append({
                'input': img_array,
                'output': [choice, rot]
            })

        X = np.array([sample['input'] for sample in samples], dtype=np.float32) / 255.0
        y_class = to_categorical([sample['output'][0] for sample in samples])
        y_rot = np.array([sample['output'][1] / 360.0 for sample in samples])

        X_train, X_test, y_class_train, y_class_test, y_rot_train, y_rot_test = train_test_split(
            X, y_class, y_rot, test_size=0.2, random_state=42
        )

        logger.info("Создание архитектуры модели...")
        inputs = Input(shape=(128, 128, 3))
        x = Conv2D(32, (3, 3), activation='relu')(inputs)
        x = MaxPooling2D((2, 2))(x)
        x = Conv2D(64, (3, 3), activation='relu')(x)
        x = MaxPooling2D((2, 2))(x)
        x = Conv2D(128, (3, 3), activation='relu')(x)
        x = MaxPooling2D((2, 2))(x)
        x = Flatten()(x)
        
        class_output = Dense(2, activation='softmax', name='class_output')(x)
        rot_output = Dense(1, activation='sigmoid', name='rot_output')(x)
        
        model = Model(inputs=inputs, outputs=[class_output, rot_output])
        
        model.compile(
            optimizer='adam',
            loss={
                'class_output': 'categorical_crossentropy',
                'rot_output': 'mse'
            },
            metrics={
                'class_output': 'accuracy',
                'rot_output': 'mae'
            }
        )
        
        logger.info("Начало обучения модели...")
        model.fit(
            X_train,
            {'class_output': y_class_train, 'rot_output': y_rot_train},
            epochs=15,
            batch_size=32,
            validation_data=(X_test, {'class_output': y_class_test, 'rot_output': y_rot_test})
        )

        model_path = 'weapon_detector_model.h5'
        save_model(model, model_path)
        logger.info(f"Модель сохранена в {os.path.abspath(model_path)}")
        messagebox.showinfo("Успех", f"Модель успешно обучена и сохранена в {model_path}")
        return model
    
    except Exception as e:
        logger.error(f"Ошибка при обучении модели: {e}", exc_info=True)
        messagebox.showerror("Ошибка", f"Ошибка при обучении модели: {e}")
        return None

class WeaponRecognizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Распознавание оружия")
        self.root.geometry("500x600")
        
        self.model = None
        self.initialize_ui()
        self.load_model()
    
    def initialize_ui(self):
        self.canvas = Canvas(self.root, width=400, height=400, bg='white')
        self.canvas.pack(pady=10)
        
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<ButtonRelease-1>", self.reset)
        self.last_x, self.last_y = None, None
        
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)
        
        self.clear_btn = Button(button_frame, text="Очистить", command=self.clear_canvas)
        self.clear_btn.pack(side=tk.LEFT, padx=10)
        
        self.recognize_btn = Button(button_frame, text="Распознать", command=self.recognize_drawing)
        self.recognize_btn.pack(side=tk.LEFT, padx=10)
        
        self.train_btn = Button(button_frame, text="Обучить модель", command=self.train_model)
        self.train_btn.pack(side=tk.LEFT, padx=10)
        
        self.result_label = Label(self.root, text="Нарисуйте оружие и нажмите 'Распознать'", 
                                font=('Arial', 12), wraplength=450)
        self.result_label.pack(pady=10)
        
        self.image = Image.new("RGB", (400, 400), "white")
        self.draw = ImageDraw.Draw(self.image)
        
        self.brush_size = 15
        self.brush_color = 'black'
    
    def load_model(self):
        model_path = 'weapon_detector_model.h5'
        if os.path.exists(model_path):
            logger.info(f"Попытка загрузки модели из {os.path.abspath(model_path)}")
            
            if not check_model_compatibility(model_path):
                messagebox.showerror("Ошибка", 
                    "Файл модели поврежден или несовместим. Обучите модель заново.")
                return
            
            self.model = safe_load_model(model_path)
            
            if self.model is not None:
                logger.info("Модель успешно загружена")
                messagebox.showinfo("Успех", "Модель успешно загружена")
            else:
                messagebox.showerror("Ошибка", 
                    "Не удалось загрузить модель. Обучите модель заново.")
        else:
            logger.warning(f"Файл модели не найден: {os.path.abspath(model_path)}")
            messagebox.showwarning("Внимание", 
                "Файл модели не найден. Пожалуйста, обучите модель сначала.")
    
    def paint(self, event):
        if self.last_x and self.last_y:
            self.canvas.create_line(self.last_x, self.last_y, event.x, event.y, 
                                  width=self.brush_size, fill=self.brush_color,
                                  capstyle=tk.ROUND, smooth=tk.TRUE)
            self.draw.line([self.last_x, self.last_y, event.x, event.y], 
                         fill=self.brush_color, width=self.brush_size)
        self.last_x, self.last_y = event.x, event.y
    
    def reset(self, event):
        self.last_x, self.last_y = None, None
    
    def clear_canvas(self):
        self.canvas.delete("all")
        self.image = Image.new("RGB", (400, 400), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.result_label.config(text="Холст очищен")
    
    def recognize_drawing(self):
        if self.model is None:
            messagebox.showerror("Ошибка", "Модель не загружена. Обучите модель сначала.")
            return
        
        try:
            img = self.image.resize((128, 128))
            img_array = np.array(img) / 255.0
            img_array = np.expand_dims(img_array, axis=0)
            
            class_pred, rot_pred = self.model.predict(img_array, verbose=0)
            
            weapon_class = "Glock-17" if np.argmax(class_pred) == 0 else "Remington 870"
            rotation_angle = rot_pred[0][0] * 360
            
            confidence = max(class_pred[0])
            result_text = (f"Распознано: {weapon_class}\n"
                         f"Уверенность: {confidence:.1%}\n"
                         f"Угол поворота: {rotation_angle:.1f}°")
            
            self.result_label.config(text=result_text)
            
            # Визуализация для отладки
            debug_img = Image.fromarray((img_array[0] * 255).astype(np.uint8))
            debug_img.show(title="Что видит нейросеть")
            
        except Exception as e:
            logger.error(f"Ошибка распознавания: {e}", exc_info=True)
            self.result_label.config(text=f"Ошибка распознавания: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка при распознавании: {e}")
    
    def train_model(self):
        self.model = generate_and_train_model()

if __name__ == "__main__":
    try:
        # Проверяем доступность TensorFlow
        tf_version = tf.__version__
        logger.info(f"Используется TensorFlow {tf_version}")
        
        root = tk.Tk()
        app = WeaponRecognizerApp(root)
        root.mainloop()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        messagebox.showerror("Ошибка", f"Критическая ошибка: {e}\nПроверьте установку TensorFlow")