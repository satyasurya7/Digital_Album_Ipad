from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import shutil
from PIL import Image
import piexif
import json
import requests
from functools import lru_cache

app = FastAPI()

IMAGES_DIR = "/media/crazy7/ipad_pics"
app.mount("/static", StaticFiles(directory=IMAGES_DIR), name="static")

@lru_cache(maxsize=256)
def reverse_geocode(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse?format=json&lat={0}&lon={1}&zoom=10&addressdetails=1".format(lat, lon)
    headers = {"User-Agent": "DigitalAlbum/1.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return data.get("address", {}).get("city") or data.get("address", {}).get("town") or data.get("address", {}).get("village") or data.get("display_name")
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


@app.get("/", response_class=HTMLResponse)
async def photo_album(request: Request):
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

    images_json = json.dumps(images_data)

    first_image = images_data[0]['filename'] if images_data else ''
    first_datetime = images_data[0]['datetime'] if images_data else 'Unknown'
    first_location = images_data[0]['location'] if images_data else 'Unknown'

    html = """
    <html>
    <head>
      <title>Digital Album with Geo & Date</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body {{ margin: 0; font-family: Arial, sans-serif; background: black; color: white; text-align:center; overflow: hidden; }}
        #slideshow {{ width: 100vw; height: 100vh; object-fit: contain; }}
        #infoBox {{
          position: fixed;
          bottom: 10px;
          right: 10px;
          background: rgba(0,0,0,0.6);
          padding: 8px 14px;
          border-radius: 6px;
          font-size: 14px;
          max-width: 280px;
          text-align: left;
          z-index: 10;
        }}
        #uploadForm {{
          position: fixed;
          top: 10px;
          right: 10px;
          z-index: 10;
          background: rgba(0,0,0,0.6);
          padding: 6px 12px;
          border-radius: 6px;
        }}
        input[type="file"] {{ margin: 10px 5px 0 0; }}
        button {{ padding: 6px 12px; font-size: 16px; cursor: pointer; }}
        /* Arrow buttons */
        #navArrows {{
          position: fixed;
          top: 50%;
          width: 100%;
          pointer-events: none;
          z-index: 10;
        }}
        #prevBtn, #nextBtn {{
          pointer-events: all;
          background: rgba(0,0,0,0.5);
          border: none;
          color: white;
          font-size: 40px;
          padding: 10px 20px;
          border-radius: 6px;
          user-select: none;
          cursor: pointer;
        }}
        #prevBtn {{ position: absolute; left: 10px; transform: translateY(-50%); }}
        #nextBtn {{ position: absolute; right: 10px; transform: translateY(-50%); }}
      </style>
    </head>
    <body>
      <form id="uploadForm" action="/upload" method="post" enctype="multipart/form-data">
          <input type="file" name="file" accept="image/*" required>
          <button type="submit">Upload Photo</button>
      </form>

      <img id="slideshow" src="/static/{first_image}" alt="Photo Album Image">

      <div id="infoBox">
        <div><b>Date & Time:</b> {first_datetime}</div>
        <div><b>Location:</b> {first_location}</div>
      </div>

      <div id="navArrows">
        <button id="prevBtn">&#10094;</button>
        <button id="nextBtn">&#10095;</button>
      </div>

      <script>
        var images = {images_json};
        var currentIndex = 0;
        var slideshow = document.getElementById('slideshow');
        var infoBox = document.getElementById('infoBox');
        var prevBtn = document.getElementById('prevBtn');
        var nextBtn = document.getElementById('nextBtn');
        var slideTimer;

        function updateSlide() {{
          var image = images[currentIndex];
          slideshow.src = '/static/' + image.filename + '?t=' + new Date().getTime();
          infoBox.innerHTML = '<div><b>Date & Time:</b> ' + image.datetime + '</div>' +
                              '<div><b>Location:</b> ' + (image.location || 'Unknown') + '</div>';
        }}

        function showNextImage() {{
          currentIndex = (currentIndex + 1) % images.length;
          updateSlide();
        }}

        function showPrevImage() {{
          currentIndex = (currentIndex - 1 + images.length) % images.length;
          updateSlide();
        }}

        function startSlideshow() {{
          slideTimer = setInterval(showNextImage, 10000);
          console.log('Slideshow started');
        }}

        function stopSlideshow() {{
          clearInterval(slideTimer);
          console.log('Slideshow stopped');
        }}

        function resetSlideshowTimer() {{
          stopSlideshow();
          slideTimer = setTimeout(startSlideshow, 10000);
          console.log('Slideshow reset timer');
        }}

        prevBtn.addEventListener('click', function() {{
          showPrevImage();
          resetSlideshowTimer();
        }});

        nextBtn.addEventListener('click', function() {{
          showNextImage();
          resetSlideshowTimer();
        }});

        if(images.length > 1) {{
          startSlideshow();
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
