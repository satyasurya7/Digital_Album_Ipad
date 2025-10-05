var images = [];
var currentIndex = 0;
var slideshow = document.getElementById('slideshow');
var dateTimeSpan = document.getElementById('dateTime');
var locationSpan = document.getElementById('location');
var prevBtn = document.getElementById('prevBtn');
var nextBtn = document.getElementById('nextBtn');
var slideTimer;
var refreshTimer;

function fetchImages() {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/api/images', true);
  xhr.onreadystatechange = function() {
    if (xhr.readyState === 4 && xhr.status === 200) {
      try {
        var newImages = JSON.parse(xhr.responseText);
        if (JSON.stringify(newImages) !== JSON.stringify(images)) {
          images = newImages;
          currentIndex = 0;
          updateSlide();
        }
      } catch (e) { console.error('Error parsing images JSON', e); }
    }
  };
  xhr.send();
}

function updateSlide() {
  if(images.length === 0) {
    slideshow.src = '';
    dateTimeSpan.textContent = 'No images';
    locationSpan.textContent = '';
    return;
  }
  var image = images[currentIndex];
  slideshow.src = '/media/ipad_pics/' + image.filename + '?t=' + new Date().getTime();
  dateTimeSpan.textContent = image.datetime || 'Unknown';
  locationSpan.textContent = image.location || 'Unknown';
}

function showNextImage() {
  currentIndex = (currentIndex + 1) % images.length;
  updateSlide();
}

function showPrevImage() {
  currentIndex = (currentIndex - 1 + images.length) % images.length;
  updateSlide();
}

function startSlideshow() {
  stopSlideshow();
  slideTimer = setInterval(showNextImage, 10000);
}

function stopSlideshow() {
  if (slideTimer) clearInterval(slideTimer);
}

function resetSlideshowTimer() {
  stopSlideshow();
  slideTimer = setTimeout(startSlideshow, 10000);
}

prevBtn.addEventListener('click', function() {
  showPrevImage();
  resetSlideshowTimer();
});

nextBtn.addEventListener('click', function() {
  showNextImage();
  resetSlideshowTimer();
});

// Upload form toggle
var uploadForm = document.getElementById('uploadForm');
var toggleUploadBtn = document.getElementById('toggleUploadBtn');
toggleUploadBtn.addEventListener('click', function() {
  if (uploadForm.classList.contains('expanded')) {
    uploadForm.classList.remove('expanded');
    toggleUploadBtn.textContent = 'Upload ▼';
  } else {
    uploadForm.classList.add('expanded');
    toggleUploadBtn.textContent = 'Upload ▲';
  }
});

// Hide URL bar on iPad Safari
window.addEventListener('load', function() {
  setTimeout(function() { window.scrollTo(0, 1); }, 0);
});

window.addEventListener('orientationchange', function() {
  setTimeout(function() { window.scrollTo(0, 1); }, 0);
});

// Initial load
fetchImages();
setInterval(fetchImages, 30000); // refresh images every 30 seconds
startSlideshow();
