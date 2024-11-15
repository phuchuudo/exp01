import os
import cv2
import sys
import torch
import random
import numpy as np
import time

from utils.util import *
from model.model import Model

device = torch.device("cuda")
seed = 1234
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
torch.cuda.manual_seed_all(seed)
torch.backends.cudnn.benchmark = True

# Các tham số trực tiếp điền vào
image_0_path = 'images/frame-000001.jpg'  # Đường dẫn tới ảnh gốc
image_1_path = 'images/frame-000002.jpg'  # Đường dẫn tới ảnh dự đoán
load_path = 'pretrained_models/dmvfn_kitti.pkl'       # Đường dẫn tới mô hình đã huấn luyện
output_dir = 'images/pred.png'               # Đường dẫn tới ảnh kết quả (output)

def evaluate(model, image_0_path, image_1_path, output_dir):
    with torch.no_grad():
        img_0 = cv2.imread(image_0_path)
        img_1 = cv2.imread(image_1_path)
        if img_0 is None or img_1 is None:
            raise Exception("Images not found.")
        img_0 = img_0.transpose(2, 0, 1).astype('float32')
        img_1 = img_1.transpose(2, 0, 1).astype('float32')
        img = torch.cat([torch.tensor(img_0), torch.tensor(img_1)], dim=0)
        img = img.unsqueeze(0).unsqueeze(0).to(device, non_blocking=True) # NCHW
        img = img.to(device, non_blocking=True) / 255.

        pred = model.eval(img, 'single_test') # 1CHW
        pred = np.array(pred.cpu().squeeze() * 255).transpose(1, 2, 0) # CHW -> HWC
        cv2.imwrite(output_dir, pred)

if __name__ == "__main__":
    model = Model(load_path=load_path, training=False)

    t1 = time.time()
    evaluate(model, image_0_path, image_1_path, output_dir)
    t2 = time.time()
    print(f'run time: {t2 - t1} seconds')
