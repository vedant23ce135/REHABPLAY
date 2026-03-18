# 🏥 Rehab Games Platform

**AI-Powered Rehabilitation Games for Physiotherapy & Special Education**

---

## 🌟 Features

✅ **Real-time AI Tracking** - MediaPipe pose and hand detection  
✅ **Multiple Games** - Shoulder rehab, hand coordination, finger training  
✅ **Web-Based** - Play directly in browser, no installation needed  
✅ **Accessible** - Designed for special needs and physiotherapy patients  
✅ **Progress Tracking** - Monitor scores, reps, and improvements  
✅ **Easy to Extend** - Add new games with simple templates  

---

## 🎮 Available Games

### 1. **Shoulder & Posture Rehab** 💪
- Shoulder raise exercises
- Sit-to-stand movements
- Real-time angle feedback
- Rep counting

### 2. **Pinch & Catch Challenge** 🎯
- Hand coordination training
- Pinch gesture detection
- Progressive difficulty levels
- Reaction time improvement

### 3. **Finger Coordination Trainer** 👆
- Individual finger control
- Multi-finger combinations
- 4 difficulty levels
- Dexterity development

---

## 🚀 Quick Start

### **Option 1: Pure Web (Easiest)**

1. Open `web_platform/index.html` in your browser
2. Or run a simple server:
   ```powershell
   cd web_platform
   python -m http.server 8000
   ```
3. Visit `http://localhost:8000`
4. Click on any game and allow camera access

### **Option 2: With Flask Backend**

1. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

2. Run the server:
   ```powershell
   python flask_server.py
   ```

3. Visit `http://localhost:5000`

---

## 📋 Requirements

### **For Web Version (Approach 1):**
- Modern web browser (Chrome/Edge recommended)
- Webcam
- Internet connection (for MediaPipe CDN)

### **For Python Version (Approach 2):**
- Python 3.8+
- Webcam
- Dependencies from `requirements.txt`

---

## 📁 Project Structure

```
Newgame/
├── web_platform/          # Main web platform
│   ├── index.html        # Dashboard
│   ├── styles.css        # Styling
│   ├── app.js            # Platform logic
│   └── games/            # Game files
│       ├── shoulder_rehab.html
│       ├── object_catch.html
│       └── finger_trainer.html
│
├── rehabplay.py          # Original Python games
├── object_catch_game.py
├── 1one.py
│
├── flask_server.py       # Optional Flask backend
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

---

## 🎯 Use Cases

- **Physiotherapy Clinics** - Interactive exercises for patients
- **Special Education** - Engaging activities for motor skill development
- **Home Rehabilitation** - Self-guided exercises
- **Occupational Therapy** - Hand and finger coordination training
- **Elderly Care** - Gentle exercises for mobility maintenance

---

## 💻 Technologies

- **Frontend:** HTML5, CSS3, JavaScript
- **AI/ML:** MediaPipe (Pose & Hands)
- **Backend:** Flask (optional)
- **Video:** OpenCV, WebRTC
- **Deployment:** Static hosting compatible

---

## 🌐 Deployment

### **Easy Deployment (Web Version):**

1. **GitHub Pages:**
   - Push to GitHub
   - Enable Pages in settings
   - Free HTTPS hosting

2. **Netlify/Vercel:**
   - Drag & drop deployment
   - Automatic HTTPS
   - Free tier available

3. **Any Web Server:**
   - Upload `web_platform` folder
   - Configure web server
   - Done!

---

## 🔧 Adding New Games

See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for detailed instructions on:
- Creating new games
- Customizing existing games  
- Modifying difficulty levels
- Adding new features

---

## 📸 Screenshots

```
┌─────────────────────────────────────────┐
│  🏥 Rehab Games Platform               │
│  ───────────────────────────────────    │
│                                          │
│  ┌──────┐  ┌──────┐  ┌──────┐          │
│  │  💪  │  │  🎯  │  │  👆  │          │
│  │Rehab │  │Catch │  │Finger│          │
│  └──────┘  └──────┘  └──────┘          │
│                                          │
│  AI-Powered Rehabilitation Games        │
└─────────────────────────────────────────┘
```

---

## 🤝 Contributing

Interested in adding games or features?
1. Fork the repository
2. Create new game following template
3. Test thoroughly with camera
4. Submit pull request

---

## 📝 License

Created for educational and rehabilitation purposes.

---

## 🆘 Support & Troubleshooting

**Camera not working?**
- Check browser permissions
- Use HTTPS or localhost
- Try Chrome/Edge browsers

**Games not loading?**
- Check internet connection
- Clear browser cache
- Open browser console (F12) for errors

**Performance issues?**
- Lower video resolution in game settings
- Close other browser tabs
- Try different browser
- Ensure good lighting for camera

---

## 📞 Contact

For questions, issues, or feature requests, please open an issue on the repository.

---

## 🙏 Acknowledgments

- **MediaPipe** - Google's ML solutions
- **OpenCV** - Computer vision library
- **Flask** - Python web framework

---

**Made with ❤️ for rehabilitation and accessibility**

*Empowering recovery through gamified exercises* 🌟
