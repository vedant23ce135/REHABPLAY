# 🎮 Adding New Games - Quick Guide

This guide shows you how to quickly add a new game to the platform.

---

## Method 1: Copy and Modify Template (Easiest)

1. **Copy the template:**
   ```powershell
   cp web_platform/games/GAME_TEMPLATE.html web_platform/games/my_game.html
   ```

2. **Customize your game:**
   - Open `my_game.html`
   - Replace `YOUR_GAME_NAME`
   - Replace `YOUR_COLOR_1` and `YOUR_COLOR_2` with your colors
   - Add your game logic in the `onResults()` function

3. **Add to platform:**
   
   **a) Update `index.html`** - Add game card:
   ```html
   <div class="game-card" data-game="my-game">
       <div class="game-thumbnail my-game-bg">
           <div class="game-icon">🎮</div>
       </div>
       <div class="game-info">
           <h4>My Awesome Game</h4>
           <p>Description of what your game does</p>
           <div class="game-meta">
               <span class="difficulty easy">Easy</span>
               <span class="type">Hand Tracking</span>
           </div>
           <button class="play-btn" onclick="launchGame('my-game')">
               <span>▶</span> Play Now
           </button>
       </div>
   </div>
   ```
   
   **b) Update `app.js`** - Register the game:
   ```javascript
   const games = {
       // ... existing games
       'my-game': {
           title: 'My Awesome Game',
           file: 'games/my_game.html',
           description: 'Game description'
       }
   };
   ```
   
   **c) Update `styles.css`** - Add gradient:
   ```css
   .my-game-bg {
       background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%);
   }
   ```

4. **Test it:**
   - Refresh the platform
   - Click on your new game card
   - Allow camera access
   - Start playing!

---

## Method 2: From Scratch

### Step 1: Create HTML File

Create `web_platform/games/your_game.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Your Game</title>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
    <style>
        body { margin: 0; overflow: hidden; }
        #canvas { width: 100vw; height: 100vh; }
    </style>
</head>
<body>
    <canvas id="canvas"></canvas>
    <script>
        // Your game code here
    </script>
</body>
</html>
```

### Step 2: Choose Tracking Type

**For Hand Tracking:**
```javascript
const hands = new Hands({
    locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
});

hands.setOptions({
    maxNumHands: 2,
    minDetectionConfidence: 0.7,
    minTrackingConfidence: 0.7
});

hands.onResults(onResults);
```

**For Pose Tracking:**
```javascript
const pose = new Pose({
    locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`
});

pose.setOptions({
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5
});

pose.onResults(onResults);
```

### Step 3: Implement Game Logic

```javascript
function onResults(results) {
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw video
    ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);
    
    // Hand tracking
    if (results.multiHandLandmarks) {
        for (const landmarks of results.multiHandLandmarks) {
            // Get finger positions
            const indexTip = landmarks[8];
            const thumbTip = landmarks[4];
            
            // Your game logic here
            // Example: check gestures, detect collisions, etc.
        }
    }
    
    // Pose tracking
    if (results.poseLandmarks) {
        const shoulder = results.poseLandmarks[12];
        const elbow = results.poseLandmarks[14];
        // Your game logic here
    }
}
```

---

## MediaPipe Landmark Reference

### Hand Landmarks (0-20):
- **0:** Wrist
- **4:** Thumb tip
- **8:** Index finger tip
- **12:** Middle finger tip
- **16:** Ring finger tip
- **20:** Pinky tip

### Pose Landmarks (0-32):
- **11-12:** Shoulders
- **13-14:** Elbows
- **15-16:** Wrists
- **23-24:** Hips
- **25-26:** Knees
- **27-28:** Ankles

---

## Game Ideas

### Easy Games (Beginner):
1. **Balloon Pop** - Touch balloons with finger tips
2. **Follow the Dot** - Track a moving target with hand
3. **Simple Catch** - Catch falling objects
4. **Color Match** - Touch objects of matching color

### Medium Games:
1. **Gesture Simon Says** - Copy gesture sequences
2. **Balance Challenge** - Hold pose for time
3. **Speed Tapper** - Quick hand movements
4. **Precision Reach** - Touch small targets

### Advanced Games:
1. **Multi-hand Coordination** - Use both hands independently
2. **Complex Poses** - Full body movements
3. **Rhythm Game** - Time movements to beat
4. **Reaction Training** - Quick response to visual cues

---

## Testing Checklist

- [ ] Camera loads correctly
- [ ] Landmarks detected accurately
- [ ] Game responds to movements
- [ ] UI elements visible and functional
- [ ] Score/feedback working
- [ ] No console errors
- [ ] Works in different lighting conditions
- [ ] Responsive on different screen sizes

---

## Tips for Good Games

1. **Start Simple** - One interaction type is enough
2. **Clear Instructions** - Tell users what to do
3. **Visual Feedback** - Show when actions are recognized
4. **Progressive Difficulty** - Start easy, get harder
5. **Audio Feedback** - Consider adding sounds
6. **Test with Users** - Get real patient/user feedback
7. **Accessibility** - Consider different ability levels

---

## Troubleshooting

**Game not launching:**
- Check file path in app.js
- Verify HTML file exists
- Check browser console for errors

**Tracking not working:**
- Ensure good lighting
- Check camera permissions
- Verify MediaPipe CDN loading
- Lower detection confidence

**Poor performance:**
- Reduce `modelComplexity` to 0
- Lower camera resolution
- Limit frame rate
- Simplify drawing operations

---

## Example: Simple Balloon Pop Game

```javascript
// Game state
const balloons = [];
let score = 0;

// Create balloon
function createBalloon() {
    return {
        x: Math.random() * canvas.width,
        y: canvas.height,
        radius: 30,
        speed: 2
    };
}

// Update game
function onResults(results) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Update balloons
    balloons.forEach(balloon => {
        balloon.y -= balloon.speed;
        
        // Draw balloon
        ctx.beginPath();
        ctx.arc(balloon.x, balloon.y, balloon.radius, 0, Math.PI * 2);
        ctx.fillStyle = 'red';
        ctx.fill();
        
        // Check collision with finger
        if (results.multiHandLandmarks) {
            const fingertip = results.multiHandLandmarks[0][8];
            const fx = fingertip.x * canvas.width;
            const fy = fingertip.y * canvas.height;
            
            const dist = Math.sqrt(
                (fx - balloon.x) ** 2 + 
                (fy - balloon.y) ** 2
            );
            
            if (dist < balloon.radius) {
                score += 10;
                balloon.y = -100; // Remove balloon
            }
        }
    });
    
    // Add new balloons
    if (Math.random() < 0.02) {
        balloons.push(createBalloon());
    }
    
    // Draw score
    ctx.fillStyle = 'white';
    ctx.font = '30px Arial';
    ctx.fillText('Score: ' + score, 20, 50);
}
```

---

## Resources

- **MediaPipe Docs:** https://google.github.io/mediapipe/
- **Canvas API:** https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API
- **Game Examples:** Check existing games in `web_platform/games/`

---

**Happy Game Development! 🎮**
