# Arquitetura (visão geral)

O **Virtual Gesture Mouse** controla o mouse do SO por gestos da mão capturados pela webcam, com suporte a múltiplos monitores e ações avançadas de clique e rolagem.
Detalhes técnicos, equações e diagramas: [arquitetura.md](arquitetura.md).
Guia das novas features: [features_multimonitor_duplo_clique.md](features_multimonitor_duplo_clique.md).

## Camadas

| Camada | Arquivo | Responsabilidade |
|---|---|---|
| Configuração | `src/config.py` | Constantes ajustáveis: sensibilidade, monitores, limiares, duplo clique |
| Geometria/Telas | `src/monitors.py` | Detecção via `screeninfo`, cálculo de desktop virtual (`SPAN` e `ACTIVE_SWITCH`) |
| Percepção | `src/hand_tracker.py` | MediaPipe (Legado ou Tasks) -> `HandData` (21 landmarks e distâncias) |
| Decisão/Ação | `src/gesture_controller.py` | Máquina de estados (clique, duplo clique, arraste, scroll) + LERP + pyautogui |
| Apresentação/Orquestração | `src/main.py` | Captura de vídeo, loop principal, HUD visual, atalhos de monitor e saída limpa |

## Fluxo

`Webcam -> flip -> HandTracker.process -> HandData -> GestureController.update (via MonitorManager) -> pyautogui` e, em paralelo, `draw_hud -> imshow`.

## Padrões Arquiteturais

- **Injeção de dependência**: `GestureController` recebe o backend de mouse (padrão: `pyautogui`) e o `MonitorManager`, viabilizando suítes de testes sem mover o mouse real.
- **Adapter**: `HandTracker` esconde duas APIs do MediaPipe (legada e Tasks) atrás da mesma interface unificada `HandData`.
- **Máquina de Estados Hierárquica**: Diferencia toques rápidos (clique simples e double-tap), sustentação temporal para arraste (`DRAG_HOLD_TIME`), debounce para duplo clique com anelar e clique direito, e confirmação por quadros para gestos livres.
- **Gerenciador de Desktop Virtual**: `MonitorManager` unifica múltiplos monitores conectados (mesmo com resoluções desiguais e offsets negativos) em coordenadas contínuas compatíveis com o SO.
- Dependências unidirecionais: `main -> (gesture_controller, hand_tracker, monitors, config)`.
