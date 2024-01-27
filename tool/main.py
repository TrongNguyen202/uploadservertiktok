import tkinter as tk
from tkinter import filedialog
from concurrent.futures import ThreadPoolExecutor
import traceback
import pandas as pd
from PIL import Image
import base64
import os
import requests
import uuid
import hmac
import hashlib
from datetime import datetime
import json
import urllib.parse

secret = "df329e59a6f78121409d77c33ee1decfbfa088a4"
app_key = "6atknvel13hna"
grant_type = "authorized_code"


class GenerateSign:
    def obj_key_sort(self, obj):
        return {k: obj[k] for k in sorted(obj)}

    def get_timestamp(self):
        return int(datetime.now().timestamp())

    def cal_sign(self, secret, url, query_params, body):
        sorted_params = self.obj_key_sort(query_params)
        sorted_params.pop("sign", None)
        sorted_params.pop("access_token", None)
        sign_string = secret + url.path
        for key, value in sorted_params.items():
            sign_string += key + str(value)
        sign_string += body + secret
        signature = hmac.new(secret.encode(), sign_string.encode(), hashlib.sha256).hexdigest()
        return signature


class GenerateSignNoBody:
    def obj_key_sort(self, obj):
        return {k: obj[k] for k in sorted(obj)}

    def get_timestamp(self):
        return int(datetime.now().timestamp())

    def cal_sign(self, secret, url, query_params):
        sorted_params = self.obj_key_sort(query_params)
        sorted_params.pop("sign", None)
        sorted_params.pop("access_token", None)
        sign_string = secret + url.path
        for key, value in sorted_params.items():
            sign_string += key + str(value)
        sign_string += secret
        signature = hmac.new(secret.encode(), sign_string.encode(), hashlib.sha256).hexdigest()
        return signature


SIGNNOBODY = GenerateSignNoBody()
SIGN = GenerateSign()


def callUploadImage(access_token, img_data):
    try:
        url = "https://open-api.tiktokglobalshop.com/api/products/upload_imgs"

        query_params = {
            "app_key": app_key,
            "access_token": access_token,
            "timestamp": SIGN.get_timestamp(),
        }

        body = json.dumps({
            "img_data": img_data,
            "img_scene": 1
        })

        sign = SIGN.cal_sign(secret, urllib.parse.urlparse(url), query_params, body)
        query_params["sign"] = sign

        response = requests.post(url, params=query_params, json=json.loads(body))

        data = json.loads(response.text)

        if data and "data" in data and "img_id" in data["data"]:
            img_id = data["data"]["img_id"]
            return img_id
        else:
            print(f"Invalid response format: 'data' or 'img_id' not found in the response")
            return ""

    except Exception as e:
        print(f"Error in callUploadImage: {str(e)}")
        print(traceback.format_exc())
        return ""


class MultithreadProcessExcelApp(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("Image Processing App")
        self.geometry("600x400")

        self.create_widgets()

    def create_widgets(self):
        self.label = tk.Label(self, text="Select Excel File:")
        self.label.pack(pady=10)

        self.file_button = tk.Button(self, text="Choose File", command=self.choose_file)
        self.file_button.pack(pady=10)

        self.process_button = tk.Button(self, text="Process", command=self.process_excel)
        self.process_button.pack(pady=10)

        self.result_text = tk.Text(self, height=10, width=60)
        self.result_text.pack(pady=10)

    def choose_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx;*.xls")])
        self.excel_file_path = file_path
        self.label.config(text=f"Selected File: {os.path.basename(file_path)}")

    def process_excel(self):
        try:
            if not hasattr(self, 'excel_file_path'):
                self.result_text.insert(tk.END, "Please select an Excel file.\n")
                return

            excel_file = pd.read_excel(self.excel_file_path)

            processed_data = []
            selected_columns = [col for col in excel_file.columns if col.startswith('images') or col == 'title']

            with ThreadPoolExecutor() as executor:
                futures = []
                for index, row in excel_file.iterrows():
                    row_data = {col: row[col] for col in selected_columns}
                    processed_data.append(row_data)
                    futures.append(executor.submit(self.process_row_data, row_data))

                for future in futures:
                    future.result()

            # Create a new DataFrame with the processed data
            new_df = pd.DataFrame(processed_data)

            # Save the new DataFrame to a new Excel file
            output_excel_path = "output_processed_data.xlsx"
            new_df.to_excel(output_excel_path, index=False)

            self.result_text.insert(tk.END, f"Processing completed. Output saved to {output_excel_path}\n")

        except Exception as e:
            self.result_text.insert(tk.END, f"Error: {str(e)}\n")
            print(traceback.format_exc())

    def process_row_data(self, row_data):
       downloaded_image_paths = []
       futures = []
       image_ids_per_row = {}
       counts =0

       with ThreadPoolExecutor() as executor:
           for col, image_url in row_data.items():
              
               if col.startswith('images') and not pd.isna(image_url):
                   counts+=1
                   futures.append(executor.submit(self.download_image, image_url, col))

           for future in futures:
               downloaded_image_paths.append(future.result())

       base64_images = self.process_images(downloaded_image_paths)
       images_ids = self.upload_images(base64_images)
       
       
      
       index = 0  

       for col, image_url in row_data.items():
           if col.startswith('images') and image_url is not None:
               if index < len(images_ids):
                   row_data[col] = f"https://p16-oec-ttp.tiktokcdn-us.com/{images_ids[index]}~tplv-omjb5zjo8w-origin-jpeg.jpeg?from=520841845"
                   index += 1
            
       return row_data



    def download_image(self, image_url, col):
        download_dir = 'C:/anhtiktok'
        os.makedirs(download_dir, exist_ok=True)
        random_string = str(uuid.uuid4())[:8]
        image_filename = os.path.join(download_dir, f"{col}_{random_string}.jpg")
        response = requests.get(image_url)
        if response.status_code == 200:
            with open(image_filename, 'wb') as f:
                f.write(response.content)
        return image_filename

    def process_images(self, downloaded_image_paths):
        base64_images = []
        for image_path in downloaded_image_paths:
            try:
                img = Image.open(image_path)
                if img.mode != 'RGB' or img.bits != 8:
                    img = img.convert('RGB')
                img.verify()
                img.close()

                with open(image_path, 'rb') as img_file:
                    base64_image = base64.b64encode(img_file.read()).decode('utf-8')
                base64_images.append(base64_image)

            except Exception as e:
                print(f"Error processing image: {image_path}, {str(e)}")

        return base64_images

    def upload_images(self, base64_images):
        images_ids = []
        for img_data in base64_images:
            # Call the TikTok upload function and retrieve image IDs
            img_id = callUploadImage(
                access_token="TTP_A6ztxAAAAADAOSpfAfIpqKWnTYKylE2CbxKgTLv1olThQtT6ayhoS3gIH2UF06GZkYWjGEGqWCt_Tw3wpSP-Cs_KcwRNoV5bQHRBPWvvKhsQngA880XiXggz6TWfWGFlKaVvCAqxt8Lli_Ynq7jsQsh0kb5lYy3I7zBgh-EklnBMHg5rn0mMXw",
                img_data=img_data
            )  # Replace with actual access token
            images_ids.append(img_id)

        return images_ids


if __name__ == "__main__":
    app = MultithreadProcessExcelApp()
    app.mainloop()
