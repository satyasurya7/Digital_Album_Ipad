# App Name: Digital-Album-Ipad
# Version: 0.0.2
# Date: 2025-10-05
# Ver Update: Updated Code with Full screen images and re-structured folders

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import shutil
from PIL import Image
import piexif
import requests
from functools import lru_cache
import json

app = FastAPI()

IMAGES_DIR = "/media/crazy7/ipad_pics"

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory=IMAGES_DIR), name="media")  # for images

templates = Jinja2Templates(directory="templates")


@lru_cache(maxsize=256)
def reverse_geocode(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1"
    headers = {"User-Agent": "DigitalAlbum/1.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return (
                data.get("address", {}).get("city") or
                data.get("address", {}).get("town") or
                data.get("address", {}).get("village") or
                data.get("display_name")
            )
    except Exception:
        return None
    return None


def get_exif_data(img_path):
    try:
        img = Image.open(img_path)
        exif_dict = piexif.load(img.info.get('exif', b''))
        return exif_dict
    except Exception:
        return None


def _convert_to_degrees(value):
    try:
        d = value[0][0] / value[0][1]
        m = value[1][0] / value[1][1]
        s = value[2][0] / value[2][1]
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None


def get_lat_lon(exif_dict):
    if not exif_dict:
        return None, None

    gps = exif_dict.get('GPS', {})
    if not gps:
        return None, None

    gps_latitude = gps.get(piexif.GPSIFD.GPSLatitude)
    gps_latitude_ref = gps.get(piexif.GPSIFD.GPSLatitudeRef)
    gps_longitude = gps.get(piexif.GPSIFD.GPSLongitude)
    gps_longitude_ref = gps.get(piexif.GPSIFD.GPSLongitudeRef)

    if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
        lat = _convert_to_degrees(gps_latitude)
        lon = _convert_to_degrees(gps_longitude)
        if lat is None or lon is None:
            return None, None
        if gps_latitude_ref != b'N':
            lat = -lat
        if gps_longitude_ref != b'E':
            lon = -lon
        return round(lat, 6), round(lon, 6)
    return None, None


def get_datetime(exif_dict):
    if not exif_dict:
        return None
    datetime_bytes = exif_dict.get('Exif', {}).get(piexif.ExifIFD.DateTimeOriginal)
    if datetime_bytes:
        try:
            return datetime_bytes.decode()
        except Exception:
            return None
    return None


def scan_images():
    files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
    images_data = []
    for f in files:
        path = os.path.join(IMAGES_DIR, f)
        exif = get_exif_data(path)
        lat, lon = get_lat_lon(exif)
        datetime_str = get_datetime(exif)
        location_name = reverse_geocode(lat, lon) if lat and lon else None
        images_data.append({
            "filename": f,
            "latitude": lat,
            "longitude": lon,
            "datetime": datetime_str or "Unknown",
            "location": location_name or "Unknown"
        })
    return images_data


@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/images", response_class=JSONResponse)
async def get_images_api():
    images = scan_images()
    return images


@app.post("/upload", response_class=HTMLResponse)
async def upload_photo(file: UploadFile = File(...)):
    save_path = os.path.join(IMAGES_DIR, file.filename)
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return """
    <html>
    <body style='font-family: Arial, sans-serif; text-align:center; padding:20px; background:#222; color:#eee;'>
      <h3>Upload Successful!</h3>
      <p><a href="/">Return to Album</a></p>
    </body>
    </html>
    """
