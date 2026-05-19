# 🎯 mHandStudio FBX Automation

Automação inteligente para converter arquivos `.md` do mHandStudio em arquivos `.fbx` usando **OCR (Optical Character Recognition)** para detecção adaptativa de interface.

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Requisitos](#-requisitos)
- [Instalação](#-instalação)
- [Uso](#-uso)
- [Configuração](#-configuração)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 Visão Geral

Script Python que automatiza a conversão de arquivos de captura de movimento (`.md`) do mHandStudio para o formato FBX usando automação de interface com reconhecimento óptico de caracteres (OCR).

### ✨ Características

- ✅ **Independente de Resolução** - Funciona em qualquer tamanho de tela ou escala de DPI
- ✅ **Auto-Ajustável** - Localiza elementos da UI lendo texto na tela (não usa coordenadas fixas)
- ✅ **Gerenciamento Automático de Diálogos** - Detecta e fecha diálogo de Auto Update automaticamente
- ✅ **Seleção Inteligente de Formato** - Garante seleção de "FBX binary" no formato de exportação
- ✅ **Debug Automático** - Salva screenshots de cada passo em `_ocr_debug/`
- ✅ **Processamento em Lote** - Converte múltiplos arquivos com script PowerShell

---

## 📦 Requisitos

### 1. Sistema Operacional
- **Windows 10/11** (testado e recomendado)

### 2. Python 3.7+

**Download:** https://www.python.org/downloads/  
**Recomendado:** Python 3.9 - 3.11

⚠️ **IMPORTANTE:** Durante a instalação, marcar a opção **"Add Python to PATH"**

**Verificar instalação:**
```powershell
python --version
```

Deve retornar algo como: `Python 3.11.x`

---

### 3. Tesseract OCR (Obrigatório)

O Tesseract é necessário para o script ler texto na tela e localizar botões/menus.

#### Instalação do Tesseract:

1. **Download:** https://github.com/UB-Mannheim/tesseract/wiki
2. **Arquivo:** Baixar `tesseract-ocr-w64-setup-5.3.x.exe` (ou versão mais recente)
3. **Executar instalador:**
   - ✅ **IMPORTANTE:** Marcar opção **"Add to PATH"**
   - ✅ Instalar idioma inglês (eng.traineddata) - já vem por padrão
4. **Caminho padrão:** `C:\Program Files\Tesseract-OCR\tesseract.exe`

#### Verificar instalação do Tesseract:

```powershell
tesseract --version
```

**Saída esperada:**
```
tesseract v5.3.0.20221222
 leptonica-1.82.0
  libgif 5.2.1 : libjpeg 8d (libjpeg-turbo 2.1.3) : libpng 1.6.38 : libtiff 4.4.0 : zlib 1.2.12 : libwebp 1.2.4 : libopenjp2 2.5.0
```

Se este comando não funcionar, o Tesseract não está instalado corretamente ou não está no PATH.

---

### 4. Dependências Python

O script requer as seguintes bibliotecas Python:

```txt
pyautogui>=0.9.53      # Automação de interface (cliques, teclas, screenshots)
pygetwindow>=0.0.9     # Controle de janelas do Windows
psutil>=5.9.0          # Gerenciamento de processos
opencv-python>=4.8.0   # Processamento de imagem
pytesseract>=0.3.10    # Wrapper Python para Tesseract OCR
numpy>=1.24.0          # Operações numéricas
Pillow>=10.0.0         # Manipulação de imagens
```

Todas estão listadas no arquivo `requirements.txt`.

---

### 5. mHandStudio

O software mHandStudio deve estar instalado.

**Caminho configurável no script** (linha ~45):
```python
"mhand_exe": r"C:\Users\Locatech\Downloads\mHandStudio\mHandStudio\mHandStudio.exe"
```

---

## 🚀 Instalação

### Passo 1: Instalar Python

1. Baixar Python de https://www.python.org/downloads/
2. Executar instalador
3. ✅ Marcar **"Add Python to PATH"**
4. Clicar "Install Now"

Verificar:
```powershell
python --version
```

---

### Passo 2: Instalar Tesseract OCR

1. Baixar de https://github.com/UB-Mannheim/tesseract/wiki
2. Executar `tesseract-ocr-w64-setup-5.3.x.exe`
3. ✅ Marcar **"Add to PATH"**
4. Instalar em `C:\Program Files\Tesseract-OCR\`

Verificar:
```powershell
tesseract --version
```

---

### Passo 3: Instalar Dependências Python

Navegar até a pasta do projeto:
```powershell
cd C:\Users\Locatech\automacao_mhand\mHandStudio_fbx_conversion
```

Instalar dependências:
```powershell
pip install -r requirements.txt
```

**Ou instalar manualmente:**
```powershell
pip install pyautogui pygetwindow psutil opencv-python pytesseract numpy Pillow
```

---

### Passo 4: Verificar Instalação Completa

Execute um teste rápido:

```powershell
# Verificar Python
python --version

# Verificar Tesseract
tesseract --version

# Verificar dependências Python
python -c "import pyautogui, cv2, pytesseract; print('✓ Dependências OK')"
```

Se todos os comandos funcionarem sem erro, a instalação está completa! ✅

---

## 💻 Uso

### Conversão de Arquivo Único

```powershell
python mhand_to_fbx_ocr.py --input "mao\01-05\Abastar.md"
```

O arquivo FBX será salvo na mesma pasta do arquivo `.md` de entrada.

**Especificar saída customizada:**
```powershell
python mhand_to_fbx_ocr.py --input "mao\01-05\Abastar.md" --output "fbx\Abastar.fbx"
```

---

### Processamento em Lote

Use o script PowerShell `md_to_fbx.ps1` para processar múltiplos arquivos:

#### Uso Básico

```powershell
# Processar todos os arquivos na pasta padrão (mao)
.\md_to_fbx.ps1

# Especificar pasta raiz customizada
.\md_to_fbx.ps1 -RootPath "C:\caminho\para\arquivos"

# Usar versão OCR (mais confiável)
.\md_to_fbx.ps1 -UseOCR

# Combinar parâmetros
.\md_to_fbx.ps1 -RootPath "mao\01-05" -UseOCR

# Processar apenas uma subpasta específica
.\md_to_fbx.ps1 -RootPath "mao\10-04"
```

#### Parâmetros

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `-RootPath` | String | `"mao"` | Diretório raiz onde buscar arquivos `.md` recursivamente |
| `-UseOCR` | Switch | `$false` | Usar `mhand_to_fbx_ocr.py` (OCR) ao invés de `mhand_to_fbx.py` |

#### Saída do Script

O script mostra um relatório completo:

```
================================================
  mHand MD to FBX Batch Converter
================================================
Root Path: mao
Script: mhand_to_fbx_ocr.py

Found 15 .md file(s)

Processing: Abastar.md
  Path: C:\...\mao\01-05\Abastar.md
  ✓ Success

Processing: Acordar.md
  Path: C:\...\mao\10-04\Acordar.md
  ✓ Success

================================================
  Batch Conversion Complete
================================================
Total: 15 | Success: 15 | Failed: 0

All conversions completed successfully! ✓
```

---

## ⚙️ Configuração

### Editar Configurações

Abrir `mhand_to_fbx_ocr.py` e editar o dicionário `CFG` (linhas ~45-53):

```python
CFG = {
    # Caminho para o executável do mHandStudio
    "mhand_exe": r"C:\Users\Locatech\Downloads\mHandStudio\mHandStudio\mHandStudio.exe",
    
    # Pasta de saída (None = mesma pasta do arquivo .md)
    "output_dir": None,
    
    # Timeout para o mHandStudio abrir (segundos)
    "startup_timeout": 30,
    
    # Delay entre ações de UI (segundos)
    "ui_delay": 0.8,
    
    # Título da janela do mHandStudio
    "window_title": "mHandStudio",
    
    # Fechar instâncias existentes antes de abrir nova
    "force_restart": True,
    
    # Formato FBX (binary ou ascii)
    "fbx_format": "binary",
    
    # Habilitar OCR
    "use_ocr": True,
}
```

### Configurar Caminho do Tesseract (se necessário)

Se o Tesseract foi instalado em local diferente do padrão, editar `ocr_ui_helper.py` (linha ~20):

```python
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Alterar para o caminho correto onde o Tesseract foi instalado.

---

## 🔧 Como Funciona

O script executa automaticamente os seguintes passos:

### 1️⃣ Lançar mHandStudio
- Fecha instâncias existentes do mHandStudio (se `force_restart: True`)
- Abre nova instância do mHandStudio
- Aguarda interface carregar completamente

### 2️⃣ Gerenciar Diálogo de Auto Update
- Detecta se aparece diálogo "Auto Update" / "Update Now"
- Se detectado: clica em "Cancel" para fechar
- Verifica se menu "Edit" está visível

### 3️⃣ Entrar em Modo de Edição
- Localiza e clica no menu "Edit" usando OCR
- Aguarda modo de edição ativar

### 4️⃣ Adicionar Arquivo
- Localiza e clica no botão "+" usando OCR
- Abre seletor de arquivos do Windows
- Digita caminho completo do arquivo `.md`
- Confirma seleção

### 5️⃣ Carregar Arquivo no Timeline
- Localiza o arquivo na lista usando OCR (busca pelo nome)
- Executa duplo-clique no arquivo
- Aguarda carregar no timeline

### 6️⃣ Exportar para FBX
- Localiza e clica no botão Export (ícone inferior direito)
- Abre diálogo "DataExport"
- Preenche campos:
  - **File Name:** nome do arquivo (sem extensão)
  - **Export As:** seleciona "FBX binary" no dropdown
  - **Rotation Order:** mantém padrão (YXZ)
- Clica em "Confirm"

### 7️⃣ Finalizar
- Aguarda exportação completar
- Verifica se arquivo `.fbx` foi criado
- Move de `MotionFiles/` para pasta de saída (se necessário)
- Confirma sucesso ou reporta erro

---

## 📸 Debug Automático

Durante a execução, screenshots são salvos automaticamente em:

```
mao/01-05/_ocr_debug/
```

Exemplos de screenshots salvos:
- `00_initial.png` - Interface inicial do mHandStudio
- `00a_check_update.png` - Verificação de diálogo de update
- `01_search_menu_Edit.png` - Busca pelo menu Edit
- `02_search_plus.png` - Busca pelo botão +
- `04_search_Abastar.png` - Busca pelo arquivo na lista
- `05_search_FBX_binary.png` - Busca pela opção FBX binary
- `06_format_selected.png` - Formato selecionado
- `07_format_verified.png` - Verificação final

Use estes screenshots para diagnosticar problemas!

---

## 🐛 Troubleshooting

### ❌ Erro: "Tesseract not found"

**Causa:** Tesseract não está instalado ou não está no PATH

**Solução:**
```powershell
# Testar se Tesseract está acessível
tesseract --version
```

Se não funcionar:
1. Reinstalar Tesseract e marcar "Add to PATH"
2. OU configurar caminho manualmente em `ocr_ui_helper.py`:
   ```python
   TESSERACT_PATH = r"C:\Seu\Caminho\tesseract.exe"
   ```

---

### ❌ Erro: "Could not find Edit menu"

**Causas possíveis:**
- Interface do mHandStudio não carregou completamente
- Diálogo de update bloqueando a tela
- OCR não conseguiu ler o texto

**Soluções:**
1. Aumentar `startup_timeout` em CFG (padrão: 30s)
2. Verificar screenshots em `_ocr_debug/` para ver o que OCR viu
3. Verificar se idioma do mHandStudio é inglês

---

### ❌ Erro: "FBX file not found after export"

**Causas possíveis:**
- Exportação falhou
- Arquivo salvo em local diferente
- Sem permissão de escrita

**Soluções:**
1. Verificar pasta `MotionFiles/` no diretório do script
2. Verificar permissões de escrita
3. Verificar espaço em disco
4. Checar screenshots de debug para ver se diálogo foi preenchido corretamente

---

### ❌ Diálogo de Auto Update Não Fecha

**Solução:** O script tem dupla proteção para isso:
- Detecção ao abrir app
- Verificação antes de iniciar workflow

Se ainda aparecer, verificar logs do console para ver quais palavras foram detectadas.

---

### ❌ Erro: "ModuleNotFoundError: No module named 'cv2'"

**Causa:** OpenCV não está instalado

**Solução:**
```powershell
pip install opencv-python
```

---

### ❌ OCR Não Detecta Texto na Tela

**Soluções:**
1. Verificar idioma do Tesseract instalado (deve ter 'eng')
2. Verificar resolução/qualidade da tela
3. Aumentar tempo de espera entre ações (`ui_delay` em CFG)
4. Reduzir `confidence_threshold` no código (padrão: 0.4-0.5)

---

### ❌ Script Clica no Lugar Errado

**Causa:** OCR detectou texto mas calculou posição incorreta

**Solução:**
1. Verificar screenshots de debug
2. Ajustar offsets de clique no código
3. Verificar se há múltiplos elementos com mesmo texto

---

## 📁 Estrutura do Projeto

```
mHandStudio_fbx_conversion/
├── mhand_to_fbx_ocr.py      # Script principal
├── ocr_ui_helper.py         # Módulo de funções OCR
├── md_to_fbx.ps1            # Script PowerShell para lote
├── requirements.txt         # Dependências Python
├── README.md                # Este arquivo
├── mao/                     # Pasta de arquivos .md (entrada)
│   └── 01-05/
│       ├── Abastar.md
│       └── _ocr_debug/      # Screenshots de debug
├── fbx/                     # Pasta de arquivos .fbx (saída)
└── MotionFiles/            # Pasta temporária do mHandStudio
```

---

## 📝 Checklist de Setup Completo

Antes de executar o script, verificar:

- [ ] Python 3.7+ instalado e no PATH
- [ ] Tesseract OCR instalado e no PATH
- [ ] Todas as dependências Python instaladas (`pip install -r requirements.txt`)
- [ ] mHandStudio instalado e caminho configurado no script
- [ ] Arquivos `.md` na pasta `mao/`
- [ ] Testes executados com sucesso:
  ```powershell
  python --version
  tesseract --version
  python -c "import pyautogui, cv2, pytesseract; print('OK')"
  ```

---

## 🎯 Exemplo Completo de Uso

```powershell
# 1. Navegar para pasta do projeto
cd C:\Users\Locatech\automacao_mhand\mHandStudio_fbx_conversion

# 2. Converter um arquivo
python mhand_to_fbx_ocr.py --input "mao\01-05\Abastar.md"

# 3. Verificar saída
# Arquivo FBX criado em: mao\01-05\Abastar.fbx

# 4. Verificar logs de debug
dir mao\01-05\_ocr_debug
```

---

**Última atualização:** Maio 2026  
**Versão:** 2.0
