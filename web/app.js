// API Configuration
const API_BASE = 'http://localhost:8000/api/v1';

// Unicode chess pieces
const PIECES = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
};

// Game state
let currentGameId = null;
let currentObservation = null;
let gameInterval = null;
let isGameRunning = false;
let moveCount = 0;
let lastFromSquare = null;
let lastToSquare = null;

// Audio commentary state
let audioContext = null;
let audioCurrentTime = 0;
let commentaryEnabled = true;  // Auto-enabled
let audioEventSource = null;
let scheduledAudioSources = [];  // Track all scheduled audio sources

// DOM Elements
const startButton = document.getElementById('startGame');
const stopButton = document.getElementById('stopGame');
const chessBoard = document.getElementById('chessBoard');
const moveHistory = document.getElementById('moveHistory');
const statusText = document.getElementById('statusText');
const gameIdEl = document.getElementById('gameId');
const currentTurnEl = document.getElementById('currentTurn');
const moveCountEl = document.getElementById('moveCount');
const lastMoveEl = document.getElementById('lastMove');
const boardFenEl = document.getElementById('boardFen');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeBoard();
    loadServerStats();
    initializeAudioCommentary();
    
    startButton.addEventListener('click', startNewGame);
    stopButton.addEventListener('click', stopGame);
    
    // Update stats every 5 seconds
    setInterval(loadServerStats, 5000);
});

// Initialize empty board
function initializeBoard() {
    chessBoard.innerHTML = '';
    for (let rank = 7; rank >= 0; rank--) {
        for (let file = 0; file < 8; file++) {
            const square = document.createElement('div');
            square.className = `square ${(rank + file) % 2 === 0 ? 'dark' : 'light'}`;
            square.dataset.rank = rank;
            square.dataset.file = file;
            chessBoard.appendChild(square);
        }
    }
}

// Parse FEN and render board
function renderBoard(fen) {
    const parts = fen.split(' ');
    const position = parts[0];
    const ranks = position.split('/');
    
    const squares = chessBoard.querySelectorAll('.square');
    squares.forEach(sq => {
        sq.textContent = '';
        sq.classList.remove('last-move');
    });
    
    // Render from rank 8 (index 0 in FEN) down to rank 1 (index 7 in FEN)
    let squareIndex = 0;
    for (let rankIndex = 0; rankIndex < 8; rankIndex++) {
        const rankStr = ranks[rankIndex]; // FEN rank string (rank 8 is index 0)
        
        for (let charIndex = 0; charIndex < rankStr.length; charIndex++) {
            const char = rankStr[charIndex];
            
            if (char >= '1' && char <= '8') {
                // Empty squares - skip this many squares
                const emptyCount = parseInt(char);
                squareIndex += emptyCount;
            } else if (PIECES[char]) {
                // Piece - place it on the current square
                const square = squares[squareIndex];
                square.textContent = PIECES[char];
                squareIndex++;
            }
        }
    }
    
    boardFenEl.textContent = `FEN: ${fen}`;
}

// Highlight last move
function highlightLastMove(uciMove) {
    if (!uciMove || uciMove.length < 4) return;
    
    const fromFile = uciMove.charCodeAt(0) - 97; // a=0, b=1, etc.
    const fromRank = parseInt(uciMove[1]) - 1;
    const toFile = uciMove.charCodeAt(2) - 97;
    const toRank = parseInt(uciMove[3]) - 1;
    
    const squares = chessBoard.querySelectorAll('.square');
    squares.forEach(square => {
        const rank = parseInt(square.dataset.rank);
        const file = parseInt(square.dataset.file);
        
        if ((rank === fromRank && file === fromFile) || 
            (rank === toRank && file === toFile)) {
            square.classList.add('last-move');
        }
    });
}

// Add move to history
function addMoveToHistory(moveNum, player, san, uci) {
    const moveEntry = document.createElement('div');
    moveEntry.className = 'move-entry';
    
    const detailId = `move-detail-${moveCount}`;
    
    // Extract piece from SAN notation (first char if uppercase, else pawn)
    let pieceSymbol = '♙'; // default pawn
    if (san[0] >= 'A' && san[0] <= 'Z') {
        const pieceMap = {
            'K': player === 'white' ? '♔' : '♚',
            'Q': player === 'white' ? '♕' : '♛',
            'R': player === 'white' ? '♖' : '♜',
            'B': player === 'white' ? '♗' : '♝',
            'N': player === 'white' ? '♘' : '♞'
        };
        pieceSymbol = pieceMap[san[0]] || pieceSymbol;
    } else {
        pieceSymbol = player === 'white' ? '♙' : '♟';
    }
    
    // Check if move resulted in check or checkmate
    const isCheck = san.includes('+') ? ' ✓' : '';
    const isCheckmate = san.includes('#') ? ' #' : '';
    
    moveEntry.innerHTML = `
        <div class="move-main" onclick="document.getElementById('${detailId}').classList.toggle('hidden')">
            <span class="move-number">${moveNum}.</span>
            <span class="move-player ${player}">${pieceSymbol}</span>
            <span class="move-notation">${san}${isCheck}${isCheckmate}</span>
            <span class="move-toggle">▼</span>
        </div>
        <div id="${detailId}" class="move-details hidden">
            <div><strong>Move:</strong> ${uci}</div>
            <div><strong>Player:</strong> ${player.charAt(0).toUpperCase() + player.slice(1)}</div>
            <div><strong>Position After:</strong> ${currentObservation?.board_state?.fen?.split(' ').slice(0, 2).join(' ') || 'N/A'}</div>
            <div><strong>Available Moves:</strong> ${currentObservation?.legal_moves?.length || 0} legal moves</div>
        </div>
    `;
    moveHistory.appendChild(moveEntry);
    moveHistory.scrollTop = moveHistory.scrollHeight;
}

// Start new game
async function startNewGame() {
    console.log('startNewGame called');
    try {
        startButton.disabled = true;
        stopButton.disabled = false;
        isGameRunning = true;
        moveHistory.innerHTML = '';
        moveCount = 0;
        
        statusText.textContent = 'Initializing...';
        statusText.className = 'status-active';
        
        const whiteAgent = document.getElementById('whiteAgent').value;
        const blackAgent = document.getElementById('blackAgent').value;
        const useLLM = document.getElementById('useLLM').checked;
        
        console.log('Game config:', { whiteAgent, blackAgent, useLLM });
        
        // Reset game
        const resetResponse = await fetch(`${API_BASE}/reset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                white_agent_id: whiteAgent,
                black_agent_id: blackAgent
            })
        });
        
        if (!resetResponse.ok) {
            throw new Error('Failed to initialize game');
        }
        
        const resetData = await resetResponse.json();
        console.log('Game initialized:', resetData.game_id);
        currentGameId = resetData.game_id;
        currentObservation = resetData.observation;
        gameIdEl.textContent = currentGameId;
        
        // Render initial board
        const fen = resetData.observation.board_state.fen;
        renderBoard(fen);
        
        // Play energetic game introduction
        await playGameIntroduction(whiteAgent, blackAgent);
        
        statusText.textContent = 'Game Running';
        currentTurnEl.textContent = 'White';
        moveCountEl.textContent = '0';
        lastMoveEl.textContent = '-';
        
        console.log('Starting game loop, useLLM:', useLLM);
        // Start game loop
        if (useLLM) {
            console.log('Using LLM agents');
            playGameWithAgents();
        } else {
            console.log('Using random moves');
            playGameWithRandom();
        }
        
    } catch (error) {
        console.error('Error starting game:', error);
        statusText.textContent = 'Error: ' + error.message;
        statusText.className = 'status-error';
        startButton.disabled = false;
        stopButton.disabled = true;
        isGameRunning = false;
    }
}

// Play game with LLM agents (slower but intelligent)
async function playGameWithAgents() {
    const maxMoves = parseInt(document.getElementById('maxMoves').value);
    
    while (isGameRunning && moveCount < maxMoves) {
        try {
            // Check if game was stopped
            if (!isGameRunning) {
                break;
            }
            
            // Get current state
            const stateResponse = await fetch(`${API_BASE}/state/${currentGameId}`);
            const state = await stateResponse.json();
            
            if (state.is_terminal) {
                endGame(state.result);
                break;
            }
            
            currentTurnEl.textContent = state.current_player === 'white' ? 'White' : 'Black';
            
            // Check again before making move
            if (!isGameRunning) {
                break;
            }
            
            // Use agent to generate and execute move
            statusText.textContent = `Thinking... (${state.current_player})`;
            statusText.className = 'status-thinking';
            
            await playAgentMove();
            
            // Check if game was stopped during the move
            if (!isGameRunning) {
                break;
            }
            
            // Wait a bit before next move so user can see
            await new Promise(resolve => setTimeout(resolve, 1000));
            
        } catch (error) {
            console.error('Error in game loop:', error);
            statusText.textContent = 'Error: ' + error.message;
            statusText.className = 'status-error';
            stopGame();
            break;
        }
    }
    
    if (isGameRunning && moveCount >= maxMoves) {
        endGame('Max moves reached');
    }
}

// Execute a move using LLM agent
async function playAgentMove() {
    try {
        const startTime = Date.now();
        
        // Call agent-move endpoint (this takes 2-30 seconds)
        const stepResponse = await fetch(`${API_BASE}/agent-move`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                game_id: currentGameId
            })
        });
        
        if (!stepResponse.ok) {
            const error = await stepResponse.json();
            throw new Error(error.detail || 'Agent move failed');
        }
        
        const stepData = await stepResponse.json();
        const elapsedTime = ((Date.now() - startTime) / 1000).toFixed(1);
        
        // Store new observation for random fallback if needed
        currentObservation = stepData.observation;
        
        // Update board
        const fen = stepData.observation.board_state.fen;
        renderBoard(fen);
        highlightLastMove(stepData.info.last_move);
        
        // Update UI
        moveCount++;
        moveCountEl.textContent = moveCount;
        lastMoveEl.textContent = `${stepData.info.san_move} (${elapsedTime}s)`;
        statusText.textContent = 'Game Running';
        statusText.className = 'status-running';
        
        const moveNum = moveCount;
        const player = stepData.observation.board_state.current_player === 'black' ? 'white' : 'black';
        addMoveToHistory(moveNum, player, stepData.info.san_move, stepData.info.last_move);
        
        // Play audio commentary with full context
        await playCommentary({
            ...stepData.info,
            player: player,
            move_number: moveNum,
            fen: stepData.observation.board_state.fen
        });
        
        // Check if game ended
        if (stepData.terminated) {
            const result = stepData.info.result || 'Game Over';
            endGame(result);
        }
        
    } catch (error) {
        console.error('Error making agent move:', error);
        statusText.textContent = 'Agent error: ' + error.message;
        statusText.className = 'status-error';
        throw error;
    }
}

// Play game with random moves (fast)
async function playGameWithRandom() {
    const maxMoves = parseInt(document.getElementById('maxMoves').value);
    
    gameInterval = setInterval(async () => {
        if (!isGameRunning || moveCount >= maxMoves) {
            clearInterval(gameInterval);
            gameInterval = null;
            if (moveCount >= maxMoves) {
                endGame('Max moves reached');
            }
            return;
        }
        
        await playRandomMove();
    }, 500); // Move every 500ms
}

// Execute a random move
async function playRandomMove() {
    try {
        // Check if we have legal moves from last observation
        if (!currentObservation || !currentObservation.legal_moves) {
            endGame('No legal moves available');
            return;
        }
        
        const legalMoves = currentObservation.legal_moves;
        if (legalMoves.length === 0) {
            endGame('No legal moves available');
            return;
        }
        
        // Pick a random legal move
        const randomMove = legalMoves[Math.floor(Math.random() * legalMoves.length)];
        
        // Make move
        const stepResponse = await fetch(`${API_BASE}/step`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                game_id: currentGameId,
                action: randomMove
            })
        });
        
        if (!stepResponse.ok) {
            // Move failed, try to continue
            return;
        }
        
        const stepData = await stepResponse.json();
        
        // Store new observation for next move
        currentObservation = stepData.observation;
        
        // Update board
        const fen = stepData.observation.board_state.fen;
        renderBoard(fen);
        highlightLastMove(randomMove);
        
        // Update UI
        moveCount++;
        moveCountEl.textContent = moveCount;
        lastMoveEl.textContent = stepData.info.san_move;
        
        const moveNum = moveCount;
        const player = stepData.observation.board_state.current_player === 'black' ? 'white' : 'black';
        addMoveToHistory(moveNum, player, stepData.info.san_move, randomMove);
        
        // Play audio commentary with full context
        await playCommentary({
            ...stepData.info,
            player: player,
            move_number: moveNum,
            fen: stepData.observation.board_state.fen
        });
        
        // Check if game ended
        if (stepData.terminated) {
            const result = stepData.info.result || 'Game Over';
            endGame(result);
        }
        
    } catch (error) {
        console.error('Error making move:', error);
    }
}

// Stop game
function stopGame() {
    isGameRunning = false;
    if (gameInterval) {
        clearInterval(gameInterval);
        gameInterval = null;
    }
    
    // Close audio commentary stream
    if (audioEventSource) {
        audioEventSource.close();
        audioEventSource = null;
        const statusEl = document.getElementById('commentaryStatus');
        if (statusEl && commentaryEnabled) {
            statusEl.textContent = 'Stopped';
        }
    }
    
    // Stop all scheduled audio sources immediately
    scheduledAudioSources.forEach(source => {
        try {
            source.stop();
        } catch (e) {
            // Source may have already finished or been stopped
        }
    });
    scheduledAudioSources = [];
    
    // Reset audio timing
    if (audioContext) {
        audioCurrentTime = audioContext.currentTime;
    }
    
    startButton.disabled = false;
    stopButton.disabled = true;
    statusText.textContent = 'Stopped';
    statusText.className = 'status-completed';
}

// End game
function endGame(result) {
    stopGame();
    statusText.textContent = `Game Over: ${result}`;
    statusText.className = 'status-completed';
}

// Load server stats
async function loadServerStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const stats = await response.json();
        
        document.getElementById('totalGames').textContent = stats.total_games;
        document.getElementById('activeGames').textContent = stats.active_games;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Initialize audio commentary system
function initializeAudioCommentary() {
    const toggleBtn = document.getElementById('toggleCommentary');
    const statusEl = document.getElementById('commentaryStatus');
    
    // Set initial state to enabled
    if (toggleBtn) {
        toggleBtn.textContent = 'Disable Commentary';
        toggleBtn.className = 'btn btn-warning';
        toggleBtn.addEventListener('click', toggleCommentary);
    }
    
    if (statusEl) {
        statusEl.textContent = 'Enabled';
        statusEl.className = 'status-active';
    }
}

// Toggle audio commentary on/off
function toggleCommentary() {
    commentaryEnabled = !commentaryEnabled;
    const toggleBtn = document.getElementById('toggleCommentary');
    const statusEl = document.getElementById('commentaryStatus');
    
    if (toggleBtn) {
        toggleBtn.textContent = commentaryEnabled ? 'Disable Commentary' : 'Enable Commentary';
        toggleBtn.className = commentaryEnabled ? 'btn btn-warning' : 'btn btn-primary';
    }
    
    if (statusEl) {
        statusEl.textContent = commentaryEnabled ? 'Enabled' : 'Disabled';
        statusEl.className = commentaryEnabled ? 'status-active' : 'status-stopped';
    }
    
    if (!commentaryEnabled && audioEventSource) {
        audioEventSource.close();
        audioEventSource = null;
    }
}

// Play energetic game introduction
async function playGameIntroduction(whiteAgent, blackAgent) {
    if (!commentaryEnabled) return;
    
    return new Promise((resolve) => {
        try {
            // Initialize Web Audio API if needed
            if (!audioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                audioCurrentTime = audioContext.currentTime;
            }
            
            const statusEl = document.getElementById('commentaryStatus');
            const transcriptEl = document.getElementById('commentaryTranscript');
            
            if (statusEl) statusEl.textContent = '🎙️ Introduction playing...';
            if (transcriptEl) transcriptEl.textContent = '';
            
            // Close existing connection
            if (audioEventSource) {
                audioEventSource.close();
            }
            
            // Connect to introduction SSE stream
            const url = `${API_BASE}/commentary/introduction?white_agent=${encodeURIComponent(whiteAgent)}&black_agent=${encodeURIComponent(blackAgent)}`;
            audioEventSource = new EventSource(url);
            
            audioEventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.audio) {
                        // Decode base64 audio (PCM16 at 24kHz)
                        const audioData = atob(data.audio);
                        const audioArray = new Int16Array(audioData.length / 2);
                        for (let i = 0; i < audioData.length; i += 2) {
                            audioArray[i/2] = (audioData.charCodeAt(i+1) << 8) | audioData.charCodeAt(i);
                        }
                        
                        // Convert PCM16 to Float32Array
                        const floatArray = new Float32Array(audioArray.length);
                        for (let i = 0; i < audioArray.length; i++) {
                            floatArray[i] = audioArray[i] / 32768.0;
                        }
                        
                        // Create audio buffer at 24kHz
                        const audioBuffer = audioContext.createBuffer(1, floatArray.length, 24000);
                        audioBuffer.getChannelData(0).set(floatArray);
                        
                        // Schedule sequential playback
                        const source = audioContext.createBufferSource();
                        source.buffer = audioBuffer;
                        source.connect(audioContext.destination);
                        
                        const currentTime = audioContext.currentTime;
                        const startTime = Math.max(currentTime, audioCurrentTime);
                        source.start(startTime);
                        
                        // Track source so it can be stopped
                        scheduledAudioSources.push(source);
                        source.onended = () => {
                            const index = scheduledAudioSources.indexOf(source);
                            if (index > -1) scheduledAudioSources.splice(index, 1);
                        };
                        
                        audioCurrentTime = startTime + audioBuffer.duration;
                    }
                    
                    if (data.text && transcriptEl) {
                        transcriptEl.textContent += data.text;
                    }
                    
                    if (data.done) {
                        audioEventSource.close();
                        audioEventSource = null;
                        if (statusEl) statusEl.textContent = 'Ready';
                        
                        // Wait for audio to finish playing, then resolve
                        const remainingTime = Math.max(0, audioCurrentTime - audioContext.currentTime);
                        setTimeout(resolve, remainingTime * 1000);
                    }
                    
                    if (data.error) {
                        console.error('Introduction error:', data.error);
                        audioEventSource.close();
                        audioEventSource = null;
                        if (statusEl) statusEl.textContent = 'Error';
                        resolve(); // Continue game even if introduction fails
                    }
                    
                } catch (err) {
                    console.error('Error processing introduction event:', err);
                }
            };
            
            audioEventSource.onerror = (error) => {
                console.error('Introduction stream error:', error);
                audioEventSource.close();
                audioEventSource = null;
                if (statusEl) statusEl.textContent = 'Error';
                resolve(); // Continue game even if introduction fails
            };
            
        } catch (error) {
            console.error('Error playing introduction:', error);
            resolve(); // Continue game even if introduction fails
        }
    });
}

// Play audio commentary for a move
async function playCommentary(moveInfo) {
    if (!commentaryEnabled) return;
    
    try {
        // Initialize Web Audio API if needed
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            audioCurrentTime = audioContext.currentTime;
        }
        
        const statusEl = document.getElementById('commentaryStatus');
        const transcriptEl = document.getElementById('commentaryTranscript');
        
        if (statusEl) statusEl.textContent = 'Streaming...';
        if (transcriptEl) transcriptEl.textContent = '';
        
        // Close existing connection
        if (audioEventSource) {
            audioEventSource.close();
        }
        
        // Build query parameters from move info
        const params = new URLSearchParams({
            san_move: moveInfo.san_move || 'Unknown',
            player: moveInfo.player || 'white',
        });
        
        // Add evaluation if available
        if (moveInfo.evaluation !== undefined && moveInfo.evaluation !== null) {
            params.append('evaluation', moveInfo.evaluation);
        }
        
        // Add evaluation change if available
        if (moveInfo.eval_change !== undefined && moveInfo.eval_change !== null) {
            params.append('eval_change', moveInfo.eval_change);
        }
        
        // Add FEN if available
        if (moveInfo.fen) {
            params.append('fen', moveInfo.fen);
        }
        
        // Add move number if available
        if (moveInfo.move_number !== undefined) {
            params.append('move_number', moveInfo.move_number);
        }
        
        // Determine trigger type based on evaluation change
        let trigger = 'TACTICAL';  // Default to TACTICAL for generic moves
        if (moveInfo.eval_change !== undefined && moveInfo.eval_change !== null) {
            const absChange = Math.abs(moveInfo.eval_change);
            if (absChange >= 300) {
                trigger = moveInfo.eval_change < 0 ? 'BLUNDER' : 'BRILLIANT';
            } else if (absChange >= 100) {
                trigger = 'TACTICAL';
            }
        }
        params.append('trigger', trigger);
        
        // Connect to SSE stream with move data
        const url = `${API_BASE}/commentary/stream?${params.toString()}`;
        console.log('Requesting commentary:', url);
        
        audioEventSource = new EventSource(url);
        let buffer = '';
        
        audioEventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                
                if (data.audio) {
                    // Decode base64 audio (PCM16 at 24kHz)
                    const audioData = atob(data.audio);
                    const audioArray = new Int16Array(audioData.length / 2);
                    for (let i = 0; i < audioData.length; i += 2) {
                        audioArray[i/2] = (audioData.charCodeAt(i+1) << 8) | audioData.charCodeAt(i);
                    }
                    
                    // Convert PCM16 to Float32Array
                    const floatArray = new Float32Array(audioArray.length);
                    for (let i = 0; i < audioArray.length; i++) {
                        floatArray[i] = audioArray[i] / 32768.0;
                    }
                    
                    // Create audio buffer at 24kHz
                    const audioBuffer = audioContext.createBuffer(1, floatArray.length, 24000);
                    audioBuffer.getChannelData(0).set(floatArray);
                    
                    // Schedule sequential playback
                    const source = audioContext.createBufferSource();
                    source.buffer = audioBuffer;
                    source.connect(audioContext.destination);
                    
                    const currentTime = audioContext.currentTime;
                    const startTime = Math.max(currentTime, audioCurrentTime);
                    source.start(startTime);
                    
                    // Track source so it can be stopped
                    scheduledAudioSources.push(source);
                    source.onended = () => {
                        const index = scheduledAudioSources.indexOf(source);
                        if (index > -1) scheduledAudioSources.splice(index, 1);
                    };
                    
                    audioCurrentTime = startTime + audioBuffer.duration;
                    
                    if (statusEl) statusEl.textContent = 'Playing...';
                }
                
                if (data.text && transcriptEl) {
                    transcriptEl.textContent += data.text;
                }
                
                if (data.done) {
                    audioEventSource.close();
                    audioEventSource = null;
                    if (statusEl) statusEl.textContent = 'Ready';
                }
                
                if (data.error) {
                    console.error('Commentary error:', data.error);
                    audioEventSource.close();
                    audioEventSource = null;
                    if (statusEl) statusEl.textContent = 'Error';
                    if (transcriptEl) transcriptEl.textContent = `Error: ${data.error}`;
                }
            } catch (e) {
                console.error('Error processing audio event:', e);
            }
        };
        
        audioEventSource.onerror = (error) => {
            console.error('SSE connection error:', error);
            audioEventSource.close();
            audioEventSource = null;
            if (statusEl) statusEl.textContent = 'Connection Error';
        };
        
    } catch (error) {
        console.error('Error playing commentary:', error);
    }
}
