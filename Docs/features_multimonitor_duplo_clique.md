# Guia das Features: Múltiplos Monitores e Duplo Clique

Este documento detalha o funcionamento, as configurações e o guia prático de calibração para as duas novas funcionalidades do **Virtual Gesture Mouse**:
1. **Suporte a Múltiplos Monitores** (`SPAN` e `ACTIVE_SWITCH`).
2. **Duplo Clique** (Detecção Temporal e Gesto Dedicado do Dedo Anelar).

---

## 1. Suporte a Múltiplos Monitores

### 1.1 Como a biblioteca detecta múltiplos monitores
O sistema utiliza a biblioteca `screeninfo` integrada à API Win32 com suporte a DPI Awareness (`ctypes.windll.user32.SetProcessDPIAware()`). Isso garante que os pixels físicos reais de cada monitor sejam consultados sem distorções de escala do Windows (p.ex., telas 4K ou notebooks com escala de 125%/150%).

- **Enumeração e Ordenação:** Todos os monitores detectados são ordenados automaticamente no eixo horizontal (`x` crescente).
- **Tratamento de offsets negativos:** Em configurações onde o monitor secundário fica à esquerda do monitor principal, suas coordenadas no sistema operacional começam em valores negativos (por exemplo, `x = -1600`). O `MonitorManager` trata esses offsets nativamente, permitindo que o `pyautogui.moveTo(x, y)` posicione o cursor corretamente em qualquer tela.
- **Fallback Suave:** Se o computador possuir apenas um monitor ou se a biblioteca não estiver disponível, o sistema opera de forma transparente em modo tela única `(0, 0, width, height)` sem erros.
- **Sobrescrita Manual (`MONITORS_OVERRIDE`):** Caso queira forçar geometrias específicas sem detecção automática, configure em `src/config.py`:
  ```python
  MONITORS_OVERRIDE = [
      (-1600, 130, 1600, 900),   # Monitor Secundário à esquerda
      (0, 0, 1920, 1080)         # Monitor Primário
  ]
  ```

---

### 1.2 Estratégias de Navegação

Defina o comportamento desejado em `src/config.py` através da chave `MULTI_MONITOR_MODE`:

#### Modo `SPAN` (Padrão)
A moldura ativa da webcam cobre toda a largura combinada dos monitores conectados:
- **Vantagem:** Navegação contínua e fluida. Mover a mão da esquerda para a direita atravessa a borda do Monitor 1 direto para o Monitor 2.
- **Ideal para:** Monitores lado a lado com resoluções semelhantes onde você deseja arrastar janelas ou mover o cursor entre telas rapidamente.
- **Proteção contra zonas mortas:** Se as telas tiverem alturas diferentes, o algoritmo projeta (*clamp*) o cursor para a tela física mais próxima, impedindo que o ponteiro se perca no vazio.

#### Modo `ACTIVE_SWITCH`
A moldura ativa da webcam é associada exclusivamente a um monitor por vez com proporção 1:1:
- **Vantagem:** Máxima sensibilidade e precisão espacial em cada tela individualmente.
- **Como alternar:**
  - Pressione a tecla `'m'` (ou a tecla definida em `MONITOR_SWITCH_KEY`) na janela da câmera para circular entre os monitores.
  - Pressione teclas numéricas `'1'` a `'9'` para focar diretamente no monitor desejado.
- Ao trocar de tela, o cursor é suavemente posicionado no centro do novo monitor.

---

### 1.3 Calibração de Sensibilidade para Telas Mistas (ex.: Ultrawide + Full HD)

Quando combinamos telas com proporções ou resoluções muito diferentes (p.ex., um Ultrawide de `3440x1440` + Full HD de `1920x1080` totalizando `5360px` de largura virtual):

1. **No modo `SPAN`:**
   - Como a largura total é muito grande, um pequeno deslocamento da mão cobre mais pixels na horizontal do que na vertical.
   - Para compensar e não perder o alcance vertical, reduza `FRAME_MARGIN_Y` em relação a `FRAME_MARGIN_X` em `src/config.py`:
     ```python
     FRAME_MARGIN_X = 110   # margem horizontal
     FRAME_MARGIN_Y = 70    # margem vertical menor (aumenta o alcance vertical da mão)
     ```
   - Ajuste `SMOOTHING_FACTOR`: para áreas de trabalho muito largas, um valor entre `0.20` e `0.28` garante estabilidade sem que o cursor pareça pesado.

2. **No modo `ACTIVE_SWITCH`:**
   - Cada monitor preserva 100% da sua resolução nativa dentro da moldura da câmera.
   - Não há distorção de proporção horizontal/vertical. Recomendado se você precisa de trabalho de precisão (edição de texto, seleção detalhada) em telas de tamanhos diferentes.

---

## 2. Reconhecimento de Duplo Clique (Double-Click)

O sistema conta com duas abordagens independentes que podem ser usadas em conjunto:

### 2.1 Detecção Temporal (Double-Tap com Indicador)
- **Gesto:** Realize o gesto de pinça padrão (Indicador + Polegar) duas vezes seguidas rapidamente.
- **Como funciona:**
  - O primeiro toque fecha a pinça por tempo inferior a `DRAG_HOLD_TIME` (padrão `0.18s`).
  - O cursor permanece travado na posição onde o primeiro toque ocorreu.
  - Se a segunda pinça for iniciada dentro de `DOUBLE_CLICK_TIMEOUT` (padrão `0.35s`), o sistema emite `pyautogui.doubleClick()`.
  - Se o tempo expirar sem a segunda pinça, o sistema dispara o clique simples normal retroativo.
- **Desativação Opcional:** Se você prefere que o botão esquerdo do mouse pressione instantaneamente no primeiro milissegundo de contato da pinça (sem esperar janela de duplo toque), defina:
  ```python
  DOUBLE_TAP_ENABLED = False
  ```

### 2.2 Gesto Dedicado Instantâneo (Pinça do Dedo Anelar)
- **Gesto:** Encoste a ponta do Dedo Anelar (Landmark 16) na ponta do Polegar (Landmark 4).
- **Como funciona:**
  - Disparo imediato de `pyautogui.doubleClick()`.
  - Não requer espera ou múltiplos movimentos: ideal para abrir arquivos ou pastas no explorador de arquivos com um único gesto deliberado.
  - **Filtro Anti-Punho:** A pinça do anelar é desconsiderada se todos os outros dedos estiverem recolhidos (mão fechada em punho). Isso evita cliques acidentais quando você fecha a mão para descansar.

---

### 2.3 Como Calibrar os Tempos e Limiares

Em `src/config.py`:

```python
# Janela máxima entre o início da 1ª e da 2ª pinça para validar duplo clique:
DOUBLE_CLICK_TIMEOUT = 0.35   # Aumente (ex: 0.40 a 0.45s) se achar o tempo curto demais
                              # Reduza (ex: 0.28 a 0.30s) para cliques simples responderem mais rápido

# Tempo com a pinça fechada para iniciar o modo de arrastar (drag and drop):
DRAG_HOLD_TIME = 0.18         # Deve ser sempre menor que DOUBLE_CLICK_TIMEOUT

# Limiares da pinça do dedo anelar (razão normalizada):
RING_PINCH_THRESHOLD_NORM = 0.28       # Fechamento (abaixo disso = pinça ativa)
RING_PINCH_OPEN_THRESHOLD_NORM = 0.40  # Abertura (histerese para soltar o gesto)

# Intervalo mínimo entre dois duplos cliques com o dedo anelar (debounce):
DOUBLE_CLICK_DEBOUNCE_S = 0.8          # Evita múltiplos cliques indesejados no mesmo gesto
```

#### Dicas de Ajuste:
- **Clique simples parece ter atraso?**
  Reduza `DOUBLE_CLICK_TIMEOUT` para `0.28s` ou desative `DOUBLE_TAP_ENABLED = False` e utilize exclusivamente a pinça do anelar para duplos cliques.
- **Duplo clique do indicador vira arraste por engano?**
  Garanta que os toques sejam rápidos (menos de `0.18s` de contato entre os dedos). Se necessário, aumente `DRAG_HOLD_TIME = 0.22`.
- **Pinça do anelar difícil de alcançar?**
  Aumente `RING_PINCH_THRESHOLD_NORM = 0.32` para que os dedos não precisem se tocar com tanta força.
