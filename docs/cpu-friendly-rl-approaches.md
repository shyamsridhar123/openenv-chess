# CPU-Friendly RL Self-Play for Chess

Since training large language models requires GPUs you don't have, here are practical alternatives that work on CPU and can still create strong chess agents.

## Table of Contents

1. [MCTS Self-Play (No Neural Network)](#mcts-self-play)
2. [Tabular Q-Learning](#tabular-q-learning)
3. [Small Neural Network with Policy Gradients](#small-network-policy-gradients)
4. [Behavioral Cloning from Stockfish](#behavioral-cloning)
5. [Evolutionary Strategies](#evolutionary-strategies)

---

## 1. MCTS Self-Play (No Neural Network)

Monte Carlo Tree Search is **CPU-only** and very effective for chess. This is how early AlphaGo worked!

### Basic MCTS Implementation

```python
# src/training/mcts_agent.py
import math
import random
from typing import Dict, List, Optional
from src.chess_env import ChessOpenEnv
import chess

class MCTSNode:
    """Node in MCTS tree."""
    
    def __init__(self, state_fen: str, parent=None, action=None):
        self.state_fen = state_fen
        self.parent = parent
        self.action = action  # Move that led to this state
        self.children: Dict[str, 'MCTSNode'] = {}
        self.visits = 0
        self.value = 0.0
        self.untried_actions: List[str] = []
        
    def is_fully_expanded(self):
        return len(self.untried_actions) == 0
    
    def best_child(self, c_param=1.41):
        """Select best child using UCB1 formula."""
        choices_weights = [
            (child.value / child.visits) + 
            c_param * math.sqrt(2 * math.log(self.visits) / child.visits)
            for child in self.children.values()
        ]
        return list(self.children.values())[choices_weights.index(max(choices_weights))]
    
    def expand(self, action: str, env: ChessOpenEnv):
        """Add a new child node."""
        # Apply move
        obs, reward, done, truncated, info = env.step(action)
        child_state = obs["board_state"]["fen"]
        
        # Create child node
        child = MCTSNode(child_state, parent=self, action=action)
        child.untried_actions = obs["legal_moves"].copy()
        self.children[action] = child
        
        return child, reward, done


class MCTSAgent:
    """Chess agent using Monte Carlo Tree Search."""
    
    def __init__(self, num_simulations: int = 100):
        """
        Args:
            num_simulations: Number of MCTS simulations per move (more = stronger but slower)
                            100 = ~1 sec/move on CPU
                            1000 = ~10 sec/move on CPU
        """
        self.num_simulations = num_simulations
    
    def select_move(self, env: ChessOpenEnv) -> str:
        """Select best move using MCTS.
        
        Args:
            env: Current game environment
            
        Returns:
            Best move in UCI format
        """
        state = env.state()
        root = MCTSNode(state["fen"])
        root.untried_actions = env.get_legal_moves()
        
        # Run MCTS simulations
        for _ in range(self.num_simulations):
            node = root
            sim_env = self._clone_env(env)
            
            # Selection: traverse tree to leaf
            while node.is_fully_expanded() and node.children:
                node = node.best_child()
                sim_env.step(node.action)
            
            # Expansion: add new child if not terminal
            if not node.is_fully_expanded():
                action = random.choice(node.untried_actions)
                node.untried_actions.remove(action)
                node, reward, done = node.expand(action, sim_env)
            
            # Simulation: random playout to terminal state
            if not done:
                reward = self._simulate_random_game(sim_env)
            
            # Backpropagation: update all ancestors
            while node is not None:
                node.visits += 1
                node.value += reward
                reward = -reward  # Flip reward for opponent
                node = node.parent
        
        # Choose most visited child
        best_action = max(
            root.children.items(),
            key=lambda x: x[1].visits
        )[0]
        
        return best_action
    
    def _clone_env(self, env: ChessOpenEnv) -> ChessOpenEnv:
        """Create a copy of environment for simulation."""
        state = env.state()
        new_env = ChessOpenEnv()
        new_env.reset(fen=state["fen"])
        return new_env
    
    def _simulate_random_game(self, env: ChessOpenEnv, max_moves: int = 50) -> float:
        """Play random moves until terminal or max_moves.
        
        Returns:
            Reward from perspective of current player
        """
        for _ in range(max_moves):
            legal_moves = env.get_legal_moves()
            if not legal_moves:
                break
            
            action = random.choice(legal_moves)
            obs, reward, done, truncated, info = env.step(action)
            
            if done:
                return reward
        
        # If no terminal state, return draw
        return 0.0


# Example usage
def play_mcts_vs_random():
    """Example: MCTS agent vs random agent."""
    env = ChessOpenEnv()
    mcts_agent = MCTSAgent(num_simulations=100)
    
    obs, info = env.reset()
    
    while True:
        state = env.state()
        current_player = state["current_player"]
        
        if current_player == "white":
            # MCTS plays white
            move = mcts_agent.select_move(env)
            print(f"MCTS: {move}")
        else:
            # Random plays black
            move = random.choice(env.get_legal_moves())
            print(f"Random: {move}")
        
        obs, reward, done, truncated, info = env.step(move)
        
        if done:
            print(f"Game over! Result: {info['result']}")
            break

if __name__ == "__main__":
    play_mcts_vs_random()
```

**Advantages:**
- ✅ **No GPU needed** - Pure CPU
- ✅ **No training** - Works immediately
- ✅ **Scalable** - More simulations = stronger play
- ✅ **Proven** - Foundation of AlphaGo/AlphaZero

**Self-Play Training:**
```python
# Generate training data via MCTS self-play
def generate_mcts_selfplay_games(num_games: int = 100):
    """Generate games using MCTS vs MCTS."""
    agent = MCTSAgent(num_simulations=50)
    
    for game_idx in range(num_games):
        env = ChessOpenEnv()
        obs, info = env.reset()
        game_data = []
        
        while True:
            state = env.state()
            move = agent.select_move(env)
            
            # Store (state, move, outcome) for training
            game_data.append({
                "fen": state["fen"],
                "move": move,
                "player": state["current_player"]
            })
            
            obs, reward, done, truncated, info = env.step(move)
            
            if done:
                # Annotate all moves with final outcome
                for data in game_data:
                    data["outcome"] = reward if data["player"] == "white" else -reward
                break
        
        # Save game for supervised learning
        print(f"Game {game_idx + 1}: {len(game_data)} moves, outcome: {reward}")
```

---

## 2. Tabular Q-Learning

For learning opening principles without neural networks.

### Implementation

```python
# src/training/tabular_q_learning.py
import numpy as np
from collections import defaultdict
from src.chess_env import ChessOpenEnv
import random
import chess

class TabularQLearning:
    """Q-Learning with state-action table (no neural network)."""
    
    def __init__(self, 
                 alpha: float = 0.1,      # Learning rate
                 gamma: float = 0.99,     # Discount factor
                 epsilon: float = 0.1):   # Exploration rate
        self.q_table = defaultdict(lambda: defaultdict(float))
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.game_count = 0
    
    def get_state_key(self, fen: str) -> str:
        """Simplify FEN to reduce state space."""
        # Use only piece positions (ignore castling, en passant, etc.)
        parts = fen.split()
        return parts[0]  # Just piece positions
    
    def select_action(self, env: ChessOpenEnv, training: bool = True) -> str:
        """Select action using epsilon-greedy policy."""
        state = env.state()
        state_key = self.get_state_key(state["fen"])
        legal_moves = env.get_legal_moves()
        
        if not legal_moves:
            return None
        
        # Epsilon-greedy exploration
        if training and random.random() < self.epsilon:
            return random.choice(legal_moves)
        
        # Exploit: choose best known action
        q_values = {
            move: self.q_table[state_key][move] 
            for move in legal_moves
        }
        
        if not q_values:
            return random.choice(legal_moves)
        
        return max(q_values.items(), key=lambda x: x[1])[0]
    
    def update(self, state_fen: str, action: str, reward: float, 
               next_state_fen: str, done: bool):
        """Update Q-value using Q-learning formula."""
        state_key = self.get_state_key(state_fen)
        next_state_key = self.get_state_key(next_state_fen)
        
        # Current Q-value
        current_q = self.q_table[state_key][action]
        
        # Max Q-value for next state
        if done:
            max_next_q = 0
        else:
            next_q_values = self.q_table[next_state_key]
            max_next_q = max(next_q_values.values()) if next_q_values else 0
        
        # Q-learning update
        new_q = current_q + self.alpha * (reward + self.gamma * max_next_q - current_q)
        self.q_table[state_key][action] = new_q
    
    def train_episode(self, env: ChessOpenEnv) -> float:
        """Train on one game episode."""
        obs, info = env.reset()
        total_reward = 0
        
        while True:
            state = env.state()
            state_fen = state["fen"]
            
            # Select action
            action = self.select_action(env, training=True)
            if action is None:
                break
            
            # Take action
            obs, reward, done, truncated, info = env.step(action)
            next_state_fen = obs["board_state"]["fen"]
            
            # Update Q-table
            self.update(state_fen, action, reward, next_state_fen, done)
            
            total_reward += reward
            
            if done:
                break
        
        self.game_count += 1
        return total_reward
    
    def train(self, num_episodes: int = 1000):
        """Train for multiple episodes."""
        for episode in range(num_episodes):
            env = ChessOpenEnv()
            reward = self.train_episode(env)
            
            if (episode + 1) % 100 == 0:
                print(f"Episode {episode + 1}/{num_episodes}, "
                      f"States learned: {len(self.q_table)}, "
                      f"Last reward: {reward:.2f}")
        
        print(f"Training complete! Learned {len(self.q_table)} states")

# Example usage
if __name__ == "__main__":
    agent = TabularQLearning()
    agent.train(num_episodes=1000)  # ~5-10 minutes on CPU
```

**Advantages:**
- ✅ **CPU only**
- ✅ **Fast training** (minutes not hours)
- ✅ **Interpretable** - can inspect learned values
- ⚠️ **Limited to small state spaces** (openings, endgames)

---

## 3. Small Neural Network with Policy Gradients

Use a tiny network that fits in CPU memory.

### Implementation

```python
# src/training/small_policy_network.py
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from src.chess_env import ChessOpenEnv

class SmallChessPolicy(nn.Module):
    """Tiny policy network for chess (< 100K parameters)."""
    
    def __init__(self, board_size=64, num_piece_types=12, hidden_size=128):
        super().__init__()
        
        # Simple MLP that takes flattened board
        input_size = board_size * num_piece_types  # 768
        
        self.network = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 64 * 64),  # All possible moves (simplified)
        )
        
        self.value_head = nn.Linear(hidden_size, 1)
    
    def forward(self, board_tensor):
        """
        Args:
            board_tensor: (batch, 8, 8, 12) board representation
        Returns:
            move_logits: (batch, 4096) logits for all moves
        """
        batch_size = board_tensor.shape[0]
        x = board_tensor.view(batch_size, -1)  # Flatten
        
        # Get hidden representation
        for i, layer in enumerate(self.network):
            x = layer(x)
            if i == 2:  # After first hidden layer
                hidden = x
        
        move_logits = x
        value = self.value_head(hidden)
        
        return move_logits, value


class REINFORCETrainer:
    """REINFORCE (policy gradient) trainer for CPU."""
    
    def __init__(self, learning_rate=0.001):
        self.policy = SmallChessPolicy()
        self.optimizer = optim.Adam(self.policy.parameters(), lr=learning_rate)
        
        # No GPU needed!
        self.device = torch.device("cpu")
        self.policy.to(self.device)
    
    def select_action(self, board_tensor, legal_moves):
        """Select action from policy."""
        with torch.no_grad():
            board_t = torch.FloatTensor(board_tensor).unsqueeze(0)
            logits, value = self.policy(board_t)
            
            # Mask illegal moves
            mask = torch.full((4096,), float('-inf'))
            for move_uci in legal_moves:
                move_idx = self._move_to_index(move_uci)
                if move_idx < 4096:
                    mask[move_idx] = 0
            
            logits = logits.squeeze() + mask
            probs = torch.softmax(logits, dim=0)
            
            # Sample action
            action_idx = torch.multinomial(probs, 1).item()
            log_prob = torch.log(probs[action_idx])
        
        return action_idx, log_prob.item(), value.item()
    
    def _move_to_index(self, move_uci: str) -> int:
        """Convert UCI move to index (simplified)."""
        # e.g., "e2e4" -> index
        from_sq = chess.SQUARE_NAMES.index(move_uci[:2])
        to_sq = chess.SQUARE_NAMES.index(move_uci[2:4])
        return from_sq * 64 + to_sq
    
    def _index_to_move(self, idx: int, legal_moves: list) -> str:
        """Convert index back to move."""
        from_sq = idx // 64
        to_sq = idx % 64
        move_uci = chess.SQUARE_NAMES[from_sq] + chess.SQUARE_NAMES[to_sq]
        
        # Find matching legal move
        for move in legal_moves:
            if move.startswith(move_uci):
                return move
        
        return legal_moves[0] if legal_moves else "a1a1"
    
    def train_episode(self, env: ChessOpenEnv):
        """Train on one game using REINFORCE."""
        obs, info = env.reset()
        
        log_probs = []
        rewards = []
        values = []
        
        while True:
            board_tensor = np.array(obs["board_state"]["board_tensor"])
            legal_moves = obs["legal_moves"]
            
            # Select action
            action_idx, log_prob, value = self.select_action(board_tensor, legal_moves)
            action_uci = self._index_to_move(action_idx, legal_moves)
            
            log_probs.append(log_prob)
            values.append(value)
            
            # Take step
            obs, reward, done, truncated, info = env.step(action_uci)
            rewards.append(reward)
            
            if done:
                break
        
        # Compute returns
        returns = []
        R = 0
        for r in reversed(rewards):
            R = r + 0.99 * R
            returns.insert(0, R)
        
        # Policy gradient update
        returns = torch.FloatTensor(returns)
        log_probs = torch.FloatTensor(log_probs)
        
        # REINFORCE loss
        loss = -(log_probs * returns).mean()
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return sum(rewards), loss.item()
    
    def train(self, num_episodes=1000):
        """Train for multiple episodes."""
        for episode in range(num_episodes):
            env = ChessOpenEnv()
            reward, loss = self.train_episode(env)
            
            if (episode + 1) % 10 == 0:
                print(f"Episode {episode + 1}: Reward={reward:.2f}, Loss={loss:.4f}")
        
        # Save model
        torch.save(self.policy.state_dict(), "small_chess_policy.pt")

# Example usage
if __name__ == "__main__":
    trainer = REINFORCETrainer()
    trainer.train(num_episodes=100)  # ~30 minutes on CPU
```

**Advantages:**
- ✅ **CPU trainable** (with patience)
- ✅ **Generalizes better** than tabular
- ✅ **Small model** (< 100K params)
- ⚠️ **Slower than tabular** (but faster than LLMs!)

---

## 4. Behavioral Cloning from Stockfish

Learn by imitating a strong engine - supervised learning only!

```python
# src/training/behavioral_cloning.py
import chess
import chess.engine
from src.chess_env import ChessOpenEnv
import random

def generate_stockfish_games(num_games: int = 100, 
                            stockfish_path: str = "/usr/bin/stockfish",
                            time_limit: float = 0.1):
    """Generate games played by Stockfish for supervised learning."""
    
    engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
    dataset = []
    
    for game_idx in range(num_games):
        env = ChessOpenEnv()
        board = chess.Board()
        obs, info = env.reset()
        
        while not board.is_game_over():
            # Get Stockfish's best move
            result = engine.play(board, chess.engine.Limit(time=time_limit))
            move_uci = result.move.uci()
            
            # Store (state, action) pair for training
            dataset.append({
                "fen": board.fen(),
                "board_tensor": obs["board_state"]["board_tensor"],
                "move_uci": move_uci,
                "legal_moves": obs["legal_moves"]
            })
            
            # Apply move
            board.push(result.move)
            obs, reward, done, truncated, info = env.step(move_uci)
            
            if done:
                break
        
        print(f"Game {game_idx + 1}/{num_games} generated")
    
    engine.quit()
    
    return dataset

# Train a small network on this data
def train_behavioral_cloning():
    """Train policy via supervised learning from Stockfish."""
    
    # Generate data
    print("Generating training data from Stockfish...")
    dataset = generate_stockfish_games(num_games=100)
    
    # Train model (supervised learning - very fast on CPU!)
    model = SmallChessPolicy()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    for epoch in range(10):
        total_loss = 0
        random.shuffle(dataset)
        
        for sample in dataset:
            board_tensor = torch.FloatTensor(sample["board_tensor"]).unsqueeze(0)
            move_idx = move_to_index(sample["move_uci"])
            
            # Forward pass
            logits, _ = model(board_tensor)
            
            # Cross-entropy loss
            loss = nn.CrossEntropyLoss()(logits, torch.LongTensor([move_idx]))
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        print(f"Epoch {epoch + 1}: Loss = {total_loss / len(dataset):.4f}")
    
    torch.save(model.state_dict(), "behavioral_cloning_policy.pt")
    print("Training complete!")

if __name__ == "__main__":
    train_behavioral_cloning()
```

**Advantages:**
- ✅ **Fastest training** (supervised learning)
- ✅ **CPU only**
- ✅ **Strong baseline** (learns from expert)
- ✅ **No self-play needed**

---

## 5. Evolutionary Strategies

Evolve policies without gradients!

```python
# src/training/evolutionary_strategies.py
import numpy as np
from src.chess_env import ChessOpenEnv
from copy import deepcopy

class SimplePolicy:
    """Simple heuristic policy with learnable weights."""
    
    def __init__(self):
        # Weights for chess heuristics
        self.weights = {
            'material': 1.0,
            'center_control': 0.3,
            'king_safety': 0.5,
            'development': 0.4,
        }
    
    def evaluate_position(self, env: ChessOpenEnv) -> float:
        """Score a position using weighted heuristics."""
        state = env.state()
        board = chess.Board(state["fen"])
        
        score = 0.0
        score += self._material_score(board) * self.weights['material']
        score += self._center_control(board) * self.weights['center_control']
        score += self._king_safety(board) * self.weights['king_safety']
        
        return score
    
    def _material_score(self, board: chess.Board) -> float:
        """Material count."""
        piece_values = {
            chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
            chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0
        }
        
        score = 0
        for piece_type in piece_values:
            score += len(board.pieces(piece_type, chess.WHITE)) * piece_values[piece_type]
            score -= len(board.pieces(piece_type, chess.BLACK)) * piece_values[piece_type]
        
        return score
    
    def _center_control(self, board: chess.Board) -> float:
        """Control of center squares."""
        center_squares = [chess.E4, chess.E5, chess.D4, chess.D5]
        score = 0
        for sq in center_squares:
            piece = board.piece_at(sq)
            if piece:
                score += 1 if piece.color == chess.WHITE else -1
        return score
    
    def _king_safety(self, board: chess.Board) -> float:
        """King safety score."""
        # Simplified: just check if castled
        score = 0
        if board.has_castling_rights(chess.WHITE):
            score += 1
        if board.has_castling_rights(chess.BLACK):
            score -= 1
        return score
    
    def select_move(self, env: ChessOpenEnv) -> str:
        """Select move by evaluating all options."""
        legal_moves = env.get_legal_moves()
        
        best_move = None
        best_score = float('-inf')
        
        for move in legal_moves:
            # Simulate move
            sim_env = deepcopy(env)
            sim_env.step(move)
            score = self.evaluate_position(sim_env)
            
            if score > best_score:
                best_score = score
                best_move = move
        
        return best_move or legal_moves[0]
    
    def mutate(self, mutation_rate: float = 0.1):
        """Mutate weights."""
        new_policy = SimplePolicy()
        for key in self.weights:
            new_policy.weights[key] = self.weights[key] + np.random.normal(0, mutation_rate)
        return new_policy


def evolutionary_training(population_size: int = 20, 
                         generations: int = 50):
    """Evolve a population of policies."""
    
    # Initialize population
    population = [SimplePolicy() for _ in range(population_size)]
    
    for gen in range(generations):
        # Evaluate fitness (play games)
        fitness_scores = []
        
        for i, policy in enumerate(population):
            # Play 10 games vs random
            wins = 0
            for _ in range(10):
                env = ChessOpenEnv()
                env.reset()
                
                while True:
                    state = env.state()
                    if state["is_terminal"]:
                        if state["result"] == "white_wins":
                            wins += 1
                        break
                    
                    move = policy.select_move(env)
                    env.step(move)
            
            fitness_scores.append(wins)
            print(f"Gen {gen+1}, Policy {i+1}: {wins}/10 wins")
        
        # Selection: keep top 50%
        top_indices = np.argsort(fitness_scores)[-population_size//2:]
        survivors = [population[i] for i in top_indices]
        
        # Reproduction: mutate survivors
        population = survivors.copy()
        for survivor in survivors:
            child = survivor.mutate()
            population.append(child)
    
    # Return best policy
    best_idx = np.argmax(fitness_scores)
    return population[best_idx]


if __name__ == "__main__":
    best_policy = evolutionary_training()
    print("Evolution complete!")
```

**Advantages:**
- ✅ **CPU only**
- ✅ **No gradients needed**
- ✅ **Parallelizable**
- ✅ **Simple to understand**

---

## Recommendations

### For Immediate Results (Today!)
1. **Use MCTS** - Works immediately, no training
2. **Stockfish behavioral cloning** - Train in < 1 hour on CPU

### For Learning RL (This Week)
1. **Tabular Q-Learning** - Good for openings/endgames
2. **Small Policy Network** - General but slower

### For Research (Long Term)
1. **MCTS + Small NN** (AlphaZero-lite)
2. **Evolutionary Strategies**
3. Eventually rent cheap GPU for experiments

---

## Comparison Table

| Method | Training Time (CPU) | Strength | GPU Needed? | Complexity |
|--------|-------------------|----------|-------------|------------|
| MCTS (no training) | 0 (instant) | Medium | No ✅ | Low |
| Tabular Q-Learning | 5-10 min | Weak-Medium | No ✅ | Low |
| Small Neural Network | 30-60 min | Medium | No ✅ | Medium |
| Behavioral Cloning | 1-2 hours | Strong | No ✅ | Low |
| Evolutionary | 2-4 hours | Medium | No ✅ | Medium |
| **LLM + PPO** | **100+ GPU hours** | **Variable** | **Yes ❌** | **High** |

---

## Next Steps

1. **Start with MCTS** - Copy the code above, run it today
2. **Generate data** - Create dataset via self-play or Stockfish
3. **Train small network** - Behavioral cloning or policy gradients
4. **Evaluate** - Play against Stockfish at different levels
5. **Iterate** - Improve heuristics, add features, tune hyperparameters

All of these work on your laptop without any GPU! 🚀
