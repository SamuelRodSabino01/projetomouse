# Mapa de Arquivos

| Arquivo | Finalidade | Importa | Usado por |
|---|---|---|---|
| `requirements.txt` | Dependências com versões fixas (OpenCV, MediaPipe, PyAutoGUI, screeninfo) | - | Instalação (`pip`) |
| `README.md` | Apresentação geral, guia de instalação, tabela de gestos, configuração e troubleshooting | - | Apresentação e guia rápido |
| `.gitignore` | Ignora `.venv/`, `models/`, caches, `.env*` | - | git |
| `models/hand_landmarker.task` | Modelo MediaPipe (baixado automaticamente; ignorado pelo git) | - | `src/hand_tracker.py` |
| `src/__init__.py` | Marca o pacote | - | - |
| `src/config.py` | Constantes: câmera, margens, limiares, suavização, multimonitor, duplo clique, scroll, HUD | - | `hand_tracker`, `gesture_controller`, `monitors`, `main` |
| `src/monitors.py` | `Monitor`, `MonitorManager`, detecção via `screeninfo` e projeção para o desktop virtual | `config`, `numpy`, `screeninfo` | `gesture_controller`, `main` |
| `src/hand_tracker.py` | `HandData` e `HandTracker` (MediaPipe legado/Tasks), distâncias dos landmarks | `config`, `cv2`, `numpy`, `mediapipe` | `gesture_controller` (constantes de landmarks, `HandData`), `main` (`HandTracker`, `HAND_CONNECTIONS`) |
| `src/gesture_controller.py` | `Mode`, `GestureController` (máquina de estados: clique, duplo clique, arraste, scroll) | `config`, `hand_tracker`, `monitors`, `numpy`, `pyautogui` (lazy) | `main` |
| `src/main.py` | Loop principal, captura, HUD visual multimonitor, atalhos de troca de tela, saída limpa | `config`, `gesture_controller`, `hand_tracker`, `monitors`, `cv2` | Ponto de entrada (`python -m src.main`) |
| `Docs/ARCHITECTURE.md` | Visão geral da arquitetura | - | - |
| `Docs/arquitetura.md` | Fluxo, equações multimonitor, interpolação e diagrama da máquina de estados | - | - |
| `Docs/features_multimonitor_duplo_clique.md` | Manual e guia de calibração para multimonitor e duplo clique | - | - |
| `Docs/manual_uso.md` | Instalação, operação e calibração geral | - | - |
| `Docs/FILE_MAP.md` | Este índice | - | - |
| `Docs/MODULES.md` | Funções, classes e regras de negócio | - | - |
| `Docs/CHANGELOG.md` | Histórico de mudanças em ordem cronológica reversa | - | - |
| `Docs/DECISIONS.md` | Registros de Decisões Arquiteturais (ADRs) | - | - |
