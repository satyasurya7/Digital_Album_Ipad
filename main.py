from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import shutil
from PIL import Image
import piexif
import json

app = FastAPI()

IMAGES_DIR = "/media/crazy7/ipad_pics"
app.mount("/static", StaticFiles(directory=IMAGES_DIR), name="static")


def get_exif_data(img_path):
    try:
        img = Image.open(img_path)
        exif_dict = piexif.load(img.info.get('exif', b''))
        return exif_dict
    except Exception:
        return None


def _convert_to_degrees(value):
    d = value[0][0] / value[0][1]
    m = value[1][0] / value[1][1]
    s = value[2][0] / value[2][1]
    return d + (m / 60.0) + (s / 3600.0)


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
        if gps_latitude_ref != b'N':
            lat = -lat

        lon = _convert_to_degrees(gps_longitude)
        if gps_longitude_ref != b'E':
            lon = -lon

        return round(lat, 6), round(lon, 6)
    return None, None


def get_datetime(exif_dict):
    if not exif_dict:
        return None
    datetime_bytes = exif_dict.get('Exif', {}).get(piexif.ExifIFD.DateTimeOriginal)
    if datetime_bytes:
        return datetime_bytes.decode()
    return None


@app.get("/", response_class=HTMLResponse)
async def photo_album(request: Request):
    files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
    images_data = []
    for f in files:
        path = os.path.join(IMAGES_DIR, f)
        exif = get_exif_data(path)
        lat, lon = get_lat_lon(exif)
        datetime_str = get_datetime(exif)
        images_data.append({
            "filename": f,
            "latitude": lat,
            "longitude": lon,
            "datetime": datetime_str or "Unknown"
        })

    images_json = json.dumps(images_data)  # safe JSON serialization

    # Defaults for first image info
    first_image = images_data[0]['filename'] if images_data else ''
    first_datetime = images_data[0]['datetime'] if images_data else 'Unknown'
    if images_data and images_data[0]['latitude'] is not None:
        first_location = f"{images_data[0]['latitude']}, {images_data[0]['longitude']}"
    else:
        first_location = "Unknown"

    html = """
    <html>
    <head>
      <title>Digital Album with Geo & Date</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body {{ margin: 10px; font-family: Arial, sans-serif; background: #222; color: white; text-align:center; }}
        #slideshow {{ max-width: 90vw; max-height: 70vh; border-radius: 8px; }}
        #infoBox {{ position: fixed; bottom: 10px; right: 10px; background: rgba(0,0,0,0.6); padding: 8px 14px; border-radius: 6px; font-size: 14px; max-width: 280px; text-align: left; }}
        #uploadForm {{ margin-top: 20px; }}
        input[type="file"] {{ margin: 10px 0; }}
        input[type="submit"] {{ padding: 6px 12px; font-size: 16px; cursor: pointer; }}
      </style>
    </head>
    <body>
      <h2>Digital Photo Album</h2>
      <img id="slideshow" src="/static/{first_image}" alt="Photo Album Image">
      <div id="infoBox">
        <div><b>Date & Time:</b> {first_datetime}</div>
        <div><b>Location:</b> {first_location}</div>
      </div>
      <form id="uploadForm" action="/upload" method="post" enctype="multipart/form-data">
          <input type="file" name="file" accept="image/*" required>
          <button type="submit">Upload Photo</button>
      </form>
      <script>
        const images = {images_json};
        let currentIndex = 0;
        const slideshow = document.getElementById('slideshow');
        const infoBox = document.getElementById('infoBox');

        function showNextImage() {{
          currentIndex = (currentIndex + 1) % images.length;
          const image = images[currentIndex];
          slideshow.src = '/static/' + image.filename;
          infoBox.innerHTML = `
            <div><b>Date & Time:</b> ${image.datetime}</div>
            <div><b>Location:</b> ${image.latitude !== null ? image.latitude + ', ' + image.longitude : 'Unknown'}</div>
          `;
        }}

        if(images.length > 1) {{
          setInterval(showNextImage, 10000);
        }}
      </script>
    </body>
    </html>
    """.format(
        images_json=images_json,
        first_image=first_image,
        first_datetime=first_datetime,
        first_location=first_location
    )

    return HTMLResponse(content=html)


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
