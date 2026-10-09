# 🖱️ Virtual Gesture Mouse

> Controle o cursor, cliques, rolagem e múltiplos monitores usando visão computacional e gestos das mãos via webcam em tempo real.

O **Virtual Gesture Mouse** é uma aplicação em Python baseada em **OpenCV**, **MediaPipe** e **PyAutoGUI** que transforma a sua mão em um mouse virtual preciso, sem a necessidade de hardware especial ou luvas. O projeto inclui detecção de múltiplos monitores, gestos dedicados para duplo clique, interpolação suave de movimento (LERP) e um HUD informativo em tempo real.

---

## 📑 Sumário

- [Recursos Principais](#-recursos-principais)
- [Demonstração dos Gestos](#-tabela-de-gestos)
- [Requisitos de Sistema](#-requisitos-de-sistema)
- [Instalação](#-instalação)
- [Como Usar](#-como-usar)
  - [Executando o projeto](#executando-o-projeto)
  - [Atalhos de teclado](#atalhos-de-teclado-com-a-janela-da-câmera-em-foco)
- [Tabela de Gestos](#-tabela-de-gestos)
- [Suporte a Múltiplos Monitores](#-suporte-a-múltiplos-monitores)
- [Configuração e Calibração](#-configuração-e-calibração)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Documentação Detalhada](#-documentação-detalhada)
- [Solução de Problemas](#-solução-de-problemas)

---

## ✨ Recursos Principais

- 🎯 **Rastreamento e Interpolação Suave:** Movimentação do ponteiro via ponta do dedo indicador com filtro LERP (*Linear Interpolation*) e zona morta para neutralizar tremores naturais da mão.
- 🤏 **Cliques Naturais e Arrastar:** Pinça entre indicador e polegar para clique simples ou arraste contínuo (*drag and drop*) ao sustentar a pinça.
- ⚡ **Dois Modos de Duplo Clique:**
  - *Double-Tap Temporal:* Duas pinças rápidas sucessivas com o indicador (`< 0.35s`).
  - *Gesto Instantâneo Dedicado:* Pinça entre dedo anelar e polegar para duplo clique imediato, com filtro anti-punho e debounce.
- 🖱️ **Clique com Botão Direito:** Pinça entre dedo médio e polegar com debounce temporal para evitar múltiplos acionamentos.
- 📜 **Rolagem Vertical (Scroll):** Gesto com indicador e dedo médio estendidos simultaneamente; movimentar a mão para cima ou para baixo rola a página de forma proporcional.
- 🖥️ **Suporte a Múltiplos Monitores:**
  - **Modo SPAN:** Desktop virtual unificado contínuo (transição fluida da borda de uma tela para a outra, com suporte a offsets negativos e compensação de alturas diferentes).
  - **Modo ACTIVE_SWITCH:** Foco 1:1 de precisão em uma tela por vez, alternável via tecla rápida (`'m'` ou números `'1'` a `'9'`).
  - Detecção com **DPI Awareness** no Windows para leitura fiel dos pixels físicos reais via `screeninfo`.
- 👁️ **HUD em Tempo Real:** Retângulo magenta de delimitação ativa (*bounding box*), indicadores coloridos nas pontas dos dedos, monitor ativo, FPS atual e feedback visual de ações.
- 🛡️ **Segurança e Encerramento Limpo:** Tecla `ESC` ou `q` fecha a aplicação e solta automaticamente quaisquer cliques presos (`mouseUp`), prevenindo travamentos indesejados no sistema operacional.
- 🔄 **Compatibilidade com MediaPipe:** Suporte automático tanto para a nova Tasks API (com download automático de modelo `hand_landmarker.task`) quanto para a API legada (`solutions.hands`).

---

## 🖐️ Tabela de Gestos

| Gesto | Configuração dos Dedos | Ação Executada |
|---|---|---|
| **Mover Cursor** | Apenas dedo **indicador esticado** (demais fechados) | O ponteiro segue a ponta do indicador |
| **Clique Simples** | **Pinça rápida** entre polegar e indicador | Clique com botão esquerdo |
| **Duplo Clique (Temporal)** | **Duas pinças rápidas** sucessivas com o indicador | Dispara duplo clique no alvo |
| **Duplo Clique (Instantâneo)** | **Pinça** entre dedo **anelar e polegar** | Disparo imediato de duplo clique |
| **Arrastar (Drag & Drop)** | **Fechar pinça** (indicador + polegar), segurar e mover | Botão esquerdo pressionado até abrir a mão |
| **Clique Direito** | **Pinça** entre dedo **médio e polegar** | Clique com botão direito |
| **Rolagem (Scroll)** | **Indicador + Médio esticados juntos** | Subir a mão rola para cima; descer rola para baixo |
| **Pausa / Descanso** | Punho totalmente fechado ou palma totalmente aberta | Cursor em repouso (descanse a mão com segurança) |

---

## 🖥️ Suporte a Múltiplos Monitores

O sistema detecta automaticamente todos os monitores conectados utilizando a biblioteca `screeninfo` com suporte a DPI.

Configure a estratégia no arquivo [`src/config.py`](src/config.py):

```python
MULTI_MONITOR_MODE = "SPAN"  # Opções: "SPAN" ou "ACTIVE_SWITCH"
```

1. **Modo `SPAN` (Padrão):**
   - A moldura de movimento da webcam cobre todos os monitores lado a lado.
   - Movimentar a mão da esquerda para a direita atravessa suavemente de uma tela para a outra.
   - Ideal para uso geral em monitores com resoluções semelhantes.

2. **Modo `ACTIVE_SWITCH`:**
   - Mapeia 100% da moldura da câmera para um único monitor de cada vez, garantindo máxima precisão.
   - Pressione `'m'` na janela da câmera para avançar para o próximo monitor.
   - Pressione teclas numéricas `'1'` a `'9'` para saltar diretamente para um monitor específico.
   - Ao trocar, o cursor é suavemente centralizado na nova tela.

---

## 📋 Requisitos de Sistema

- **Sistema Operacional:** Windows 10/11 (recomendado), Linux (com servidor X11) ou macOS.
- **Python:** Versão 3.10 ou superior (testado no Python 3.13).
- **Webcam:** Qualquer webcam integrada ou USB funcional (resolução mínima recomendada: 640x480 a 30 FPS).
- **Acesso à Internet:** Apenas na 1ª execução caso utilize MediaPipe Tasks API para download automático do modelo (`hand_landmarker.task`, ~7,8 MB).

---

## 🚀 Instalação

1. **Clone ou navegue até o diretório do projeto:**
   ```powershell
   cd c:\laragon\www\projetomouse
   ```

2. **Crie e ative um ambiente virtual:**
   ```powershell
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\activate

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Instale as dependências:**
   ```powershell
   pip install -r requirements.txt
   ```

> **Nota para macOS:** Conceda permissão de *Acessibilidade* e *Gravação de Tela* para o terminal nas Preferências do Sistema.  
> **Nota para Windows:** Se você precisa interagir com janelas executadas como Administrador, execute o terminal também como Administrador.

---

## 🎮 Como Usar

### Executando o projeto

Com o ambiente virtual ativado, inicie o módulo principal a partir da raiz do projeto:

```powershell
python -m src.main
```

### Atalhos de Teclado (com a janela da câmera em foco)

| Tecla | Função |
|---|---|
| `ESC` ou `q` | Encerra a aplicação de forma limpa (soltando quaisquer cliques pendentes) |
| `m` | Alterna circularmente entre os monitores (no modo `ACTIVE_SWITCH`) |
| `1` a `9` | Seleciona diretamente o monitor correspondente (no modo `ACTIVE_SWITCH`) |

---

## ⚙️ Configuração e Calibração

Todas as constantes e sensibilidades podem ser ajustadas em [`src/config.py`](src/config.py):

### 1. Alcance e Sensibilidade do Cursor
- `FRAME_MARGIN_X` / `FRAME_MARGIN_Y`: Define a moldura ativa na imagem da câmera. Quanto **maior** a margem, menor o movimento da mão necessário para atravessar a tela inteira.
- `SMOOTHING_FACTOR` (α): Controla a interpolação LERP (padrão `0.25`). Valores menores (ex: `0.18`) aumentam a suavidade; valores maiores (ex: `0.45`) aumentam a velocidade de resposta.
- `MIN_MOVE_PIXELS`: Limiar mínimo de deslocamento para ignorar microtremores quando a mão estiver parada.

### 2. Distância da Mão à Câmera
- `USE_NORMALIZED_DISTANCE = True` (Padrão): A distância dos dedos é calculada em proporção ao tamanho da mão. Funciona de ~40 cm a ~1,5 m da webcam sem necessidade de recalibrar.
- `PINCH_CLOSE_THRESHOLD_NORM`: Limiar para detecção de pinça fechada (padrão `0.28`).
- `PINCH_OPEN_THRESHOLD_NORM`: Limiar de histerese para abertura da pinça (padrão `0.40`).

### 3. Duplo Clique e Rolagem
- `DOUBLE_CLICK_TIMEOUT`: Janela máxima de tempo para o segundo toque no modo Double-Tap (padrão `0.35s`).
- `DRAG_HOLD_TIME`: Duração com a pinça fechada para transicionar de clique para arraste (padrão `0.18s`).
- `RING_PINCH_THRESHOLD_NORM`: Limiar de aproximação do dedo anelar com o polegar para disparo instantâneo.
- `SCROLL_SENSITIVITY`: Fator multiplicador de velocidade de rolagem da página.
- `SCROLL_INVERT`: Inverte o sentido natural do scroll.

---

## 📁 Estrutura do Projeto

```text
projetomouse/
├── Docs/                                    # Documentação técnica e registros arquiteturais
│   ├── ARCHITECTURE.md                      # Visão geral da arquitetura e camadas
│   ├── arquitetura.md                       # Detalhes matemáticos, equações e diagramas
│   ├── CHANGELOG.md                         # Histórico de alterações do projeto
│   ├── DECISIONS.md                         # ADRs (Architecture Decision Records)
│   ├── features_multimonitor_duplo_clique.md# Manual detalhado de multimonitor e duplo clique
│   ├── FILE_MAP.md                          # Mapeamento completo e referências cruzadas
│   ├── manual_uso.md                        # Guia de usuário e calibração passo a passo
│   └── MODULES.md                           # Dicionário de módulos, classes e assinaturas
├── models/                                  # Armazena o modelo MediaPipe (ignorado pelo git)
│   └── hand_landmarker.task
├── src/                                     # Código-fonte da aplicação
│   ├── __init__.py
│   ├── config.py                            # Parâmetros e constantes de configuração
│   ├── gesture_controller.py                # Máquina de estados de gestos e controle do mouse
│   ├── hand_tracker.py                      # Wrapper para MediaPipe e extração de landmarks
│   ├── main.py                              # Ponto de entrada, loop de vídeo e HUD
│   └── monitors.py                          # Gerenciamento de múltiplos monitores e geometria
├── .gitignore
├── requirements.txt                         # Dependências com versões pinadas
└── README.md                                # Apresentação e documentação do projeto
```

---

## 📚 Documentação Detalhada

Para aprofundar-se em tópicos específicos, consulte os documentos na pasta [`Docs/`](Docs/):

- 📐 [**Arquitetura do Sistema**](Docs/ARCHITECTURE.md) & [**Modelagem Matemática**](Docs/arquitetura.md): Fluxo de dados, diagramas de estado e equações de projeção de coordenadas.
- 📖 [**Manual Completo de Uso**](Docs/manual_uso.md): Instruções passo a passo de calibração fina e dicas de postura.
- 🖥️ [**Guia de Múltiplos Monitores e Duplo Clique**](Docs/features_multimonitor_duplo_clique.md): Funcionamento aprofundado dos modos de tela e das duas estratégias de duplo clique.
- 💡 [**Registros de Decisões Arquiteturais (ADRs)**](Docs/DECISIONS.md): Justificativas de design (Tasks vs Legado, LERP, gerenciador de monitores, etc.).
- 🗺️ [**Mapa de Arquivos**](Docs/FILE_MAP.md) e [**Módulos**](Docs/MODULES.md): Lista de classes, métodos e dependências.

---

## 🔧 Solução de Problemas

| Problema | Possível Causa | Solução |
|---|---|---|
| `Não foi possível abrir a webcam` | A câmera está sendo usada por outro aplicativo (Zoom, Teams, navegador) ou o índice está incorreto. | Feche outros aplicativos que usem a câmera e verifique o valor de `CAMERA_INDEX` em `src/config.py`. No Windows, confira as permissões de privacidade da câmera. |
| O cursor treme na tela | Ruído no rastreamento em pontos estáticos. | Em `src/config.py`, reduza `SMOOTHING_FACTOR` (ex.: `0.20`) e aumente `MIN_MOVE_PIXELS` (ex.: `3` ou `4`). |
| O cursor parece pesado/lento | Interpolação excessiva. | Aumente `SMOOTHING_FACTOR` (ex.: `0.35` ou `0.40`). |
| Ações de clique não funcionam em certas janelas | A janela de destino está com privilégios de Administrador. | Execute o terminal com privilégios de Administrador. |
| O duplo clique vira arraste por engano | O tempo de contato da pinça excedeu `DRAG_HOLD_TIME`. | Faça movimentos de pinça mais rápidos ao clicar, ou aumente levemente `DRAG_HOLD_TIME` em `src/config.py`. Você também pode utilizar o gesto instantâneo com o **dedo anelar**. |
