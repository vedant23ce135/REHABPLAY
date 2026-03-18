# 🏥 Rehab Games Platform - Developer Guide

## Overview
A professional web platform for rehabilitation games using AI-powered pose and hand tracking. Perfect for physiotherapy patients and special education students.

---

## 🚀 Quick Start

### **Approach 1: Pure Web (Recommended)**
The games run directly in the browser using MediaPipe Web SDK - no Python server needed!

1. **Open the platform:**
   ```powershell
   cd web_platform
   # Open index.html in your browser
   # Or use a simple HTTP server:
   python -m http.server 8000
   ```

2. **Access in browser:**
   - Go to `http://localhost:8000`
   - Click on any game card to play
   - Allow camera access when prompted

**Advantages:**
- ✅ No backend required
- ✅ Runs client-side (fast & scalable)
- ✅ Easy to deploy (any static hosting)
- ✅ No server costs

---

### **Approach 2: Flask Backend (Python Games)**
Run original Python games through a Flask server.

1. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Start Flask server:**
   ```powershell
   python flask_server.py
   ```

3. **Access in browser:**
   - Go to `http://localhost:5000`

**Advantages:**
- ✅ Keeps original Python code
- ✅ Can add more Python games easily
- ❌ Requires server resources
- ❌ More complex deployment

---

## 📁 Project Structure

```
Newgame/
│
├── web_platform/              # Web Platform (Approach 1)
│   ├── index.html            # Main dashboard
│   ├── styles.css            # Platform styling
│   ├── app.js                # Platform logic
│   └── games/                # Individual game files
│       ├── shoulder_rehab.html
│       ├── object_catch.html
│       └── finger_trainer.html
│
├── rehabplay.py              # Original Python game 1
├── object_catch_game.py      # Original Python game 2
├── 1one.py                   # Original Python game 3
│
├── flask_server.py           # Flask backend (Approach 2)
├── requirements.txt          # Python dependencies
└── DEVELOPER_GUIDE.md        # This file
```

---

## 🎮 Adding New Games

### **Method 1: Add Web Game (Recommended)**

1. **Create new game HTML file:**
   ```html
   <!-- web_platform/games/my_new_game.html -->
   <!DOCTYPE html>
   <html>
   <head>
       <title>My New Game</title>
       <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
   </head>
   <body>
       <!-- Your game code here -->
   </body>
   </html>
   ```

2. **Add game card to `index.html`:**
   ```html
   <div class="game-card" data-game="my-new-game">
       <div class="game-thumbnail new-bg">
           <div class="game-icon">🎲</div>
       </div>
       <div class="game-info">
           <h4>My New Game</h4>
           <p>Game description here</p>
           <div class="game-meta">
               <span class="difficulty easy">Easy</span>
               <span class="type">Hand Tracking</span>
           </div>
           <button class="play-btn" onclick="launchGame('my-new-game')">
               <span>▶</span> Play Now
           </button>
       </div>
   </div>
   ```

3. **Register game in `app.js`:**
   ```javascript
   const games = {
       // ... existing games
       'my-new-game': {
           title: 'My New Game',
           file: 'games/my_new_game.html',
           description: 'Game description'
       }
   };
   ```

4. **Add gradient background in `styles.css`:**
   ```css
   .new-bg {
       background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
   }
   ```

### **Method 2: Add Python Game to Flask**

1. Create new `.py` file with your game
2. Add to `flask_server.py` game list
3. Update the game processing logic
4. Add game card to web interface

---

## 🎨 Customization

### **Changing Colors**

Edit `styles.css`:
```css
:root {
    --primary: #6366f1;        /* Main color */
    --secondary: #8b5cf6;      /* Secondary color */
    --gradient-1: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

### **Modifying Game Difficulty**

Edit individual game HTML files:
```javascript
// In game file
pose.setOptions({
    minDetectionConfidence: 0.5,  // Lower = easier
    minTrackingConfidence: 0.5    // Lower = less strict
});
```

### **Adding Analytics**

Add to `app.js`:
```javascript
function launchGame(gameId) {
    // Track game launches
    console.log('Game started:', gameId);
    // Add your analytics code here
}
```

---

## 📱 Responsive Design

The platform is fully responsive:
- **Desktop:** Full feature experience
- **Tablet:** Optimized layout
- **Mobile:** Works but camera angle may be challenging

---

## 🔧 Troubleshooting

### **Camera not working:**
- Check browser permissions
- Ensure HTTPS or localhost
- Try different browser (Chrome/Edge recommended)

### **MediaPipe not loading:**
- Check internet connection (CDN required)
- Clear browser cache
- Check browser console for errors

### **Games not launching:**
- Open browser console (F12)
- Check for JavaScript errors
- Verify file paths are correct

---

## 🚀 Deployment

### **Deploy Web Platform (Approach 1):**

**Option A: GitHub Pages**
1. Push `web_platform` folder to GitHub
2. Enable GitHub Pages in repository settings
3. Access via `https://username.github.io/repo-name`

**Option B: Netlify**
1. Drag `web_platform` folder to Netlify
2. Get instant URL
3. Free HTTPS included

**Option C: Vercel**
1. Import GitHub repository
2. Set root to `web_platform`
3. Deploy with one click

### **Deploy Flask Backend (Approach 2):**

**Heroku:**
```bash
# Create Procfile
echo "web: python flask_server.py" > Procfile
heroku create
git push heroku main
```

**AWS/Azure:**
- Use EC2/App Service
- Install dependencies
- Run Flask app with gunicorn

---

## 🛠️ Technologies Used

### **Frontend:**
- HTML5 Canvas
- Vanilla JavaScript
- CSS3 Animations
- MediaPipe Web SDK

### **Backend (Optional):**
- Flask (Python)
- OpenCV
- MediaPipe Python

### **AI/ML:**
- MediaPipe Pose Detection
- MediaPipe Hand Tracking
- Real-time landmark detection

---

## 📊 Performance Tips

1. **Optimize video resolution:**
   ```javascript
   const camera = new Camera(videoElement, {
       width: 1280,  // Lower for better performance
       height: 720
   });
   ```

2. **Reduce model complexity:**
   ```javascript
   hands.setOptions({
       modelComplexity: 0  // 0 = fastest, 1 = balanced
   });
   ```

3. **Limit frame rate:**
   ```javascript
   const fps = 30;  // Lower for mobile devices
   ```

---

## 🎯 Future Enhancements

- [ ] User authentication & profiles
- [ ] Progress tracking & statistics
- [ ] Multiplayer support
- [ ] Custom exercise builder
- [ ] Session recording & replay
- [ ] Therapist dashboard
- [ ] Mobile app (React Native)
- [ ] Offline mode

---

## 📝 License

This platform is designed for educational and rehabilitation purposes.

---

## 🤝 Support

For issues or questions:
1. Check browser console for errors
2. Verify camera permissions
3. Ensure modern browser (Chrome 90+, Edge 90+)
4. Test on different device if issues persist

---

## 📚 Additional Resources

- [MediaPipe Docs](https://google.github.io/mediapipe/)
- [OpenCV Docs](https://docs.opencv.org/)
- [Web APIs - Camera](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)

---

**Made with ❤️ for rehabilitation and accessibility**
