from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import shutil

app = FastAPI()

IMAGES_DIR = "/media/crazy7/ipad_pics"

app.mount("/static", StaticFiles(directory="/media/crazy7/ipad_pics"), name="static")


@app.get("/", response_class=HTMLResponse)
async def photo_album(request: Request):
    # List all image files
    files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
    images_html = "".join([f'<img src="/static/photos/{file}" style="max-width:90vw; margin:10px;"><br>' for file in files])
    html = f"""
    <html>
    <head>
      <title>Simple Digital Album</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body>
      <h2>Digital Photo Album</h2>
      {images_html}
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.post("/upload", response_class=HTMLResponse)
async def upload_photo(file: UploadFile = File(...)):
    with open(os.path.join(IMAGES_DIR, file.filename), "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return "<p>Photo uploaded! <a href='/'>View Album</a></p>"
