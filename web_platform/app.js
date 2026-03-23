// Game Platform Controller
const gameModal = document.getElementById('gameModal');

// Game Configuration
const games = {
    'shoulder-rehab': {
        title: 'Shoulder & Posture Rehab',
        file: 'games/shoulder_rehab.html',
        description: 'Full-body pose tracking for rehabilitation exercises'
    },
    'object-catch': {
        title: 'Pinch & Catch Challenge',
        file: 'games/object_catch.html',
        description: 'Hand tracking game for coordination'
    },
    'finger-trainer': {
        title: 'Finger Coordination Trainer',
        file: 'games/finger_trainer.html',
        description: 'Advanced finger dexterity exercises'
    },
    'mirror-moves': {
        title: 'Mirror Moves',
        file: 'games/mirror_moves_prototype.html',
        description: 'Guided full-body pose challenge with hold scoring'
    },
    'shape-tracing': {
        title: 'Shape Tracing',
        file: 'games/shape_tracing_prototype.html',
        description: 'Trace guided shapes with hand tracking'
    }
};

// Launch Game
function launchGame(gameId) {
    const game = games[gameId];
    if (!game) {
        console.error('Game not found:', gameId);
        return;
    }

    // Show modal
    gameModal.classList.add('active');
    
    // Load game in iframe
    const gameContainer = document.getElementById('gameContainer');
    gameContainer.innerHTML = `
        <iframe src="${game.file}" 
                title="${game.title}"
                allow="camera; microphone"
                allowfullscreen>
        </iframe>
    `;

    // Prevent body scroll
    document.body.style.overflow = 'hidden';
}

// Close Game
function closeGame() {
    gameModal.classList.remove('active');
    document.getElementById('gameContainer').innerHTML = '';
    document.body.style.overflow = 'auto';
}

// Close modal on outside click
gameModal.addEventListener('click', (e) => {
    if (e.target === gameModal) {
        closeGame();
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && gameModal.classList.contains('active')) {
        closeGame();
    }
});

// Add New Game Modal
function showAddGameModal() {
    alert('To add a new game:\n\n1. Create an HTML file in the games/ folder\n2. Add game card to index.html\n3. Update games object in app.js\n\nSee DEVELOPER_GUIDE.md for details!');
}

// Smooth scroll for navigation
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        if (link.getAttribute('href').startsWith('#')) {
            e.preventDefault();
            const target = document.querySelector(link.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    });
});

// Add hover effects to game cards
document.querySelectorAll('.game-card').forEach(card => {
    card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-10px)';
    });
    
    card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
});

// Console welcome message
console.log('%c🏥 Rehab Games Platform', 'font-size: 20px; font-weight: bold; color: #6366f1;');
console.log('%cVersion 1.0 - AI-Powered Rehabilitation Games', 'font-size: 12px; color: #94a3b8;');
